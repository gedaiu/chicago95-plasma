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
    readonly property bool win9xGrid: win9x120 && pixelScale === 1.25
    readonly property bool win98Grid: win9xGrid && look === "1998"
    readonly property real pixel: 1 / pixelScale
    readonly property string nativeFont: {
        if (look === "2000" || look === "2001") {
            const family = look === "2001" ? "Tahoma" : "Chicago95 Windows 2000 Tahoma";
            return Qt.fontFamilies().includes(family) ? family : "";
        }
        const family = "Chicago95 Windows " + look.slice(-2) + " 120 DPI";
        return win9x120 && pixelScale === 1.25 && Qt.fontFamilies().includes(family) ? family : "";
    }

    readonly property int buttonHeight: 22
    readonly property real iconLeft: win98Grid ? 4 * pixel : 4
    readonly property real iconTop: win98Grid ? 3 - pixel : 3
    readonly property int labelLeft: look === "2001" ? 25 : bevel === "2000" ? 22 : 23
    readonly property int labelTop: 6
    readonly property int labelRight: 4
    readonly property int shift: pressed ? 1 : 0

    Item {
        id: surface
        readonly property bool nativePressed: task.win9xGrid && task.pressed
        y: task.height - task.buttonHeight + (task.win9xGrid ? task.pixel : 0)
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
                color: "#000000"
            }
            Rectangle {
                anchors.fill: parent
                anchors.margins: task.pixel
                color: "#c0c0c0"
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
            readonly property real inset: task.labelLeft - (task.nativeFont ? task.pixel : 0)
            // The Windows 98 bitmap caption starts 28 physical pixels inside the button.
            x: task.win98Grid && task.nativeFont ? Math.round(inset * task.pixelScale) * task.pixel : inset
            y: task.labelTop + task.shift - (task.nativeFont ? 2 * task.pixel : 0)
            width: Math.max(0, parent.width - x - task.labelRight)
            leftPadding: task.nativeFont ? -0.125 : 0
            font.family: task.nativeFont || "MS W98 UI"
            font.pixelSize: 11
            font.bold: task.pressed
            font.hintingPreference: task.nativeFont
                ? (task.look === "2000" || task.look === "2001" ? Font.PreferFullHinting : Font.PreferNoHinting)
                : Font.PreferDefaultHinting
            color: task.textColor
            elide: Text.ElideRight
            // A pixel font: drawn without smoothing, like the original's text.
            renderType: Text.NativeRendering
            antialiasing: false
        }
    }
}
