import QtQuick
import org.kde.ksvg as KSvg
import "../clockFormat.js" as ClockFormat

// Windows 7's notification-area clock: the time over the date in white, then the Show desktop strip at the
// screen's edge (win7screenres.png: the lines centred in x 944..1008, the strip at 1009..1023).
Item {
    id: clock
    property date now: new Date()
    property string hourFormat: ""
    signal showDesktop

    readonly property int stripWidth: 15
    readonly property int textWidth: width - stripWidth

    implicitWidth: stripWidth + Math.max(65, Math.ceil(Math.max(timeLine.implicitWidth, dateLine.implicitWidth)) + 6)

    Text {
        id: timeLine
        x: Math.round((clock.textWidth - implicitWidth) / 2)
        y: 4
        text: Qt.formatTime(clock.now, ClockFormat.timeFormat(clock.hourFormat, Qt.locale().timeFormat(Locale.ShortFormat))).replace(/[  ]/g, " ")
        font.family: "Segoe UI"
        font.pixelSize: 12
        color: "#ffffff"
    }
    Text {
        id: dateLine
        x: Math.round((clock.textWidth - implicitWidth) / 2)
        y: 21
        text: Qt.formatDate(clock.now, ClockFormat.fullYearDateFormat(Qt.locale().dateFormat(Locale.ShortFormat)))
        font.family: "Segoe UI"
        font.pixelSize: 12
        color: "#ffffff"
    }

    KSvg.FrameSvgItem {
        x: clock.textWidth
        width: clock.stripWidth
        height: clock.height
        imagePath: "widgets/showdesktop"
        prefix: strip.pressed ? "pressed" : strip.containsMouse ? "hover" : "normal"

        MouseArea {
            id: strip
            anchors.fill: parent
            hoverEnabled: true
            onClicked: clock.showDesktop()
        }
    }
}
