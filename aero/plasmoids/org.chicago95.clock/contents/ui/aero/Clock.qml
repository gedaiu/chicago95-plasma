import QtQuick
import org.kde.kwindowsystem
import org.kde.plasma.core as PlasmaCore
import org.kde.ksvg as KSvg
import "../clockFormat.js" as ClockFormat

// Windows 7's notification-area clock: the time over the date in white, then the Show desktop strip at the
// screen's edge (win7screenres.png: the lines centred in x 944..1008, the strip at 1009..1023).
Item {
    id: clock
    property date now: new Date()
    property string hourFormat: ""
    signal openSettings
    function toggleCalendar() {
        if (!popup.visible) calendar.month = new Date(now.getFullYear(), now.getMonth(), 1);
        popup.visible = !popup.visible;
    }
    PlasmaCore.Dialog {
        id: popup
        visualParent: clock
        location: PlasmaCore.Types.BottomEdge
        flags: Qt.Popup
        hideOnWindowDeactivate: true
        visible: false
        mainItem: CalendarFlyout {
            id: calendar
            width: implicitWidth
            height: implicitHeight
            now: clock.now
            onSettingsRequested: { popup.visible = false; clock.openSettings(); }
        }
    }

    readonly property int stripWidth: 15
    readonly property int textWidth: width - stripWidth

    // Keep the reference clock cell while both lines fit. Wider locale formats expand it.
    implicitWidth: stripWidth + Math.max(65, Math.ceil(Math.max(timeLine.implicitWidth, dateLine.implicitWidth)))

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
            property bool peeking: false
            Timer {
                interval: 500
                id: peekDelay
                onTriggered: {
                    if (!KWindowSystem.showingDesktop) {
                        strip.peeking = true;
                        KWindowSystem.showingDesktop = true;
                    }
                }
            }
            function releasePeek() {
                if (peeking) {
                    peeking = false;
                    KWindowSystem.showingDesktop = false;
                }
            }
            onEntered: peekDelay.restart()
            onPressed: peekDelay.stop()
            onExited: { peekDelay.stop(); releasePeek(); }
            Component.onDestruction: releasePeek()
            onClicked: {
                if (!peeking) KWindowSystem.showingDesktop = !KWindowSystem.showingDesktop;
                peeking = false;
            }
        }
    }
}
