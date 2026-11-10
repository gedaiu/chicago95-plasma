import QtQuick 2.15

// Plasma loading screen. "classic": the Chicago95 background picture. "2000": a white page with the
// Start logo and banner text, a blue strip and a grey bar with a progress bar that follows Plasma's
// start-up stages. Setup writes the three settings below into the installed copy.
Rectangle {
    id: root
    property int stage

    readonly property string splashStyle: "classic"
    readonly property string brandText: "Chicago95"
    readonly property string brandLogo: ""

    readonly property bool modern: splashStyle === "2000"
    readonly property real unit: height / 768  // the layout is drawn for 1024x768 and scaled
    readonly property int stages: 6

    color: "#ffffff"

    Image {
        visible: !root.modern
        anchors.fill: parent
        source: "images/background.png"
        fillMode: Image.PreserveAspectCrop
    }

    Item {
        visible: root.modern
        anchors.fill: parent

        Image {
            id: logo
            visible: status === Image.Ready
            source: root.brandLogo ? "file://" + root.brandLogo : ""
            anchors.horizontalCenter: parent.horizontalCenter
            y: 90 * root.unit
            width: 260 * root.unit
            height: 260 * root.unit
            sourceSize.width: width * 2
            sourceSize.height: height * 2
            fillMode: Image.PreserveAspectFit
            // Pixel-art logos (the classic flag, a PNG) stay sharp; vector logos are drawn smooth.
            smooth: !root.brandLogo.endsWith(".png")
        }

        Column {
            anchors.horizontalCenter: parent.horizontalCenter
            y: (logo.visible ? 375 : 260) * root.unit
            spacing: 0

            // Words bold, numbers thin, like the Start menu banner.
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                textFormat: Text.RichText
                font.family: "MS W98 UI"
                font.pixelSize: 72 * root.unit
                color: "#000000"
                text: (root.brandText.match(/\s*\d+|\s*[^\d]+/g) || [])
                      .map(part => /^\s*\d+$/.test(part) ? part : "<b>" + part + "</b>").join("")
            }
            Text {
                anchors.right: parent.right
                font.family: "MS W98 UI"
                font.pixelSize: 40 * root.unit
                font.bold: true
                color: "#000000"
                text: "Professional"
            }
        }

        Rectangle {
            id: strip
            anchors.left: parent.left
            anchors.right: parent.right
            y: parent.height - 102 * root.unit
            height: 16 * root.unit
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0; color: "#1A5CC8" }
                GradientStop { position: 0.5; color: "#0A3BA8" }
                GradientStop { position: 1; color: "#3C8CEC" }
            }
        }

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: strip.bottom
            anchors.bottom: parent.bottom
            color: "#c0c0c0"

            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                y: 16 * root.unit
                spacing: 8 * root.unit
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Starting up..."
                    font.family: "MS W98 UI"
                    font.pixelSize: 15 * root.unit
                    color: "#000000"
                }
                // Sunken bar filled with navy blocks as Plasma reports its start-up stages.
                Rectangle {
                    id: bar
                    width: 262 * root.unit
                    height: 16 * root.unit
                    color: "#ffffff"
                    border.width: Math.max(1, Math.round(root.unit))
                    border.color: "#808080"
                    Row {
                        x: 2 * root.unit; y: 2 * root.unit
                        spacing: 2 * root.unit
                        Repeater {
                            model: Math.round(Math.min(root.stage, root.stages) / root.stages * 26)
                            Rectangle { width: 8 * root.unit; height: bar.height - 4 * root.unit; color: "#0A246A" }
                        }
                    }
                }
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                y: 50 * root.unit
                text: "Chicago95 for KDE Plasma"
                font.family: "MS W98 UI"
                font.pixelSize: 15 * root.unit
                color: "#000000"
            }
        }
    }
}
