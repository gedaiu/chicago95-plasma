import QtQuick

Item {
    id: orb
    property url source
    property bool hovered
    property bool engaged
    readonly property bool ready: base.status === Image.Ready && hot.status === Image.Ready
    readonly property int frameSize: 54
    property real hotOpacity: hovered ? 1 : 0
    Behavior on hotOpacity { NumberAnimation { duration: 300 } }

    width: frameSize
    height: 40
    clip: true
    component Frame: Image {
        required property int frameIndex
        width: orb.frameSize
        height: orb.frameSize
        anchors.verticalCenter: parent.verticalCenter
        source: orb.source
        sourceClipRect: Qt.rect(0, frameIndex * orb.frameSize, orb.frameSize, orb.frameSize)
        smooth: true
    }
    Frame {
        id: base
        frameIndex: orb.engaged ? 2 : 0
        visible: orb.engaged || hot.opacity < 1
    }
    Frame {
        id: hot
        frameIndex: 1
        opacity: orb.engaged ? 0 : orb.hotOpacity
    }
}
