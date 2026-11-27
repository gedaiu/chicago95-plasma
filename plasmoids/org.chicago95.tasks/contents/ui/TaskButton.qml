import QtQuick
import org.kde.ksvg as KSvg
import org.kde.kirigami as Kirigami

// One task button as the originals draw it (tests/test_plasma_taskbar_reference.py): the Plasma
// style's task frame ("normal" raised, "focus" sunken with the checkerboard), 22px tall at the bottom
// of its applet; the window's icon 16px at 4,3 and its title from 23px (22px on 2000, where Tahoma has no blank
// column before its capitals; 25px on XP Classic), both a pixel lower while pressed (not further right); the active window's title bold.
Item {
    id: task
    property alias text: label.text
    property var icon
    property bool hovered: false
    property bool pressed
    property string bevel: "1995"
    property string look: "1995"
    property color textColor: Kirigami.Theme.textColor
    property int referenceDpi: 96
    readonly property bool win9x120: referenceDpi === 120 && (look === "1995" || look === "1998")
    readonly property real pixelScale: Window.window?.devicePixelRatio ?? Screen.devicePixelRatio
    readonly property bool ntClassic: look === "2000" || look === "2001"
    readonly property bool classicGrid: pixelScale === 1.25 && (win9x120 || (ntClassic && referenceDpi === 120))
    readonly property bool ntGrid: classicGrid && ntClassic
    readonly property bool win98Grid: classicGrid && look === "1998"
    readonly property real pixel: 1 / pixelScale
    readonly property string strikeFamily: "Chicago95 Windows " + (look === "2000" ? "2000" : "XP") + " Taskbar 120 DPI"
    readonly property bool hasTaskStrike: ntGrid && Qt.fontFamilies().includes(strikeFamily)
    // Use the full Tahoma font for titles that need shaping or glyphs outside the imported strike.
    readonly property bool useStrike: hasTaskStrike && pressed && !/[^ -~\u00a0-\u00ff\u2026]/.test(text)
    readonly property string nativeFont: {
        if (useStrike) return strikeFamily;
        if (ntClassic) {
            const family = look === "2001" ? "Tahoma" : "Chicago95 Windows 2000 Tahoma";
            return Qt.fontFamilies().includes(family) ? family : "";
        }
        const family = "Chicago95 Windows " + look.slice(-2) + " 120 DPI";
        return win9x120 && pixelScale === 1.25 && Qt.fontFamilies().includes(family) ? family : "";
    }

    readonly property real buttonHeight: ntGrid && look === "2001" ? 22 - pixel : 22
    readonly property real iconLeft: win98Grid || (ntGrid && look === "2000") ? 4 * pixel : 4
    readonly property real iconTop: win98Grid || ntGrid ? 3 - pixel : 3
    readonly property int labelLeft: look === "2001" ? (ntGrid ? 24 : 25) : bevel === "2000" ? 22 : 23
    readonly property real labelTop: ntGrid ? 6 - (look === "2000" ? pixel : 2 * pixel) : 6
    readonly property real labelRight: ntGrid ? 2 * pixel : 4
    readonly property int shift: pressed ? 1 : 0

    Item {
        id: surface
        readonly property bool nativePressed: task.classicGrid && task.pressed
        y: task.height - task.buttonHeight + (task.classicGrid ? task.pixel : 0)
        width: task.width
        height: task.buttonHeight
        KSvg.FrameSvgItem {
            anchors.fill: parent
            visible: !surface.nativePressed
            imagePath: "widgets/tasks"
            prefix: task.pressed ? (task.win9x120 ? "focus-solid" : "focus") : "normal"
        }
        Rectangle {
            anchors.fill: parent
            visible: surface.nativePressed
            color: "#ffffff"
            Rectangle {
                width: parent.width - task.pixel
                height: parent.height - task.pixel
                color: task.ntGrid ? "#404040" : "#000000"
            }
            Rectangle {
                anchors.fill: parent
                anchors.margins: task.pixel
                color: task.ntGrid ? "#d4d0c8" : "#c0c0c0"
            }
            Rectangle {
                x: task.pixel
                y: task.pixel
                width: parent.width - 3 * task.pixel
                height: parent.height - 3 * task.pixel
                color: "#808080"
            }
            Rectangle {
                anchors.fill: parent
                anchors.margins: 2 * task.pixel
                color: "#ffffff"
                Image {
                    anchors.fill: parent
                    source: task.ntGrid ? "../images/task-checker.svg" : ""
                    fillMode: Image.Tile
                    horizontalAlignment: Image.AlignLeft
                    verticalAlignment: Image.AlignTop
                    smooth: false
                }
                Rectangle {
                    visible: task.ntGrid && task.look === "2000"
                    width: parent.width
                    height: task.pixel
                    color: "white"
                }
            }
        }

        Kirigami.Icon {
            x: task.iconLeft
            y: task.iconTop + task.shift
            width: 16
            height: 16
            source: task.icon
            roundToIconSize: false
        }
        Text {
            id: label
            readonly property real inset: task.labelLeft + (task.nativeFont
                ? (task.ntClassic && task.pixelScale === 1 ? task.pixel : -task.pixel) : 0)
            // The Windows 98 bitmap caption starts 28 physical pixels inside the button.
            x: task.useStrike ? inset + task.pixel
                : task.win98Grid && task.nativeFont ? Math.round(inset * task.pixelScale) * task.pixel : inset
            y: task.labelTop + task.shift - (task.useStrike ? task.pixel : task.nativeFont ? 2 * task.pixel : 0)
            width: Math.max(0, parent.width - x - task.labelRight)
            leftPadding: task.nativeFont ? -0.125 : 0
            font.family: task.nativeFont || "MS W98 UI"
            font.pixelSize: 11
            font.bold: task.pressed
            font.hintingPreference: task.nativeFont
                ? (task.ntClassic && !task.useStrike ? Font.PreferFullHinting : Font.PreferNoHinting)
                : Font.PreferDefaultHinting
            color: task.textColor
            elide: Text.ElideRight
            // A pixel font: drawn without smoothing, like the original's text.
            renderType: Text.NativeRendering
            antialiasing: false
        }
    }
}
