import QtQuick

Rectangle {
    id: face
    property bool held

    radius: 2
    border.width: 1
    border.color: held ? "#082E84" : "#1D5DCB"
    gradient: Gradient {
        orientation: Gradient.Horizontal
        GradientStop {
            position: 0
            color: face.held ? "#1A45A5" : "#7DB3F5"
        }
        GradientStop {
            position: 0.15
            color: face.held ? "#1348BD" : "#4A8CEE"
        }
        GradientStop {
            position: 0.5
            color: face.held ? "#0E49C9" : "#3C80E9"
        }
        GradientStop {
            position: 0.85
            color: face.held ? "#0C42B8" : "#2B6ADA"
        }
        GradientStop {
            position: 1
            color: face.held ? "#0F3D9C" : "#184DA5"
        }
    }
}
