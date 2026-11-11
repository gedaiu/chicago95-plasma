import QtQuick
import "dragSort.js" as DragSort

// The mouse area of one item in a row sorted by dragging: past the start-drag distance the item follows the
// pointer under a closed hand (dragX, clamped to its section), moved(from, to) fires each time its centre
// crosses into another slot, dropped() when it is let go, and tapped(button) for a click that was no drag.
MouseArea {
    id: area

    property Item layoutParent: parent.parent
    property int origin
    property int pitch
    property int count
    property int slot
    property int itemWidth
    property int threshold: Qt.styleHints.startDragDistance
    readonly property bool dragging: state.dragging
    readonly property int dragX: state.dragX
    // Off before the first jump to the pointer, on again before the drop, so only the snap back animates.
    readonly property bool slides: state.slides
    readonly property point pointer: state.pointer

    signal moved(int fromSlot, int toSlot)
    signal dropped(real pointerX, real pointerY)
    signal tapped(int button)

    hoverEnabled: true
    acceptedButtons: Qt.LeftButton | Qt.RightButton
    preventStealing: true
    cursorShape: dragging ? Qt.ClosedHandCursor : Qt.ArrowCursor

    QtObject {
        id: state
        property bool dragging: false
        property bool slides: true
        property bool dragged: false
        property int dragX: 0
        property point pointer
        property point pressPoint
        property real grabOffset
    }

    onPressed: mouse => {
        state.pressPoint = Qt.point(mouse.x, mouse.y);
        state.grabOffset = mouse.x;
    }
    onPositionChanged: mouse => {
        if (!(pressedButtons & Qt.LeftButton))
            return;
        if (!state.dragging && !DragSort.startsDrag(state.pressPoint.x, state.pressPoint.y, mouse.x, mouse.y, threshold))
            return;
        state.pointer = mapToItem(layoutParent, mouse.x, mouse.y);
        state.dragX = DragSort.draggedX(state.pointer.x, state.grabOffset, origin, DragSort.lastX(origin, pitch, count));
        if (!state.dragging) {
            state.slides = false;
            state.dragging = true;
        }
        const to = DragSort.slotAt(state.dragX + itemWidth / 2, origin, pitch, count);
        if (to !== slot)
            moved(slot, to);
    }
    onReleased: {
        if (!state.dragging)
            return;
        state.dragged = true;
        state.slides = true;
        state.dragging = false;
        dropped(state.pointer.x, state.pointer.y);
    }
    onClicked: mouse => {
        if (state.dragged) {
            state.dragged = false;
            return;
        }
        tapped(mouse.button);
    }
}
