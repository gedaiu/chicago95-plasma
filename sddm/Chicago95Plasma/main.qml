import QtQuick 2.15
import SddmComponents 2.0

// Chicago95 log on dialog. Drawn at 1x in classic pixels and scaled by a whole number,
// so every bevel line stays one crisp pixel wide on any screen.
// loginStyle in theme.conf: "classic" (1995/1998 key dialog on teal) or "2000" (branded banner on blue).
Rectangle {
    id: root
    width: 1024
    height: 768
    readonly property bool modern: config.loginStyle === "2000"
    color: modern ? "#3A6EA5" : "#008080"

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
        width: root.modern ? 412 : 420
        height: root.modern ? 248 : 162
        scale: root.pixelScale

        // One grid for every row: labels at labelX, controls at fieldX, rows rowPitch apart,
        // each label centred on its control. Classic puts OK and Cancel beside the first two rows,
        // 2000 puts them along the bottom under its banner.
        readonly property int labelX: root.modern ? 16 : 76
        readonly property int fieldX: root.modern ? 104 : 152
        readonly property int fieldWidth: root.modern ? 290 : 172
        readonly property int rowHeight: 21
        readonly property int firstRowY: root.modern ? 110 : 56
        readonly property int rowPitch: 28
        function rowY(row) { return firstRowY + row * rowPitch }
        function besideRow(row) { return rowY(row) + (rowHeight - 23) / 2 }
        readonly property int bottomButtonsY: height - 33

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

        Image { visible: !root.modern; x: 14; y: 30; width: 48; height: 48; source: "key.svg"; sourceSize.width: 192; sourceSize.height: 192 }

        RetroLabel { visible: !root.modern; x: dialog.labelX; y: 32; text: "Type a user name and password to log on." }

        // 2000: product banner under the title bar, text from theme.conf (Setup writes the Start banner text).
        Rectangle {
            id: brandBanner
            visible: root.modern
            x: 3; y: 21
            width: parent.width - 6
            height: 74
            color: "#ffffff"
            // The Start button's logo, copied here by Setup (the greeter cannot read a home folder).
            Image {
                id: brandLogo
                visible: status === Image.Ready
                source: config.brandLogo ? Qt.resolvedUrl(config.brandLogo) : ""
                x: 14
                anchors.verticalCenter: parent.verticalCenter
                anchors.verticalCenterOffset: -6
                height: 44
                width: 44
                sourceSize.width: 88
                sourceSize.height: 88
                fillMode: Image.PreserveAspectFit
                // Pixel-art logos (the classic flag, a PNG) stay sharp; vector logos are drawn smooth.
                smooth: !String(source).endsWith(".png")
            }
            // One line of formatted text, so the name and the edition share a baseline. Words bold,
            // numbers thin, like the Start menu banner.
            Text {
                id: brandName
                x: brandLogo.visible ? brandLogo.x + brandLogo.width + 12 : 16
                anchors.verticalCenter: brandLogo.visible ? brandLogo.verticalCenter : parent.verticalCenter
                textFormat: Text.RichText
                font.family: root.uiFamily
                font.pixelSize: 26
                color: "#000000"
                text: (String(config.brandText || "Chicago95").match(/\s*\d+|\s*[^\d]+/g) || [])
                      .map(part => /^\s*\d+$/.test(part) ? part : "<b>" + part + "</b>").join("")
                      + "&nbsp;&nbsp;<b><span style=\"font-size: 15px\">" + (config.brandEdition || "Professional") + "</span></b>"
            }
            Text {
                anchors.right: parent.right
                anchors.rightMargin: 10
                anchors.bottom: parent.bottom
                anchors.bottomMargin: 6
                text: config.brandTagline || "Built on Linux Technology"
                font.family: root.uiFamily
                font.pixelSize: 10
                color: "#000000"
            }
        }
        Rectangle {
            visible: root.modern
            x: 3; y: brandBanner.y + brandBanner.height
            width: parent.width - 6
            height: 5
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0; color: "#0A246A" }
                GradientStop { position: 1; color: "#A6CAF0" }
            }
        }

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

        RetroLabel { id: failure; x: dialog.labelX; y: root.modern ? dialog.bottomButtonsY + 5 : dialog.rowY(3) + 4; color: "#800000" }

        RetroButton {
            id: okButton
            x: root.modern ? parent.width - 170 : parent.width - 89
            y: root.modern ? dialog.bottomButtonsY : dialog.besideRow(0)
            label: "OK"
            isDefault: true
            KeyNavigation.tab: cancelButton
            onClicked: root.logIn()
        }
        RetroButton {
            id: cancelButton
            x: parent.width - 89
            y: root.modern ? dialog.bottomButtonsY : dialog.besideRow(1)
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
