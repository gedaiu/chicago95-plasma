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

    readonly property string menuCommand: "systemd-run --user --quiet --collect @HOME@/.local/bin/chicago95-startmenu"

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
    readonly property string controlPanelCommand: "systemd-run --user --quiet --collect @HOME@/.local/bin/chicago95-control-panel --page taskbar"
    readonly property string buttonText: Plasmoid.configuration.buttonText
    readonly property string logo: Plasmoid.configuration.logo
    readonly property url logoSource: logo === "flag" ? Qt.resolvedUrl("../images/logo-flag-16.png") : logo === "xp" ? Qt.resolvedUrl("../images/logo-xp-16.png") : logo === "penguin" ? Qt.resolvedUrl("../images/logo-penguin.svg") : logo !== "" ? "file://" + logo : ""

    // Colours from the colour scheme (System Settings > Colors); the bevel follows the look (Setup
    // writes it): 2000's light line is the face itself and its shadows are #808080 and #404040.
    Kirigami.Theme.colorSet: Kirigami.Theme.Button
    Kirigami.Theme.inherit: false

    // Plasma's panel starts its first applet 3px in; the originals' Start button is 2px from the
    // screen's edge, so the button reaches a pixel left of the applet (tests/test_plasma_taskbar_reference.py).
    readonly property bool isLuna: Plasmoid.configuration.taskbarStyle === "luna"
    readonly property int panelMarginOverlap: isLuna ? 4 : 1
    readonly property int buttonWidth: button.item ? button.item.implicitWidth : 0
    readonly property int gapAfterButton: Plasmoid.configuration.look === "2001" ? 1 : 0
    readonly property int appletWidth: buttonWidth - (isLuna ? 0 : panelMarginOverlap) + gapAfterButton
    Layout.minimumWidth: appletWidth
    Layout.preferredWidth: appletWidth
    Layout.maximumWidth: appletWidth
    Layout.fillHeight: true

    // Programs start as their own transient systemd service: Setup restarts plasmashell, and as it stops
    // its QProcesses kill the programs they started (tests/test_plasmoid_launches.py).
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

    Loader {
        id: button
        x: -root.panelMarginOverlap
        width: root.buttonWidth
        height: parent.height
        source: Qt.resolvedUrl(root.isLuna ? "luna/StartButton.qml" : "StartButton.qml")
    }
    Binding {
        target: button.item
        property: "text"
        value: root.buttonText
    }
    Binding {
        target: button.item
        property: "logoSource"
        value: root.logoSource
    }
    Binding {
        target: button.item
        property: "customLogo"
        when: root.isLuna
        value: ["", "flag", "xp"].indexOf(root.logo) < 0
    }
    Binding {
        target: button.item
        property: "held"
        value: clickArea.pressed && clickArea.containsMouse
    }
    Binding {
        target: button.item
        property: "look"
        when: !root.isLuna
        value: Plasmoid.configuration.look
    }
    Binding {
        target: button.item
        property: "bevel"
        value: Plasmoid.configuration.bevel
    }
    Binding {
        target: button.item
        property: "face"
        value: Kirigami.Theme.backgroundColor
    }
    Binding {
        target: button.item
        property: "textColor"
        value: Kirigami.Theme.textColor
    }

    MouseArea {
        id: clickArea
        anchors.fill: button
        onClicked: root.toggleMenu()
    }
}
