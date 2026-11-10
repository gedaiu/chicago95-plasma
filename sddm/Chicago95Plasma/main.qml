import QtQuick 2.15
import SddmComponents 2.0

// Chicago95 log on dialog. Drawn at 1x in classic pixels and scaled by a whole number,
// so every bevel line stays one crisp pixel wide on any screen.
Rectangle {
    id: root
    width: 1024
    height: 768
    color: "#008080"

    readonly property int pixelScale: config.scale > 0 ? config.scale
                                      : Math.max(1, Math.floor(Math.min(width / 640, height / 720)))
    readonly property string uiFamily: uiFont.status === FontLoader.Ready ? uiFont.name : "sans-serif"
    property int sessionIndex: Math.max(0, sessionModel.lastIndex)

    FontLoader { id: uiFont; source: "MSW98UI-Regular.otf" }
    TextConstants { id: textConstants }

    function logIn() {
        if (userField.text === "") {
            userField.forceActiveFocus()
            return
        }
        failure.text = ""
        sddm.login(userField.text, passwordField.text, sessionIndex)
    }

    Connections {
        target: sddm
        function onLoginFailed() {
            failure.text = "The password is incorrect. Try again."
            passwordField.text = ""
            passwordField.forceActiveFocus()
        }
    }

    component RetroLabel: Text {
        font.family: root.uiFamily
        font.pixelSize: 11
        color: "#000000"
    }

    component RetroField: Bevel {
        property alias text: input.text
        property alias echoMode: input.echoMode
        property alias input: input
        style: "sunken"
        width: 170
        height: 21
        TextInput {
            id: input
            anchors.fill: parent
            anchors.leftMargin: 4
            anchors.rightMargin: 4
            verticalAlignment: TextInput.AlignVCenter
            font.family: root.uiFamily
            font.pixelSize: 11
            color: "#000000"
            selectionColor: "#000080"
            selectedTextColor: "#ffffff"
            selectByMouse: true
            clip: true
            passwordCharacter: "*"
            Keys.onReturnPressed: root.logIn()
            Keys.onEnterPressed: root.logIn()
        }
    }

    component RetroButton: Bevel {
        id: button
        property alias label: caption.text
        property bool held: mouse.pressed && mouse.containsMouse
        signal clicked()
        width: 75
        height: 23
        style: held ? "pressed" : "raised"
        activeFocusOnTab: true
        RetroLabel {
            id: caption
            anchors.centerIn: parent
            anchors.horizontalCenterOffset: button.held ? 1 : 0
            anchors.verticalCenterOffset: button.held ? 1 : 0
        }
        // The classic desktop draws a dotted rectangle inside the focused button.
        Rectangle {
            visible: button.activeFocus
            anchors.fill: parent
            anchors.margins: 4
            color: "transparent"
            border.width: 1
            border.color: "#000000"
            opacity: 0.6
        }
        MouseArea { id: mouse; anchors.fill: parent; onClicked: button.clicked() }
        Keys.onSpacePressed: button.clicked()
        Keys.onReturnPressed: button.clicked()
    }

    Bevel {
        id: dialog
        anchors.centerIn: parent
        width: 420
        height: 162
        scale: root.pixelScale

        // One grid for every row: labels at labelX, controls at fieldX, rows rowPitch apart,
        // each label centred on its control; OK and Cancel centred on the first two rows.
        readonly property int labelX: 76
        readonly property int fieldX: 152
        readonly property int fieldWidth: 172
        readonly property int rowHeight: 21
        readonly property int firstRowY: 56
        readonly property int rowPitch: 28
        function rowY(row) { return firstRowY + row * rowPitch }

        Rectangle {
            id: titleBar
            x: 3; y: 3
            width: parent.width - 6
            height: 18
            // The colour scheme's selection colour (navy in the classic schemes); theme.conf can pin
            // a colour, or start,end for a gradient, with titleActive.
            SystemPalette { id: scheme; colorGroup: SystemPalette.Active }
            readonly property var colors: config.titleActive ? String(config.titleActive).split(",") : [scheme.highlight]
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0; color: titleBar.colors[0] }
                GradientStop { position: 1; color: titleBar.colors[titleBar.colors.length - 1] }
            }
            RetroLabel {
                x: 4
                anchors.verticalCenter: parent.verticalCenter
                text: "Log On to " + (sddm.hostName || "this computer")
                color: "#ffffff"
                font.bold: true
            }
        }

        Image { x: 14; y: 32; source: "key.png"; smooth: false }

        RetroLabel { x: dialog.labelX; y: 32; text: "Type a user name and password to log on." }

        RetroLabel { x: dialog.labelX; anchors.verticalCenter: userField.verticalCenter; text: "User name:" }
        RetroField {
            id: userField
            x: dialog.fieldX; y: dialog.rowY(0)
            width: dialog.fieldWidth; height: dialog.rowHeight
            text: userModel.lastUser
            KeyNavigation.tab: passwordField.input
        }

        RetroLabel { x: dialog.labelX; anchors.verticalCenter: passwordField.verticalCenter; text: "Password:" }
        RetroField {
            id: passwordField
            x: dialog.fieldX; y: dialog.rowY(1)
            width: dialog.fieldWidth; height: dialog.rowHeight
            echoMode: TextInput.Password
            KeyNavigation.tab: okButton
        }

        RetroLabel { id: failure; x: dialog.labelX; y: dialog.rowY(3) + 4; color: "#800000" }

        RetroButton {
            id: okButton
            x: parent.width - 89; anchors.verticalCenter: userField.verticalCenter
            label: "OK"
            isDefault: true
            KeyNavigation.tab: cancelButton
            onClicked: root.logIn()
        }
        RetroButton {
            id: cancelButton
            x: parent.width - 89; anchors.verticalCenter: passwordField.verticalCenter
            label: "Cancel"
            KeyNavigation.tab: sessionButton
            onClicked: {
                passwordField.text = ""
                failure.text = ""
                userField.input.selectAll()
                userField.input.forceActiveFocus()
            }
        }

        RetroLabel { x: dialog.labelX; anchors.verticalCenter: sessionButton.verticalCenter; text: "Session:" }
        RetroButton {
            id: sessionButton
            x: dialog.fieldX; y: dialog.rowY(2)
            width: dialog.fieldWidth; height: dialog.rowHeight
            label: ""
            KeyNavigation.tab: userField.input
            onClicked: sessionList.visible = !sessionList.visible
            RetroLabel {
                x: 6
                anchors.verticalCenter: parent.verticalCenter
                width: parent.width - 30
                elide: Text.ElideRight
                // count changes when the sessions arrive, which re-evaluates this lookup.
                text: sessionNames.count > root.sessionIndex ? sessionNames.itemAt(root.sessionIndex).name : ""
            }
            Canvas {
                width: 7; height: 4
                anchors.right: parent.right
                anchors.rightMargin: 7
                anchors.verticalCenter: parent.verticalCenter
                onPaint: {
                    const context = getContext("2d")
                    context.fillStyle = "#000000"
                    context.beginPath(); context.moveTo(0, 0); context.lineTo(7, 0); context.lineTo(3.5, 4); context.fill()
                }
            }
        }
        Repeater { id: sessionNames; model: sessionModel; delegate: Item { property string name: model.name } }

        Bevel {
            id: sessionList
            visible: false
            z: 1
            x: sessionButton.x
            y: sessionButton.y + sessionButton.height
            width: sessionButton.width
            height: sessionColumn.height + 4
            style: "sunken"
            Column {
                id: sessionColumn
                x: 2; y: 2
                width: parent.width - 4
                Repeater {
                    model: sessionModel
                    delegate: Rectangle {
                        width: sessionColumn.width
                        height: 18
                        color: pick.containsMouse ? "#000080" : "#ffffff"
                        RetroLabel {
                            x: 4
                            anchors.verticalCenter: parent.verticalCenter
                            text: model.name
                            color: pick.containsMouse ? "#ffffff" : "#000000"
                        }
                        MouseArea {
                            id: pick
                            anchors.fill: parent
                            hoverEnabled: true
                            onClicked: { root.sessionIndex = index; sessionList.visible = false }
                        }
                    }
                }
            }
        }
    }

    Component.onCompleted: (userField.text === "" ? userField : passwordField).input.forceActiveFocus()
}
