import QtQuick 2.15

// Classic two-pixel bevel. "raised" for buttons, "window" for window frames (light outside, white
// inside), "sunken" for text fields, "pressed" for a button held down; isDefault adds the black outline
// of the default button. The 2000 login style uses 2000's greys: light is the face itself, and the
// shadows are #808080 and #404040 instead of a derived grey and black.
Rectangle {
    id: bevel
    property string style: "raised"
    property bool isDefault: false
    // Face from the colour scheme ("Apply Plasma Settings" in System Settings > Login Screen copies it
    // to the login screen); light and shadow derive from it as #DFDFDF and #808080 do from #C0C0C0.
    SystemPalette {
        id: scheme
        colorGroup: SystemPalette.Active
    }
    readonly property bool modern: config.loginStyle === "2000"
    readonly property color face: scheme.window
    readonly property color white: "#ffffff"
    readonly property color light: modern ? face : Qt.tint(face, "#80ffffff")  // halfway to white
    readonly property color shadow: modern ? "#808080" : Qt.darker(face, 1.5)  // two thirds of the face
    readonly property color dark: modern ? "#404040" : "#000000"
    readonly property bool sunken: style === "sunken" || style === "pressed"
    readonly property int outline: isDefault ? 1 : 0
    // A held button is dark outside, a text field is grey outside; both are white at the bottom right.
    readonly property color outerTopLeft: style === "pressed" ? dark : sunken ? shadow : style === "window" ? light : white
    readonly property color innerTopLeft: style === "pressed" ? shadow : sunken ? dark : style === "window" ? white : light

    color: style === "sunken" ? scheme.base : face
    border.width: outline
    border.color: "#000000"

    Item {
        anchors.fill: parent
        anchors.margins: bevel.outline

        Rectangle {
            x: 0
            y: 0
            width: parent.width - 1
            height: 1
            color: bevel.outerTopLeft
        }
        Rectangle {
            x: 0
            y: 0
            width: 1
            height: parent.height - 1
            color: bevel.outerTopLeft
        }
        Rectangle {
            x: 0
            y: parent.height - 1
            width: parent.width
            height: 1
            color: bevel.sunken ? bevel.white : bevel.dark
        }
        Rectangle {
            x: parent.width - 1
            y: 0
            width: 1
            height: parent.height
            color: bevel.sunken ? bevel.white : bevel.dark
        }

        Rectangle {
            x: 1
            y: 1
            width: parent.width - 3
            height: 1
            color: bevel.innerTopLeft
        }
        Rectangle {
            x: 1
            y: 1
            width: 1
            height: parent.height - 3
            color: bevel.innerTopLeft
        }
        Rectangle {
            x: 1
            y: parent.height - 2
            width: parent.width - 2
            height: 1
            color: bevel.sunken ? bevel.light : bevel.shadow
        }
        Rectangle {
            x: parent.width - 2
            y: 1
            width: 1
            height: parent.height - 2
            color: bevel.sunken ? bevel.light : bevel.shadow
        }
    }
}
