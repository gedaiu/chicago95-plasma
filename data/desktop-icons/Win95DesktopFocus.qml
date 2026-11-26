import QtQuick

ShaderEffect {
    id: outline

    required property Item wallpaper
    required property real scaleFactor
    required property point itemPosition
    readonly property size edge: Qt.size(1 / (width * scaleFactor), 1 / (height * scaleFactor))

    function snap(value: real): real {
        return Math.round(value * scaleFactor) / scaleFactor;
    }

    fragmentShader: "win95-focus.frag.qsb"
    property var source: ShaderEffectSource {
        sourceItem: outline.wallpaper
        sourceRect: {
            if (!outline.wallpaper || !outline.visible || !outline.itemPosition) return Qt.rect(0, 0, 1, 1);
            return outline.mapToItem(outline.wallpaper, 0, 0, outline.width, outline.height);
        }
        textureSize: Qt.size(Math.round(outline.width * outline.scaleFactor),
                             Math.round(outline.height * outline.scaleFactor))
        smooth: false
    }
}
