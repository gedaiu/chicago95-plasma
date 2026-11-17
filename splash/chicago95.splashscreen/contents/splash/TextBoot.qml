import QtQuick 2.15

// Optional rehearsal of the text loader, not an emulated BIOS or a boot console.
Rectangle {
    id: root
    color: "black"
    property bool ntLoader: false
    property string systemName: "Windows 95"
    property real progress: 0
    property string consoleText: "Starting " + systemName + "..."
    readonly property real unit: Math.min(width / 640, height / 480)
    Item {
        width: 640 * root.unit
        height: 480 * root.unit
        anchors.centerIn: parent
        clip: true
        Text {
            objectName: "loaderText"
            x: 0
            y: root.ntLoader ? 368 * root.unit : 0
            width: parent.width
            horizontalAlignment: root.ntLoader ? Text.AlignHCenter : Text.AlignLeft
            text: root.ntLoader ? "Starting Windows..." : root.consoleText
            color: "#aaaaaa"
            font.family: "Monospace"
            font.pixelSize: 16 * root.unit
            renderType: Text.NativeRendering
        }
        Row {
            objectName: "loaderProgress"
            visible: root.ntLoader
            y: 384 * root.unit
            spacing: 0
            Repeater {
                model: 72
                Item {
                    required property int index
                    readonly property bool filled: index < Math.floor(root.progress * 72)
                    width: 9 * root.unit
                    height: 16 * root.unit
                    // Full block character (█): fill the entire cell without font-dependent gaps.
                    Rectangle {
                        width: (parent.filled ? 9 : 5) * root.unit
                        height: parent.height
                        color: parent.filled ? "#aaaaaa" : "#333333"
                    }
                }
            }
        }
        Text {
            visible: root.ntLoader
            y: 416 * root.unit
            text: "For troubleshooting and advanced startup options for Windows 2000, press F8."
            color: "#aaaaaa"
            font.family: "Monospace"
            font.pixelSize: 12 * root.unit
            renderType: Text.NativeRendering
        }
    }
}
