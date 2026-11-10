import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.plasma5support as Plasma5Support
import org.kde.kirigami as Kirigami

// Start button drawn from its settings (text and logo, chosen in Setup or in Configure) by
// StartButton.qml, with the classic two-pixel raised bevel that presses in while held.
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

    // Colours from the colour scheme (System Settings > Colors); the bevel follows the look (Setup
    // writes it): 2000's light line is the face itself and its shadows are #808080 and #404040.
    Kirigami.Theme.colorSet: Kirigami.Theme.Button
    Kirigami.Theme.inherit: false
    readonly property bool look2000: Plasmoid.configuration.look === "2000"

    Layout.minimumWidth: button.implicitWidth
    Layout.preferredWidth: button.implicitWidth
    Layout.maximumWidth: button.implicitWidth
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

    StartButton {
        id: button
        anchors.fill: parent
        text: root.buttonText
        logoSource: root.logoSource
        held: clickArea.pressed && clickArea.containsMouse
        face: Kirigami.Theme.backgroundColor
        light: root.look2000 ? face : Qt.tint(face, "#80ffffff")  // halfway to white
        shadow: root.look2000 ? "#808080" : Qt.darker(face, 1.5)  // two thirds of the face
        dark: root.look2000 ? "#404040" : "#000000"
        textColor: Kirigami.Theme.textColor
    }

    MouseArea {
        id: clickArea
        anchors.fill: parent
        onClicked: root.toggleMenu()
    }
}
