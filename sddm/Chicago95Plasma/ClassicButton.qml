import QtQuick 2.15

// A push button: raised, pressed while held, with the dotted focus rectangle inside when focused.
Bevel {
    id: button
    property alias label: caption.text
    property alias family: caption.font.family
    property alias glyph: captionGlyph.source
    property bool held: mouse.pressed && mouse.containsMouse
    signal clicked
    width: 75
    height: 23
    style: held ? "pressed" : "raised"
    activeFocusOnTab: true
    ClassicText {
        id: caption
        visible: !captionGlyph.visible
        anchors.centerIn: parent
        anchors.horizontalCenterOffset: button.held ? 1 : 0
        anchors.verticalCenterOffset: button.held ? 1 : 0
    }
    Image {
        id: captionGlyph
        visible: source.toString() !== ""
        width: 16
        height: 14
        x: button.held ? 1 : 0
        y: x
        smooth: false
    }
    Rectangle {
        visible: button.activeFocus
        anchors.fill: parent
        anchors.margins: 4
        color: "transparent"
        border.width: 1
        border.color: "#000000"
        opacity: 0.6
    }
    MouseArea {
        id: mouse
        anchors.fill: parent
        onClicked: button.clicked()
    }
    Keys.onSpacePressed: button.clicked()
    Keys.onReturnPressed: button.clicked()
}
