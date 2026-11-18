import QtQuick
import org.kde.ksvg as KSvg
import org.kde.kirigami as Kirigami

// A program pinned to the superbar: its icon alone, glowing under the pointer and while held.
Item {
    id: cell
    property var icon
    property bool hovered
    property bool held

    readonly property int iconSize: 32

    KSvg.FrameSvgItem {
        anchors.fill: parent
        imagePath: "widgets/tasks"
        prefix: cell.held ? "launcher-pressed" : cell.hovered ? "launcher-hover" : "launcher"
    }
    Kirigami.Icon {
        anchors.centerIn: parent
        width: cell.iconSize
        height: cell.iconSize
        source: cell.icon
        roundToIconSize: false
    }
}
