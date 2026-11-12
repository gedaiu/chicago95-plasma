import QtQuick 2.15

// The classic 2000 status dialog. The caller supplies real session status.
Rectangle {
    id: root
    property string statusText: "Starting your desktop..."
    property url banner: "brand-banner.png"
    width: 417
    height: 144
    color: "#c0c0c0"
    border.color: "#404040"
    Rectangle { x: 1; y: 1; width: parent.width - 3; height: 1; color: "white" }
    Rectangle { x: 1; y: 1; width: 1; height: parent.height - 3; color: "white" }
    Rectangle {
        x: 3; y: 3; width: parent.width - 6; height: 18; color: "#000080"
        Text { x: 2; anchors.verticalCenter: parent.verticalCenter; text: "Please wait..."
            color: "white"; font.family: "MS W98 UI"; font.pixelSize: 11; font.bold: true }
    }
    Image { x: 3; y: 21; width: 411; height: 77; source: root.banner; fillMode: Image.PreserveAspectCrop; smooth: false }
    Text { objectName: "sessionStatusText"; x: 14; y: 113; text: root.statusText
        color: "black"; font.family: "MS W98 UI"; font.pixelSize: 11 }
}
