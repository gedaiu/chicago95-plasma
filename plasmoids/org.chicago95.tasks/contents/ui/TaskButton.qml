import QtQuick
import org.kde.ksvg as KSvg
import org.kde.kirigami as Kirigami

// One task button as the originals draw it (tests/test_plasma_taskbar_reference.py): the Plasma
// style's task frame ("normal" raised, "focus" sunken with the checkerboard), 22px tall at the bottom
// of its applet; the window's icon 16px at 4,3 and its title from 23px (22px on 2000, where Tahoma has no blank
// column before its capitals), both a pixel lower while pressed (not further right); the active window's title bold.
Item {
    id: task
    property alias text: label.text
    property var icon
    property bool pressed
    property string look: "1995"
    property color textColor: Kirigami.Theme.textColor

    readonly property int buttonHeight: 22
    readonly property int iconLeft: 4
    readonly property int iconTop: 3
    readonly property int labelLeft: look === "2000" ? 22 : 23
    readonly property int labelTop: 6
    readonly property int labelRight: 4
    readonly property int shift: pressed ? 1 : 0

    KSvg.FrameSvgItem {
        imagePath: "widgets/tasks"
        prefix: task.pressed ? "focus" : "normal"
        y: task.height - task.buttonHeight
        width: task.width
        height: task.buttonHeight

        Kirigami.Icon {
            x: task.iconLeft
            y: task.iconTop + task.shift
            width: 16
            height: 16
            source: task.icon
            roundToIconSize: false
        }
        Text {
            id: label
            x: task.labelLeft
            y: task.labelTop + task.shift
            width: Math.max(0, parent.width - x - task.labelRight)
            font.family: "MS W98 UI"
            font.pixelSize: 11
            font.bold: task.pressed
            color: task.textColor
            elide: Text.ElideRight
            // A pixel font: drawn without smoothing, like the original's text.
            renderType: Text.NativeRendering
            antialiasing: false
        }
    }
}
