import QtQuick 2.15

// A window's title bar: the colour scheme's selection colour (navy in the classic schemes), or pinned:
// one colour, or start,end for a gradient. 9x ends the gradient early; 2000 runs it to the end.
Rectangle {
    id: titleBar
    property alias title: titleText.text
    property alias family: titleText.font.family
    property bool modern: false
    property string pinned: ""
    readonly property var colors: pinned ? pinned.split(",") : [scheme.highlight]
    x: 3
    y: 3
    width: parent.width - 6
    height: 18
    SystemPalette {
        id: scheme
        colorGroup: SystemPalette.Active
    }
    gradient: Gradient {
        orientation: Gradient.Horizontal
        GradientStop {
            position: 0
            color: titleBar.colors[0]
        }
        GradientStop {
            position: titleBar.modern ? 1 : 0.95
            color: titleBar.colors[titleBar.colors.length - 1]
        }
    }
    Rectangle {
        visible: !titleBar.modern
        anchors.right: parent.right
        width: 36
        height: parent.height
        color: titleBar.colors[titleBar.colors.length - 1]
    }
    ClassicText {
        id: titleText
        x: 4
        anchors.verticalCenter: parent.verticalCenter
        color: "#ffffff"
        font.bold: true
    }
}
