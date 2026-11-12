import QtQuick 2.15

// A sunken one-line text box. accepted is Return or Enter.
Bevel {
    id: field
    property alias text: input.text
    property alias echoMode: input.echoMode
    property alias input: input
    property string family: "MS W98 UI"
    property int arrowSpace: 0  // room on the right for a dropdown arrow button
    signal accepted
    style: "sunken"
    width: 170
    height: 21
    TextInput {
        id: input
        anchors.fill: parent
        anchors.leftMargin: 4
        anchors.rightMargin: 4 + field.arrowSpace
        verticalAlignment: TextInput.AlignVCenter
        font.family: field.family
        font.pixelSize: 11
        color: "#000000"
        selectionColor: "#000080"
        selectedTextColor: "#ffffff"
        selectByMouse: true
        clip: true
        passwordCharacter: "*"
        Keys.onReturnPressed: field.accepted()
        Keys.onEnterPressed: field.accepted()
    }
}
