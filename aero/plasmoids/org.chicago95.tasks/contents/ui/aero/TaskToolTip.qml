pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Window
import org.kde.kirigami as Kirigami
import org.kde.pipewire as PipeWire
import org.kde.taskmanager as TaskManager

Rectangle {
    id: tip
    property string title
    property var windowId
    property int previewSize
    property string bevel
    property color face
    property var ids: []
    property var titleAt: row => title
    property var iconAt: row => ""
    signal chooseWindow(int row)
    signal closeWindow(int row)

    readonly property int cardWidth: Math.max(140, previewSize + 8)
    readonly property bool listMode: previewSize <= 0 || ids.length * cardWidth > Screen.desktopAvailableWidth - 32
    readonly property int cardHeight: listMode ? 27 : 30 + Math.round(previewSize * 0.65)
    color: "transparent"
    implicitWidth: (listMode ? 1 : Math.max(1, ids.length)) * cardWidth + 8
    implicitHeight: Math.min((listMode ? Math.max(1, ids.length) : 1) * cardHeight + 8, Screen.desktopAvailableHeight - 60)
    width: implicitWidth
    height: implicitHeight

    // The same Plasma window hosts both ordinary tooltips and our thumbnail previews.
    // Keep its rounded blur mask and let the preview paint its own translucent fill.
    readonly property var host: Window.window
    readonly property var hostFrame: {
        if (host?.mainItem !== parent || !parent) return null;
        for (const layer of host.contentItem.children) {
            for (const frame of layer.children) {
                if (frame.imagePath === "widgets/tooltip") return frame;
            }
        }
        return null;
    }
    Binding {
        target: tip.hostFrame
        property: "opacity"
        value: 0
        when: tip.hostFrame !== null
        restoreMode: Binding.RestoreBindingOrValue
    }
    Rectangle {
        anchors.fill: parent
        // Plasma adds its own tooltip padding around the hosted Loader.
        anchors.leftMargin: -(tip.Window.window?.leftPadding ?? 0)
        anchors.rightMargin: -(tip.Window.window?.rightPadding ?? 0)
        anchors.topMargin: -(tip.Window.window?.topPadding ?? 0)
        anchors.bottomMargin: -(tip.Window.window?.bottomPadding ?? 0)
        radius: 4
        border.color: "#91a9b8"
        color: "#94233446"
    }
    ListView {
        anchors.fill: parent
        anchors.margins: 4
        clip: true
        orientation: tip.listMode ? ListView.Vertical : ListView.Horizontal
        model: tip.ids
        delegate: Rectangle {
            id: card
            required property int index
            required property var modelData
            width: tip.cardWidth
            height: tip.cardHeight
            radius: 3
            color: target.containsMouse ? "#527cadce" : "transparent"
            HoverHandler { id: hover }
            Kirigami.Icon {
                x: 6
                y: 4
                width: 16
                height: 16
                source: tip.iconAt(card.index)
            }
            Text {
                x: 26
                y: 4
                width: parent.width - x - (closeButton.opacity > 0 ? 26 : 6)
                text: tip.titleAt(card.index) || tip.title
                elide: Text.ElideRight
                color: "white"
                font.family: "Segoe UI"
                font.pixelSize: 12
            }
            Rectangle {
                x: 3
                y: 23
                width: parent.width - 6
                height: Math.max(0, parent.height - y - 3)
                color: "#303e5160"
                border.color: "#90798a97"
                visible: !tip.listMode
            }
            Loader {
                x: 4
                y: 24
                width: parent.width - 8
                height: Math.max(0, parent.height - y - 4)
                active: !tip.listMode && tip.Window.window?.visible === true
                sourceComponent: PipeWire.PipeWireSourceItem {
                    nodeId: stream.nodeId
                    TaskManager.ScreencastingRequest {
                        id: stream
                        uuid: card.modelData
                    }
                }
            }
            MouseArea {
                id: target
                anchors.fill: parent
                hoverEnabled: true
                onClicked: tip.chooseWindow(card.index)
            }
            Rectangle {
                id: closeButton
                anchors.right: parent.right
                anchors.rightMargin: 3
                y: 3
                width: 20
                height: 17
                radius: 2
                opacity: hover.hovered || closeArea.containsMouse ? 1 : 0
                color: closeArea.containsMouse ? "#c84932" : "#647c8e"
                border.color: "#b9c8d1"
                Text { anchors.centerIn: parent; text: "×"; color: "white"; font.pixelSize: 14 }
                MouseArea {
                    id: closeArea
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: tip.closeWindow(card.index)
                }
            }
        }
    }
}
