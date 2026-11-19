pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic

Rectangle {
    id: page
    required property var greeter
    required property var users
    required property var sessions
    required property int lastSession
    required property string lastUser
    gradient: Gradient {
        GradientStop {
            position: 0
            color: "#053b68"
        }
        GradientStop {
            position: 0.5
            color: "#2579a5"
        }
        GradientStop {
            position: 1
            color: "#073456"
        }
    }

    function submit() {
        if (!account.editText.trim()) {
            account.forceActiveFocus();
            return;
        }
        failure.text = "";
        greeter.login(account.editText, password.text, Math.max(0, session.currentIndex));
    }

    Column {
        anchors.centerIn: parent
        spacing: 10
        Rectangle {
            anchors.horizontalCenter: parent.horizontalCenter
            width: 94
            height: 94
            radius: 8
            color: "#c1dbe4"
            border.color: "#f7ffff"
            Rectangle {
                anchors.fill: parent
                anchors.margins: 5
                radius: 4
                gradient: Gradient {
                    GradientStop {
                        position: 0
                        color: "#82bcd3"
                    }
                    GradientStop {
                        position: 1
                        color: "#225a89"
                    }
                }
                Rectangle {
                    anchors.horizontalCenter: parent.horizontalCenter
                    y: 14
                    width: 30
                    height: 30
                    radius: 15
                    color: "#eaf6fa"
                }
                Rectangle {
                    anchors.horizontalCenter: parent.horizontalCenter
                    y: 47
                    width: 55
                    height: 29
                    radius: 13
                    color: "#eaf6fa"
                }
            }
        }
        ComboBox {
            id: account
            width: 210
            editable: true
            model: page.users
            Component.onCompleted: editText = page.lastUser || currentText
            onAccepted: password.forceActiveFocus()
        }
        Row {
            spacing: 4
            TextField {
                id: password
                objectName: "aeroPassword"
                width: 178
                echoMode: TextInput.Password
                placeholderText: qsTr("Password")
                onAccepted: page.submit()
            }
            Button {
                text: "➜"
                onClicked: page.submit()
                Accessible.name: qsTr("Log on")
            }
        }
        Label {
            id: failure
            color: "white"
        }
    }
    ComboBox {
        id: session
        anchors.left: parent.left
        anchors.bottom: parent.bottom
        anchors.margins: 18
        model: page.sessions
        currentIndex: page.lastSession
        visible: count > 1
    }
    Button {
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 18
        text: qsTr("Shut down")
        visible: page.greeter.canPowerOff
        onClicked: page.greeter.powerOff()
    }
    Connections {
        target: page.greeter
        function onLoginFailed() {
            failure.text = qsTr("The user name or password is incorrect.");
            password.clear();
            password.forceActiveFocus();
        }
    }
    Component.onCompleted: password.forceActiveFocus()
}
