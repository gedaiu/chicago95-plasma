import QtQuick 2.15

// Original light-only frames, followed by the user's artwork. No flag frames
// are sampled. Canvas keeps this available in the software Plymouth exporter.
Canvas {
    id: canvas
    objectName: "customSeven"
    property url logoSource
    property int frame: 0
    property var palette: []
    readonly property url atlas: Qt.resolvedUrl("seven.png")
    canvasSize: Qt.size(200, 200)
    onFrameChanged: requestPaint()
    onLogoSourceChanged: { palette = []; loadImage(logoSource); requestPaint(); }
    Component.onCompleted: { loadImage(atlas); loadImage(logoSource); }
    onImageLoaded: requestPaint()
    Image { id: original; source: canvas.logoSource; visible: false }

    function sample(ctx) {
        ctx.clearRect(0, 0, 200, 200);
        ctx.drawImage(logoSource, 0, 0, 32, 32);
        var pixels = ctx.getImageData(0, 0, 32, 32).data;
        var sums = [[0,0,0,0], [0,0,0,0], [0,0,0,0], [0,0,0,0]];
        for (var y = 0; y < 32; y++) {
            for (var x = 0; x < 32; x++) {
                var n = (y * 32 + x) * 4;
                var r = pixels[n], g = pixels[n+1], b = pixels[n+2];
                // Transparent padding contributes nothing; saturated colors
                // outweigh white lettering without discarding monochrome logos.
                var weight = pixels[n+3] / 255 * (0.05 + (Math.max(r,g,b)-Math.min(r,g,b))/255);
                var sum = sums[(y < 16 ? 0 : 2) + (x < 16 ? 0 : 1)];
                sum[0] += r*weight; sum[1] += g*weight; sum[2] += b*weight; sum[3] += weight;
            }
        }
        var total = [0,0,0,0];
        for (var i=0; i<4; i++) for (var k=0; k<4; k++) total[k] += sums[i][k];
        var colors = [];
        for (i=0; i<4; i++) {
            var v = sums[i][3] > 0 ? sums[i] : total;
            var c = v[3] > 0 ? [v[0]/v[3],v[1]/v[3],v[2]/v[3]] : [210,210,210];
            // Keep dark artwork's lights visible, preserving its hue.
            if (Math.max(c[0], c[1], c[2]) < 1) c = [210,210,210];
            var gain = 255 / Math.max(1, c[0], c[1], c[2]);
            colors.push(c.map(function(value) { return Math.min(255, Math.round(value*gain)); }));
        }
        palette = colors;
    }
    onPaint: {
        if (!isImageLoaded(logoSource) || !isImageLoaded(atlas)) return;
        var ctx = getContext("2d");
        ctx.reset();
        if (!palette.length) sample(ctx);
        ctx.clearRect(0, 0, 200, 200);
        if (frame < 60) {
            var f = Math.min(55, frame);
            ctx.drawImage(atlas, (f%15)*200, Math.floor(f/15)*200, 200, 200, 0, 0, 200, 200);
            var data = ctx.getImageData(0, 0, 200, 200);
            var pixels = data.data;
            for (var p=0; p<pixels.length; p+=4) {
                var r=pixels[p], g=pixels[p+1], b=pixels[p+2];
                var c=palette[b > r && b > g ? 2 : g > r*1.2 ? 1 : r > g*1.5 ? 0 : 3];
                var bright=Math.max(r,g,b)/255;
                var white=Math.min(r,g,b)/255;
                for (var k=0; k<3; k++) pixels[p+k]=Math.min(255, c[k]*bright*(1-white)+255*white);
                pixels[p+3] *= Math.min(1, (60-frame)/5);
            }
            ctx.clearRect(0, 0, 200, 200);
            ctx.putImageData(data, 0, 0, 0, 0, 200, 200);
        }
        if (frame >= 55) {
            var ratio = original.implicitWidth / Math.max(1, original.implicitHeight);
            var w=ratio >= 1 ? 160 : 160*ratio, h=ratio >= 1 ? 160/ratio : 160;
            var reveal=Math.min(1, (frame-55)/5);
            ctx.globalAlpha=reveal;
            ctx.drawImage(logoSource, (200-w)/2, (200-h)/2, w, h);
            ctx.globalCompositeOperation="source-atop";
            // The 45-frame loop closes exactly when playback returns to frame 60.
            var phase=2*Math.PI*(frame-60)/45;
            ctx.globalAlpha=reveal*(0.16+0.10*Math.sin(phase));
            for (var i=0; i<4; i++) {
                var color=palette[i];
                var x=70+(i%2)*60+12*Math.sin(phase+i), y=70+Math.floor(i/2)*60;
                var glow=ctx.createRadialGradient(x,y,0,x,y,65);
                glow.addColorStop(0, "rgba("+color.join(",")+",1)");
                glow.addColorStop(1, "rgba("+color.join(",")+",0)");
                ctx.fillStyle=glow; ctx.fillRect(0,0,200,200);
            }
        }
    }
}
