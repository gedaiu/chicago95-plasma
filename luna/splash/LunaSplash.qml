// Windows XP SP3, measured at 640 × 480. Each sweep has 18 discrete states.
import QtQuick 2.15
import QtQuick.Window 2.15
import "../qml"

Rectangle {
    id: root

    property int stage
    property string edition: stockBrand ? "" : "Professional"
    property string brandText: ""
    property string brandLogo: ""
    property string company: ""
    property string footer: stockBrand ? "Copyright © Microsoft Corporation" : "Copyright © 1985-2001\nMicrosoft Corporation"
    property string family: "Trebuchet MS"
    property bool animated: true
    property real phase: 0

    readonly property real unit: Math.min(width / 640, height / 480)
    readonly property real layoutX: (width - 640 * unit) / 2
    readonly property real layoutY: (height - 480 * unit) / 2
    readonly property real wordmarkScale: 1.85
    readonly property bool stockBrand: brandText === ""
    readonly property bool nativeStock: stockBrand && edition === "" && footer === "Copyright © Microsoft Corporation"
        && family === "Trebuchet MS" && unit === 1 && Screen.devicePixelRatio === 1
    readonly property int sweepMilliseconds: 1688
    readonly property int step: Math.min(17, Math.floor(phase * 18))

    color: "#000000"

    NumberAnimation on phase {
        running: root.animated
        from: 0
        to: 1
        duration: root.sweepMilliseconds
        loops: Animation.Infinite
    }

    Image {
        visible: root.nativeStock
        x: root.layoutX
        y: root.layoutY
        width: 640
        height: 480
        source: visible ? "boot-stock-640.png" : ""
        smooth: false
    }

    XpWordmark {
        id: wordmark
        visible: !root.nativeStock
        // The XP wordmark's measured place; a branded mark, wider, is centred where that one's centre is (x 331).
        x: root.stockBrand ? root.layoutX + 210 * root.unit : root.layoutX + 331 * root.unit - wordmark.width / 2
        y: root.layoutY + (root.stockBrand ? 123 : 124) * root.unit
        unit: root.unit * root.wordmarkScale
        edition: root.edition
        textColor: "#efefef"
        family: root.family
        name: root.brandText
        logo: root.brandLogo
        company: root.company
    }

    Image {
        x: root.layoutX + 255 * root.unit
        y: root.layoutY + 351 * root.unit
        width: 126 * root.unit
        height: 15 * root.unit
        source: "boot-trough.svg"
        smooth: false

        Item {
            x: 4 * root.unit
            y: 3 * root.unit
            width: 118 * root.unit
            height: 9 * root.unit
            clip: true
            Image {
                x: (root.step - 3) * 8 * root.unit
                width: 22 * root.unit
                height: parent.height
                source: "boot-blocks.svg"
                smooth: false
            }
        }
    }

    Text {
        visible: !root.nativeStock
        x: root.layoutX + (root.stockBrand ? 21 : 22) * root.unit
        y: root.layoutY + (root.stockBrand ? 447 : 433) * root.unit
        text: root.footer
        color: "#efefef"
        lineHeight: 1.1
        font.family: root.family
        font.pixelSize: (root.stockBrand ? 12 : 11) * root.unit
    }
    // The corner's company: the user's own when the screen carries their branding, ending where "Microsoft" ends.
    Text {
        visible: !root.nativeStock
        x: root.stockBrand ? root.layoutX + 546 * root.unit : root.layoutX + 635 * root.unit - width
        y: root.layoutY + (root.stockBrand ? 444 : 441) * root.unit
        text: root.stockBrand ? "Microsoft" : root.company
        color: "#efefef"
        font.family: root.family
        font.bold: true
        font.italic: true
        font.pixelSize: (root.stockBrand ? 14 : 17) * root.unit
    }
}
