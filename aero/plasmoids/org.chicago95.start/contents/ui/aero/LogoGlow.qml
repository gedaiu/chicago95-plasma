import QtQuick

// Sample each quarter of the configured mark for the coloured light on the glass.
// Draw the falloff in orb coordinates so it stays round at fractional display scales.
Canvas {
    id: glow
    property url source
    property bool active
    property bool pressed
    property point centre: Qt.point(27, 20)
    property int logoSize: 20

    implicitWidth: 58
    implicitHeight: 40
    opacity: active ? (pressed ? 0.66 : 1) : 0
    Behavior on opacity {
        NumberAnimation { duration: 150 }
    }

    function updateSource() {
        if (source.toString()) loadImage(source);
        requestPaint();
    }
    onSourceChanged: updateSource()
    Component.onCompleted: updateSource()
    onImageLoaded: requestPaint()
    onLogoSizeChanged: requestPaint()
    onCentreChanged: requestPaint()

    onPaint: {
        const ctx = getContext("2d");
        ctx.clearRect(0, 0, width, height);
        if (!isImageLoaded(source))
            return;

        const size = 16;
        ctx.drawImage(source, 0, 0, size, size);
        const sample = ctx.getImageData(0, 0, size, size).data;
        const quadrants = Array.from({length: 4}, () => [0, 0, 0, 0]);
        for (let y = 0; y < size; ++y) {
            for (let x = 0; x < size; ++x) {
                const i = 4 * (y * size + x);
                const area = quadrants[(x >= size / 2 ? 1 : 0) + (y >= size / 2 ? 2 : 0)];
                const alpha = sample[i + 3] / 255;
                for (let c = 0; c < 3; ++c)
                    area[c] += alpha * sample[i + c];
                area[3] += alpha;
            }
        }
        ctx.clearRect(0, 0, width, height);
        quadrants.forEach((area, index) => {
            const peak = Math.max(area[0], area[1], area[2]);
            if (!peak) return;
            const intensity = Math.min(1, peak / (170 * area[3])) * Math.min(1, area[3] / 24);
            const colour = alpha => Qt.rgba(area[0] / peak, area[1] / peak, area[2] / peak, alpha * intensity);
            const offset = logoSize * 0.25;
            const x = centre.x + (index % 2 ? offset : -offset);
            const y = centre.y + (index >= 2 ? offset : -offset);
            const wash = ctx.createRadialGradient(x, y, 0, x, y, 21);
            wash.addColorStop(0, colour(0.64));
            wash.addColorStop(0.60, colour(0.53));
            wash.addColorStop(0.82, colour(0.24));
            wash.addColorStop(1, colour(0));
            ctx.fillStyle = wash;
            ctx.fillRect(0, 0, width, height);
        });
    }
}
