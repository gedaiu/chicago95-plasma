import QtQuick 2.15
import QtQuick.Shapes 1.15

// The 2000 start-up screen's mark, in two layers: generated framed squares behind, the user's OS logo
// in front. Laid out in the original's pixels (210x196, measured from tests/references/w2kboot.png by
// tests/test_loading_screen_reference.py) and scaled by unit. Back to front: a blue square shading
// from the paper to navy along a slant, a yellow and a green bar under it, a darker orange frame
// offset to the lower right, then the orange frame whose top-left fades into the paper, holding the logo.
Item {
    id: mark
    property real unit: 1
    property color paper: "#f7f7f7"
    property string logo
    readonly property color orange: "#dd5d04"

    function px(value) {
        return Math.round(value * unit);
    }

    width: px(210)
    height: px(196)

    Shape {
        x: mark.px(57)
        y: mark.px(50)
        width: mark.px(153)
        height: mark.px(146)
        ShapePath {
            strokeColor: "transparent"
            // The top edge fades in along a slant: lower on the right than on the left.
            fillGradient: LinearGradient {
                x1: mark.px(130)
                y1: mark.px(-1)
                x2: mark.px(83)
                y2: mark.px(128)
                GradientStop {
                    position: 0.00
                    color: mark.paper
                }
                GradientStop {
                    position: 0.02
                    color: "#9acde1"
                }
                GradientStop {
                    position: 0.045
                    color: "#50b2e4"
                }
                GradientStop {
                    position: 0.075
                    color: "#0f9cf5"
                }
                GradientStop {
                    position: 0.13
                    color: "#058ced"
                }
                GradientStop {
                    position: 0.19
                    color: "#0279de"
                }
                GradientStop {
                    position: 0.24
                    color: "#026cd9"
                }
                GradientStop {
                    position: 0.32
                    color: "#0861d3"
                }
                GradientStop {
                    position: 0.44
                    color: "#0b5ad0"
                }
                GradientStop {
                    position: 0.57
                    color: "#0a4ec6"
                }
                GradientStop {
                    position: 0.65
                    color: "#0a41b8"
                }
                GradientStop {
                    position: 0.73
                    color: "#0936ac"
                }
                GradientStop {
                    position: 0.81
                    color: "#0229a3"
                }
                GradientStop {
                    position: 0.86
                    color: "#0025a0"
                }
                GradientStop {
                    position: 1.00
                    color: "#0025a0"
                }
            }
            PathLine {
                x: mark.px(153)
                y: 0
            }
            PathLine {
                x: mark.px(153)
                y: mark.px(146)
            }
            PathLine {
                x: 0
                y: mark.px(146)
            }
            PathLine {
                x: 0
                y: 0
            }
        }
    }
    Rectangle {
        x: mark.px(1)
        y: mark.px(138)
        width: mark.px(42)
        height: mark.px(48)
        gradient: Gradient {
            GradientStop {
                position: 0.00
                color: mark.paper
            }
            GradientStop {
                position: 0.05
                color: "#f6ecc2"
            }
            GradientStop {
                position: 0.12
                color: "#f1db77"
            }
            GradientStop {
                position: 0.18
                color: "#f3d139"
            }
            GradientStop {
                position: 0.24
                color: "#facf1f"
            }
            GradientStop {
                position: 0.30
                color: "#fccf0a"
            }
            GradientStop {
                position: 1.00
                color: "#fccf0a"
            }
        }
    }
    // Green, blending into the yellow on its left and into the blue on its right.
    Rectangle {
        x: mark.px(43)
        y: mark.px(140)
        width: mark.px(105)
        height: mark.px(47)
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop {
                position: 0.00
                color: "#a99b1d"
            }
            GradientStop {
                position: 0.07
                color: "#958b25"
            }
            GradientStop {
                position: 0.08
                color: "#0b740c"
            }
            GradientStop {
                position: 0.91
                color: "#0b6f12"
            }
            GradientStop {
                position: 0.95
                color: "#115534"
            }
            GradientStop {
                position: 1.00
                color: "#124260"
            }
        }
    }
    Rectangle {
        x: mark.px(22)
        y: mark.px(13)
        width: mark.px(165)
        height: mark.px(166)
        gradient: Gradient {
            GradientStop {
                position: 0.00
                color: "#db5803"
            }
            GradientStop {
                position: 0.50
                color: "#d24209"
            }
            GradientStop {
                position: 0.72
                color: "#d63807"
            }
            GradientStop {
                position: 1.00
                color: "#d63808"
            }
        }
    }

    Item {
        x: mark.px(8)
        width: mark.px(173)
        height: mark.px(173)
        readonly property int thin: mark.px(13)   // top and left edges
        readonly property int thick: mark.px(14)  // right and bottom edges

        Rectangle {
            anchors.fill: parent
            color: mark.paper
        }
        Rectangle {
            width: parent.width
            height: parent.thin
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop {
                    position: 0.59
                    color: mark.paper
                }
                GradientStop {
                    position: 0.67
                    color: mark.orange
                }
            }
        }
        Rectangle {
            width: parent.thin
            height: parent.height
            gradient: Gradient {
                GradientStop {
                    position: 0.52
                    color: mark.paper
                }
                GradientStop {
                    position: 0.66
                    color: mark.orange
                }
            }
        }
        Rectangle {
            x: parent.width - width
            width: parent.thick
            height: parent.height
            gradient: Gradient {
                GradientStop {
                    position: 0.14
                    color: mark.orange
                }
                GradientStop {
                    position: 0.30
                    color: mark.paper
                }
                GradientStop {
                    position: 0.53
                    color: mark.paper
                }
                GradientStop {
                    position: 0.70
                    color: mark.orange
                }
            }
        }
        Rectangle {
            y: parent.height - height
            width: parent.width
            height: parent.thick
            color: mark.orange
        }
    }

    Image {
        visible: status === Image.Ready
        source: mark.logo ? "file://" + mark.logo : ""
        x: mark.px(36)
        y: mark.px(28)
        width: mark.px(139)
        height: mark.px(113)
        sourceSize.width: width * 2
        sourceSize.height: height * 2
        fillMode: Image.PreserveAspectFit
        smooth: !mark.logo.endsWith(".png")  // pixel-art logos stay sharp
    }
}
