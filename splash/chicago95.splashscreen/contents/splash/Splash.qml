pragma ComponentBehavior: Bound
import QtQuick 2.15
import "settings.js" as Settings

// Plasma loading screen. KSplash shows it after log on, while Plasma starts: then it continues the login
// screen the user came from, as the originals do. A Welcome (luna) log on keeps the XP Welcome screen with
// "Loading your personal settings..." (luna/splash/LunaWelcome.qml); any other is the desktop's colour.
// Both show the hourglass pointer; KWin's log on effect fades them into the desktop.
// booting: the boot page instead, for the boot screen's picture (chicago95-splash-image) and the
// Control Panel's preview. "luna": the Windows XP start-up screen (luna/splash/LunaSplash.qml), loaded
// in place of the two below. "classic": a picture filling the screen. "2000": the 2000 start-up screen,
// laid out in the original's 640x480 pixels (measured by tests/test_loading_screen_reference.py) and scaled to the
// screen height: logo and name on a near-white page, a three-tone blue strip, a grey bar with a
// block progress bar that follows Plasma's start-up stages, and a footer line.
// Setup writes settings.js with the user's texts and pictures.
Rectangle {
    id: root
    property int stage
    property bool booting: false
    property string loadingText: Settings.loadingText
    property bool textBoot: false
    property int textBootDuration: 2500
    property int bitmapDuration: 3000
    property real textBootProgress: 0
    property int bootStripStep: -1
    property string textBootName: Settings.brandText || "Windows 95"
    property url statusBanner: "brand-banner.png"
    property real statusStripPhase: -1
    // KSplash stage is supplied by the session, not a timer or a fabricated service list.
    property string sessionStatus: stage < 5 ? "Loading your personal settings..." : "Waiting for desktop readiness..."
    function playBootPreview() {
        textFill.stop();
        bitmapTimer.stop();
        booting = true;
        textBoot = !luna && !postXp;
        textBootProgress = 0;
        if (textBoot) textFill.start();
        else bitmapTimer.start();
    }
    NumberAnimation {
        id: textFill
        target: root; property: "textBootProgress"
        from: 0; to: 1; duration: root.textBootDuration
        onFinished: { root.textBoot = false; bitmapTimer.start(); }
    }
    Timer {
        id: bitmapTimer
        interval: root.bitmapDuration
        onTriggered: root.booting = false
    }
    TextBoot {
        anchors.fill: parent
        z: 100
        visible: root.booting && root.textBoot
        ntLoader: Settings.style === "2000"
        systemName: root.textBootName
        progress: root.textBootProgress
    }
    Loader {
        active: !root.booting && Settings.logonStyle === "2000"
        visible: active
        anchors.centerIn: parent
        anchors.verticalCenterOffset: -parent.height * 0.14
        scale: Math.min(1, parent.width / (width + 12))
        sourceComponent: Component {
            StartupStatus { statusText: root.sessionStatus; banner: root.statusBanner; stripPhase: root.statusStripPhase }
        }
    }

    Loader {
        anchors.fill: parent
        active: !root.booting && Settings.logonStyle === "aero"
        source: active ? "SevenSession.qml" : ""
    }

    readonly property bool modern: booting && Settings.style === "2000"
    readonly property bool stock2000: modern && Settings.brandText === "Windows 2000"
        && Settings.company === "Microsoft" && !Settings.companyLogo
        && (!Settings.brandLogo || /(?:waving-flag|logo-flag-16)\.png$/.test(Settings.brandLogo))
    readonly property bool luna: booting && Settings.style === "luna"
    readonly property bool postXp: booting && ["vista", "7", "8", "8.1", "10", "11"].indexOf(Settings.style) !== -1
    readonly property bool classic: booting && !modern && !luna && !postXp
    readonly property bool win95Picture: Settings.picture === "images/background.png"
        || Settings.picture.endsWith("/chicago95.splashscreen/contents/splash/images/background.png")
    readonly property bool welcome: !booting && Settings.logonStyle === "luna"
    readonly property real unit: height / 480
    readonly property real layoutX: (width - 640 * unit) / 2  // the 640-wide layout, centred ("left" is taken by Item)
    readonly property int stages: 6

    function px(value) {
        return Math.round(value * unit);
    }

    color: booting ? (stock2000 ? "#ffffff" : "#f7f7f7") : Settings.desktopColor || "#008080"

    Loader {
        anchors.fill: parent
        active: root.postXp
        source: "PostXpBoot.qml"
        onLoaded: {
            item.style = Settings.style;
            item.options = Settings.postXp || {};
        }
    }

    Image {
        id: bootPicture
        visible: root.classic && !root.win95Picture
        anchors.fill: parent
        source: Settings.picture.startsWith("/") ? "file://" + Settings.picture : Settings.picture
        fillMode: Image.PreserveAspectCrop
    }

    AnimatedImage {
        visible: root.classic && root.win95Picture
        anchors.fill: parent
        source: visible ? "images/windows95-boot.gif" : ""
        fillMode: Image.PreserveAspectCrop
        smooth: false
        playing: visible && root.bootStripStep < 0
        currentFrame: root.bootStripStep >= 0 ? root.bootStripStep % 20 : 0
    }

    Item {
        id: win98BootStrip
        visible: root.classic && Settings.picture.endsWith("/windows98.png")
        x: (root.width - width) / 2
        y: (root.height - bootPicture.paintedHeight) / 2 + bootPicture.paintedHeight * (472 / 480)
        width: visible ? bootPicture.paintedWidth : 0
        height: visible ? bootPicture.paintedHeight * (8 / 480) : 0
        clip: true
        property real phase: 0
        readonly property int step: root.bootStripStep >= 0 ? root.bootStripStep % 20 : Math.min(19, Math.floor(phase * 20))

        NumberAnimation on phase {
            running: win98BootStrip.visible && root.bootStripStep < 0
            from: 0
            to: 1
            duration: 1111
            loops: Animation.Infinite
        }
        Image {
            anchors.fill: parent
            source: win98BootStrip.visible ? "images/windows98-boot-strip.svg" : ""
            sourceClipRect: Qt.rect(0, win98BootStrip.step * 8, 640, 8)
            smooth: false
        }
    }

    Loader {
        anchors.fill: parent
        active: root.luna
        source: "luna/splash/LunaSplash.qml"
        onLoaded: {
            item.edition = Settings.edition;
            item.footer = Settings.footer;
            item.brandText = Settings.brandText || "";
            item.brandLogo = Settings.brandLogo || "";
            item.company = Settings.company || "";
            item.stage = Qt.binding(() => root.stage);
        }
    }

    Loader {
        anchors.fill: parent
        active: root.welcome
        source: "luna/splash/LunaWelcome.qml"
        onLoaded: {
            item.userName = Settings.userName || "";
            item.userPicture = Settings.userPicture ? "file://" + Settings.userPicture : "";
            item.branding = {
                brandText: Settings.brandText || "",
                brandLogo: Settings.brandLogo || "",
                company: Settings.company || "",
                edition: Settings.edition || ""
            };
        }
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
            id: companyName
            visible: !!Settings.company
            x: root.layoutX + root.px(116)
            y: root.unit * 255 - companyName.baselineOffset
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
                    id: part
                    required property string modelData
                    readonly property bool isNumber: /^\d+$/.test(modelData)
                    width: isNumber ? thin.width : heavy.width
                    height: 1  // the parts place themselves on the baseline; Row skips empty items
                    HeavyText {
                        id: heavy
                        visible: !part.isNumber
                        text: part.modelData
                        pixelSize: root.unit * 58
                        embolden: root.unit * 1.2
                        letterSpacing: root.unit * 1.1
                        baselineY: root.unit * 300
                    }
                    Text {
                        id: thin
                        visible: part.isNumber
                        y: root.unit * 302 - thin.baselineOffset
                        font.family: "Arial"
                        font.pixelSize: root.unit * 50
                        font.letterSpacing: root.unit * -3
                        color: "#000000"
                        text: part.modelData
                    }
                }
            }
        }
        HeavyText {
            id: edition
            x: nameRow.x + nameRow.width - edition.width + root.px(3)
            text: Settings.edition
            pixelSize: root.unit * 40
            embolden: root.unit
            letterSpacing: root.unit * 0.9
            baselineY: root.unit * 337
        }
        Text {
            id: tagline
            x: nameRow.x + nameRow.width - tagline.width
            y: root.unit * 354 - tagline.baselineOffset
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
            visible: companyLogo.status === Image.Ready
            source: Settings.companyLogo ? "file://" + Settings.companyLogo : ""
            x: root.layoutX + root.px(617) - companyLogo.width
            y: root.px(12)
            width: root.px(120)
            height: root.px(24)
            sourceSize.width: companyLogo.width * 2
            sourceSize.height: companyLogo.height * 2
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
            visible: !root.stock2000
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
                    color: root.stock2000 ? "#00289f" : "#0071d8"
                }
                GradientStop {
                    position: root.stock2000 ? 0.202 : 0.23
                    color: root.stock2000 ? "#00289f" : "#0071d8"
                }
                GradientStop {
                    position: root.stock2000 ? 0.375 : 0.39
                    color: root.stock2000 ? "#0070df" : "#0025a0"
                }
                GradientStop {
                    position: root.stock2000 ? 0.64 : 0.723
                    color: root.stock2000 ? "#0070df" : "#0025a0"
                }
                GradientStop {
                    position: root.stock2000 ? 0.836 : 0.725
                    color: root.stock2000 ? "#00289f" : "#133777"
                }
                GradientStop {
                    position: 1.00
                    color: root.stock2000 ? "#00289f" : "#133777"
                }
            }
        }
        // The strip's left end is capped by darker corner pixels on its first and last coloured rows.
        Rectangle {
            visible: !root.stock2000
            x: 0
            y: root.px(416)
            width: root.px(1)
            height: root.px(1)
            color: "#4d6596"
        }
        Rectangle {
            visible: !root.stock2000
            x: 0
            y: root.px(425)
            width: root.px(1)
            height: root.px(1)
            color: "#4d6596"
        }
        Rectangle {
            visible: !root.stock2000
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
            y: root.px(root.stock2000 ? 426 : 427)
            width: parent.width
            height: parent.height - y
            color: root.stock2000 ? "#c0c0c0" : "#c1bfc3"
        }

        Image {
            id: win2000Artwork
            visible: root.stock2000
            x: root.layoutX
            width: 640 * root.unit
            height: 480 * root.unit
            source: visible ? "images/windows2000-boot.png" : ""
            smooth: false
        }

        Item {
            id: win2000BootStrip
            objectName: "win2000BootStrip"
            visible: root.stock2000
            x: win2000Artwork.x
            y: win2000Artwork.height * (416 / 480)
            width: win2000Artwork.width
            height: win2000Artwork.height * (10 / 480)
            clip: true
            property real phase: 0
            readonly property int step: root.bootStripStep >= 0 ? root.bootStripStep % 160
                : Math.min(159, Math.floor(phase * 160))

            SequentialAnimation {
                running: win2000BootStrip.visible && root.bootStripStep < 0
                PauseAnimation { duration: 328 }
                NumberAnimation {
                    target: win2000BootStrip
                    property: "phase"
                    from: 0
                    to: 1
                    duration: 10000
                    loops: Animation.Infinite
                }
            }

            Repeater {
                model: win2000BootStrip.visible ? 2 : 0
                Image {
                    required property int index
                    x: (index - 1 + win2000BootStrip.step / 160) * width
                    width: win2000BootStrip.width
                    height: win2000BootStrip.height
                    source: win2000Artwork.source
                    sourceClipRect: Qt.rect(0, 416, 640, 10)
                    smooth: false
                }
            }
        }

        Rectangle {
            visible: root.stock2000 && loadingLabel.visible
            x: root.layoutX + root.px(200)
            y: root.px(436)
            width: root.px(71)
            height: root.px(12)
            color: "#c0c0c0"
        }

        Text {
            id: loadingLabel
            visible: !root.stock2000 || root.loadingText !== "Starting up..."
            x: root.layoutX + root.px(200)
            y: root.px(437)
            font.family: "MS W98 UI"
            font.pixelSize: root.px(11)
            renderType: Text.NativeRendering
            color: "#000000"
            text: root.loadingText
        }

        // Windows 2000 Professional, 1×. The shadow owns the two diagonal corners.
        Rectangle {
            x: root.layoutX + root.px(273)
            y: root.px(436)
            width: root.px(165)
            height: root.px(10)
            color: "#808080"
            Rectangle {
                x: root.px(1)
                y: root.px(1)
                width: parent.width - x
                height: parent.height - y
                color: "white"
                Rectangle {
                    width: parent.width - root.px(1)
                    height: parent.height - root.px(1)
                    color: "#c0c0c0"
                }
            }
            Repeater {
                model: Math.round(Math.min(root.stage, root.stages) / root.stages * 18)
                Rectangle {
                    required property int index
                    x: root.px(1 + 9 * index)
                    y: root.px(1)
                    width: root.px(8)
                    height: root.px(8)
                    color: "#00289f"
                }
            }
        }

        Rectangle {
            visible: root.stock2000 && copyrightLabel.visible
            x: root.layoutX + root.px(194)
            y: root.px(457)
            width: root.px(252)
            height: root.px(13)
            color: "#c0c0c0"
        }

        Text {
            id: copyrightLabel
            visible: !root.stock2000 || Settings.footer !== "Copyright © 1985-1999 Microsoft Corporation"
            anchors.horizontalCenter: parent.horizontalCenter
            y: root.px(458)
            font.family: "MS W98 UI"
            font.pixelSize: root.px(11)
            renderType: Text.NativeRendering
            color: "#000000"
            text: Settings.footer
        }
    }

    MouseArea {
        objectName: "waitPointer"
        visible: !root.booting
        anchors.fill: parent
        cursorShape: Qt.WaitCursor
    }
}
