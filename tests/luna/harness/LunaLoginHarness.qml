import QtQuick 2.15
import "../../../luna/sddm"

LunaLogin {
    width: 800
    height: 600
    greeter: sddm
    users: userModel
    sessions: sessionModel
    theme: config
    keyboardState: keyboard
}
