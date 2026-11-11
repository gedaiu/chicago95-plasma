import QtQuick
import org.kde.pipewire as PipeWire
import org.kde.taskmanager as TaskManager

// A task button's tooltip (tests/test_task_tooltip.py): the window's title in black on the classic pale yellow,
// 3px in from a 1px black border; with a preview size, a live picture of the window (4:3, through the same
// screencast as Plasma's own task manager uses) in a 1px sunken frame above the title.
Item {
    id: tip

    property string title
    property var windowId
    property int previewSize: 0

    readonly property int padding: 3
    readonly property int previewHeight: Math.round(previewSize * 3 / 4)
    readonly property int previewGap: previewSize > 0 ? 4 : 0

    implicitWidth: 2 + 2 * padding + Math.max(label.implicitWidth, previewSize > 0 ? previewSize + 2 : 0)
    implicitHeight: 2 + 2 * padding + (previewSize > 0 ? previewHeight + 2 + previewGap : 0) + label.implicitHeight
    width: implicitWidth
    height: implicitHeight

    Rectangle {
        anchors.fill: parent
        color: "#FFFFE1"
        border.width: 1
        border.color: "#000000"
    }
    Item {
        id: preview
        visible: tip.previewSize > 0
        x: 1 + tip.padding
        y: 1 + tip.padding
        width: tip.previewSize + 2
        height: tip.previewHeight + 2
        // Sunken 1px frame: shadow above and left, white below and right.
        Rectangle { x: 0; y: 0; width: parent.width; height: 1; color: "#808080" }
        Rectangle { x: 0; y: 0; width: 1; height: parent.height; color: "#808080" }
        Rectangle { x: 0; y: parent.height - 1; width: parent.width; height: 1; color: "#FFFFFF" }
        Rectangle { x: parent.width - 1; y: 0; width: 1; height: parent.height; color: "#FFFFFF" }
        PipeWire.PipeWireSourceItem {
            anchors.fill: parent
            anchors.margins: 1
            visible: tip.previewSize > 0 && tip.windowId !== null
            nodeId: screencast.nodeId
            TaskManager.ScreencastingRequest {
                id: screencast
                uuid: tip.previewSize > 0 && tip.windowId !== null ? tip.windowId : ""
            }
        }
    }
    Text {
        id: label
        x: 1 + tip.padding
        y: 1 + tip.padding + (tip.previewSize > 0 ? tip.previewHeight + 2 + tip.previewGap : 0)
        text: tip.title
        font.family: "MS W98 UI"
        font.pixelSize: 11
        color: "#000000"
        renderType: Text.NativeRendering
        antialiasing: false
    }
}
