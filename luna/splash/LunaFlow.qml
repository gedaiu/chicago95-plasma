import QtQuick 2.15
import "../sddm"

Item {
    id: root
    objectName: "loginFlow"
    property string stage: "boot"
    property string userName: ""
    property string userPicture: ""
    property url desktopImage
    property int fadeMilliseconds: 500
    signal sessionRequested(string user)
    signal desktopShown()
    readonly property var login: loginScreen

    function restart() {
        fade.stop();
        stage = "boot";
        welcome.opacity = 1;
        loginScreen.selectedName = "";
        loginScreen.message = "";
        loginScreen.loadingStatus = "";
    }
    function showLogin() {
        fade.stop();
        stage = "login";
        welcome.opacity = 1;
        loginScreen.selectedName = "";
        loginScreen.message = "";
        loginScreen.loadingStatus = "";
    }
    function authenticated() {
        if (stage !== "login") return;
        userName = loginScreen.selectedName;
        for (let i = 0; i < accounts.count; i++) {
            const account = accounts.itemAt(i);
            if (account.model.name === userName) userPicture = account.model.icon || "";
        }
        stage = "loading";
        sessionRequested(userName);
    }
    function showLogoff() { stage = "logging-off"; }
    function showShutdown() { stage = "shutting-down"; }
    function desktopReady() {
        if (stage !== "loading" || desktop.status !== Image.Ready) return false;
        stage = "fading";
        fade.start();
        return true;
    }
    Rectangle { anchors.fill: parent; color: "black"; visible: root.stage === "powered-off" }
    Image {
        id: desktop
        anchors.fill: parent
        source: root.desktopImage
        fillMode: Image.PreserveAspectCrop
        visible: root.stage === "fading" || root.stage === "desktop"
    }
    LunaSplash {
        anchors.fill: parent
        visible: root.stage === "boot"
        animated: visible
        edition: config.edition || "Professional"
        brandText: config.brandText || ""
        company: config.company || ""
        brandLogo: !config.brandLogo ? "" : String(config.brandLogo).indexOf("/") === 0
                   ? config.brandLogo : Qt.resolvedUrl("../../" + config.brandLogo)
    }
    LunaLogin {
        id: loginScreen
        anchors.fill: parent
        visible: root.stage === "login"
        enabled: visible
        users: userModel
        sessions: sessionModel
        greeter: sddm
        theme: config
        keyboardState: keyboard
    }
    LunaWelcome {
        id: welcome
        anchors.fill: parent
        visible: root.stage === "loading" || root.stage === "fading"
        userName: root.userName
        userPicture: root.userPicture
        branding: config
    }
    LunaStatus {
        anchors.fill: parent
        visible: root.stage === "logging-off" || root.stage === "shutting-down"
        statusText: root.stage === "logging-off" ? "Logging off..." : "Windows is shutting down..."
        branding: config
    }
    Repeater {
        id: accounts
        model: userModel
        delegate: Item { required property var model }
    }
    NumberAnimation {
        id: fade
        target: welcome
        property: "opacity"
        from: 1
        to: 0
        duration: root.fadeMilliseconds
        onFinished: { root.stage = "desktop"; root.desktopShown(); }
    }
    Connections {
        target: sddm
        function onLoginSucceeded() { root.authenticated(); }
    }
}
