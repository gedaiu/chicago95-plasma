import QtQuick
import QtCore
import "settings.js" as Settings

Rectangle {
    id: page
    property bool shuttingDown: false
    property string statusText: shuttingDown ? qsTr("Shutting down...") : qsTr("Welcome")
    property int frame: 0
    property bool animated: true
    readonly property url art: StandardPaths.locate(StandardPaths.GenericDataLocation, "chicago95/session/background")
    readonly property url strip: {
        const svg = StandardPaths.locate(StandardPaths.GenericDataLocation, "chicago95/session/spinner.svg");
        return svg.toString() ? svg : StandardPaths.locate(StandardPaths.GenericDataLocation, "chicago95/session/spinner.png");
    }
    color: "#196ba4"
    Image { anchors.fill: parent; source: page.art; fillMode: Image.PreserveAspectCrop }
    Row {
        anchors.centerIn: parent
        // The SP1 shutdown row sits 50 logical pixels above centre at both 600 and 768 px.
        anchors.verticalCenterOffset: page.shuttingDown ? -50 : 0
        anchors.horizontalCenterOffset: page.shuttingDown ? -2 : 0
        spacing: 8
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
            font.family: "Segoe UI"
            font.pixelSize: page.shuttingDown ? 24 : 23
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
        anchors.bottomMargin: 22
        spacing: 7
        Image {
            width: 35; height: 35
            source: Settings.brandLogo
            visible: status === Image.Ready
            fillMode: Image.PreserveAspectFit
        }
        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: Settings.brandText
            color: "white"
            font.family: "Segoe UI"
            font.pixelSize: 26
        }
    }
}
