import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.plasma5support as Plasma5Support

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
                                    : logo === "penguin" ? Qt.resolvedUrl("../images/logo-penguin.png")
                                    : logo !== "" ? "file://" + logo : ""
    readonly property bool held: clickArea.pressed && clickArea.containsMouse

    readonly property int topInset: 2
    readonly property int padding: 4
    readonly property int logoSize: Math.max(12, height - topInset - 2 * padding - 2)

    Layout.minimumWidth: content.implicitWidth + 2 * padding + 6
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
        id: face
        anchors.fill: parent
        anchors.topMargin: root.topInset

        Rectangle { anchors.fill: parent; color: "#c0c0c0" }
        // Outer ring: white/black raised, black/white held; inner ring: light/shadow raised, shadow/light held.
        Rectangle { x: 0; y: 0; width: parent.width - 1; height: 1; color: root.held ? "#000000" : "#ffffff" }
        Rectangle { x: 0; y: 0; width: 1; height: parent.height - 1; color: root.held ? "#000000" : "#ffffff" }
        Rectangle { x: 0; y: parent.height - 1; width: parent.width; height: 1; color: root.held ? "#ffffff" : "#000000" }
        Rectangle { x: parent.width - 1; y: 0; width: 1; height: parent.height; color: root.held ? "#ffffff" : "#000000" }
        Rectangle { x: 1; y: 1; width: parent.width - 3; height: 1; color: root.held ? "#808080" : "#dfdfdf" }
        Rectangle { x: 1; y: 1; width: 1; height: parent.height - 3; color: root.held ? "#808080" : "#dfdfdf" }
        Rectangle { x: 1; y: parent.height - 2; width: parent.width - 2; height: 1; color: root.held ? "#dfdfdf" : "#808080" }
        Rectangle { x: parent.width - 2; y: 1; width: 1; height: parent.height - 2; color: root.held ? "#dfdfdf" : "#808080" }

        RowLayout {
            id: content
            spacing: 3
            anchors.verticalCenter: parent.verticalCenter
            anchors.verticalCenterOffset: root.held ? 1 : 0
            x: root.padding + 2 + (root.held ? 1 : 0)

            Image {
                visible: root.logoSource != ""
                source: root.logoSource
                Layout.preferredWidth: root.logoSize
                Layout.preferredHeight: root.logoSize
                sourceSize.width: root.logoSize * 2
                sourceSize.height: root.logoSize * 2
                fillMode: Image.PreserveAspectFit
                smooth: true
            }
            Text {
                visible: root.buttonText !== ""
                text: root.buttonText
                font.family: "MS W98 UI"
                font.bold: true
                font.pixelSize: 11
                color: "#000000"
            }
        }
    }

    MouseArea {
        id: clickArea
        anchors.fill: parent
        onClicked: root.toggleMenu()
    }
}
