import QtQuick
import QtQuick.Window
import QtCore
import "settings.js" as Settings

Rectangle {
    id: page
    property bool shuttingDown: false
    property string statusText: shuttingDown ? qsTr("Shutting down...") : qsTr("Welcome")
    property int frame: 0
    property bool animated: true
    readonly property url art: {
        const folder = "chicago95/session/";
        const widthPixels = Math.round(width * Screen.devicePixelRatio);
        const heightPixels = Math.round(height * Screen.devicePixelRatio);
        const version = widthPixels === 1024 && heightPixels === 768 ? "background-1024x768.jpg"
            : Math.abs(width * 3 - height * 4) < 1 ? "background-4x3.jpg" : "";
        const fitted = version ? StandardPaths.locate(StandardPaths.GenericDataLocation, folder + version) : "";
        return fitted.toString() ? fitted : StandardPaths.locate(StandardPaths.GenericDataLocation, folder + "background");
    }
    readonly property string uiFamily: Qt.fontFamilies().includes("Segoe UI") ? "Segoe UI"
        : Qt.fontFamilies().includes("Selawik") ? "Selawik" : "sans-serif"
    readonly property url strip: {
        const svg = StandardPaths.locate(StandardPaths.GenericDataLocation, "chicago95/session/spinner.svg");
        return svg.toString() ? svg : StandardPaths.locate(StandardPaths.GenericDataLocation, "chicago95/session/spinner.png");
    }
    color: "#196ba4"
    Image { anchors.fill: parent; source: page.art; fillMode: Image.PreserveAspectCrop }
    Row {
        x: page.shuttingDown ? Math.round(parent.width / 2) - 103 : (parent.width - width) / 2
        anchors.verticalCenter: parent.verticalCenter
        // The SP1 shutdown row sits 50 logical pixels above centre at both 600 and 768 px.
        anchors.verticalCenterOffset: page.shuttingDown ? -50 : 0
        spacing: page.shuttingDown ? 12 : 8
        Item {
            objectName: "sessionSpinner"
            width: 20; height: 20; clip: true
            anchors.verticalCenter: parent.verticalCenter
            Image {
                width: 18 * parent.width; height: parent.height
                x: -page.frame * parent.width
                source: page.strip
            }
        }
        Text {
            text: page.statusText
            color: "white"
            font.family: page.uiFamily
            font.pixelSize: page.shuttingDown ? 24 : 23
            font.letterSpacing: page.shuttingDown ? -0.6 : 0
            style: Text.Raised
            styleColor: "#475763"
        }
    }
    Timer {
        running: page.animated && page.visible
        repeat: true
        interval: page.shuttingDown ? 46 : 67
        onTriggered: page.frame = (page.frame + 1) % 18
    }
    Row {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: Settings.edition ? 29 : 22
        spacing: 7
        visible: !!Settings.brandText || !!Settings.brandLogo
        Image {
            width: Settings.edition ? 28 : 35
            height: width
            anchors.verticalCenter: parent.verticalCenter
            source: Settings.brandLogo
            visible: status === Image.Ready
            fillMode: Image.PreserveAspectFit
        }
        Text {
            id: brandName
            anchors.verticalCenter: parent.verticalCenter
            text: Settings.brandText
            color: "white"
            font.family: page.uiFamily
            font.pixelSize: Settings.edition ? 27 : 26
        }
        Text {
            anchors.baseline: brandName.baseline
            visible: !!Settings.brandText && !!Settings.edition
            text: Settings.edition
            color: "white"
            font.family: page.uiFamily
            font.pixelSize: 19
        }
    }
}
