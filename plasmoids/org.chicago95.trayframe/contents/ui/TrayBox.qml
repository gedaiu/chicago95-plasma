import QtQuick

// The sunken box around the tray icons and the clock, as the originals draw it
// (tests/test_taskbar_reference.py): 1px, shadow along the top and left, white along the bottom and
// right (the white owns the top-right and bottom-left corners), as tall as the buttons, at the bottom
// of its applet.
Item {
    id: box
    property color shadow: "#808080"
    property color white: "#ffffff"
    readonly property int boxHeight: 22

    Item {
        y: box.height - box.boxHeight
        width: box.width
        height: box.boxHeight
        Rectangle { width: parent.width; height: 1; color: box.shadow }
        Rectangle { width: 1; height: parent.height; color: box.shadow }
        Rectangle { y: parent.height - 1; width: parent.width; height: 1; color: box.white }
        Rectangle { x: parent.width - 1; width: 1; height: parent.height; color: box.white }
    }
}
