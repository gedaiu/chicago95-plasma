import QtQuick
import org.kde.pipewire as PipeWire
import org.kde.taskmanager as TaskManager

// A Luna task button's tooltip (tests/test_task_tooltip.py, tests/luna/test_luna_taskbar.py): the window's title in
// Tahoma on the pale yellow box with its 1px black border, 3px in. With a preview size from the Control Panel, a
// live picture of the window (4:3, the same screencast as Plasma's task manager) in a 1px black frame under the title.
Item {
    id: tip
    property string title
    property var windowId
    property int previewSize: 0
    property string bevel
    property color face

    readonly property bool previews: previewSize > 0
    readonly property int padding: 3
    readonly property int frame: 1
    readonly property int titleGap: 3
    readonly property int previewHeight: Math.round(previewSize * 3 / 4)

    implicitWidth: 2 * (frame + padding) + Math.max(label.implicitWidth, previews ? previewSize + 2 : 0)
    implicitHeight: 2 * (frame + padding) + label.implicitHeight + (previews ? titleGap + previewHeight + 2 : 0)
    width: implicitWidth
    height: implicitHeight

    Rectangle {
        anchors.fill: parent
        color: "#FFFFE1"
        border.width: tip.frame
        border.color: "#000000"
    }
    Text {
        id: label
        x: tip.frame + tip.padding
        y: tip.frame + tip.padding
        text: tip.title
        font.family: "Tahoma"
        font.pixelSize: 11
        color: "#000000"
        renderType: Text.QtRendering
    }
    Rectangle {
        visible: tip.previews
        x: tip.frame + tip.padding
        y: label.y + label.implicitHeight + tip.titleGap
        width: tip.previewSize + 2
        height: tip.previewHeight + 2
        color: "#000000"
        // The stream starts only once the tooltip is on screen: a screencast item without a window gives up.
        Loader {
            anchors.fill: parent
            anchors.margins: 1
            active: tip.previews && tip.windowId !== null && tip.Window.visibility !== Window.Hidden
            sourceComponent: PipeWire.PipeWireSourceItem {
                nodeId: screencast.nodeId
                TaskManager.ScreencastingRequest {
                    id: screencast
                    uuid: tip.windowId
                }
            }
        }
    }
}
