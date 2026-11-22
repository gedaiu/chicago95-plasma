pragma ComponentBehavior: Bound
import QtQuick
import org.kde.plasma.workspace.keyboardlayout as Keyboards
import QtQuick.Controls.Basic

Rectangle {
    id: page
    required property var greeter
    required property var users
    required property var sessions
    required property int lastSession
    required property string lastUser
    property bool unlockOnly: false
    property bool canSwitchUser: false
    signal switchUserRequested()
    property url userPicture
    property string brandText
    property url brandLogo
    property string account: lastUser || users[0] || ""
    property bool choosing: !account
    property bool manual: false
    property bool largeText: false
    property bool reveal: false
    property int sessionIndex: Math.max(0, lastSession)
    readonly property string uiFamily: Qt.fontFamilies().includes("Segoe UI") ? "Segoe UI"
        : fallbackFont.status === FontLoader.Ready ? fallbackFont.name : "sans-serif"
    FontLoader {
        id: fallbackFont
        source: Qt.resolvedUrl("fonts/selawik/selawk.ttf")
    }
    color: "#105784"

    function art(name) { return Qt.resolvedUrl("aero-art/" + name); }
    function selectUser(name) {
        account = name;
        manual = !name;
        choosing = false;
        failure.text = "";
        password.clear();
        reveal = false;
        if (manual) userField.forceActiveFocus();
        else password.forceActiveFocus();
    }
    function focusPassword() { password.forceActiveFocus(); }
    function clear() { password.clear(); focusPassword(); }
    function submit() {
        const name = manual ? userField.text.trim() : account;
        if (!name) {
            userField.forceActiveFocus();
            return;
        }
        failure.text = "";
        greeter.login(name, password.text, sessionIndex);
    }
    Image {
        anchors.fill: parent
        source: page.art("background")
        fillMode: Image.PreserveAspectCrop
    }
    component GlassButton: Button {
        id: control
        property string sprite: "switch-user-button"
        property string glyph
        hoverEnabled: true
        background: Image {
            source: page.art(control.sprite + (control.down && control.sprite !== "access-button" ? "-active" : control.hovered || control.activeFocus ? "-hover" : "") + ".svg")
        }
        contentItem: Item {
            implicitWidth: buttonLabel.implicitWidth
            Image {
                anchors.centerIn: parent
                source: control.glyph ? page.art(control.glyph) : ""
            }
            Text {
                id: buttonLabel
                anchors.centerIn: parent
                text: control.text
                color: "white"
                font.family: page.uiFamily
                font.pixelSize: page.largeText ? 16 : 12
            }
        }
    }
    Item {
        id: credentials
        anchors.fill: parent
        visible: !page.choosing
        Item {
            id: portrait
            anchors.horizontalCenter: parent.horizontalCenter
            // Center the locked account group above its footer, measured at 600px and 768px.
            readonly property int preferredY: page.unlockOnly
                ? Math.round(parent.height * 0.525) - 166 : Math.round(parent.height / 2) - 134
            y: page.unlockOnly && page.canSwitchUser
                ? Math.max(-15, Math.min(preferredY, parent.height - 432))
                : preferredY
            width: 190
            height: 190
            Image {
                anchors.centerIn: parent
                width: 126
                height: 126
                source: page.art("user.png")
            }
            Image {
                anchors.centerIn: parent
                width: 126
                height: 126
                source: page.userPicture.toString() ? page.userPicture : !page.unlockOnly && !page.manual && page.account ? "file:///var/lib/AccountsService/icons/" + encodeURIComponent(page.account) : ""
                fillMode: Image.PreserveAspectCrop
            }
            Image { anchors.fill: parent; source: Qt.resolvedUrl("AeroPortraitFrame.svg") }
        }
        Text {
            id: nameLabel
            anchors.top: portrait.bottom
            anchors.topMargin: 0
            anchors.horizontalCenter: parent.horizontalCenter
            color: "white"
            style: Text.Raised
            styleColor: "#344853"
            font.family: page.uiFamily
            font.pixelSize: page.largeText ? 30 : 23
            width: Math.min(implicitWidth, parent.width - 32)
            elide: Text.ElideRight
            text: page.manual ? qsTr("Other user") : page.account
        }
        Text {
            id: lockedLabel
            anchors.top: nameLabel.bottom
            anchors.horizontalCenter: parent.horizontalCenter
            visible: page.unlockOnly
            text: qsTr("Locked")
            color: nameLabel.color
            style: nameLabel.style
            styleColor: nameLabel.styleColor
            font.family: nameLabel.font.family
            font.pixelSize: page.largeText ? 16 : 12
        }
        component CredentialField: TextField {
            id: field
            width: 225
            height: page.largeText ? 32 : page.unlockOnly ? 25 : 24
            color: "#171717"
            placeholderTextColor: "#555555"
            leftPadding: 6
            topPadding: 0
            bottomPadding: 0
            font.family: page.uiFamily
            font.pixelSize: page.largeText ? 18 : 13
            selectByMouse: true
            background: Item {
                Rectangle {
                    anchors.fill: parent
                    visible: page.unlockOnly
                    color: "#80ffffff"
                    Rectangle {
                        anchors.fill: parent
                        anchors.margins: 1
                        color: "white"
                        border.color: "#666666"
                    }
                }
                Image {
                    anchors.fill: parent
                    visible: !page.unlockOnly
                    source: page.art(field.activeFocus ? "input-focus.svg" : "input.svg")
                }
            }
        }
        Column {
            id: fields
            anchors.top: lockedLabel.visible ? lockedLabel.bottom : nameLabel.bottom
            anchors.topMargin: page.unlockOnly ? 6 : 8
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 4
            CredentialField {
                id: userField
                visible: page.manual
                placeholderText: qsTr("User name")
                onAccepted: password.forceActiveFocus()
            }
            CredentialField {
                id: password
                objectName: "aeroPassword"
                echoMode: page.reveal ? TextInput.Normal : TextInput.Password
                placeholderText: qsTr("Password")
                onAccepted: page.submit()
                Button {
                    id: go
                    anchors.left: parent.right
                    anchors.leftMargin: 4
                    anchors.verticalCenter: parent.verticalCenter
                    width: 30
                    height: 30
                    hoverEnabled: true
                    Accessible.name: page.unlockOnly ? qsTr("Unlock") : qsTr("Log on")
                    background: Image { source: page.art(go.down ? "gopressed.svg" : go.hovered || go.activeFocus ? "gohover.svg" : "go.svg") }
                    onClicked: page.submit()
                }
            }
        }
        Text {
            id: failure
            anchors.top: fields.bottom
            anchors.topMargin: 6
            anchors.horizontalCenter: parent.horizontalCenter
            color: "white"
            font.family: page.uiFamily
            font.pixelSize: page.largeText ? 18 : 13
        }
        GlassButton {
            anchors.top: page.unlockOnly ? portrait.bottom : fields.bottom
            anchors.topMargin: page.unlockOnly ? 138 : 48
            anchors.horizontalCenter: parent.horizontalCenter
            width: Math.max(108, contentItem.implicitWidth + 20)
            height: page.largeText ? 34 : 28
            objectName: "aeroSwitchUser"
            visible: !page.unlockOnly || page.canSwitchUser
            text: qsTr("Switch User")
            onClicked: {
                password.clear();
                if (page.unlockOnly) {
                    page.switchUserRequested();
                } else {
                    page.choosing = true;
                    accountList.forceActiveFocus();
                }
            }
        }
    }
    GridView {
        id: accountList
        anchors.centerIn: parent
        visible: page.choosing
        cellWidth: 140
        cellHeight: 145
        width: Math.max(1, Math.min(count, Math.floor(page.width / cellWidth))) * cellWidth
        height: Math.min(page.height - 100, Math.ceil(count / Math.max(1, width / cellWidth)) * cellHeight)
        clip: true
        model: page.unlockOnly ? [] : [...page.users, ""]
        Keys.onReturnPressed: page.selectUser(model[currentIndex])
        delegate: Button {
            id: tile
            required property string modelData
            required property int index
            width: accountList.cellWidth
            height: accountList.cellHeight
            onClicked: page.selectUser(modelData)
            Accessible.name: modelData || qsTr("Other user")
            background: Rectangle { radius: 5; color: tile.hovered || (accountList.activeFocus && accountList.currentIndex === tile.index) ? "#407ed2ef" : "transparent" }
            contentItem: Column {
                Item {
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: 110; height: 110
                    Image { anchors.centerIn: parent; width: 74; height: 74; source: page.art("user.png") }
                    Image { anchors.centerIn: parent; width: 74; height: 74; source: tile.modelData ? "file:///var/lib/AccountsService/icons/" + encodeURIComponent(tile.modelData) : ""; fillMode: Image.PreserveAspectCrop }
                    Image { anchors.fill: parent; source: Qt.resolvedUrl("AeroPortraitFrame.svg") }
                }
                Text {
                    width: parent.width
                    horizontalAlignment: Text.AlignHCenter
                    text: tile.Accessible.name
                    elide: Text.ElideRight
                    color: "white"
                    font.family: page.uiFamily
                    font.pixelSize: page.largeText ? 20 : 15
                }
            }
        }
    }
    Row {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 22
        spacing: 7
        Image {
            width: 35
            height: 35
            visible: !!page.brandLogo.toString()
            source: page.brandLogo
            fillMode: Image.PreserveAspectFit
        }
        Text {
            anchors.verticalCenter: parent.verticalCenter
            font.family: page.uiFamily
            font.pixelSize: 26
            color: "white"
            text: page.brandText
        }
    }
    GlassButton {
        id: options
        objectName: "aeroAccessibility"
        anchors.left: parent.left
        anchors.bottom: parent.bottom
        anchors.leftMargin: 34
        anchors.bottomMargin: 34
        width: 38
        height: 28
        sprite: "access-button"
        glyph: "12213.svg"
        Accessible.name: qsTr("Ease of Access and sign-in options")
        onClicked: settings.open()
        Menu {
            id: settings
            font.family: page.uiFamily
            font.pixelSize: page.largeText ? 17 : 13
            y: -height
            MenuItem {
                objectName: "aeroLargeText"
                text: qsTr("Make text larger")
                checkable: true
                checked: page.largeText
                onTriggered: page.largeText = checked
            }
            MenuItem {
                text: qsTr("On-screen keyboard")
                enabled: Keyboards.KWinVirtualKeyboard.available
                onTriggered: {
                    if (page.manual && !userField.text) userField.forceActiveFocus();
                    else password.forceActiveFocus();
                    Keyboards.KWinVirtualKeyboard.forceActivate();
                }
            }
            Menu {
                id: sessionMenu
                font.family: page.uiFamily
                font.pixelSize: page.largeText ? 17 : 13
                title: qsTr("Session")
                enabled: page.sessions.length > 1
                Instantiator {
                    model: page.sessions
                    delegate: MenuItem {
                        required property string modelData
                        required property int index
                        text: modelData
                        checkable: true
                        checked: page.sessionIndex === index
                        onTriggered: page.sessionIndex = index
                    }
                    onObjectAdded: (index, item) => sessionMenu.insertItem(index, item)
                    onObjectRemoved: (index, item) => sessionMenu.removeItem(item)
                }
            }
            MenuItem {
                text: qsTr("Show password")
                checkable: true
                checked: page.reveal
                onTriggered: page.reveal = checked
            }
        }
    }
    Row {
        anchors.right: parent.right
        anchors.bottom: options.bottom
        anchors.rightMargin: 34
        visible: page.greeter.canPowerOff || page.greeter.canReboot
        GlassButton {
            objectName: "aeroShutdown"
            width: 38
            height: 28
            sprite: "power"
            glyph: "power-glyph.svg"
            Accessible.name: qsTr("Shut down")
            enabled: page.greeter.canPowerOff
            onClicked: page.greeter.powerOff()
        }
        Button {
            id: powerOptions
            objectName: "aeroPowerOptions"
            width: 20
            height: 28
            Accessible.name: qsTr("Power options")
            hoverEnabled: true
            background: Image {
                source: page.art((powerOptions.down ? "12301" : powerOptions.hovered
                    ? (powerOptions.activeFocus ? "12298" : "12300")
                    : (powerOptions.activeFocus ? "12299" : "12302")) + ".svg")
            }
            contentItem: Item {
                Image { anchors.centerIn: parent; source: page.art("power-glyph-arrow.svg") }
            }
            onClicked: powerMenu.open()
            Menu {
                id: powerMenu
                font.family: page.uiFamily
                font.pixelSize: page.largeText ? 17 : 13
                objectName: "aeroPowerMenu"
                y: -height
                x: powerOptions.width - width
                MenuItem { text: qsTr("Restart"); enabled: page.greeter.canReboot; onTriggered: page.greeter.reboot() }
                MenuItem { text: qsTr("Shut down"); enabled: page.greeter.canPowerOff; onTriggered: page.greeter.powerOff() }
            }
        }
    }
    Connections {
        target: page.greeter
        function onLoginFailed() {
            failure.text = qsTr("The user name or password is incorrect.");
            password.clear();
            password.forceActiveFocus();
        }
    }
    Component.onCompleted: if (!unlockOnly && choosing) accountList.forceActiveFocus(); else password.forceActiveFocus()
}
