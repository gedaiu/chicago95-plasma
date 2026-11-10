import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.plasma5support as Plasma5Support
import org.kde.kirigami as Kirigami

// Start button drawn from its settings (text and logo, chosen in Setup or in Configure),
// with the classic two-pixel raised bevel that presses in while held.
PlasmoidItem {
    id: root

    preferredRepresentation: fullRepresentation
    Plasmoid.backgroundHints: PlasmaCore.Types.NoBackground

    readonly property string menuCommand: "@HOME@/.local/bin/chicago95-startmenu"
    readonly property string buttonText: Plasmoid.configuration.buttonText
    readonly property string logo: Plasmoid.configuration.logo
    readonly property url logoSource: logo === "flag" ? Qt.resolvedUrl("../images/logo-flag.png")
                                    : logo === "penguin" ? Qt.resolvedUrl("../images/logo-penguin.svg")
                                    : logo !== "" ? "file://" + logo : ""
    readonly property bool held: clickArea.pressed && clickArea.containsMouse

    // Colours from the colour scheme (System Settings > Colors); light and shadow derive from the face
    // the way #DFDFDF and #808080 derive from #C0C0C0.
    Kirigami.Theme.colorSet: Kirigami.Theme.Button
    Kirigami.Theme.inherit: false
    readonly property color face: Kirigami.Theme.backgroundColor
    readonly property color light: Qt.tint(face, "#80ffffff")  // halfway to white
    readonly property color shadow: Qt.darker(face, 1.5)  // two thirds of the face

    readonly property int topInset: 2
    // 98's button: 2px bevel, 2px gap, logo, 3px gap, text, 4px; 54x22 with "Start".
    readonly property int padding: 2
    // The logo fills the face inside the 2px bevel with 2px to spare on each side.
    readonly property int logoSize: Math.max(12, height - topInset - 8)

    Layout.minimumWidth: 2 + padding + content.implicitWidth + 4 + 2
    Layout.preferredWidth: Layout.minimumWidth
    Layout.maximumWidth: Layout.minimumWidth
    Layout.fillHeight: true

    Plasma5Support.DataSource {
        id: runner
        engine: "executable"
        connectedSources: []
        onNewData: (sourceName, data) => disconnectSource(sourceName)
    }

    function toggleMenu() {
        runner.connectSource(root.menuCommand)
    }

    Connections {
        target: Plasmoid
        function onActivated() { root.toggleMenu() }
    }

    Item {
        id: buttonFace  // not "face": that name is the colour property above
        anchors.fill: parent
        anchors.topMargin: root.topInset

        Rectangle { anchors.fill: parent; color: root.face }
        // Outer ring: white/black raised, black/white held; inner ring: light/shadow raised, shadow/light held.
        Rectangle { x: 0; y: 0; width: parent.width - 1; height: 1; color: root.held ? "#000000" : "#ffffff" }
        Rectangle { x: 0; y: 0; width: 1; height: parent.height - 1; color: root.held ? "#000000" : "#ffffff" }
        Rectangle { x: 0; y: parent.height - 1; width: parent.width; height: 1; color: root.held ? "#ffffff" : "#000000" }
        Rectangle { x: parent.width - 1; y: 0; width: 1; height: parent.height; color: root.held ? "#ffffff" : "#000000" }
        Rectangle { x: 1; y: 1; width: parent.width - 3; height: 1; color: root.held ? root.shadow : root.light }
        Rectangle { x: 1; y: 1; width: 1; height: parent.height - 3; color: root.held ? root.shadow : root.light }
        Rectangle { x: 1; y: parent.height - 2; width: parent.width - 2; height: 1; color: root.held ? root.light : root.shadow }
        Rectangle { x: parent.width - 2; y: 1; width: 1; height: parent.height - 2; color: root.held ? root.light : root.shadow }

        RowLayout {
            id: content
            spacing: 3
            anchors.verticalCenter: parent.verticalCenter
            anchors.verticalCenterOffset: root.held ? 1 : 0
            x: 2 + root.padding + (root.held ? 1 : 0)

            Image {
                visible: root.logoSource != ""
                source: root.logoSource
                Layout.preferredWidth: root.logoSize
                Layout.preferredHeight: root.logoSize
                sourceSize.width: root.logoSize * 2
                sourceSize.height: root.logoSize * 2
                fillMode: Image.PreserveAspectFit
                // The flag is pixel art: whole-pixel scaling keeps it sharp. Vector logos are drawn smooth.
                smooth: !String(root.logoSource).endsWith("logo-flag.png")
                cache: false  // the logo file can be replaced by the user; always read the current one
            }
            Text {
                visible: root.buttonText !== ""
                text: root.buttonText
                font.family: "MS W98 UI"
                font.bold: true
                font.pixelSize: 11
                color: Kirigami.Theme.textColor
                // Plasma's native text gets RGB subpixel fringes; curve rendering draws plain grey edges.
                renderType: Text.CurveRendering
            }
        }
    }

    MouseArea {
        id: clickArea
        anchors.fill: parent
        onClicked: root.toggleMenu()
    }
}
