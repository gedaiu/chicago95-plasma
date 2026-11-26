import QtQuick 2.15

// The classic dialogs' 8pt UI text. The login sets the family to the font it ships beside the theme, since the
// greeter cannot see the user's fonts; the lock screen runs as the user and finds it installed.
Text {
    readonly property bool nativeWin95: font.family === "Chicago95 Windows 95"
    font.family: "MS W98 UI"
    font.pixelSize: 11
    font.hintingPreference: nativeWin95 ? Font.PreferNoHinting : Font.PreferDefaultHinting
    renderType: nativeWin95 ? Text.NativeRendering : Text.QtRendering
    antialiasing: !nativeWin95
    color: "#000000"
}
