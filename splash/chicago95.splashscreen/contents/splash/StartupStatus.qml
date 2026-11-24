import QtQuick 2.15

// The classic 2000 status dialog. The caller supplies real session status.
Rectangle {
    id: root
    objectName: "startupStatus"
    property string statusText: "Loading your personal settings..."
    property url banner: "brand-banner.png"
    property real stripPhase: -1
    width: 443
    height: 127
    color: "#d4d0c8"
    border.color: "#404040"
    Rectangle { x: 1; y: 1; width: parent.width - 3; height: 1; color: "white" }
    Rectangle { x: 1; y: 1; width: 1; height: parent.height - 3; color: "white" }
    Rectangle {
        x: 3; y: 3; width: parent.width - 6; height: 18
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0; color: "#0a246a" }
            GradientStop { position: 1; color: "#a6caf0" }
        }
        Text { x: 2; anchors.verticalCenter: parent.verticalCenter; text: "Please wait..."
            color: "white"; font.family: "MS W98 UI"; font.pixelSize: 11; font.bold: true }
    }
    Image {
        x: 3; y: 22; width: parent.width - 6; height: 61; source: root.banner
        fillMode: Image.PreserveAspectCrop; mipmap: true
    }
    Item {
        id: strip
        objectName: "sessionStatusStrip"
        x: 3; y: 79; width: parent.width - 6; height: 4
        clip: true
        property real travel: 0
        readonly property real phase: root.stripPhase >= 0 ? root.stripPhase : travel
        NumberAnimation on travel {
            running: root.visible && root.stripPhase < 0
            from: 0
            to: 1
            // The Windows 2000 capture moves 175 of 548 pixels in 1.098 s.
            duration: 3460
            loops: Animation.Infinite
        }
        Repeater {
            model: 2
            Rectangle {
                required property int index
                width: strip.width
                height: strip.height
                x: (index - 1 + strip.phase) * width
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0; color: "#003452" }
                    GradientStop { position: 0.16; color: "#00598c" }
                    GradientStop { position: 0.32; color: "#63aade" }
                    GradientStop { position: 0.5; color: "#9cc3de" }
                    GradientStop { position: 0.68; color: "#63aade" }
                    GradientStop { position: 0.84; color: "#00598c" }
                    GradientStop { position: 1; color: "#003452" }
                }
            }
        }
    }
    Text { objectName: "sessionStatusText"; x: 14; y: 96; text: root.statusText
        color: "black"; font.family: "MS W98 UI"; font.pixelSize: 11 }
}
