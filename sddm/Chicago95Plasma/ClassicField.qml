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
        anchors.leftMargin: nativeWin95 ? 3 : 4
        anchors.rightMargin: 4 + field.arrowSpace
        anchors.topMargin: nativeWin95 ? -2 : 0
        anchors.bottomMargin: nativeWin95 ? 2 : 0
        verticalAlignment: TextInput.AlignVCenter
        font.family: field.family
        font.pixelSize: 11
        readonly property bool nativeWin95: field.family === "Chicago95 Windows 95"
        font.hintingPreference: nativeWin95 ? Font.PreferNoHinting : Font.PreferDefaultHinting
        renderType: nativeWin95 ? TextInput.NativeRendering : TextInput.QtRendering
        antialiasing: !nativeWin95
        cursorDelegate: nativeWin95 ? win95Cursor : null
        color: "#000000"
        selectionColor: "#000080"
        selectedTextColor: "#ffffff"
        selectByMouse: true
        clip: true
        passwordCharacter: "*"
        Keys.onReturnPressed: field.accepted()
        Keys.onEnterPressed: field.accepted()
    }
    Component {
        id: win95Cursor
        Item {
            width: 1
            height: 13
            Rectangle { y: -1; width: 1; height: 13; color: "#000000" }
        }
    }
}
