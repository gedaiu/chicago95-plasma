import QtQuick
import QtQuick.Shapes

// Windows 7's hover light: the button washed in its icon's colour, brightest at its foot under the pointer.
Shape {
    id: glow
    property color tint: "#ffffff"
    property real pointerX: width / 2

    // Measured on win7peek.png's hovered Explorer button: 85% at the foot, about half at the sides.
    readonly property real footOpacity: 0.85
    readonly property real sideOpacity: 0.45

    preferredRendererType: Shape.CurveRenderer
    ShapePath {
        strokeWidth: -1
        fillGradient: RadialGradient {
            centerX: glow.pointerX
            centerY: glow.height
            centerRadius: glow.width
            focalX: centerX
            focalY: centerY
            GradientStop { position: 0; color: Qt.alpha(glow.tint, glow.footOpacity) }
            GradientStop { position: 0.6; color: Qt.alpha(glow.tint, glow.sideOpacity) }
            GradientStop { position: 1; color: Qt.alpha(glow.tint, 0.3) }
        }
        PathRectangle { width: glow.width; height: glow.height }
    }
}
