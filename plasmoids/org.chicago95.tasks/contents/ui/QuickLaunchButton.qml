import QtQuick
import org.kde.kirigami as Kirigami

// A Quick Launch cell as the originals draw it (tests/test_plasma_taskbar_reference.py): 23px wide and as
// tall as the buttons, the program's 16px icon 3px in and 3px down; a flat button that rises under the
// mouse and sinks while pressed.
Item {
    id: cell
    property var icon
    property bool hovered
    property bool held
    property color shadow: "#808080"
    property color white: "#ffffff"

    readonly property int cellWidth: 23
    readonly property int cellHeight: 22
    readonly property int iconInset: 3

    implicitWidth: cellWidth
    implicitHeight: cellHeight

    Item {
        y: cell.height - cell.cellHeight
        width: cell.width
        height: cell.cellHeight

        Kirigami.Icon {
            x: cell.iconInset + (cell.held ? 1 : 0)
            y: cell.iconInset + (cell.held ? 1 : 0)
            width: 16
            height: 16
            source: cell.icon
            roundToIconSize: false
        }
        Item {
            anchors.fill: parent
            visible: cell.hovered || cell.held
            Rectangle { width: parent.width; height: 1; color: cell.held ? cell.shadow : cell.white }
            Rectangle { width: 1; height: parent.height; color: cell.held ? cell.shadow : cell.white }
            Rectangle { y: parent.height - 1; width: parent.width; height: 1; color: cell.held ? cell.white : cell.shadow }
            Rectangle { x: parent.width - 1; width: 1; height: parent.height; color: cell.held ? cell.white : cell.shadow }
        }
    }
}
