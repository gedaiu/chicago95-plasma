pragma ComponentBehavior: Bound
import QtQuick 2.15

/*
 * The classic lock screen, drawn with the log on dialog's parts on the desktop colour and shown from the start:
 * 9x locks with the screen saver's password box, 2000 and XP Classic with Unlock Computer. A wrong password brings up a message
 * box over it. The lock screen's own code keeps the authenticator; this file only reports the typed password
 * through passwordEntered. Installed as lockscreen/classic next to the lock screen's own files.
 */
Rectangle {
    id: root

    property string userName
    property var authenticator
    property bool modern: false
    property bool xpClassic: false
    property string hostName
    property url bannerSource
    property color desktopColor: modern ? "#3A6EA5" : "#008080"
    readonly property int interactiveFailure: 0
    // The session's sizes are already multiplied by the screen's scale; a classic pixel is drawn as that scale
    // rounded to whole screen pixels, so its lines stay crisp, as Winamp's Double Size does.
    property real screenScale: Screen.devicePixelRatio
    readonly property real pixelScale: Math.max(1, Math.round(screenScale)) / screenScale
    readonly property real dialogScale: modern ? 1 : pixelScale
    readonly property real imageScale: modern ? screenScale : pixelScale
    readonly property string title: modern ? "Unlock Computer" : "Windows Screen Saver"
    readonly property string fontFamily: xpClassic
        ? (Qt.fontFamilies().includes("Tahoma") ? "Tahoma" : "Liberation Sans") : "MS W98 UI"
    readonly property string lockedAccount: userName
        ? (xpClassic && hostName ? hostName + "\\" + userName : userName) : "the user who locked it"

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
        anchors.verticalCenterOffset: root.modern ? -root.height / 8 : 0
        width: root.modern ? 389 : 360
        height: root.modern ? 262 : 104
        scale: root.dialogScale
        style: "window"

        readonly property int fieldX: root.modern ? 129 : 126
        readonly property int passwordY: root.modern ? 190 : 68

        ClassicTitleBar {
            modern: root.modern
            title: root.title
            family: root.fontFamily
            pinned: root.modern
                ? (message.visible ? "#808080,#b5b5b5" : "#0a246a,#a6caf0")
                : ""
        }

        Image {
            visible: root.modern && !!root.bannerSource.toString()
            x: 3
            y: 22
            width: dialog.width - 6
            height: 61
            source: root.bannerSource
            mipmap: true
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
            x: root.modern ? 21 : 12
            y: root.modern ? 98 : 30
            width: root.modern ? 26 : 45
            height: root.modern ? 22 : 48
            source: root.modern ? "Win2000Lock.svg" : "key-9x.png"
            sourceSize.width: Math.round(width * root.imageScale)
            sourceSize.height: Math.round(height * root.imageScale)
            smooth: root.modern
        }

        ClassicText {
            font.family: root.fontFamily
            x: root.modern ? 69 : 70
            y: root.modern ? 95 : 34
            width: dialog.width - x - (root.modern ? 12 : 98)
            wrapMode: Text.WordWrap
            lineHeight: 1.2
            text: root.modern ? "This computer is in use and has been locked."
                + (root.xpClassic ? "\n\n" : "\n")
                + "Only " + root.lockedAccount + " or an administrator can unlock this computer."
                : "Type your password:"
        }

        ClassicText {
            font.family: root.fontFamily
            visible: root.modern
            x: 69
            anchors.verticalCenter: userField.verticalCenter
            text: "User name:"
        }

        ClassicField {
            id: userField
            visible: root.modern
            modern: root.modern
            family: root.fontFamily
            x: dialog.fieldX
            y: 163
            width: 178
            height: 20
            text: root.userName
            input.readOnly: true
            input.activeFocusOnTab: false
        }

        ClassicText {
            font.family: root.fontFamily
            x: root.modern ? 69 : 70
            anchors.verticalCenter: passwordField.verticalCenter
            text: "Password:"
        }

        ClassicField {
            id: passwordField
            objectName: "lockPassword"
            modern: root.modern
            family: root.fontFamily
            x: dialog.fieldX
            y: dialog.passwordY
            width: root.modern ? 178 : 136
            height: root.modern ? 20 : 21
            echoMode: TextInput.Password
            input.passwordCharacter: root.xpClassic ? "\u25cf" : "*"
            onAccepted: root.unlock()
        }

        ClassicButton {
            objectName: "lockOk"
            modern: root.modern
            family: root.fontFamily
            isDefault: !root.xpClassic || activeFocus
            x: root.modern ? dialog.width - 158 : dialog.width - 87
            y: root.modern ? 226 : 30
            width: root.modern ? 71 : 75
            height: root.modern ? 22 : 23
            label: "OK"
            onClicked: root.unlock()
        }

        ClassicButton {
            objectName: "lockCancel"
            modern: root.modern
            family: root.fontFamily
            x: dialog.width - (root.modern ? 81 : 87)
            y: root.modern ? 226 : 59
            width: root.modern ? 71 : 75
            height: root.modern ? 22 : 23
            enabled: !root.modern
            opacity: enabled ? 1 : 0.55
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
        anchors.horizontalCenterOffset: root.xpClassic && parent.width >= 638 ? 3 : 0
        anchors.verticalCenterOffset: root.xpClassic ? 20 : root.modern ? 10 : 0
        width: root.modern ? Math.min(618, parent.width - 20) : 250
        height: root.modern ? Math.max(root.xpClassic ? 116 : 115, messageText.y + messageText.implicitHeight + 46) : 92
        scale: root.dialogScale
        style: "window"

        function close() {
            visible = false;
            root.clear();
        }

        ClassicTitleBar {
            modern: root.modern
            family: root.fontFamily
            title: root.modern ? "Computer Locked." : root.title
            pinned: root.modern ? "#0a246a,#a6caf0" : ""
        }

        ClassicButton {
            visible: root.modern
            modern: true
            family: root.fontFamily
            x: message.width - 20
            y: 5
            width: 16
            height: 14
            label: "×"
            onClicked: message.close()
        }

        Image {
            x: root.modern ? 13 : 12
            y: 32
            width: root.modern ? 26 : 32
            height: width
            source: "error.svg"
            sourceSize.width: Math.round(width * root.imageScale)
            sourceSize.height: Math.round(height * root.imageScale)
        }

        ClassicText {
            id: messageText
            font.family: root.fontFamily
            x: root.modern ? 60 : 56
            y: root.xpClassic ? 35 : 32
            width: message.width - x - 12
            wrapMode: Text.WordWrap
            text: root.modern
                ? "The password is incorrect. Please retype your password. Letters in passwords must be typed using the correct case."
                    + (root.xpClassic ? "" : " Make sure that Caps Lock is not accidentally on.")
                : "The password is incorrect. Try again."
        }

        ClassicButton {
            id: messageOk
            objectName: "lockMessageOk"
            modern: root.modern
            family: root.fontFamily
            isDefault: true
            anchors.horizontalCenter: parent.horizontalCenter
            y: message.height - (root.modern ? 38 : 33)
            width: root.modern ? 81 : 75
            height: root.modern ? 24 : 23
            label: "OK"
            onClicked: message.close()
            Keys.onEnterPressed: message.close()
        }
    }
}
