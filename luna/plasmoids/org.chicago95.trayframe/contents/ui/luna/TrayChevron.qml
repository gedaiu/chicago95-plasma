import QtQuick
import QtQuick.Shapes

Item {
    id: chevron
    objectName: "lunaChevron"

    readonly property int diameter: 16
    property bool hovered: pointer.hovered
    property bool held: press.pressed
    readonly property var body: held ? ["#8AD0EE", "#0A82D4", "#0040B0"] : hovered ? ["#D0ECFA", "#6FC2F2", "#0A80E0"] : ["#8ED6F9", "#1CA0F2", "#0A5BE1"]

    implicitWidth: diameter
    implicitHeight: diameter
    width: diameter
    height: diameter

    HoverHandler {
        id: pointer
    }
    TapHandler {
        id: press
    }

    component Disc: Rectangle {
        required property var colours
        radius: width / 2
        rotation: -45
        antialiasing: true
        gradient: Gradient {
            GradientStop {
                position: 0
                color: colours[0]
            }
            GradientStop {
                position: chevron.held || chevron.hovered ? 0.5 : 0.45
                color: colours[1]
            }
            GradientStop {
                position: 1
                color: colours[2]
            }
        }
    }

    Disc {
        width: chevron.diameter
        height: chevron.diameter
        colours: ["#0E1C57", "#8A90B0", "#C2C6D6"]
    }
    Disc {
        x: 1
        y: 1
        width: chevron.diameter - 2
        height: chevron.diameter - 2
        colours: chevron.body
    }
    Shape {
        width: chevron.diameter
        height: chevron.diameter
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            fillColor: "transparent"
            strokeColor: "#FFFFFF"
            strokeWidth: 2.2
            joinStyle: ShapePath.MiterJoin
            startX: 9.5
            startY: 4.5
            PathLine {
                x: 5.5
                y: 8
            }
            PathLine {
                x: 9.5
                y: 11.5
            }
        }
    }
}
