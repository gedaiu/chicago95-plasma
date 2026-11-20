pragma ComponentBehavior: Bound
import QtQuick

AeroLogin {
    id: screen
    property string userName
    property var authenticator: null
    signal passwordEntered(string password)
    signal suspendRequested()

    greeter: adapter
    users: [userName]
    sessions: []
    lastSession: 0
    lastUser: userName
    account: userName
    choosing: false
    unlockOnly: true

    QtObject {
        id: adapter
        readonly property bool canPowerOff: false
        readonly property bool canReboot: false
        signal loginFailed()
        function login(user, password, session) {
            screen.passwordEntered(password);
        }
    }
    Connections {
        target: screen.authenticator
        function onFailed(kind) {
            if (kind === 0) adapter.loginFailed();
        }
    }
}
