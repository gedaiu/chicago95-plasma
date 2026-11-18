import QtQuick
import QtQuick.Window
import org.kde.ksvg as KSvg

// Windows 7's notification area has no box: its icons sit on the superbar's glass, which Explorer darkens from before
// the icons to the Show desktop strip and lightens behind it (widgets/trayshade, fitted to win7screenres.png).
Item {
    id: box
    property string bevel: "1995"

    // Where the panel window's right edge lies in this item's coordinates; the panel moves applets as they resize.
    property real screenRight: width
    function measure() {
        if (box.Window.window)
            box.screenRight = box.mapFromItem(null, box.Window.window.width, 0).x;
    }
    Timer {
        interval: 500
        running: true
        repeat: true
        triggeredOnStart: true
        onTriggered: box.measure()
    }
    Connections {
        target: box.Window.window
        function onWidthChanged() {
            box.measure();
        }
    }

    KSvg.SvgItem {
        imagePath: "widgets/trayshade"
        width: implicitWidth
        height: implicitHeight
        x: box.screenRight - width
        y: 2 // below the bar's top line and highlight (palette.START_SHADE_TOP)
    }
}
