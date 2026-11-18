import QtQuick

// The orb's glow while the Start menu is open or the pointer is on it: the logo's own colours, enlarged and
// blurred, blooming over the orb (win7allprograms.png). At rest there is none (win7dragedge.png).
// It is light only: a pixel glows as bright as it is, so a logo's dark outline adds nothing.
Item {
    id: glow
    property url source
    property bool active
    property point centre: Qt.point(27.5, 20)
    property int logoSize: 20

    // How far the light spreads past the logo, and how bright it blooms.
    readonly property real spread: 2.1
    readonly property real strength: 1
    // Drawn this small and stretched smoothly, the logo blurs without a shader, on every scene graph backend;
    // the empty margin round it lets the light fade out before the glow's edges.
    readonly property int blurredPixels: 6
    readonly property int margin: 2

    implicitWidth: 58
    implicitHeight: 40

    Canvas {
        id: lightCanvas
        readonly property int pixels: glow.blurredPixels + 2 * glow.margin
        width: pixels
        height: pixels
        x: glow.centre.x - width / 2
        y: glow.centre.y - height / 2
        scale: glow.logoSize * glow.spread / glow.blurredPixels
        smooth: true
        opacity: glow.active ? glow.strength : 0
        visible: opacity > 0
        renderTarget: Canvas.Image
        Behavior on opacity {
            NumberAnimation {
                duration: 150
            }
        }
        onPaint: {
            const context = getContext("2d");
            context.clearRect(0, 0, pixels, pixels);
            if (!isImageLoaded(glow.source))
                return;
            context.drawImage(glow.source, glow.margin, glow.margin, glow.blurredPixels, glow.blurredPixels);
            const logo = context.getImageData(0, 0, pixels, pixels).data;
            context.clearRect(0, 0, pixels, pixels);
            // Each pixel as light: its colour at full brightness, as opaque as it was bright. The map is ten
            // pixels square, so it is painted pixel by pixel; Qt's putImageData blends rather than replaces.
            for (let index = 0; index < logo.length; index += 4) {
                const brightest = Math.max(logo[index], logo[index + 1], logo[index + 2]);
                if (!brightest)
                    continue;
                const pixel = index / 4;
                context.fillStyle = Qt.rgba(logo[index] / brightest, logo[index + 1] / brightest, logo[index + 2] / brightest, logo[index + 3] / 255 * brightest / 255);
                context.fillRect(pixel % pixels, Math.floor(pixel / pixels), 1, 1);
            }
        }
        onImageLoaded: requestPaint()
        Component.onCompleted: loadImage(glow.source)
        Connections {
            target: glow
            function onSourceChanged() {
                lightCanvas.loadImage(glow.source);
                lightCanvas.requestPaint();
            }
        }
    }
}
