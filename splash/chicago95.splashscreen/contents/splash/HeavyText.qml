import QtQuick 2.15

// Heavy lettering for the 2000 screen's name and edition, emboldened like the Start menu banner: Arial
// Bold drawn again at every point of a small circle, so each stroke grows by embolden pixels on every
// side and keeps its smooth (feathered) edges. baselineY is where the letters sit, in the parent's
// coordinates.
Item {
    id: heavy
    property string text
    property real pixelSize
    property real embolden
    property real letterSpacing
    property bool italic
    property color color: "#000000"
    property real baselineY  // "baseline" is taken by Item
    readonly property int copies: 16

    y: baselineY - letters.baselineOffset
    width: letters.implicitWidth + embolden * 2
    height: letters.implicitHeight

    Text {
        id: letters
        x: heavy.embolden
        font.family: "Arial"
        font.bold: true
        font.italic: heavy.italic
        font.pixelSize: heavy.pixelSize
        font.letterSpacing: heavy.letterSpacing
        color: heavy.color
        text: heavy.text
    }
    Repeater {
        model: heavy.copies
        Text {
            readonly property real angle: 2 * Math.PI * index / heavy.copies
            x: letters.x + heavy.embolden * Math.cos(angle)
            y: heavy.embolden * Math.sin(angle)
            font: letters.font
            color: heavy.color
            text: heavy.text
        }
    }
}
