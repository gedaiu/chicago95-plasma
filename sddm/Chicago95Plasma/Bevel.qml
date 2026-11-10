import QtQuick 2.15

// Classic two-pixel bevel. "raised" for windows and buttons, "sunken" for text fields,
// "pressed" for a button held down; "default" adds the black outline of the default button.
Rectangle {
    id: bevel
    property string style: "raised"
    property bool isDefault: false
    readonly property color white: "#ffffff"
    readonly property color light: "#dfdfdf"
    readonly property color shadow: "#808080"
    readonly property color dark: "#000000"
    readonly property bool sunken: style === "sunken" || style === "pressed"
    readonly property int outline: isDefault ? 1 : 0
    // A held button is dark outside, a text field is grey outside; both are white at the bottom right.
    readonly property color outerTopLeft: style === "pressed" ? dark : sunken ? shadow : white
    readonly property color innerTopLeft: style === "pressed" ? shadow : sunken ? dark : light

    color: style === "sunken" ? "#ffffff" : "#c0c0c0"
    border.width: outline
    border.color: dark

    Item {
        anchors.fill: parent
        anchors.margins: bevel.outline

        Rectangle { x: 0; y: 0; width: parent.width - 1; height: 1; color: bevel.outerTopLeft }
        Rectangle { x: 0; y: 0; width: 1; height: parent.height - 1; color: bevel.outerTopLeft }
        Rectangle { x: 0; y: parent.height - 1; width: parent.width; height: 1; color: bevel.sunken ? bevel.white : bevel.dark }
        Rectangle { x: parent.width - 1; y: 0; width: 1; height: parent.height; color: bevel.sunken ? bevel.white : bevel.dark }

        Rectangle { x: 1; y: 1; width: parent.width - 3; height: 1; color: bevel.innerTopLeft }
        Rectangle { x: 1; y: 1; width: 1; height: parent.height - 3; color: bevel.innerTopLeft }
        Rectangle { x: 1; y: parent.height - 2; width: parent.width - 2; height: 1; color: bevel.sunken ? bevel.light : bevel.shadow }
        Rectangle { x: parent.width - 2; y: 1; width: 1; height: parent.height - 2; color: bevel.sunken ? bevel.light : bevel.shadow }
    }
}
