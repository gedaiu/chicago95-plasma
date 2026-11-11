pragma ComponentBehavior: Bound
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

    readonly property int pixelScale: config.scale > 0 ? config.scale : Math.max(1, Math.floor(Math.min(width / 640, height / 720)))
    readonly property string uiFamily: uiFont.status === FontLoader.Ready ? uiFont.name : "sans-serif"
    property int sessionIndex: Math.max(0, sessionModel.lastIndex)
    property bool showOptions: false

    // qmllint disable unqualified
    // The SDDM greeter injects these as context properties, which qmllint cannot see; every other use goes through them.
    readonly property var greeter: sddm
    readonly property var theme: config
    readonly property var sessions: sessionModel
    readonly property var users: userModel
    readonly property var keyboardState: typeof keyboard !== "undefined" ? keyboard : null
    // qmllint enable unqualified

    FontLoader {
        id: uiFont
        source: "MSW98UI-Regular.otf"
    }
    TextConstants {
        id: textConstants
    }

    function logIn() {
        if (userField.text === "") {
            userField.forceActiveFocus();
            return;
        }
        failure.text = "";
        sddm.login(userField.text, passwordField.text, sessionIndex);
    }

    Connections {
        target: root.greeter
        function onLoginFailed() {
            failure.text = "The password is incorrect. Try again.";
            passwordField.text = "";
            passwordField.forceActiveFocus();
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
        property int arrowSpace: 0  // room on the right for a dropdown arrow button
        style: "sunken"
        width: 170
        height: 21
        TextInput {
            id: input
            anchors.fill: parent
            anchors.leftMargin: 4
            anchors.rightMargin: 4 + parent.arrowSpace
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
        signal clicked
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
        MouseArea {
            id: mouse
            anchors.fill: parent
            onClicked: button.clicked()
        }
        Keys.onSpacePressed: button.clicked()
        Keys.onReturnPressed: button.clicked()
    }

    // A sunken list of names under whatever opens it: the dropdowns' lists and the Shutdown... choices.
    component PopupList: Bevel {
        id: popup
        property var names: []
        signal picked(int index)
        visible: false
        z: 1
        height: column.height + 4
        style: "sunken"
        Column {
            id: column
            x: 2
            y: 2
            width: parent.width - 4
            Repeater {
                model: popup.names
                delegate: Rectangle {
                    id: row
                    required property string modelData
                    required property int index
                    width: column.width
                    height: 18
                    color: pick.containsMouse ? "#000080" : "#ffffff"
                    RetroLabel {
                        x: 4
                        anchors.verticalCenter: parent.verticalCenter
                        text: row.modelData
                        color: pick.containsMouse ? "#ffffff" : "#000000"
                    }
                    MouseArea {
                        id: pick
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: {
                            popup.visible = false;
                            popup.picked(row.index);
                        }
                    }
                }
            }
        }
    }

    // The arrow button inside a dropdown's right edge.
    component ArrowButton: Bevel {
        property bool open
        x: parent.width - 2 - width
        y: 2
        width: 16
        height: parent.height - 4
        style: open ? "pressed" : "window"
        // A black arrow, rows 7, 5, 3 and 1 pixels wide.
        Item {
            x: Math.floor((parent.width - 7) / 2) + (parent.open ? 1 : 0)
            y: Math.floor((parent.height - 4) / 2) + (parent.open ? 1 : 0)
            Repeater {
                model: 4
                Rectangle {
                    required property int index
                    x: index
                    y: index
                    width: 7 - 2 * index
                    height: 1
                    color: "#000000"
                }
            }
        }
    }

    // A check box: a sunken white 13px box with the classic 7x7 check mark, and its label.
    component RetroCheck: Item {
        id: check
        property bool checked
        property alias label: caption.text
        signal toggled
        width: caption.x + caption.implicitWidth + 2
        height: 13
        activeFocusOnTab: true
        Keys.onSpacePressed: check.toggled()
        Bevel {
            width: 13
            height: 13
            style: "sunken"
            Repeater {
                // The check mark, one run of pixels per row: [first column, last column].
                model: check.checked ? [[6, 6], [5, 6], [0, 0, 4, 6], [0, 1, 3, 5], [0, 4], [1, 3], [2, 2]] : []
                Item {
                    id: pixelRow
                    required property var modelData
                    required property int index
                    readonly property var runs: modelData
                    y: 3 + index
                    Repeater {
                        model: pixelRow.runs.length / 2
                        Rectangle {
                            required property int index
                            x: 3 + pixelRow.runs[index * 2]
                            width: pixelRow.runs[index * 2 + 1] - pixelRow.runs[index * 2] + 1
                            height: 1
                            color: "#000000"
                        }
                    }
                }
            }
        }
        RetroLabel {
            id: caption
            x: 17
            anchors.verticalCenter: parent.verticalCenter
        }
        // The classic dotted focus rectangle, around the label.
        Rectangle {
            visible: check.activeFocus
            x: caption.x - 1
            y: caption.y - 1
            width: caption.implicitWidth + 2
            height: caption.implicitHeight + 2
            color: "transparent"
            border.width: 1
            border.color: "#000000"
            opacity: 0.6
        }
        MouseArea {
            anchors.fill: parent
            onClicked: check.toggled()
        }
    }

    // A dropdown drawn like the Shut Down dialog's: a sunken white field with the choice in it and an
    // arrow button inside its right edge; its list opens under it.
    component RetroCombo: Bevel {
        id: combo
        property var names: []
        property int currentIndex: 0
        signal activated(int index)
        style: "sunken"
        activeFocusOnTab: true
        z: list.visible ? 2 : 0
        Keys.onSpacePressed: list.visible = !list.visible
        Keys.onUpPressed: if (currentIndex > 0)
            activated(currentIndex - 1)
        Keys.onDownPressed: if (currentIndex + 1 < names.length)
            activated(currentIndex + 1)
        Keys.onEscapePressed: list.visible = false
        onVisibleChanged: list.visible = false
        RetroLabel {
            x: 4
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width - 24
            elide: Text.ElideRight
            text: combo.names[combo.currentIndex] || ""
        }
        ArrowButton {
            open: list.visible
        }
        MouseArea {
            anchors.fill: parent
            onClicked: list.visible = !list.visible
        }
        PopupList {
            id: list
            y: parent.height
            width: parent.width
            names: combo.names
            onPicked: index => combo.activated(index)
        }
    }

    // One invisible item per row of a model, carrying the row's name role.
    component NamedItem: Item {
        required property string name
    }

    // The session names, and the keyboard layouts when there is more than one to pick from.
    Repeater {
        id: sessionRepeater
        model: root.sessions
        delegate: NamedItem {}
    }
    readonly property var sessionNames: {
        const names = [];
        for (let index = 0; index < sessionRepeater.count; index++)
            names.push((sessionRepeater.itemAt(index) as NamedItem).name);
        return names;
    }
    readonly property var layoutNames: {
        const names = [];
        const layouts = typeof keyboard !== "undefined" && keyboard ? keyboard.layouts : [];
        for (let index = 0; index < layouts.length; index++)
            names.push(layouts[index].longName);
        return names;
    }
    readonly property bool canPickLayout: modern && layoutNames.length > 1
    Repeater {
        id: userRepeater
        model: root.users
        delegate: NamedItem {}
    }
    readonly property var userNames: {
        const names = [];
        for (let index = 0; index < userRepeater.count; index++)
            names.push((userRepeater.itemAt(index) as NamedItem).name);
        return names;
    }
    readonly property bool hasKeyboard: !!keyboardState
    property bool showPassword: false

    // 2000's Options: collapsed shows only the user name and password; expanded grows the dialog
    // downwards by one row each for the session, the keyboard layout (when there are several) and the
    // Num Lock and Show password check boxes, which sit where the original's dial-up box does.
    readonly property int optionRows: showOptions ? 2 + (canPickLayout ? 1 : 0) : 0
    readonly property int checkRow: canPickLayout ? 4 : 3
    Shortcut {
        sequence: "Alt+O"
        enabled: root.modern
        onActivated: root.showOptions = !root.showOptions
    }

    Bevel {
        id: dialog
        // 2000's top edge sits a third of the way down the free space above its expanded size, like the
        // original, and stays there while Options grows the dialog; classic is centred.
        anchors.horizontalCenter: parent.horizontalCenter
        y: root.modern ? Math.round((parent.height - 256 * root.pixelScale) * 0.33) : (parent.height - height) / 2
        transformOrigin: root.modern ? Item.Top : Item.Center
        width: root.modern ? 417 : 420
        height: root.modern ? 229 + 27 * root.optionRows : 162
        scale: root.pixelScale
        style: root.modern ? "window" : "raised"

        // One grid for every row: labels at labelX, controls at fieldX, rows rowPitch apart,
        // each label centred on its control. Classic puts OK and Cancel beside the first two rows,
        // 2000 puts four buttons along the bottom under its banner. 2000's numbers are the original's
        // (tests/test_login_reference.py).
        readonly property int labelX: root.modern ? 12 : 76
        readonly property int fieldX: root.modern ? 87 : 152
        readonly property int fieldWidth: root.modern ? 243 : 172
        readonly property int rowHeight: root.modern ? 20 : 21
        readonly property int firstRowY: root.modern ? 130 : 56
        readonly property int rowPitch: root.modern ? 27 : 28
        function rowY(row) {
            return firstRowY + row * rowPitch;
        }
        function besideRow(row) {
            return rowY(row) + (rowHeight - 23) / 2;
        }
        readonly property int bottomButtonsY: height - 37

        Rectangle {
            id: titleBar
            x: 3
            y: 3
            width: parent.width - 6
            height: 18
            // The colour scheme's selection colour (navy in the classic schemes); theme.conf can pin
            // a colour, or start,end for a gradient, with titleActive.
            SystemPalette {
                id: scheme
                colorGroup: SystemPalette.Active
            }
            readonly property var colors: root.theme.titleActive ? String(root.theme.titleActive).split(",") : [scheme.highlight]
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop {
                    position: 0
                    color: titleBar.colors[0]
                }
                GradientStop {
                    position: 1
                    color: titleBar.colors[titleBar.colors.length - 1]
                }
            }
            RetroLabel {
                x: 4
                anchors.verticalCenter: parent.verticalCenter
                text: String(root.theme.loginTitle || "Log On to %h").replace("%h", root.greeter.hostName || "this computer")
                color: "#ffffff"
                font.bold: true
            }
        }

        Image {
            visible: !root.modern
            x: 14
            y: 30
            width: 48
            height: 48
            source: root.theme.loginIcon || "key.svg"
            sourceSize.width: 192
            sourceSize.height: 192
        }

        RetroLabel {
            visible: !root.modern
            x: dialog.labelX
            y: 32
            text: root.theme.loginMessage || "Type a user name and password to log on."
        }

        // 2000: the product banner under the title bar. Setup draws it (chicago95-shutdown --login-banner,
        // the Shut Down banner's code) with the user's logo and texts, 4 times the original's pixels.
        Image {
            visible: root.modern
            x: 3
            y: 22
            width: 411
            height: 93
            source: root.modern ? "brand-banner.png" : ""
            sourceSize.width: 411 * 4
            sourceSize.height: 93 * 4
            smooth: true
            mipmap: true
        }

        RetroLabel {
            x: dialog.labelX
            anchors.verticalCenter: userField.verticalCenter
            text: "User name:"
        }
        RetroField {
            id: userField
            x: dialog.fieldX
            y: dialog.rowY(0)
            width: dialog.fieldWidth
            height: dialog.rowHeight
            text: root.users.lastUser
            KeyNavigation.tab: passwordField.input
            arrowSpace: root.userNames.length > 0 ? 18 : 0
            // The users of this computer, like an editable dropdown: type a name or pick one.
            ArrowButton {
                visible: root.userNames.length > 0
                open: userList.visible
                MouseArea {
                    anchors.fill: parent
                    onClicked: userList.visible = !userList.visible
                }
            }
            PopupList {
                id: userList
                y: parent.height
                width: parent.width
                names: root.userNames
                onPicked: index => {
                    userField.text = root.userNames[index];
                    passwordField.input.forceActiveFocus();
                }
            }
            Keys.onDownPressed: if (root.userNames.length > 0)
                userList.visible = true
            Keys.onEscapePressed: userList.visible = false
        }

        RetroLabel {
            x: dialog.labelX
            anchors.verticalCenter: passwordField.verticalCenter
            text: "Password:"
        }
        RetroField {
            id: passwordField
            x: dialog.fieldX
            y: dialog.rowY(1)
            width: dialog.fieldWidth
            height: dialog.rowHeight
            echoMode: root.showPassword ? TextInput.Normal : TextInput.Password
            KeyNavigation.tab: okButton
        }
        // A balloon under the password while Caps Lock is on, as later versions of the dialog show.
        Rectangle {
            visible: root.hasKeyboard && root.keyboardState.capsLock && passwordField.input.activeFocus
            z: 3
            x: passwordField.x + 10
            y: passwordField.y + passwordField.height + 6
            width: 230
            height: capsText.y + capsText.implicitHeight + 6
            color: "#ffffe1"
            border.color: "#000000"
            radius: 6
            Canvas {  // the tail pointing at the password field
                x: 14
                y: -7
                width: 12
                height: 8
                onPaint: {
                    const context = getContext("2d");
                    context.fillStyle = "#ffffe1";
                    context.strokeStyle = "#000000";
                    context.lineWidth = 1;
                    context.beginPath();
                    context.moveTo(0.5, 8);
                    context.lineTo(0.5, 0.5);
                    context.lineTo(11.5, 8);
                    context.fill();
                    context.stroke();
                }
            }
            RetroLabel {
                id: capsTitle
                x: 8
                y: 6
                font.bold: true
                text: "Caps Lock is On"
            }
            RetroLabel {
                id: capsText
                x: 8
                y: capsTitle.y + capsTitle.implicitHeight + 4
                width: parent.width - 16
                wrapMode: Text.WordWrap
                text: "Having Caps Lock on may cause you to enter your password incorrectly."
            }
        }

        RetroLabel {
            id: failure
            x: dialog.labelX
            y: root.modern ? dialog.bottomButtonsY + 5 : dialog.rowY(3) + 4
            color: "#800000"
        }

        RetroButton {
            id: okButton
            x: root.modern ? 86 : parent.width - 89
            y: root.modern ? dialog.bottomButtonsY : dialog.besideRow(0)
            label: "OK"
            isDefault: true
            KeyNavigation.tab: cancelButton
            onClicked: root.logIn()
        }
        RetroButton {
            id: cancelButton
            x: root.modern ? 167 : parent.width - 89
            y: root.modern ? dialog.bottomButtonsY : dialog.besideRow(1)
            label: "Cancel"
            KeyNavigation.tab: root.modern ? shutDownButton : sessionCombo
            onClicked: {
                passwordField.text = "";
                failure.text = "";
                userField.input.selectAll();
                userField.input.forceActiveFocus();
            }
        }

        // 2000: Shutdown... offers to shut down or restart; Options hides and shows the session row.
        RetroButton {
            id: shutDownButton
            visible: root.modern
            x: 248
            y: dialog.bottomButtonsY
            label: "Shutdown..."
            KeyNavigation.tab: optionsButton
            onClicked: powerList.visible = !powerList.visible
        }
        RetroButton {
            id: optionsButton
            visible: root.modern
            x: 329
            y: dialog.bottomButtonsY
            label: root.showOptions ? "Options <<" : "Options >>"
            KeyNavigation.tab: sessionCombo.visible ? sessionCombo : userField.input
            onClicked: root.showOptions = !root.showOptions
        }
        PopupList {
            id: powerList
            x: shutDownButton.x
            y: shutDownButton.y + shutDownButton.height
            width: 100
            // Stand by and Hibernate only where the machine can do them.
            readonly property var choices: [
                {
                    name: "Shut down",
                    run: () => root.greeter.powerOff()
                },
                {
                    name: "Restart",
                    run: () => root.greeter.reboot()
                }
            ].concat(root.greeter.canSuspend ? [
                {
                    name: "Stand by",
                    run: () => root.greeter.suspend()
                }
            ] : []).concat(root.greeter.canHibernate ? [
                {
                    name: "Hibernate",
                    run: () => root.greeter.hibernate()
                }
            ] : [])
            names: choices.map(choice => choice.name)
            onPicked: index => choices[index].run()
        }

        RetroLabel {
            visible: sessionCombo.visible
            x: dialog.labelX
            anchors.verticalCenter: sessionCombo.verticalCenter
            text: "Session:"
        }
        RetroCombo {
            id: sessionCombo
            visible: !root.modern || root.showOptions
            x: dialog.fieldX
            y: dialog.rowY(2)
            width: dialog.fieldWidth
            height: dialog.rowHeight
            names: root.sessionNames
            currentIndex: root.sessionIndex
            onActivated: index => root.sessionIndex = index
            KeyNavigation.tab: layoutCombo.visible ? layoutCombo : numLockCheck
        }
        RetroLabel {
            visible: layoutCombo.visible
            x: dialog.labelX
            anchors.verticalCenter: layoutCombo.verticalCenter
            text: "Keyboard:"
        }
        RetroCombo {
            id: layoutCombo
            visible: root.canPickLayout && root.showOptions
            x: dialog.fieldX
            y: dialog.rowY(3)
            width: dialog.fieldWidth
            height: dialog.rowHeight
            names: root.layoutNames
            currentIndex: visible ? root.keyboardState.currentLayout : 0
            onActivated: index => root.keyboardState.currentLayout = index
            KeyNavigation.tab: numLockCheck
        }
        Row {
            visible: root.modern && root.showOptions
            x: dialog.fieldX
            y: dialog.rowY(root.checkRow) + 4
            spacing: 16
            RetroCheck {
                id: numLockCheck
                visible: root.hasKeyboard
                label: "Turn on Num Lock"
                checked: root.hasKeyboard && root.keyboardState.numLock
                onToggled: root.keyboardState.numLock = !root.keyboardState.numLock
                KeyNavigation.tab: showPasswordCheck
            }
            RetroCheck {
                id: showPasswordCheck
                label: "Show password"
                checked: root.showPassword
                onToggled: root.showPassword = !root.showPassword
                KeyNavigation.tab: userField.input
            }
        }
    }

    Component.onCompleted: (userField.text === "" ? userField : passwordField).input.forceActiveFocus()
}
