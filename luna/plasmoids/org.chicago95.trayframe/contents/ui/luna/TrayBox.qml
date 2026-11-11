import QtQuick

Item {
    id: box
    readonly property int boxHeight: 30
    readonly property int notchHeight: boxHeight - 2
    readonly property int leftWashWidth: 28
    readonly property int rightWashWidth: 24

    component Wash: Rectangle {
        required property color tint
        required property var alphas
        y: 1
        height: box.notchHeight
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0; color: Qt.alpha(tint, alphas[0]) }
            GradientStop { position: 0.1071; color: Qt.alpha(tint, alphas[1]) }
            GradientStop { position: 0.1429; color: Qt.alpha(tint, alphas[2]) }
            GradientStop { position: 0.25; color: Qt.alpha(tint, alphas[3]) }
            GradientStop { position: 0.4286; color: Qt.alpha(tint, alphas[4]) }
            GradientStop { position: 0.6071; color: Qt.alpha(tint, alphas[5]) }
            GradientStop { position: 0.9643; color: Qt.alpha(tint, alphas[6]) }
        }
    }

    Rectangle {
        width: box.width
        height: box.boxHeight
        gradient: Gradient {
            GradientStop { position: 0.0167; color: "#095BC9" }
            GradientStop { position: 0.0500; color: "#16ADF0" }
            GradientStop { position: 0.0833; color: "#19B9F3" }
            GradientStop { position: 0.1167; color: "#149EED" }
            GradientStop { position: 0.1833; color: "#1290E8" }
            GradientStop { position: 0.4833; color: "#118DEA" }
            GradientStop { position: 0.6167; color: "#0D8DEA" }
            GradientStop { position: 0.8167; color: "#0E9EF0" }
            GradientStop { position: 0.8500; color: "#0F9EEE" }
            GradientStop { position: 0.8833; color: "#119CEA" }
            GradientStop { position: 0.9167; color: "#1393E4" }
            GradientStop { position: 0.9500; color: "#1581D9" }
            GradientStop { position: 0.9833; color: "#095BC9" }
        }
    }
    Wash {
        width: box.leftWashWidth
        tint: "#1BC8F7"
        alphas: [0.6, 0.6, 0.38, 0.32, 0.22, 0.06, 0]
    }
    Wash {
        x: box.width - box.rightWashWidth
        width: box.rightWashWidth
        tint: "#000000"
        alphas: [0, 0, 0, 0.015, 0.04, 0.05, 0.05]
    }
    component Notch: Rectangle {
        required property int column
        required property var tints
        x: column
        y: 1
        width: 1
        height: box.notchHeight
        gradient: Gradient {
            GradientStop { position: 0; color: tints[0] }
            GradientStop { position: 0.0357; color: tints[1] }
            GradientStop { position: 0.1071; color: tints[2] }
            GradientStop { position: 0.1429; color: tints[3] }
            GradientStop { position: 0.8571; color: tints[3] }
            GradientStop { position: 0.8929; color: tints[4] }
            GradientStop { position: 1; color: tints[5] }
        }
    }
    Notch { column: 0; tints: ["#26405A", "#2E475C", "#0C2B50", "#0A2E52", "#0B3051", "#0E2857"] }
    Notch { column: 1; tints: ["#1CC8F7", "#1CC8F7", "#1CC8F7", "#22BCE6", "#1BD1F2", "#1BC9EE"] }
    Notch { column: 2; tints: ["#1CC8F7", "#1CC8F7", "#1CC8F7", "#22C7F5", "#1AD7FA", "#1CC7F5"] }
}
