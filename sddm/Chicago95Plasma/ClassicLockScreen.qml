pragma ComponentBehavior: Bound
import QtQuick 2.15

/*
 * The classic lock screen, drawn with the log on dialog's parts on the desktop colour and shown from the start:
 * 9x locks with the screen saver's password box, 2000 with Unlock Computer. A wrong password brings up a message
 * box over it. The lock screen's own code keeps the authenticator; this file only reports the typed password
 * through passwordEntered. Installed as lockscreen/classic next to the lock screen's own files.
 */
Rectangle {
    id: root

    property string userName
    property var authenticator
    property bool modern: false
    property color desktopColor: modern ? "#3A6EA5" : "#008080"
    readonly property int interactiveFailure: 0
    readonly property int pixelScale: Math.max(1, Math.floor(Math.min(width / 640, height / 720)))
    readonly property string title: modern ? "Unlock Computer" : "Windows Screen Saver"

    signal passwordEntered(string password)

    color: desktopColor

    function unlock() {
        root.passwordEntered(passwordField.text);
    }

    function focusPassword() {
        passwordField.input.forceActiveFocus();
    }

    function clear() {
        passwordField.text = "";
        focusPassword();
    }

    Connections {
        target: root.authenticator
        function onFailed(kind) {
            if (kind !== root.interactiveFailure)
                return;
            passwordField.text = "";
            message.visible = true;
            messageOk.forceActiveFocus();
        }
    }

    Component.onCompleted: focusPassword()

    Bevel {
        id: dialog
        objectName: "lockDialog"
        modern: root.modern
        enabled: !message.visible
        anchors.centerIn: parent
        width: root.modern ? 417 : 360
        height: root.modern ? 182 : 104
        scale: root.pixelScale
        style: "window"

        readonly property int fieldX: root.modern ? 87 : 126
        readonly property int passwordY: root.modern ? 111 : 68

        ClassicTitleBar {
            modern: root.modern
            title: root.title
        }

        ClassicButton {
            visible: !root.modern
            modern: root.modern
            x: parent.width - 21
            y: 5
            width: 16
            height: 14
            label: "×"
            onClicked: root.clear()
        }

        Image {
            x: root.modern ? 14 : 12
            y: root.modern ? 32 : 30
            width: root.modern ? 32 : 45
            height: root.modern ? 32 : 48
            source: root.modern ? "padlock.svg" : "key-9x.png"
            sourceSize.width: width * root.pixelScale
            sourceSize.height: height * root.pixelScale
            smooth: root.modern
        }

        ClassicText {
            x: root.modern ? 56 : 70
            y: root.modern ? 32 : 34
            width: dialog.width - x - (root.modern ? 12 : 98)
            wrapMode: Text.WordWrap
            lineHeight: 1.2
            text: root.modern ? "This computer is in use and has been locked.\nOnly " + (root.userName || "the user who locked it") + " or an administrator can unlock this computer." : "Type your password:"
        }

        ClassicText {
            visible: root.modern
            x: 12
            anchors.verticalCenter: userField.verticalCenter
            text: "User name:"
        }

        ClassicField {
            id: userField
            visible: root.modern
            modern: root.modern
            x: dialog.fieldX
            y: 84
            width: 243
            height: 20
            text: root.userName
            input.readOnly: true
            input.activeFocusOnTab: false
        }

        ClassicText {
            x: root.modern ? 12 : 70
            anchors.verticalCenter: passwordField.verticalCenter
            text: "Password:"
        }

        ClassicField {
            id: passwordField
            objectName: "lockPassword"
            modern: root.modern
            x: dialog.fieldX
            y: dialog.passwordY
            width: root.modern ? 243 : 136
            height: root.modern ? 20 : 21
            echoMode: TextInput.Password
            onAccepted: root.unlock()
        }

        ClassicButton {
            objectName: "lockOk"
            modern: root.modern
            isDefault: true
            x: root.modern ? dialog.width - 168 : dialog.width - 87
            y: root.modern ? dialog.height - 35 : 30
            label: "OK"
            onClicked: root.unlock()
        }

        ClassicButton {
            objectName: "lockCancel"
            modern: root.modern
            x: dialog.width - 87
            y: root.modern ? dialog.height - 35 : 59
            label: "Cancel"
            onClicked: root.clear()
        }
    }

    Bevel {
        id: message
        objectName: "lockMessage"
        modern: root.modern
        visible: false
        z: 10
        anchors.centerIn: parent
        width: root.modern ? 330 : 250
        height: root.modern ? 110 : 92
        scale: root.pixelScale
        style: "window"

        function close() {
            visible = false;
            root.clear();
        }

        ClassicTitleBar {
            modern: root.modern
            title: root.title
        }

        Image {
            x: 12
            y: 32
            width: 32
            height: 32
            source: "error.svg"
            sourceSize.width: width * root.pixelScale
            sourceSize.height: height * root.pixelScale
        }

        ClassicText {
            x: 56
            y: 32
            width: message.width - x - 12
            wrapMode: Text.WordWrap
            text: root.modern ? "The password is incorrect. Letters in passwords must be typed using the correct case. Type your password again." : "The password is incorrect. Try again."
        }

        ClassicButton {
            id: messageOk
            objectName: "lockMessageOk"
            modern: root.modern
            isDefault: true
            anchors.horizontalCenter: parent.horizontalCenter
            y: message.height - 33
            label: "OK"
            onClicked: message.close()
            Keys.onEnterPressed: message.close()
        }
    }
}
