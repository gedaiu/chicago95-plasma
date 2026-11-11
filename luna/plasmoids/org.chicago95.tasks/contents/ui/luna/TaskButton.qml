import QtQuick
import org.kde.ksvg as KSvg
import org.kde.kirigami as Kirigami

Item {
    id: task
    property alias text: label.text
    property var icon
    property bool pressed
    property string bevel: "1995"
    property color textColor: "#ffffff"

    readonly property int buttonHeight: 25
    readonly property int labelLeft: 29
    readonly property int buttonTop: 3
    readonly property int iconLeft: 6
    readonly property int iconTop: 4

    HoverHandler {
        id: pointer
    }

    KSvg.FrameSvgItem {
        id: pill
        imagePath: "widgets/tasks"
        prefix: task.pressed ? "focus" : pointer.hovered ? "hover" : "normal"
        y: task.buttonTop
        width: task.width
        height: task.buttonHeight

        Kirigami.Icon {
            x: task.iconLeft
            y: task.iconTop
            width: 16
            height: 16
            source: task.icon
            roundToIconSize: false
        }
        Text {
            id: label
            x: task.labelLeft
            y: pill.margins.top
            width: Math.max(0, parent.width - task.labelLeft - pill.margins.right)
            height: parent.height - pill.margins.top - pill.margins.bottom
            verticalAlignment: Text.AlignVCenter
            font.family: "Tahoma"
            font.pixelSize: 11
            color: task.textColor
            elide: Text.ElideRight
            renderType: Text.QtRendering
            antialiasing: true
        }
    }
}
