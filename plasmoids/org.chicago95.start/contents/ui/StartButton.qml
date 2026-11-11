import QtQuick
import QtQuick.Layouts

// The Start button as the originals draw it (tests/test_taskbar_reference.py): 22px tall at the bottom of
// its applet (the panel's margin puts it 2px above the taskbar's bottom edge); a two-pixel raised bevel that presses in while held; the logo 16px square 2px
// inside the bevel, the bold text 3px after it, spaced half a pixel wider than the font's own (the
// original's letters are wider), and 3px of face between its last stroke and the bevel.
Item {
    id: button
    property string text
    property url logoSource
    property bool held
    // 2000's lettering is wider than this font's: its button has a pixel more face after the text.
    property string bevel: "1995"
    // XP Classic's Start button is tighter than 2000's: 2px before the logo, 4px between logo and text,
    // 2px of face after the last stroke (tests/references/xpclassic.png).
    property string look: "1995"
    readonly property bool isXpClassic: look === "2001"
    // Bevel colours: 1995 and 1998 derive light and shadow from the face (#DFDFDF and #808080 for
    // #C0C0C0) with a black outer shadow; 2000 uses the face itself as light, #808080 and #404040.
    property color face: "#c0c0c0"
    property color light: bevel === "2000" ? face : Qt.tint(face, "#80ffffff")  // halfway to white
    property color shadow: bevel === "2000" ? "#808080" : Qt.darker(face, 1.5)  // two thirds of the face
    property color dark: bevel === "2000" ? "#404040" : "#000000"
    property color textColor: "#000000"

    readonly property int buttonHeight: 22
    readonly property int logoSize: 16

    readonly property int contentX: isXpClassic ? 2 : 4
    readonly property int trailingFace: bevel !== "2000" ? 0 : isXpClassic ? -2 : 1
    // The text's advance runs 3px past its last stroke: the original's face before the bevel.
    implicitWidth: contentX + content.implicitWidth + (label.visible ? 0 : 3) + 2 + trailingFace
    implicitHeight: buttonHeight

    Item {
        id: buttonFace
        x: 0
        y: button.height - height
        width: button.width
        height: button.buttonHeight

        Rectangle {
            anchors.fill: parent
            color: button.face
        }
        // Outer ring: white and dark raised, dark and white held; inner ring: light and shadow, swapped
        // when held. The dark lines own the top-right and bottom-left corners.
        Rectangle {
            x: 0
            y: 0
            width: parent.width - 1
            height: 1
            color: button.held ? button.dark : "#ffffff"
        }
        Rectangle {
            x: 0
            y: 0
            width: 1
            height: parent.height - 1
            color: button.held ? button.dark : "#ffffff"
        }
        Rectangle {
            x: 0
            y: parent.height - 1
            width: parent.width
            height: 1
            color: button.held ? "#ffffff" : button.dark
        }
        Rectangle {
            x: parent.width - 1
            y: 0
            width: 1
            height: parent.height
            color: button.held ? "#ffffff" : button.dark
        }
        Rectangle {
            x: 1
            y: 1
            width: parent.width - 3
            height: 1
            color: button.held ? button.shadow : button.light
        }
        Rectangle {
            x: 1
            y: 1
            width: 1
            height: parent.height - 3
            color: button.held ? button.shadow : button.light
        }
        Rectangle {
            x: 1
            y: parent.height - 2
            width: parent.width - 2
            height: 1
            color: button.held ? button.light : button.shadow
        }
        Rectangle {
            x: parent.width - 2
            y: 1
            width: 1
            height: parent.height - 2
            color: button.held ? button.light : button.shadow
        }

        RowLayout {
            id: content
            spacing: button.isXpClassic ? 4 : 3
            // Whole pixels: a half-pixel offset would resample the pixel-art logo.
            x: button.contentX + (button.held ? 1 : 0)
            y: Math.round((parent.height - height) / 2) + (button.held ? 1 : 0)

            Image {
                visible: button.logoSource.toString() !== ""
                source: button.logoSource
                Layout.preferredWidth: button.logoSize
                Layout.preferredHeight: button.logoSize
                // Pixel art (PNG) loads at its own size and is drawn unscaled when it is 16px, like the
                // flag; vector logos are rasterised at twice the size and drawn smooth.
                readonly property bool pixelArt: String(button.logoSource).endsWith(".png")
                sourceSize: pixelArt ? undefined : Qt.size(button.logoSize * 2, button.logoSize * 2)
                fillMode: Image.PreserveAspectFit
                smooth: !pixelArt
                cache: false  // the logo file can be replaced by the user; always read the current one
            }
            Text {
                id: label
                visible: button.text !== ""
                text: button.text
                font.family: "MS W98 UI"
                font.bold: true
                font.pixelSize: 11
                font.letterSpacing: 0.5
                color: button.textColor
                // A pixel font: drawn without smoothing, like the original's text.
                renderType: Text.NativeRendering
                antialiasing: false
            }
        }
    }
}
