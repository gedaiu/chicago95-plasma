/*
 * The Windows XP lock screen: the Welcome screen (luna/sddm/LunaLogin.qml) with the locked user as its only tile
 * and "Type your password". The lock screen's own code keeps the authenticator; this file only reports the typed
 * password through passwordEntered and clears the field when the authenticator says the password was wrong.
 * Installed as lockscreen/luna/lockscreen next to lockscreen/luna/sddm, qml and images.
 */
import QtQuick 2.15
import "../sddm"

Item {
    id: root

    property string userName
    property url userPicture
    property var authenticator
    property bool shuttingDown: false

    signal passwordEntered(string password)
    signal suspendRequested

    readonly property alias welcome: welcome
    readonly property int interactiveFailure: 0

    QtObject {
        id: greeter
        signal loginFailed
        property bool canSuspend: true
        function login(name, password, sessionIndex) {
            root.passwordEntered(password);
        }
        function suspend() {
            root.suspendRequested();
        }
        function powerOff() {
        }
        function reboot() {
        }
    }

    ListModel {
        id: users
        ListElement {
            name: ""
            realName: ""
            icon: ""
        }
    }
    ListModel {
        id: sessions
        ListElement {
            name: "Plasma"
        }
    }

    onUserNameChanged: users.set(0, {"name": userName, "realName": userName})
    onUserPictureChanged: users.setProperty(0, "icon", userPicture.toString())

    Connections {
        target: root.authenticator
        function onFailed(kind) {
            if (kind === root.interactiveFailure)
                greeter.loginFailed();
        }
    }

    LunaLogin {
        id: welcome
        anchors.fill: parent
        greeter: greeter
        users: users
        sessions: sessions
        selectedName: root.userName
        sessionIndex: 0
        shuttingDown: root.shuttingDown
        locked: true
    }
}
