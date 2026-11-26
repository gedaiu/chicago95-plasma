pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls as Controls

import org.kde.kirigami as Kirigami
import org.kde.plasma.plasma5support as Plasma5Support

Controls.Menu {
    id: desktopMenu

    required property var folder
    required property var desktopConfiguration
    property string look
    property string builtLook
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
                 heights: [22, 22, 7, 22, 22, 7, 24, 7, 22]},
        "1998": {width: 143, rows: ["active", "", "arrange", "line-up", "", "refresh", "", "paste",
                                   "paste-shortcut", "", "new", "", "properties"],
                 heights: [21, 7, 22, 22, 7, 24, 7, 22, 22, 7, 24, 7, 25]},
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
            width: parent.width - 2 * desktopMenu.unit
            height: desktopMenu.unit
            color: "white"
        }
        Rectangle {
            visible: !desktopMenu.aero && !desktopMenu.luna
            x: desktopMenu.unit
            y: desktopMenu.unit
            width: desktopMenu.unit
            height: parent.height - 2 * desktopMenu.unit
            color: "white"
        }
    }

    Component {
        id: row
        Controls.MenuItem {
            id: item
            property string command
            text: desktopMenu.labels[command] ?? ""
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
                    x: (desktopMenu.aero ? 32 : 22) * desktopMenu.unit - item.leftPadding
                    anchors.verticalCenter: parent.verticalCenter
                    text: item.text
                    color: !item.enabled ? "#808080" : item.highlighted && !desktopMenu.aero ? "#ffffff" : "#000000"
                    font.family: desktopMenu.aero ? "Segoe UI" : desktopMenu.nt || desktopMenu.luna ? "Tahoma" : "MS W98 UI"
                    font.pixelSize: desktopMenu.aero ? 12 : 11
                }
            }
            arrow: Text {
                visible: !!item.subMenu
                text: "▸"
                x: parent.width - 14
                anchors.verticalCenter: parent.verticalCenter
                color: item.highlighted && !desktopMenu.aero ? "#ffffff" : "#000000"
            }
        }
    }

    Component {
        id: separator
        Controls.MenuSeparator {
            contentItem: Item {
                Rectangle {
                    anchors.verticalCenter: parent.verticalCenter
                    x: desktopMenu.aero ? 28 : 0
                    width: parent.width - x
                    height: desktopMenu.unit
                    color: desktopMenu.luna ? "#aca899" : desktopMenu.aero ? "#d7d7d7" : "#808080"
                }
            }
        }
    }

    Component {
        id: cascade
        Controls.Menu {
            id: child
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
