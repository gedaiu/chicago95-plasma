import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.plasma5support as Plasma5Support
import org.kde.kirigami as Kirigami

// The tray's clock as the originals show it (tests/test_plasma_taskbar_reference.py): the time in the
// locale's short format, in the UI font without smoothing, centred in a cell that ends at the tray
// box's inner edge (60px wide; 69px on 2000, whose lettering is wider). The date shows on hover;
// a double click opens the date and time settings.
PlasmoidItem {
    id: root

    preferredRepresentation: fullRepresentation
    Plasmoid.backgroundHints: PlasmaCore.Types.NoBackground

    readonly property int cellWidth: Plasmoid.configuration.look === "2000" ? 69 : 60
    readonly property int textTop: 9   // the lettering's top row in the applet, which starts 2px into the taskbar
    property date now: new Date()

    Layout.minimumWidth: cellWidth
    Layout.preferredWidth: cellWidth
    Layout.maximumWidth: cellWidth
    Layout.fillHeight: true

    toolTipMainText: Qt.formatDate(now, Qt.locale().dateFormat(Locale.LongFormat))

    Timer {
        interval: 1000
        running: true
        repeat: true
        onTriggered: root.now = new Date()
    }

    Plasma5Support.DataSource {
        id: runner
        engine: "executable"
        connectedSources: []
        onNewData: (sourceName, data) => disconnectSource(sourceName)
    }

    Text {
        x: Math.round((root.width - implicitWidth) / 2)
        y: root.textTop
        // Locales put a narrow no-break space before AM and PM; the originals have a full space.
        text: Qt.formatTime(root.now, Qt.locale().timeFormat(Locale.ShortFormat)).replace(/[\u00a0\u202f]/g, " ")
        font.family: "MS W98 UI"
        font.pixelSize: 11
        color: Kirigami.Theme.textColor
        renderType: Text.NativeRendering
        antialiasing: false
    }

    MouseArea {
        anchors.fill: parent
        onDoubleClicked: runner.connectSource("kcmshell6 kcm_clock")
    }
}
