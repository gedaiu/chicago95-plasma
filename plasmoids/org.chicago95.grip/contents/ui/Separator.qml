import QtQuick

// The originals' toolbar separator on the taskbar (tests/test_taskbar_reference.py): after a 2px gap an
// etched line (shadow, then white) as tall as the buttons, 2px of face, then a 3px grip 18px tall (white
// left and top, shadow right and bottom), then 4px before the next item. Bottom-aligned like the
// buttons: 2px above the taskbar's bottom edge.
Item {
    id: separator
    property color shadow: "#808080"
    property color white: "#ffffff"

    readonly property int lead: 2
    readonly property int trail: 4
    readonly property int lineHeight: 22
    readonly property int gripHeight: 18
    readonly property int bottomGap: 2

    implicitWidth: lead + 2 + 2 + 3 + trail
    implicitHeight: lineHeight + bottomGap

    Item {
        x: separator.lead
        y: separator.height - separator.bottomGap - separator.lineHeight
        width: 7
        height: separator.lineHeight

        Rectangle { x: 0; width: 1; height: parent.height; color: separator.shadow }
        Rectangle { x: 1; width: 1; height: parent.height; color: separator.white }

        Item {
            x: 4; y: 2
            width: 3; height: separator.gripHeight
            Rectangle { x: 0; y: 0; width: 1; height: parent.height - 1; color: separator.white }
            Rectangle { x: 0; y: 0; width: 2; height: 1; color: separator.white }
            Rectangle { x: 2; y: 0; width: 1; height: parent.height; color: separator.shadow }
            Rectangle { x: 0; y: parent.height - 1; width: 3; height: 1; color: separator.shadow }
        }
    }
}
