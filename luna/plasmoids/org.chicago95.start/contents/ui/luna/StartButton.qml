import QtQuick
import org.kde.ksvg as KSvg

Item {
    id: button
    property string text
    property url logoSource
    property bool held
    property string bevel: "1995"
    property color face: "#ece9d8"
    property color textColor: "#ffffff"

    readonly property int pillWidth: 98
    readonly property int pillHeight: 30
    readonly property int flagLeft: 10
    readonly property int flagTop: 6
    readonly property size flagInk: Qt.size(20, 18)
    readonly property int inkLeft: 35
    readonly property int inkWidth: 37
    readonly property int inkHeight: 12
    readonly property int baselineRow: 21
    readonly property int probeSize: 100
    readonly property string lettering: text.toLowerCase()
    readonly property int lettersPixelSize: Math.round(inkHeight * probeSize / probe.tightBoundingRect.height)
    readonly property real lettersStretch: inkWidth / (probe.tightBoundingRect.width * lettersPixelSize / probeSize)

    implicitWidth: pillWidth
    implicitHeight: pillHeight

    HoverHandler {
        id: pointer
    }

    KSvg.FrameSvgItem {
        anchors.fill: parent
        imagePath: "widgets/startbutton"
        prefix: button.held ? "pressed" : pointer.hovered ? "hover" : "normal"
    }

    Image {
        x: button.flagLeft
        y: button.flagTop
        width: button.flagInk.width
        height: button.flagInk.height
        sourceSize: Qt.size(width * Screen.devicePixelRatio, height * Screen.devicePixelRatio)
        source: "../../images/windows-xp-flag.svg"
    }

    readonly property string lettersFamilies: "Franklin Gothic Medium, Trebuchet MS, Noto Sans, DejaVu Sans"

    Text {
        id: sample
        visible: false
        text: "start"
        font.family: button.lettersFamilies
        font.pixelSize: button.probeSize
        font.bold: true
        font.italic: true
    }
    TextMetrics {
        id: probe
        text: sample.text
        font: sample.font
    }

    readonly property real lettersX: inkLeft - probe.tightBoundingRect.x * lettersPixelSize / probeSize * lettersStretch

    component Lettering: Text {
        property int shadowOffset: 0
        text: button.lettering
        visible: button.text !== ""
        font.family: button.lettersFamilies
        font.pixelSize: button.lettersPixelSize
        font.bold: true
        font.italic: true
        font.hintingPreference: Font.PreferNoHinting
        x: button.lettersX + shadowOffset
        y: button.baselineRow - baselineOffset + shadowOffset
        renderType: Text.CurveRendering
        transform: Scale {
            xScale: button.lettersStretch
        }
    }

    Lettering {
        color: "#404A10"
        shadowOffset: 1
        z: 1
    }
    Lettering {
        color: "#ffffff"
        z: 2
    }
}
