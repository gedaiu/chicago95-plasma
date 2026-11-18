import QtQuick
import org.kde.ksvg as KSvg
import org.kde.kirigami as Kirigami

// A program pinned to the superbar: its icon alone, lit in its colour under the pointer, darker while held.
Item {
    id: cell
    property var icon
    property bool hovered
    property bool held

    readonly property int iconSize: 32

    HoverHandler {
        id: pointer
    }

    KSvg.FrameSvgItem {
        anchors.fill: parent
        anchors.leftMargin: 1 // a slot is the 62-pixel pitch; its button is 60 wide in the middle
        anchors.rightMargin: 1
        imagePath: "widgets/tasks"
        prefix: cell.held ? "launcher-pressed" : cell.hovered ? "launcher-hover" : "launcher"
    }
    Kirigami.ImageColors {
        id: iconColours
        source: cell.icon
    }
    HoverGlow {
        anchors.fill: parent
        anchors.leftMargin: 1
        anchors.rightMargin: 1
        visible: cell.hovered && !cell.held
        tint: iconColours.dominant
        pointerX: pointer.point.position.x - 1
    }
    Kirigami.Icon {
        anchors.centerIn: parent
        width: cell.iconSize
        height: cell.iconSize
        source: cell.icon
        roundToIconSize: false
    }
}
