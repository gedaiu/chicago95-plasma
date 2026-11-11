import QtQuick 2.15
import "settings.js" as Settings

// Plasma loading screen. "classic": a picture filling the screen. "2000": the 2000 start-up screen,
// laid out in the original's 640x480 pixels (measured by tests/test_loading_screen_reference.py) and scaled to the
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

    function px(value) {
        return Math.round(value * unit);
    }

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

        BrandMark {
            x: root.layoutX + root.px(265)
            y: root.px(44)
            unit: root.unit
            paper: root.color
            logo: Settings.brandLogo
        }

        // The name: words heavy, numbers thin, like the Start menu banner; the company's name above it
        // in plain letters, the edition and the tagline right-aligned under it. Sizes and baselines
        // are the original's (tests/test_loading_screen_reference.py).
        Text {
            visible: !!Settings.company
            x: root.layoutX + root.px(116)
            y: root.unit * 255 - baselineOffset
            font.family: "Arial"
            font.pixelSize: root.unit * 22
            color: "#000000"
            text: Settings.company || ""
        }
        Row {
            id: nameRow
            x: root.layoutX + root.px(136)
            spacing: root.unit * 8
            Repeater {
                model: (String(Settings.brandText).match(/\d+|[^\d]+/g) || []).map(part => part.trim()).filter(part => part)
                Item {
                    readonly property bool isNumber: /^\d+$/.test(modelData)
                    width: isNumber ? thin.width : heavy.width
                    height: 1  // the parts place themselves on the baseline; Row skips empty items
                    HeavyText {
                        id: heavy
                        visible: !parent.isNumber
                        text: modelData
                        pixelSize: root.unit * 58
                        embolden: root.unit * 1.2
                        letterSpacing: root.unit * 1.1
                        baselineY: root.unit * 300
                    }
                    Text {
                        id: thin
                        visible: parent.isNumber
                        y: root.unit * 302 - baselineOffset
                        font.family: "Arial"
                        font.pixelSize: root.unit * 50
                        font.letterSpacing: root.unit * -3
                        color: "#000000"
                        text: modelData
                    }
                }
            }
        }
        HeavyText {
            x: nameRow.x + nameRow.width - width + root.px(3)
            text: Settings.edition
            pixelSize: root.unit * 40
            embolden: root.unit
            letterSpacing: root.unit * 0.9
            baselineY: root.unit * 337
        }
        Text {
            x: nameRow.x + nameRow.width - width
            y: root.unit * 354 - baselineOffset
            font.family: "Arial"
            font.bold: true
            font.pixelSize: root.unit * 13
            font.letterSpacing: root.unit
            color: "#000000"
            text: Settings.tagline || ""
        }

        // Top right: the company's logo, or its name in bold italics when there is no logo.
        Image {
            id: companyLogo
            visible: status === Image.Ready
            source: Settings.companyLogo ? "file://" + Settings.companyLogo : ""
            x: root.layoutX + root.px(617) - width
            y: root.px(12)
            width: root.px(120)
            height: root.px(24)
            sourceSize.width: width * 2
            sourceSize.height: height * 2
            fillMode: Image.PreserveAspectFit
            horizontalAlignment: Image.AlignRight
        }
        HeavyText {
            visible: !companyLogo.visible && !!Settings.company
            x: root.layoutX + root.unit * 610 - width
            text: Settings.company || ""
            italic: true
            pixelSize: root.unit * 22
            embolden: root.unit * 0.6
            letterSpacing: 0
            baselineY: root.unit * 32
        }

        // The strip: a pale line, ten rows of bright blue shading to navy then slate, a light line.
        Rectangle {
            x: 0
            y: root.px(415)
            width: parent.width
            height: root.px(1)
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop {
                    position: 0
                    color: "#deffff"
                }
                GradientStop {
                    position: 1
                    color: "#efffff"
                }
            }
        }
        Rectangle {
            x: 0
            y: root.px(416)
            width: parent.width
            height: root.px(10)
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop {
                    position: 0.00
                    color: "#0071d8"
                }
                GradientStop {
                    position: 0.23
                    color: "#0071d8"
                }
                GradientStop {
                    position: 0.39
                    color: "#0025a0"
                }
                GradientStop {
                    position: 0.723
                    color: "#0025a0"
                }
                GradientStop {
                    position: 0.725
                    color: "#133777"
                }
                GradientStop {
                    position: 1.00
                    color: "#133777"
                }
            }
        }
        // The strip's left end is capped by darker corner pixels on its first and last coloured rows.
        Rectangle {
            x: 0
            y: root.px(416)
            width: root.px(1)
            height: root.px(1)
            color: "#4d6596"
        }
        Rectangle {
            x: 0
            y: root.px(425)
            width: root.px(1)
            height: root.px(1)
            color: "#4d6596"
        }
        Rectangle {
            x: 0
            y: root.px(426)
            width: parent.width
            height: root.px(1)
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop {
                    position: 0
                    color: "#a5cbec"
                }
                GradientStop {
                    position: 1
                    color: "#bac4ed"
                }
            }
        }

        Rectangle {
            x: 0
            y: root.px(427)
            width: parent.width
            height: parent.height - y
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

        // Sunken progress bar: grey shadow on top, darker on the left, white bottom-right, the bar's own grey
        // inside, 8px navy blocks 1px apart.
        Item {
            x: root.layoutX + root.px(273)
            y: root.px(436)
            width: root.px(165)
            height: root.px(10)
            Rectangle {
                x: 0
                y: 0
                width: root.px(1)
                height: parent.height
                color: "#7d8196"
            }
            Rectangle {
                x: 0
                y: 0
                width: parent.width
                height: root.px(1)
                color: "#898689"
            }
            Rectangle {
                x: 0
                y: parent.height - height
                width: root.px(1)
                height: root.px(1)
                color: "#898689"
            }
            // The shadow owns the bottom-left and top-right corner pixels; the white edges start one pixel in.
            Rectangle {
                x: root.px(1)
                y: parent.height - root.px(1)
                width: parent.width - root.px(1)
                height: root.px(1)
                color: "#f7f7f7"
            }
            Rectangle {
                x: parent.width - root.px(1)
                y: root.px(1)
                width: root.px(1)
                height: parent.height - root.px(1)
                color: "#f7f7f7"
            }
            Repeater {
                model: Math.round(Math.min(root.stage, root.stages) / root.stages * 18)
                Rectangle {
                    x: root.px(1 + 9 * index)
                    y: root.px(1)
                    width: root.px(8)
                    height: root.px(8)
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
