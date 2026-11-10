import QtQuick 2.15
import "settings.js" as Settings

// Plasma loading screen. "classic": a picture filling the screen. "2000": the 2000 start-up screen,
// laid out in the original's 640x480 pixels (measured by tests/test_references.py) and scaled to the
// screen height: logo and name on a near-white page, a three-tone blue strip, a grey bar with a
// block progress bar that follows Plasma's start-up stages, and a footer line.
// Setup writes settings.js with the user's texts and pictures.
Rectangle {
    id: root
    property int stage

    readonly property bool modern: Settings.style === "2000"
    readonly property real unit: height / 480
    readonly property real layoutX: (width - 640 * unit) / 2  // the 640-wide layout, centred ("left" is taken by Item)
    readonly property int stages: 6

    function px(value) { return Math.round(value * unit) }

    color: "#f7f7f7"

    Image {
        visible: !root.modern
        anchors.fill: parent
        source: Settings.picture.startsWith("/") ? "file://" + Settings.picture : Settings.picture
        fillMode: Image.PreserveAspectCrop
    }

    Item {
        visible: root.modern
        anchors.fill: parent

        Image {
            id: logo
            visible: status === Image.Ready
            source: Settings.brandLogo ? "file://" + Settings.brandLogo : ""
            x: root.layoutX + root.px(262)
            y: root.px(38)
            width: root.px(190)
            height: root.px(190)
            sourceSize.width: width * 2
            sourceSize.height: height * 2
            fillMode: Image.PreserveAspectFit
            smooth: !Settings.brandLogo.endsWith(".png")  // pixel-art logos stay sharp
        }

        Column {
            x: root.layoutX + root.px(118)
            y: root.px(238)
            // Words bold, numbers thin, like the Start menu banner.
            Text {
                textFormat: Text.RichText
                font.family: "Arial"
                font.pixelSize: root.px(48)
                color: "#000000"
                text: (Settings.brandText.match(/\s*\d+|\s*[^\d]+/g) || [])
                      .map(part => /^\s*\d+$/.test(part) ? part : "<b>" + part + "</b>").join("")
            }
            Text {
                anchors.right: parent.right
                font.family: "Arial"
                font.pixelSize: root.px(34)
                font.bold: true
                color: "#000000"
                text: Settings.edition
            }
        }

        // The strip: a pale line, ten rows of bright blue shading to navy then slate, a light line.
        Rectangle {
            x: 0; y: root.px(415); width: parent.width; height: root.px(1)
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0; color: "#deffff" }
                GradientStop { position: 1; color: "#efffff" }
            }
        }
        Rectangle {
            x: 0; y: root.px(416); width: parent.width; height: root.px(10)
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.00; color: "#0071d8" }
                GradientStop { position: 0.23; color: "#0071d8" }
                GradientStop { position: 0.39; color: "#0025a0" }
                GradientStop { position: 0.723; color: "#0025a0" }
                GradientStop { position: 0.725; color: "#133777" }
                GradientStop { position: 1.00; color: "#133777" }
            }
        }
        // The strip's left end is capped by darker corner pixels on its first and last coloured rows.
        Rectangle { x: 0; y: root.px(416); width: root.px(1); height: root.px(1); color: "#4d6596" }
        Rectangle { x: 0; y: root.px(425); width: root.px(1); height: root.px(1); color: "#4d6596" }
        Rectangle {
            x: 0; y: root.px(426); width: parent.width; height: root.px(1)
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0; color: "#a5cbec" }
                GradientStop { position: 1; color: "#bac4ed" }
            }
        }

        Rectangle {
            x: 0; y: root.px(427); width: parent.width; height: parent.height - y
            color: "#c1bfc3"
        }

        Text {
            x: root.layoutX + root.px(200)
            y: root.px(437)
            font.family: "MS W98 UI"
            font.pixelSize: root.px(11)
            renderType: Text.NativeRendering
            color: "#000000"
            text: Settings.loadingText
        }

        // Sunken progress bar: shadow top-left, white bottom-right, pale inside, 8px navy blocks 1px apart.
        Item {
            x: root.layoutX + root.px(273); y: root.px(436)
            width: root.px(165); height: root.px(10)
            Rectangle { anchors.fill: parent; color: "#bac4ed" }
            Rectangle { x: 0; y: 0; width: parent.width; height: root.px(1); color: "#7d8196" }
            Rectangle { x: 0; y: 0; width: root.px(1); height: parent.height; color: "#7d8196" }
            // The shadow owns the bottom-left corner pixel; the white edge starts one pixel in.
            Rectangle { x: root.px(1); y: parent.height - root.px(1); width: parent.width - root.px(1); height: root.px(1); color: "#f7f7f7" }
            Rectangle { x: parent.width - root.px(1); y: 0; width: root.px(1); height: parent.height; color: "#f7f7f7" }
            Repeater {
                model: Math.round(Math.min(root.stage, root.stages) / root.stages * 18)
                Rectangle {
                    x: root.px(1 + 9 * index); y: root.px(1)
                    width: root.px(8); height: root.px(8)
                    color: "#0025a0"
                }
            }
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            y: root.px(458)
            font.family: "MS W98 UI"
            font.pixelSize: root.px(11)
            renderType: Text.NativeRendering
            color: "#000000"
            text: Settings.footer
        }
    }
}
