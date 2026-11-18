import QtQuick

// The orb's glow while the Start menu is open or the pointer is on it: the logo's own colours, enlarged and
// blurred, blooming over the orb (win7allprograms.png). At rest there is none (win7dragedge.png).
Item {
    id: glow
    property url source
    property bool active
    property point centre: Qt.point(27.5, 20)
    property int logoSize: 20

    // How far the light spreads past the logo, and how bright it blooms.
    readonly property real spread: 1.8
    readonly property real strength: 0.9
    // Loaded this small and stretched smoothly, the logo blurs without a shader, on every scene graph backend.
    readonly property int blurredPixels: 6

    implicitWidth: 58
    implicitHeight: 40

    Image {
        width: glow.logoSize * glow.spread
        height: width
        x: glow.centre.x - width / 2
        y: glow.centre.y - height / 2
        sourceSize: Qt.size(glow.blurredPixels, glow.blurredPixels)
        source: glow.source
        fillMode: Image.PreserveAspectFit
        smooth: true
        opacity: glow.active ? glow.strength : 0
        Behavior on opacity {
            NumberAnimation {
                duration: 150
            }
        }
    }
}
