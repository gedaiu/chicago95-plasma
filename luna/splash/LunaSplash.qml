/*
 * The Windows XP boot splash at 640x480, the layout measured from tests/references/xpsplash.png.
 *
 * Fitted gradients. The reference is a 256-colour screenshot, so each block's profile was read from the
 * columns 308..312 / 316..320 / 324..328 averaged, rows 354..362 (the 9 rows of a block), and reduced to the
 * fewest linear stops that stay within 12 per channel of the 3-row moving average (max deviation 0.3, 6.0, 6.7).
 * Positions are fractions of the block's 9px height, sampled at pixel centres: row k is (k + 0.5) / 9.
 * The three blocks of a group are three different slices of the animated sheen, so each has its own stops.
 */
import QtQuick 2.15
import "../qml"

Rectangle {
    id: root

    property int stage
    property string edition: "Professional"
    property string footer: "Copyright © 1985-2001\nMicrosoft Corporation"
    property string family: "Trebuchet MS"
    property bool animated: true
    property real phase: 0

    readonly property real unit: Math.min(width / 640, height / 480)
    readonly property real layoutX: (width - 640 * unit) / 2
    readonly property real layoutY: (height - 480 * unit) / 2
    readonly property real wordmarkScale: 1.85
    readonly property int sweepMilliseconds: 1000
    readonly property int blockCount: 3
    readonly property real blockPitch: 8
    readonly property real groupWidth: blockPitch * blockCount - 2
    readonly property real troughInnerWidth: 122
    readonly property string navy: "#2838c7"
    readonly property string blue: "#5979ef"
    readonly property string sheen: "#869ef3"
    readonly property real blockHeight: 9

    color: "#000000"

    component Block: Rectangle {
        width: 6 * root.unit
        height: root.blockHeight * root.unit
    }

    NumberAnimation on phase {
        running: root.animated
        from: 0
        to: 1
        duration: root.sweepMilliseconds
        loops: Animation.Infinite
    }

    XpWordmark {
        x: root.layoutX + 210 * root.unit
        y: root.layoutY + 124 * root.unit
        unit: root.unit * root.wordmarkScale
        edition: root.edition
        textColor: "#efefef"
        family: root.family
    }

    Rectangle {
        id: trough
        x: root.layoutX + 255 * root.unit
        y: root.layoutY + 351 * root.unit
        width: 126 * root.unit
        height: 15 * root.unit
        radius: 4 * root.unit
        color: "#000000"
        border.width: root.unit
        border.color: "#b2b2b2"
        Rectangle {
            anchors.fill: parent
            anchors.margins: root.unit
            radius: 3 * root.unit
            color: "transparent"
            border.width: root.unit
            border.color: "#414141"
        }
        Item {
            x: 2 * root.unit
            y: 2 * root.unit
            width: root.troughInnerWidth * root.unit
            height: parent.height - 4 * root.unit
            clip: true
            Row {
                x: (-root.groupWidth + root.phase * (root.troughInnerWidth + root.groupWidth)) * root.unit
                y: 1 * root.unit
                spacing: 2 * root.unit
                Block {
                    gradient: Gradient {
                        GradientStop {
                            position: 0.056
                            color: root.navy
                        }
                        GradientStop {
                            position: 0.167
                            color: root.blue
                        }
                        GradientStop {
                            position: 0.278
                            color: root.sheen
                        }
                        GradientStop {
                            position: 0.389
                            color: root.sheen
                        }
                        GradientStop {
                            position: 0.5
                            color: root.blue
                        }
                        GradientStop {
                            position: 0.611
                            color: root.navy
                        }
                    }
                }
                Block {
                    gradient: Gradient {
                        GradientStop {
                            position: 0.056
                            color: root.navy
                        }
                        GradientStop {
                            position: 0.167
                            color: root.blue
                        }
                        GradientStop {
                            position: 0.278
                            color: root.sheen
                        }
                        GradientStop {
                            position: 0.389
                            color: root.sheen
                        }
                        GradientStop {
                            position: 0.58
                            color: root.blue
                        }
                        GradientStop {
                            position: 0.7
                            color: root.navy
                        }
                    }
                }
                Block {
                    gradient: Gradient {
                        GradientStop {
                            position: 0.056
                            color: root.navy
                        }
                        GradientStop {
                            position: 0.167
                            color: root.blue
                        }
                        GradientStop {
                            position: 0.278
                            color: root.sheen
                        }
                        GradientStop {
                            position: 0.5
                            color: root.sheen
                        }
                        GradientStop {
                            position: 0.7
                            color: root.blue
                        }
                        GradientStop {
                            position: 0.78
                            color: root.navy
                        }
                    }
                }
            }
        }
    }

    Text {
        x: root.layoutX + 22 * root.unit
        y: root.layoutY + 433 * root.unit
        text: root.footer
        color: "#efefef"
        lineHeight: 1.1
        font.family: root.family
        font.pixelSize: 11 * root.unit
    }
    Text {
        x: root.layoutX + 546 * root.unit
        y: root.layoutY + 441 * root.unit
        text: "Microsoft"
        color: "#efefef"
        font.family: root.family
        font.bold: true
        font.italic: true
        font.pixelSize: 17 * root.unit
    }
}
