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
        height: orb.frameSize * 3
        y: (orb.height - orb.frameSize) / 2 - frameIndex * orb.frameSize
        source: orb.source
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
