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

    readonly property string menuCommand: "systemd-run --user --scope --quiet --collect @HOME@/.local/bin/chicago95-startmenu"

    Plasmoid.contextualActions: [
        PlasmaCore.Action {
            // qmllint disable unqualified
            // i18n() is injected into the applet context by Plasma.
            text: i18n("Properties")
            // qmllint enable unqualified
            icon.name: "preferences-system"
            onTriggered: runner.connectSource(root.controlPanelCommand)
        }
    ]
    readonly property string controlPanelCommand: "systemd-run --user --scope --quiet --collect @HOME@/.local/bin/chicago95-control-panel --page taskbar"
    readonly property string buttonText: Plasmoid.configuration.buttonText
    readonly property string logo: Plasmoid.configuration.logo
    readonly property url logoSource: logo === "flag" ? Qt.resolvedUrl("../images/logo-flag-16.png") : logo === "penguin" ? Qt.resolvedUrl("../images/logo-penguin.svg") : logo !== "" ? "file://" + logo : ""

    // Colours from the colour scheme (System Settings > Colors); the bevel follows the look (Setup
    // writes it): 2000's light line is the face itself and its shadows are #808080 and #404040.
    Kirigami.Theme.colorSet: Kirigami.Theme.Button
    Kirigami.Theme.inherit: false
    readonly property bool look2000: Plasmoid.configuration.look === "2000"

    // Plasma's panel starts its first applet 3px in; the originals' Start button is 2px from the
    // screen's edge, so the button reaches a pixel left of the applet (tests/test_plasma_taskbar_reference.py).
    readonly property int panelMarginOverlap: 1
    Layout.minimumWidth: button.implicitWidth - panelMarginOverlap
    Layout.preferredWidth: button.implicitWidth - panelMarginOverlap
    Layout.maximumWidth: button.implicitWidth - panelMarginOverlap
    Layout.fillHeight: true

    // Programs start in their own systemd scope: Setup restarts plasmashell, and stopping its service
    // stops every process started inside it (tests/test_plasmoid_launches.py).
    Plasma5Support.DataSource {
        id: runner
        engine: "executable"
        connectedSources: []
        onNewData: (sourceName, data) => disconnectSource(sourceName)
    }

    function toggleMenu() {
        runner.connectSource(root.menuCommand);
    }

    Connections {
        target: Plasmoid
        function onActivated() {
            root.toggleMenu();
        }
    }

    StartButton {
        id: button
        x: -root.panelMarginOverlap
        width: implicitWidth
        height: parent.height
        text: root.buttonText
        logoSource: root.logoSource
        held: clickArea.pressed && clickArea.containsMouse
        look: Plasmoid.configuration.look
        face: Kirigami.Theme.backgroundColor
        light: root.look2000 ? face : Qt.tint(face, "#80ffffff")  // halfway to white
        shadow: root.look2000 ? "#808080" : Qt.darker(face, 1.5)  // two thirds of the face
        dark: root.look2000 ? "#404040" : "#000000"
        textColor: Kirigami.Theme.textColor
    }

    MouseArea {
        id: clickArea
        anchors.fill: button
        onClicked: root.toggleMenu()
    }
}
