import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.plasma5support as Plasma5Support
import org.kde.kirigami as Kirigami
import "clockFormat.js" as ClockFormat

// The tray's clock as the originals show it (tests/test_plasma_taskbar_reference.py): the time in the
// locale's short format, in the UI font without smoothing, centred in a cell that ends at the tray
// box's inner edge (60px wide; 69px on 2000, whose lettering is wider; XP Classic's is 60px again, a row higher). The date shows on hover;
// a double click opens the date and time settings.
PlasmoidItem {
    id: root

    preferredRepresentation: fullRepresentation
    Plasmoid.backgroundHints: PlasmaCore.Types.NoBackground

    readonly property bool isLuna: Plasmoid.configuration.taskbarStyle === "luna"
    readonly property bool isAero: Plasmoid.configuration.taskbarStyle === "aero"  // two lines, then Show desktop
    readonly property bool isXpClassic: Plasmoid.configuration.look === "2001"
    readonly property int cellWidth: isAero ? (aeroClock.face?.implicitWidth || 80) : isLuna ? 68 : Plasmoid.configuration.bevel === "2000" && !isXpClassic ? 69 : 60
    readonly property int textTop: isXpClassic ? 8 : 9   // the lettering's top row in the applet, which starts 2px into the taskbar
    // Windows 7's Show desktop strip ends at the screen's edge: the clock reaches over the panel's last 4px.
    readonly property int panelMarginOverlap: isAero ? 4 : 0
    property date now: new Date()

    Layout.minimumWidth: cellWidth - panelMarginOverlap
    Layout.preferredWidth: cellWidth - panelMarginOverlap
    Layout.maximumWidth: cellWidth - panelMarginOverlap
    Layout.fillHeight: true

    toolTipMainText: Qt.formatDate(now, Qt.locale().dateFormat(Locale.LongFormat))

    Timer {
        interval: 1000
        running: true
        repeat: true
        onTriggered: root.now = new Date()
    }

    // Programs start as their own transient systemd service: Setup restarts plasmashell, and as it stops
    // its QProcesses kill the programs they started (tests/test_plasmoid_launches.py).
    Plasma5Support.DataSource {
        id: runner
        engine: "executable"
        connectedSources: []
        onNewData: (sourceName, data) => disconnectSource(sourceName)
    }

    Loader {
        id: aeroClock
        readonly property var face: item
        width: root.cellWidth
        height: parent.height
        active: root.isAero
        source: Qt.resolvedUrl("aero/Clock.qml")
        onLoaded: face.openSettings.connect(() => runner.connectSource("systemd-run --user --quiet --collect kcmshell6 kcm_clock"))
    }
    Binding {
        target: aeroClock.item
        property: "now"
        value: root.now
    }
    Binding {
        target: aeroClock.item
        property: "hourFormat"
        value: Plasmoid.configuration.hourFormat
    }

    Text {
        id: clockText
        visible: !root.isAero
        x: Math.round((root.width - implicitWidth) / 2)
        y: root.textTop
        // Locales put a narrow no-break space before AM and PM; the originals have a full space.
        text: Qt.formatTime(root.now, ClockFormat.timeFormat(Plasmoid.configuration.hourFormat, Qt.locale().timeFormat(Locale.ShortFormat))).replace(/[\u00a0\u202f]/g, " ")
        font.family: "MS W98 UI"
        font.pixelSize: 11
        color: Kirigami.Theme.textColor
        renderType: Text.NativeRendering
        antialiasing: false
    }
    Binding {
        target: clockText
        property: "font.family"
        value: "Tahoma"
        when: root.isLuna
    }
    Binding {
        target: clockText
        property: "color"
        value: "#ffffff"
        when: root.isLuna
    }
    Binding {
        target: clockText
        property: "renderType"
        value: Text.QtRendering
        when: root.isLuna
    }
    Binding {
        target: clockText
        property: "antialiasing"
        value: true
        when: root.isLuna
    }

    MouseArea {
        width: root.isAero && aeroClock.face ? root.cellWidth - aeroClock.face.stripWidth : root.width
        height: parent.height
        onClicked: if (root.isAero) aeroClock.face?.toggleCalendar()
        onDoubleClicked: if (!root.isAero) runner.connectSource("systemd-run --user --quiet --collect kcmshell6 kcm_clock")
    }
}
