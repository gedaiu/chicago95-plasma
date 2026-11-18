import QtQuick
import org.kde.ksvg as KSvg
import org.kde.kirigami as Kirigami

// A Windows 7 superbar button: the program's icon on TaskBand2's glass, lighter while its window has the focus.
Item {
    id: task
    property string text
    property var icon
    property bool hovered: pointer.hovered
    property bool pressed // the window is the active one
    property string bevel: "1995"
    property string look: "1995"

    readonly property int iconSize: 32

    HoverHandler {
        id: pointer
    }

    KSvg.FrameSvgItem {
        anchors.fill: parent
        imagePath: "widgets/tasks"
        prefix: (task.pressed ? "focus" : "") + (task.pressed && task.hovered ? "-" : "") + (task.hovered ? "hover" : "") || "normal"
    }
    Kirigami.Icon {
        anchors.centerIn: parent
        width: task.iconSize
        height: task.iconSize
        source: task.icon
        roundToIconSize: false
    }
}
