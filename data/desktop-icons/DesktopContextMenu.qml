pragma ComponentBehavior: Bound

import QtQuick
import "classicFonts.js" as ClassicFonts
import QtQuick.Controls as Controls
import QtQuick.Shapes

import org.kde.kirigami as Kirigami
import org.kde.plasma.plasma5support as Plasma5Support

Controls.Menu {
    id: desktopMenu

    required property var folder
    required property var desktopConfiguration
    property string look
    property string builtLook
    readonly property bool win95: look === "1995"
    readonly property bool win9x: win95 || look === "1998"
    // On Wayland, Screen rounds fractional scales up. The window has the scale used to draw the menu.
    readonly property real windowScale: parent?.Window.window?.devicePixelRatio ?? Screen.devicePixelRatio
    readonly property string nativeFont: desktopConfiguration.chicago95NativeDesktopFont
        ? ClassicFonts.nativeFamily(look, windowScale, Qt.fontFamilies()) : ""
    font.family: aero ? "Segoe UI" : nativeFont || (nt || luna ? "Tahoma" : "MS W98 UI")
    readonly property bool aero: look === "aero"
    readonly property bool luna: look === "luna"
    readonly property bool nt: look === "2000" || look === "2001"
    // Classic captures use 120 DPI. Aero's menu uses 96 DPI.
    readonly property real unit: aero ? 1 : 0.8
    readonly property real highlightHeight: aero ? 22 :
        Screen.devicePixelRatio === 1 && !nt && !luna ? 17 : (nt || luna ? 21 : 20) * unit
    readonly property color face: aero ? "#f0f0f0" : luna ? "#ffffff" : nt ? "#d4d0c8" : "#c0c0c0"
    readonly property color dark: aero ? "#979797" : luna ? "#aca899" : nt ? "#404040" : "#000000"
    readonly property var profiles: ({
        "1995": {width: 138, rows: ["arrange", "line-up", "", "paste", "paste-shortcut", "", "new", "", "properties"],
                 heights: [20, 20, 11, 20, 20, 11, 20, 11, 22]},
        "1998": {width: 143, rows: ["active", "", "arrange", "line-up", "", "refresh", "", "paste",
                                   "paste-shortcut", "", "new", "", "properties"],
                 heights: [20, 11, 20, 20, 11, 20, 11, 20, 20, 11, 20, 11, 22]},
        "2000": {width: 146, rows: ["active", "", "arrange", "line-up", "refresh", "", "paste",
                                   "paste-shortcut", "", "new", "", "properties"],
                 heights: [22, 7, 22, 22, 22, 8, 23, 23, 7, 25, 7, 26]},
        "2001": {width: 163, rows: ["arrange-by", "refresh", "", "paste", "paste-shortcut", "", "new", "", "properties"],
                 heights: [22, 22, 7, 23, 23, 7, 25, 7, 29]},
        "luna": {width: 164, rows: ["arrange-by", "refresh", "", "paste", "paste-shortcut", "", "new", "", "properties"],
                 heights: [24, 22, 8, 24, 22, 8, 25, 8, 27]},
        "aero": {width: 167, rows: ["view", "sort", "refresh", "", "paste", "paste-shortcut", "",
                                  "new", "", "resolution", "gadgets", "personalize"],
                 heights: [22, 22, 22, 7, 22, 22, 7, 22, 7, 22, 22, 22]},
    })
    readonly property var labels: ({
        "arrange": qsTr("Arrange Icons"), "arrange-by": qsTr("Arrange Icons By"), "view": qsTr("View"),
        "sort": qsTr("Sort by"), "line-up": qsTr("Line Up Icons"), "refresh": qsTr("Refresh"),
        "paste": qsTr("Paste"), "paste-shortcut": aero ? qsTr("Paste shortcut") : qsTr("Paste Shortcut"),
        "active": qsTr("Active Desktop"), "new": qsTr("New"), "properties": qsTr("Properties"),
        "resolution": qsTr("Screen resolution"), "gadgets": qsTr("Gadgets"), "personalize": qsTr("Personalize"),
    })
    readonly property var win9xLabels: ({
        "arrange": qsTr("Arrange &Icons"), "line-up": win95 ? qsTr("Lin&e up Icons") : qsTr("Line &Up Icons"),
        "active": qsTr("&Active Desktop"), "refresh": qsTr("Re&fresh"),
        "paste": qsTr("&Paste"), "paste-shortcut": qsTr("Paste &Shortcut"),
        "new": win95 ? qsTr("Ne&w") : qsTr("&New"), "properties": qsTr("P&roperties"),
    })
    readonly property var submenus: ({
        "arrange": sorting, "arrange-by": sorting, "sort": sorting,
        "view": [[qsTr("Small icons"), () => desktopConfiguration.iconSize = 1],
                 [qsTr("Medium icons"), () => desktopConfiguration.iconSize = 2],
                 [qsTr("Large icons"), () => desktopConfiguration.iconSize = 3]],
        "active": [[qsTr("Desktop and Wallpaper"), () => launch("kcmshell6 kcm_wallpaper")]],
        "new": [[qsTr("Folder"), () => folder.createFolder()]],
    })
    readonly property var sorting: [
        [qsTr("Name"), () => desktopConfiguration.sortMode = 0],
        [qsTr("Size"), () => desktopConfiguration.sortMode = 1],
        [qsTr("Item type"), () => desktopConfiguration.sortMode = 6],
        [qsTr("Date modified"), () => desktopConfiguration.sortMode = 2],
    ]
    readonly property var icons: ({
        "resolution": "preferences-desktop-display", "gadgets": "preferences-desktop-widgets",
        "personalize": "preferences-desktop-theme",
    })
    readonly property var profile: profiles[look] ?? profiles["1995"]

    popupType: Controls.Popup.Item
    width: profile.width * unit
    height: topPadding + bottomPadding + profile.heights.reduce((height, row) => height + row, 0) * unit
    padding: 2 * unit
    topPadding: (aero ? 6 : 2) * unit
    bottomPadding: (aero ? 4 : 2) * unit
    overlap: unit

    function launch(command) {
        runner.connectSource("systemd-run --user --quiet --collect " + command);
    }

    function run(action) {
        switch (action) {
            case "line-up": desktopConfiguration.sortMode = 0; break;
            case "refresh": folder.refresh(); break;
            case "paste": folder.paste(); break;
            case "properties":
            case "resolution": launch("chicago95-control-panel --page display"); break;
            case "personalize": launch("chicago95-control-panel --page themes"); break;
            case "gadgets":
                launch("gdbus call --session --dest org.kde.plasmashell --object-path /PlasmaShell "
                       + "--method org.kde.PlasmaShell.toggleWidgetExplorer");
                break;
        }
    }

    function showAt(point) {
        if (builtLook !== look) {
            while (count > 0) {
                const item = itemAt(count - 1);
                if (item.subMenu)
                    removeMenu(item.subMenu);
                else
                    removeItem(item);
            }
            builtLook = look;
            for (let i = 0; i < profile.rows.length; ++i) {
                const action = profile.rows[i];
                const rowHeight = profile.heights[i] * unit;
                if (!action) {
                    addItem(separator.createObject(contentItem, {height: rowHeight}));
                    continue;
                }
                if (submenus[action]) {
                    const child = cascade.createObject(desktopMenu, {title: labels[action], flyout: submenus[action]});
                    insertMenu(count, child);
                    const delegate = itemAt(count - 1);
                    delegate.height = rowHeight;
                    delegate.command = action;
                } else {
                    addItem(row.createObject(contentItem, {command: action, height: rowHeight}));
                }
            }
        }
        folder.updateActions();
        x = Math.round(point.x * Screen.devicePixelRatio) / Screen.devicePixelRatio;
        y = Math.round(point.y * Screen.devicePixelRatio) / Screen.devicePixelRatio;
        open();
    }

    delegate: row

    contentItem: ListView {
        model: desktopMenu.contentModel
        implicitHeight: contentHeight
        interactive: false
        clip: true
        currentIndex: desktopMenu.currentIndex
    }

    background: Rectangle {
        color: desktopMenu.face
        border.width: desktopMenu.unit
        border.color: desktopMenu.dark
        Rectangle {
            visible: desktopMenu.win9x
            width: parent.width - desktopMenu.unit
            height: parent.height - desktopMenu.unit
            color: desktopMenu.face
            Rectangle {
                x: desktopMenu.unit
                y: desktopMenu.unit
                width: parent.width - x
                height: parent.height - y
                color: "#808080"
                Rectangle {
                    width: parent.width - desktopMenu.unit
                    height: parent.height - desktopMenu.unit
                    color: desktopMenu.face
                }
            }
        }
        Rectangle {
            visible: desktopMenu.aero
            x: 27
            y: desktopMenu.topPadding
            width: 1
            height: parent.height - desktopMenu.topPadding - desktopMenu.bottomPadding
            color: "#d7d7d7"
        }
        Rectangle {
            visible: !desktopMenu.aero && !desktopMenu.luna
            x: desktopMenu.unit
            y: desktopMenu.unit
            width: parent.width - (desktopMenu.win9x ? 3 : 2) * desktopMenu.unit
            height: desktopMenu.unit
            color: "white"
        }
        Rectangle {
            visible: !desktopMenu.aero && !desktopMenu.luna
            x: desktopMenu.unit
            y: desktopMenu.unit
            width: desktopMenu.unit
            height: parent.height - (desktopMenu.win9x ? 3 : 2) * desktopMenu.unit
            color: "white"
        }
    }

    Component {
        id: row
        Controls.MenuItem {
            id: item
            property string command
            text: (desktopMenu.win9x ? desktopMenu.win9xLabels : desktopMenu.labels)[command] ?? ""
            enabled: command !== "paste-shortcut" && (command !== "paste" || (desktopMenu.folder.action("paste")?.enabled ?? false))
            onTriggered: if (!subMenu) desktopMenu.run(command)
            background: Rectangle {
                visible: item.highlighted
                width: item.width
                height: desktopMenu.highlightHeight
                y: Math.round((item.y + (item.height - height) / 2) * Screen.devicePixelRatio)
                    / Screen.devicePixelRatio - item.y
                color: desktopMenu.aero ? "#d8eafb" : desktopMenu.nt ? "#0a246a" : desktopMenu.luna ? "#316ac5" : "#000080"
                border.color: desktopMenu.aero ? "#aecff7" : color
                radius: desktopMenu.aero ? 2 : 0
            }
            contentItem: Item {
                Kirigami.Icon {
                    visible: desktopMenu.aero && !!desktopMenu.icons[item.command]
                    source: desktopMenu.icons[item.command] ?? ""
                    x: 3
                    width: 16
                    height: 16
                    anchors.verticalCenter: parent.verticalCenter
                }
                Text {
                    visible: !desktopMenu.win9x
                    x: (desktopMenu.aero ? 32 : 22) * desktopMenu.unit - item.leftPadding
                    anchors.verticalCenter: parent.verticalCenter
                    text: item.text
                    color: !item.enabled ? "#808080" : item.highlighted && !desktopMenu.aero ? "#ffffff" : "#000000"
                    font.family: desktopMenu.font.family
                    font.pixelSize: desktopMenu.aero ? 12 : 11
                }
                Repeater {
                    model: desktopMenu.win9x ? 2 : 0
                    Text {
                        id: caption
                        required property int index
                        readonly property bool shadow: index === 0
                        readonly property int mnemonic: item.text.indexOf("&")
                        visible: !shadow || !item.enabled
                        x: (22 + (shadow ? 1 : 0)) * desktopMenu.unit - item.leftPadding
                        y: (2 + (shadow ? 1 : 0)) * desktopMenu.unit - item.topPadding
                        text: item.text.replace("&", "")
                        textFormat: Text.PlainText
                        // Match the subpixel origin used by the other native 120 DPI Plasma labels.
                        leftPadding: desktopMenu.nativeFont && desktopMenu.windowScale === 1.25 ? 0.125 : 0
                        font.family: desktopMenu.nativeFont || "MS W98 UI"
                        font.pixelSize: 11
                        font.hintingPreference: Font.PreferNoHinting
                        renderType: Text.NativeRendering
                        antialiasing: false
                        color: shadow || item.highlighted && item.enabled ? "white" : item.enabled ? "black" : "#808080"
                        TextMetrics {
                            id: prefix
                            font: caption.font
                            text: caption.text.slice(0, caption.mnemonic)
                        }
                        TextMetrics {
                            id: letter
                            font: caption.font
                            text: caption.text.charAt(caption.mnemonic)
                        }
                        Rectangle {
                            readonly property real scale: desktopMenu.windowScale
                            visible: caption.mnemonic >= 0
                            x: (Math.round(prefix.advanceWidth * scale) + (desktopMenu.win95 ? 0 : 1)) / scale
                            y: (Math.round(caption.baselineOffset * scale) + 1) / scale
                            width: Math.round(letter.advanceWidth * scale) / scale
                            height: 1 / scale
                            color: caption.color
                        }
                    }
                }
            }
            arrow: Text {
                visible: !!item.subMenu
                text: desktopMenu.win9x ? "" : "▸"
                x: desktopMenu.win9x ? desktopMenu.availableWidth - 13 * desktopMenu.unit : parent.width - 14
                y: desktopMenu.win9x ? 6 * desktopMenu.unit : 0
                anchors.verticalCenter: desktopMenu.win9x ? undefined : parent.verticalCenter
                color: item.highlighted && !desktopMenu.aero ? "#ffffff" : "#000000"
                Shape {
                    visible: desktopMenu.win9x
                    width: 4 * desktopMenu.unit
                    height: 7 * desktopMenu.unit
                    ShapePath {
                        strokeWidth: -1
                        fillColor: item.highlighted ? "white" : "black"
                        startX: 0; startY: -0.5 * desktopMenu.unit
                        PathLine { x: 4 * desktopMenu.unit; y: 3.5 * desktopMenu.unit }
                        PathLine { x: 0; y: 7.5 * desktopMenu.unit }
                    }
                }
            }
        }
    }

    Component {
        id: separator
        Controls.MenuSeparator {
            contentItem: Item {
                Rectangle {
                    visible: !desktopMenu.win9x
                    anchors.verticalCenter: parent.verticalCenter
                    x: desktopMenu.aero ? 28 : 0
                    width: parent.width - x
                    height: desktopMenu.unit
                    color: desktopMenu.luna ? "#aca899" : desktopMenu.aero ? "#d7d7d7" : "#808080"
                }
            }
            Rectangle {
                visible: desktopMenu.win9x
                x: (desktopMenu.win95 ? 1 : 3) * desktopMenu.unit
                y: 5 * desktopMenu.unit
                width: desktopMenu.availableWidth - x - (desktopMenu.win95 ? 2 : 3) * desktopMenu.unit
                height: desktopMenu.unit
                color: "#808080"
                Rectangle {
                    y: parent.height
                    width: parent.width
                    height: parent.height
                    color: "white"
                }
            }
        }
    }

    Component {
        id: cascade
        Controls.Menu {
            id: child
            font.family: desktopMenu.font.family
            property var flyout
            Instantiator {
                model: child.flyout
                delegate: Controls.MenuItem {
                    required property var modelData
                    text: modelData[0]
                    onTriggered: modelData[1]()
                }
                onObjectAdded: (index, object) => child.insertItem(index, object)
                onObjectRemoved: (index, object) => child.removeItem(object)
            }
        }
    }

    Plasma5Support.DataSource {
        id: runner
        engine: "executable"
        connectedSources: []
        onNewData: (source, data) => disconnectSource(source)
    }
}
