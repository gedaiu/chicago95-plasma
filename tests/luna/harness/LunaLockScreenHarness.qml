import QtQuick 2.15
import "../../../luna/lockscreen"

LunaLockScreen {
    width: 800
    height: 600
    authenticator: lockAuthenticator
    userName: "Administrator"
    onPasswordEntered: password => lockAuthenticator.respond(password)
}
