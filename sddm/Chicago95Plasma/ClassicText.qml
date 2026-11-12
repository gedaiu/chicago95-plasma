import QtQuick 2.15

// The classic dialogs' 8pt UI text. The login sets the family to the font it ships beside the theme, since the
// greeter cannot see the user's fonts; the lock screen runs as the user and finds it installed.
Text {
    font.family: "MS W98 UI"
    font.pixelSize: 11
    color: "#000000"
}
