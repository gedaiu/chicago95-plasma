import QtQuick
import org.kde.ksvg as KSvg
import org.kde.kirigami as Kirigami

// A Windows 7 superbar button: the program's icon on TaskBand2's glass, lighter while its window has the focus,
// lit in the icon's colour under the pointer. A program's combined windows stack at its right: one card for two windows,
// two for three or more (widgets/taskgroup), the face 8 pixels narrower for them.
Item {
    id: task
    property string text
    property var icon
    property bool hovered: pointer.hovered
    property bool pressed // the window is the active one
    property int windows: 1 // the windows combined into this button

    readonly property int stackWidth: windows > 1 ? 8 : 0
    property string bevel: "1995"
    property string look: "1995"

    readonly property int iconSize: 32

    HoverHandler {
        id: pointer
    }

    KSvg.FrameSvgItem {
        anchors.fill: parent
        anchors.rightMargin: task.stackWidth
        imagePath: "widgets/tasks"
        prefix: (task.pressed ? "focus" : "") + (task.pressed && task.hovered ? "-" : "") + (task.hovered ? "hover" : "") || "normal"
    }
    KSvg.FrameSvgItem {
        visible: task.windows > 1
        x: parent.width - task.stackWidth
        width: task.stackWidth
        height: parent.height
        imagePath: "widgets/taskgroup"
        prefix: (task.pressed ? "group-selected-" : "group-") + (task.windows > 2 ? "3" : "2")
    }
    Kirigami.ImageColors {
        id: iconColours
        source: task.icon
    }
    HoverGlow {
        anchors.fill: parent
        visible: task.hovered
        tint: iconColours.dominant
        pointerX: pointer.point.position.x
    }
    Kirigami.Icon {
        anchors.centerIn: parent
        width: task.iconSize
        height: task.iconSize
        source: task.icon
        roundToIconSize: false
    }
}
