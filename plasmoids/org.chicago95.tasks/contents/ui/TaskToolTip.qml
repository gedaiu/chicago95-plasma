import QtQuick
import org.kde.pipewire as PipeWire
import org.kde.taskmanager as TaskManager

// A task button's tooltip (tests/test_task_tooltip.py). Without previews: the window's title in black on the classic
// pale yellow, 3px in from a 1px black border. With a preview size: a raised grey panel in the look's bevel, the
// title along its top and a live picture of the window (4:3, through the same screencast as Plasma's own task
// manager uses) in a 1px sunken frame under it, as Windows 7 laid its previews out.
Item {
    id: tip

    property string title
    property var windowId
    property int previewSize: 0
    property string bevel: "1995"
    property color face: "#C0C0C0"

    readonly property bool previews: previewSize > 0
    readonly property int padding: previews ? 6 : 3
    readonly property int frame: previews ? 2 : 1
    readonly property int previewHeight: Math.round(previewSize * 3 / 4)
    readonly property int titleGap: 4
    readonly property color light: bevel === "2000" ? face : Qt.lighter(face, 1.16)
    readonly property color shadow: "#808080"
    readonly property color dark: bevel === "2000" ? "#404040" : "#000000"

    implicitWidth: 2 * (frame + padding) + Math.max(label.implicitWidth, previews ? previewSize + 2 : 0)
    implicitHeight: 2 * (frame + padding) + label.implicitHeight + (previews ? titleGap + previewHeight + 2 : 0)
    width: implicitWidth
    height: implicitHeight

    // The yellow tooltip's box.
    Rectangle {
        anchors.fill: parent
        visible: !tip.previews
        color: "#FFFFE1"
        border.width: 1
        border.color: "#000000"
    }
    // The preview panel: the face in a raised 2px frame.
    Item {
        anchors.fill: parent
        visible: tip.previews
        Rectangle { anchors.fill: parent; color: tip.face }
        Rectangle { x: 0; y: 0; width: parent.width - 1; height: 1; color: tip.light }
        Rectangle { x: 0; y: 0; width: 1; height: parent.height - 1; color: tip.light }
        Rectangle { x: 1; y: 1; width: parent.width - 3; height: 1; color: "#FFFFFF" }
        Rectangle { x: 1; y: 1; width: 1; height: parent.height - 3; color: "#FFFFFF" }
        Rectangle { x: 0; y: parent.height - 1; width: parent.width; height: 1; color: tip.dark }
        Rectangle { x: parent.width - 1; y: 0; width: 1; height: parent.height; color: tip.dark }
        Rectangle { x: 1; y: parent.height - 2; width: parent.width - 2; height: 1; color: tip.shadow }
        Rectangle { x: parent.width - 2; y: 1; width: 1; height: parent.height - 2; color: tip.shadow }
    }
    Text {
        id: label
        x: tip.frame + tip.padding
        y: tip.frame + tip.padding
        text: tip.title
        font.family: "MS W98 UI"
        font.pixelSize: 11
        color: "#000000"
        renderType: Text.NativeRendering
        antialiasing: false
    }
    Item {
        id: preview
        visible: tip.previews
        x: tip.frame + tip.padding
        y: label.y + label.implicitHeight + tip.titleGap
        width: tip.previewSize + 2
        height: tip.previewHeight + 2
        // Sunken 1px frame: shadow above and left, white below and right.
        Rectangle { x: 0; y: 0; width: parent.width; height: 1; color: tip.shadow }
        Rectangle { x: 0; y: 0; width: 1; height: parent.height; color: tip.shadow }
        Rectangle { x: 0; y: parent.height - 1; width: parent.width; height: 1; color: "#FFFFFF" }
        Rectangle { x: parent.width - 1; y: 0; width: 1; height: parent.height; color: "#FFFFFF" }
        // The stream starts only once the tooltip is on screen: a screencast item without a window gives up
        // ("Window not available"), and the tooltip's content exists long before it is shown.
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
