import QtQuick
import org.kde.ksvg as KSvg

// Windows 7's "show hidden icons" button (TrayNotifyHoriz::Button, widgets/trayarrow): a white triangle on the glass,
// a glass face under the pointer and while held, pointing down while the hidden icons' popup is open.
KSvg.SvgItem {
    id: chevron
    objectName: "aeroChevron"
    property bool open

    width: 21
    height: 20
    imagePath: "widgets/trayarrow"
    elementId: (open ? "open-" : "") + (press.pressed ? "pressed" : pointer.hovered ? "hot" : "normal")

    HoverHandler {
        id: pointer
    }
    TapHandler {
        id: press
    }
}
