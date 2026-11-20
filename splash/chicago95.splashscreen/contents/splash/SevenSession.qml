import QtQuick
import QtCore
import "settings.js" as Settings

Rectangle {
    id: page
    property string statusText: qsTr("Welcome")
    property int frame: 0
    property bool animated: true
    readonly property url art: StandardPaths.locate(StandardPaths.GenericDataLocation, "chicago95/session/background")
    readonly property url strip: StandardPaths.locate(StandardPaths.GenericDataLocation, "chicago95/session/spinner.png")
    color: "#196ba4"
    Image { anchors.fill: parent; source: page.art; fillMode: Image.PreserveAspectCrop }
    Row {
        anchors.centerIn: parent
        spacing: 8
        Item {
            objectName: "sessionSpinner"
            width: 20; height: 20
            anchors.verticalCenter: parent.verticalCenter
            Image {
                anchors.fill: parent
                source: page.strip
                sourceClipRect: Qt.rect(page.frame * 20, 0, 20, 20)
            }
        }
        Text {
            text: page.statusText
            color: "white"
            font.family: "Segoe UI"
            font.pixelSize: 23
            style: Text.Raised
            styleColor: "#475763"
        }
    }
    Timer {
        running: page.animated && page.visible
        repeat: true
        interval: 67
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
