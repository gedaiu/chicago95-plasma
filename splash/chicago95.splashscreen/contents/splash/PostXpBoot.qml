pragma ComponentBehavior: Bound
import QtQuick 2.15
import QtQuick.Shapes 1.15
import "postxp"

Rectangle {
    id: root
    objectName: "postXpBoot"
    SpinnerPaths { id: spinner }
    property string style: "7"
    property var options: ({})
    property bool animated: true
    // Deterministic clock for preview tests and the Plymouth frame exporter.
    property real elapsed: 0
    property bool artworkVisible: true
    property bool animationVisible: true
    readonly property bool vista: style === "vista"
    readonly property bool seven: style === "7"
    // Seven centres the artwork in a 4:3 area at a given screen height.
    readonly property real unit: Math.min(width / (seven ? 1440 : 1920), height / 1080)
    readonly property real offsetX: (width - 1920 * unit) / 2
    readonly property real offsetY: (height - 1080 * unit) / 2
    readonly property color ink: option("foreground", "#ffffff")
    readonly property color accent: option("accent", vista ? "#b9d85b" : style === "11" ? "#008bd8" : "#00ccff")
    readonly property string family: option("font", vista ? "Tahoma" : "Segoe UI")
    readonly property string customLogo: option("logo", "default")
    readonly property string customAnimation: option("animation", "") === "none" ? "" : option("animation", "")
    readonly property int frameCount: Math.max(1, Math.min(600, Number(option("frames", seven ? 105 : vista ? 19 : 117)) || 1))
    readonly property int loopStart: Math.max(0, Math.min(frameCount - 1, Number(option("loopStart", seven ? 60 : 0)) || 0))
    readonly property real fps: Math.max(1, Math.min(60, Number(option("fps", seven ? 15 : vista ? 12 : 30)) || 1))
    readonly property int tick: Math.max(0, Math.floor(elapsed * fps / 1000 + 0.000001))
    readonly property int frame: tick < frameCount ? tick : loopStart + (tick - loopStart) % (frameCount - loopStart)
    readonly property real logoSize: Math.max(16, Math.min(600, Number(option("logoSize", seven ? 281.25 : 160)) || 160))
    // Coordinates are in the reference video's 1920×1080 canvas. Vista's native
    // 640×480 and Seven's 1024×768 artwork are uniformly scaled and centred.
    readonly property rect animationRect: customAnimation !== "" || seven
        ? Qt.rect(960 - logoSize / 2, 540 - logoSize / 2, logoSize, logoSize)
        : vista ? Qt.rect(818.25, 794.25, 274.5, 24.75) : Qt.rect(939, 825, 43, 43)
    readonly property bool animatedCustomLogo: seven && customLogo !== "default" && customLogo !== "none" && customAnimation === "" && option("animation", "") !== "none"
    readonly property bool drawsAnimation: option("animation", "") !== "none" && (customAnimation !== "" || !seven || customLogo === "default" || animatedCustomLogo)
    // Preserve the reference's default lettering even without Microsoft's UI font.
    // Any content/font/palette override uses live, fully editable text instead.
    readonly property bool referenceTypography: option("font", "default") === "default"
        && color === Qt.color("#000000") && ink === Qt.color("#ffffff") && option("backgroundImage", "") === ""
    readonly property bool referenceText: referenceTypography && seven && option("text", "default") === "default"
    readonly property bool referenceFooter: referenceTypography && (seven || vista) && option("footer", "default") === "default"

    function option(key, fallback) {
        return options[key] === undefined || options[key] === "default" ? fallback : options[key];
    }
    function fileUrl(path) {
        return path.startsWith("/") ? "file://" + path : path;
    }

    color: option("background", "#000000")
    Timer {
        interval: 16
        running: root.animated && root.visible
        repeat: true
        property double started: 0
        onRunningChanged: if (running) started = Date.now() - root.elapsed
        onTriggered: root.elapsed = Date.now() - started
    }
    Image {
        visible: root.artworkVisible
        anchors.fill: parent
        source: root.fileUrl(root.option("backgroundImage", ""))
        fillMode: Image.PreserveAspectCrop
    }
    Item {
        x: root.offsetX
        y: root.offsetY
        width: 1920
        height: 1080
        scale: root.unit
        transformOrigin: Item.TopLeft

        Item {
            visible: root.artworkVisible
            anchors.fill: parent
            Item {
                id: logo
                x: (root.seven || root.vista ? 960 : 970) - width / 2
                y: (root.seven || root.vista ? 540 : 413) - height / 2
                width: root.logoSize
                height: width
                visible: !root.animatedCustomLogo && root.customLogo !== "none" && (root.customLogo !== "default" || (!root.seven && !root.vista))
                Image {
                    visible: root.customLogo !== "default"
                    anchors.fill: parent
                    source: visible ? root.fileUrl(root.customLogo) : ""
                    fillMode: Image.PreserveAspectFit
                }
                Shape {
                    visible: root.customLogo === "default"
                    width: 100
                    height: 100
                    scale: logo.width / 100
                    transformOrigin: Item.TopLeft
                    ShapePath {
                        strokeWidth: 0
                        fillGradient: LinearGradient {
                            x1: 0; y1: 0; x2: 0; y2: 100
                            GradientStop {
                                position: 0
                                color: root.style === "11" && root.option("accent", "default") === "default" ? "#138ede" : root.accent
                            }
                            GradientStop {
                                position: 1
                                color: root.style === "11" && root.option("accent", "default") === "default" ? "#0078d0" : root.accent
                            }
                        }
                        PathSvg {
                            path: root.style === "11"
                                ? "M0 0H49V49H0Z M51 0H100V49H51Z M0 51H49V100H0Z M51 51H100V100H51Z"
                                : "M0 14L43 8V49H0Z M45 7L100 0V49H45Z M0 51H43V92L0 86Z M45 51H100V100L45 93Z"
                        }
                    }
                }
            }
            Text {
                objectName: "bootName"
                anchors.horizontalCenter: parent.horizontalCenter
                y: root.seven ? 690 : root.vista ? 650 : 620
                text: root.option("name", "")
                color: root.ink
                font.family: root.family
                font.pixelSize: 32
            }
            Text {
                objectName: "bootText"
                visible: !root.referenceText
                anchors.horizontalCenter: parent.horizontalCenter
                y: root.vista ? 720 : root.seven ? 730 : 900
                text: root.option("text", root.seven ? "Starting Windows" : "")
                color: root.ink
                font.family: root.family
                font.pixelSize: root.seven ? 25.3125 : 24
                renderType: Text.NativeRendering
            }
            Text {
                objectName: "bootFooter"
                visible: !root.referenceFooter
                anchors.horizontalCenter: parent.horizontalCenter
                y: root.vista ? 872 : 1005
                text: root.option("footer", root.vista || root.seven ? "© Microsoft Corporation" : "")
                color: root.ink
                opacity: root.seven ? 0.5 : 1
                font.family: root.family
                font.pixelSize: root.vista ? 24.75 : 15.46875
                renderType: Text.NativeRendering
            }
            Image {
                visible: root.referenceText
                x: 800; y: 720; width: 320; height: 80
                source: "postxp/seven-text.png"
            }
            Image {
                visible: root.referenceFooter
                x: 800; y: root.vista ? 864 : 1000; width: 320; height: 48
                source: root.vista ? "postxp/vista-footer.png" : "postxp/seven-footer.png"
            }

        }
        Item {
            objectName: "bootAnimation"
            visible: root.animationVisible && root.drawsAnimation
            x: root.animationRect.x
            y: root.animationRect.y
            width: root.animationRect.width
            height: root.animationRect.height
            clip: true
            Image {
                visible: root.customAnimation !== ""
                source: visible ? root.fileUrl(root.customAnimation) : ""
                width: parent.width
                height: parent.height * root.frameCount
                y: -root.frame * parent.height
                smooth: true
            }
            Image {
                visible: root.seven && root.customAnimation === "" && root.customLogo === "default"
                // One 15-column, seven-row atlas; the parent clips one 200px cell.
                source: visible ? "postxp/seven.png" : ""
                width: parent.width * 15
                height: parent.height * 7
                x: -(Math.min(104, root.frame) % 15) * parent.width
                y: -Math.floor(Math.min(104, root.frame) / 15) * parent.height
            }
            CustomSeven {
                width: 200
                height: 200
                scale: parent.width / 200
                transformOrigin: Item.TopLeft
                visible: root.animatedCustomLogo
                logoSource: visible ? root.fileUrl(root.customLogo) : ""
                frame: root.frame
            }
            Item {
                visible: root.vista && root.customAnimation === ""
                x: 2.25
                y: 2.25
                width: parent.width - 4.5
                height: parent.height - 4.5
                clip: true
                Image {
                    visible: root.option("accent", "default") === "default"
                    source: "postxp/vista-progress.png"
                    x: (-24 + root.frame * 8) * 2.25
                    width: 54
                    height: 24.75
                }
                Row {
                    visible: root.option("accent", "default") !== "default"
                    x: (-24 + root.frame * 8) * 2.25
                    spacing: 2.25
                    Repeater {
                        model: 8
                        Rectangle {
                            width: 4.5
                            height: 20.25
                            gradient: Gradient {
                                GradientStop { position: 0; color: Qt.darker(root.accent, 3) }
                                GradientStop { position: 0.45; color: root.accent }
                                GradientStop { position: 1; color: Qt.darker(root.accent, 4) }
                            }
                        }
                    }
                }
            }
            Shape {
                visible: !root.seven && !root.vista && root.customAnimation === ""
                width: 64
                height: 64
                scale: parent.width / 64
                transformOrigin: Item.TopLeft
                ShapePath {
                    strokeWidth: 0
                    fillColor: root.ink
                    PathSvg { path: spinner.paths[root.frame % spinner.paths.length] }
                }
            }
        }
        Rectangle {
            visible: root.artworkVisible && root.vista && root.customAnimation === "" && root.drawsAnimation
            x: 818.25
            y: 794.25
            width: 274.5
            height: 24.75
            color: "transparent"
            antialiasing: true
            border.color: "#666666"
            border.width: Math.max(1 / root.unit, 2.25)
        }
    }
}
