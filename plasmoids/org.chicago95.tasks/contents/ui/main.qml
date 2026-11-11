import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.extras as PlasmaExtras
import org.kde.plasma.plasma5support as Plasma5Support
import org.kde.kirigami as Kirigami
import org.kde.ksvg as KSvg
import org.kde.taskmanager as TaskManager
import "sizing.js" as Sizing
import "launchers.js" as Launchers
import "quickLaunch.js" as QuickLaunch
import "quickLaunchBand.js" as Band
import "windowMenu.js" as WindowMenu

// The taskbar between the Start button and the tray, as the originals lay it out
// (tests/test_plasma_taskbar_reference.py): with Quick Launch entries, a separator, their 23px cells
// and another separator; then one button per window in the order they opened, 3px apart, as wide as
// the look allows and narrower when many share the taskbar. The originals have no gap before this
// part, so it starts over the gap Plasma's panel leaves between applets.
// A click on a window's button activates it, or minimizes it when it is already active; the right
// button opens the window's system menu (windowMenu.js), with "Add to Quick Launch". A Quick Launch entry's menu removes
// it; programs dropped on the Quick Launch are added. Dragging a task button or a Quick Launch entry along
// the taskbar sorts it (DragSortArea.qml); the Quick Launch order is saved. Whether it shows is Setup's option (quickLaunch.js).
// It sits between its two separators: the one at its docked edge carries it to either end of the taskbar;
// the one facing the window buttons sizes it, and a chevron opens the launchers that do not fit
// (quickLaunchBand.js).
PlasmoidItem {
    id: root

    preferredRepresentation: fullRepresentation
    Plasmoid.backgroundHints: PlasmaCore.Types.NoBackground
    Layout.fillWidth: true
    Layout.fillHeight: true

    readonly property bool isLuna: Plasmoid.configuration.taskbarStyle === "luna"
    readonly property int contentX: -Kirigami.Units.smallSpacing   // the panel's gap between applets
    readonly property bool showQuickLaunch: QuickLaunch.shown(Plasmoid.configuration.quickLaunch, Plasmoid.configuration.look)
    readonly property int maxButtonWidth: Sizing.maxButtonWidth(Plasmoid.configuration.maxButtonWidth, Plasmoid.configuration.look)
    readonly property int styledMaxButtonWidth: Sizing.styledButtonWidth(maxButtonWidth, Plasmoid.configuration.maxButtonWidth, Plasmoid.configuration.taskbarStyle)
    readonly property var metrics: Band.metrics(Plasmoid.configuration.taskbarStyle)
    readonly property int gap: isLuna ? 0 : metrics.taskButtonGap
    readonly property int launcherCount: tasksModel.launcherCount
    readonly property int windowCount: tasksModel.count - launcherCount
    readonly property int lead: Plasmoid.configuration.bevel === "2000" && !isLuna ? metrics.separatorLeadAfterStart2000 : metrics.separatorLead
    readonly property string dock: Plasmoid.configuration.quickLaunchDock === "right" ? "right" : "left"
    // While a separator is dragged: the band's width as the inner one sizes it, or where the outer one carries it.
    readonly property int notDragged: -2
    property int liveSize: notDragged
    property int carriedGripX: notDragged
    readonly property bool bandCarried: carriedGripX !== notDragged
    // Right after Setup, Plasma can hand over settings it has not loaded yet: undefined, which an int binding
    // turns into 0 (no launchers at all). Until they arrive, the band fits every launcher.
    readonly property int savedSize: Plasmoid.configuration.quickLaunchWidth ?? Band.fitAll()
    readonly property int size: liveSize !== notDragged ? liveSize : savedSize
    readonly property var band: Band.layout(width, contentX, lead, launcherCount, size, dock, metrics)
    readonly property int bandShift: bandCarried ? Band.carriedShift(carriedGripX, band, dock, width, contentX, metrics) : 0
    readonly property int shownLaunchers: band.shown
    readonly property int firstShown: band.firstShown   // the launchers before it are behind the chevron
    readonly property int quickLaunchX: band.cellsX + bandShift
    readonly property int quickLaunchEnd: quickLaunchX + Band.cellsWidth(shownLaunchers, metrics)
    readonly property int tasksX: band.tasksX
    readonly property int buttonWidth: windowCount === 0 ? 0 : Math.min(styledMaxButtonWidth, Math.floor((band.tasksEnd - tasksX + gap) / windowCount) - gap)

    function separatorDragged(separator, gripX) {
        if (Band.outerSeparator(dock) === separator)
            carriedGripX = gripX;
        else
            liveSize = Band.sizeAfterDrag(gripX, width, contentX, lead, dock, metrics);
    }
    function separatorReleased(separator, gripX) {
        const outer = Band.outerSeparator(dock) === separator;
        const newDock = outer ? Band.dockAfterDrag(gripX, width) : dock;
        const newSize = outer ? savedSize : Band.sizeAfterDrag(gripX, width, contentX, lead, dock, metrics);
        liveSize = notDragged;
        carriedGripX = notDragged;
        Plasmoid.configuration.quickLaunchDock = newDock;
        Plasmoid.configuration.quickLaunchWidth = newSize;
    }

    // The taskbar's own menu, as the originals' (tests/references/win98taskbarmenu.png): the toolbar, the
    // arrangements (kwin-scripts/chicago95windows, invoked through kglobalaccel's kwin component), Minimize All
    // with the Undo of whatever was last done, and Properties.
    property string lastArrangement: ""   // "Minimize All", "Cascade" or "Tile": the Undo entry names it
    readonly property string arrangeCommand: "systemd-run --user --quiet --collect gdbus call --session --dest org.kde.kglobalaccel --object-path /component/kwin --method org.kde.kglobalaccel.Component.invokeShortcut "
    function arrange(shortcut, name) {
        lastArrangement = name;
        runner.connectSource(arrangeCommand + shortcut);
    }
    // qmllint disable unqualified
    // i18n() is injected into the applet context by Plasma.
    Plasmoid.contextualActions: [
        PlasmaCore.Action {
            text: i18n("Quick Launch")
            checkable: true
            checked: root.showQuickLaunch
            onTriggered: checked => Plasmoid.configuration.quickLaunch = checked ? "yes" : "no"
        },
        PlasmaCore.Action {
            isSeparator: true
        },
        PlasmaCore.Action {
            text: i18n("Cascade Windows")
            onTriggered: root.arrange("Chicago95CascadeWindows", "Cascade")
        },
        PlasmaCore.Action {
            text: i18n("Tile Windows Horizontally")
            onTriggered: root.arrange("Chicago95TileWindowsHorizontally", "Tile")
        },
        PlasmaCore.Action {
            text: i18n("Tile Windows Vertically")
            onTriggered: root.arrange("Chicago95TileWindowsVertically", "Tile")
        },
        PlasmaCore.Action {
            isSeparator: true
        },
        PlasmaCore.Action {
            text: i18n("Minimize All Windows")
            onTriggered: root.arrange("Chicago95MinimizeAllWindows", "Minimize All")
        },
        PlasmaCore.Action {
            text: i18n("Undo %1", root.lastArrangement)
            visible: root.lastArrangement !== ""
            onTriggered: root.arrange("Chicago95UndoArrangement", "")
        },
        PlasmaCore.Action {
            isSeparator: true
        },
        PlasmaCore.Action {
            text: i18n("Properties")
            icon.name: "preferences-system"
            onTriggered: runner.connectSource(root.controlPanelCommand)
        }
    ]
    // qmllint enable unqualified
    readonly property string controlPanelCommand: "systemd-run --user --quiet --collect @HOME@/.local/bin/chicago95-control-panel --page taskbar"

    // Programs start as their own transient systemd service: Setup restarts plasmashell, and as it stops
    // its QProcesses kill the programs they started (tests/test_plasmoid_launches.py).
    Plasma5Support.DataSource {
        id: runner
        engine: "executable"
        connectedSources: []
        onNewData: (sourceName, data) => disconnectSource(sourceName)
    }

    TaskManager.VirtualDesktopInfo {
        id: virtualDesktopInfo
    }
    TaskManager.ActivityInfo {
        id: activityInfo
    }

    TaskManager.TasksModel {
        id: tasksModel
        screenGeometry: Plasmoid.containment.screenGeometry
        activity: activityInfo.currentActivity
        virtualDesktop: virtualDesktopInfo.currentDesktop
        filterByVirtualDesktop: true
        filterByActivity: true
        groupMode: TaskManager.TasksModel.GroupDisabled
        sortMode: TaskManager.TasksModel.SortManual
        separateLaunchers: true
        hideActivatedLaunchers: false
        // The launchers go in once the applet is complete. Given while it loads, Plasma never counts them: it counts
        // launchers when rows change, and with the windows already there (a login restoring the last session) no row
        // changes until a window opens, so the cells draw as window buttons until then.
        launcherList: root.completed ? QuickLaunch.launchers(root.showQuickLaunch, Plasmoid.configuration.launchers) : []
        // Entries added or removed here are saved; the setting's changes come back in through the binding.
        onLauncherListChanged: {
            if (root.showQuickLaunch && QuickLaunch.launchersDiffer(Plasmoid.configuration.launchers, launcherList))
                Plasmoid.configuration.launchers = launcherList;
        }
    }
    property bool completed: false
    Component.onCompleted: completed = true

    DropArea {
        visible: root.showQuickLaunch
        x: root.quickLaunchX
        width: Math.max(root.metrics.cellWidth, root.quickLaunchEnd - root.quickLaunchX)
        height: parent.height
        onDropped: drop => {
            const insertAt = Launchers.insertionIndexAt(x + drop.x, root.quickLaunchX, root.shownLaunchers);
            drop.urls.forEach((url, offset) => {
                const before = tasksModel.launcherCount;
                tasksModel.requestAddLauncher(url);
                if (tasksModel.launcherCount > before)
                    tasksModel.move(before, root.firstShown + insertAt + offset);
            });
        }
    }


    // While carried, the band is drawn over the window buttons on the taskbar's face.
    component CarriedBackdrop: Item {
        visible: root.bandCarried
        x: root.band.leftSeparatorX + root.bandShift
        width: root.band.rightSeparatorX + Band.separatorWidth(root.metrics.separatorLead, root.metrics) - root.band.leftSeparatorX
        height: parent.height
        z: 4
    }
    CarriedBackdrop {
        visible: root.bandCarried && !root.isLuna
        Rectangle {
            anchors.fill: parent
            color: Kirigami.Theme.backgroundColor
        }
    }
    CarriedBackdrop {
        visible: root.bandCarried && root.isLuna
        KSvg.FrameSvgItem {
            anchors.fill: parent
            imagePath: "widgets/panel-background"
        }
    }
    SeparatorSeam {
        id: leftSeparator
        luna: root.isLuna
        visible: root.launcherCount > 0
        x: root.band.leftSeparatorX + root.bandShift
        z: 5
        height: parent.height
        lead: root.dock === "left" ? root.lead : root.metrics.separatorLead
        onDragged: gripX => root.separatorDragged("leftSeparatorX", gripX)
        onReleased: gripX => root.separatorReleased("leftSeparatorX", gripX)
    }
    SeparatorSeam {
        id: rightSeparator
        luna: root.isLuna
        lead: root.metrics.separatorLead
        visible: root.launcherCount > 0
        x: root.band.rightSeparatorX + root.bandShift
        z: 5
        height: parent.height
        onDragged: gripX => root.separatorDragged("rightSeparatorX", gripX)
        onReleased: gripX => root.separatorReleased("rightSeparatorX", gripX)
    }
    Loader {
        id: chevron
        visible: root.band.chevronX >= 0
        x: root.band.chevronX + root.bandShift
        z: 5
        height: parent.height
        source: Qt.resolvedUrl(root.isLuna ? "luna/Chevron.qml" : "Chevron.qml")
        MouseArea {
            id: chevronArea
            anchors.fill: parent
            hoverEnabled: true
            onClicked: root.openChevronMenu()
        }
    }
    Binding {
        target: chevron.item
        property: "pointsRight"
        value: root.dock === "left"
    }
    Binding {
        target: chevron.item
        property: "hovered"
        value: chevronArea.containsMouse
    }
    Binding {
        target: chevron.item
        property: "held"
        value: chevronArea.pressed && chevronArea.containsMouse
    }
    PlasmaExtras.Menu {
        id: chevronMenu
        visualParent: chevron
        placement: PlasmaExtras.Menu.TopPosedLeftAlignedPopup
    }
    Component {
        id: chevronEntry
        PlasmaExtras.MenuItem {
            property int launcher
            onClicked: tasksModel.requestNewInstance(tasksModel.makeModelIndex(launcher))
        }
    }
    function openChevronMenu() {
        chevronMenu.clearMenuItems();
        Band.chevronLaunchers(launcherCount, size, dock, metrics).forEach(index => {
            const modelIndex = tasksModel.makeModelIndex(index);
            chevronMenu.addMenuItem(chevronEntry.createObject(chevronMenu, {
                launcher: index,
                text: tasksModel.data(modelIndex, Qt.DisplayRole),
                icon: tasksModel.data(modelIndex, Qt.DecorationRole)
            }));
        });
        chevronMenu.openRelative();
    }

    Repeater {
        model: tasksModel

        Loader {
            id: entry
            required property var model
            required property int index
            readonly property bool launcher: index < root.launcherCount
            readonly property var modelIndex: tasksModel.makeModelIndex(index)
            readonly property int laidOutX: launcher ? root.quickLaunchX + Band.cellsWidth(index - root.firstShown, root.metrics) : root.tasksX + (index - root.launcherCount) * (root.buttonWidth + root.gap)
            // Dragged: the button follows the pointer; the others slide into their new places.
            property bool dragging: false
            property bool slides: true
            property int dragX: 0
            x: entry.dragging ? entry.dragX : entry.laidOutX
            z: entry.dragging ? 1 : 0
            // A carried band's cells ride over the window buttons with its separators.
            Binding on z {
                when: entry.launcher && root.bandCarried
                value: 5
            }
            Behavior on x {
                enabled: entry.slides && !root.bandCarried && Plasmoid.configuration.animateButtons !== false
                NumberAnimation {
                    duration: 120
                }
            }
            width: launcher ? root.metrics.cellWidth : root.buttonWidth
            height: root.height
            visible: !launcher || (index >= root.firstShown && index < root.firstShown + root.shownLaunchers)
            sourceComponent: launcher ? launcherCell : windowButton

            Component {
                id: launcherCell
                Loader {
                    id: cell
                    anchors.fill: parent
                    source: Qt.resolvedUrl(root.isLuna ? "luna/QuickLaunchButton.qml" : "QuickLaunchButton.qml")
                    opacity: launcherArea.dragging && Launchers.releasedOffTaskbar(launcherArea.pointer.x, launcherArea.pointer.y, root.width, root.height) ? 0.5 : 1
                    Binding {
                        target: cell.item
                        property: "icon"
                        value: entry.model.decoration
                    }
                    Binding {
                        target: cell.item
                        property: "hovered"
                        value: launcherArea.containsMouse
                    }
                    Binding {
                        target: cell.item
                        property: "held"
                        value: launcherArea.pressed && launcherArea.containsMouse
                    }
                    PlasmaCore.ToolTipArea {
                        anchors.fill: parent
                        mainText: entry.model.display
                        icon: entry.model.decoration
                        DragSortArea {
                            id: launcherArea
                            anchors.fill: parent
                            layoutParent: root
                            origin: root.quickLaunchX
                            pitch: root.metrics.cellWidth
                            count: root.shownLaunchers
                            slot: entry.index - root.firstShown
                            itemWidth: root.metrics.cellWidth
                            onDraggingChanged: entry.dragging = dragging
                            onSlidesChanged: entry.slides = slides
                            onDragXChanged: entry.dragX = dragX
                            onMoved: (from, to) => tasksModel.move(root.firstShown + from, root.firstShown + to)
                            onDropped: (pointerX, pointerY) => {
                                tasksModel.syncLaunchers();
                                if (Launchers.releasedOffTaskbar(pointerX, pointerY, root.width, root.height))
                                    tasksModel.requestRemoveLauncher(entry.model.LauncherUrlWithoutIcon);
                            }
                            onTapped: (mouseButton, clickX, clickY) => {
                                if (mouseButton === Qt.RightButton) {
                                    launcherMenu.launcher = entry.model.LauncherUrlWithoutIcon;
                                    launcherMenu.visualParent = parent;
                                    launcherMenu.open(clickX, clickY);
                                } else {
                                    tasksModel.requestNewInstance(entry.modelIndex);
                                }
                            }
                        }
                    }
                }
            }
            Component {
                id: windowButton
                Item {
                    id: button
                    // Where the button is on screen: minimize effects (Title bar zoom, Squash, Magic Lamp) aim at it.
                    function publishGeometry() {
                        const corner = button.mapToGlobal(0, 0);
                        tasksModel.requestPublishDelegateGeometry(entry.modelIndex, Qt.rect(corner.x, corner.y, button.width, button.height), button);
                    }
                    Component.onCompleted: publishGeometry()
                    onWidthChanged: publishGeometry()
                    Connections {
                        target: entry
                        function onXChanged() {
                            button.publishGeometry();
                        }
                    }
                    Loader {
                        id: face
                        anchors.fill: parent
                        source: Qt.resolvedUrl(root.isLuna ? "luna/TaskButton.qml" : "TaskButton.qml")
                    }
                    Binding {
                        target: face.item
                        property: "text"
                        value: entry.model.display
                    }
                    Binding {
                        target: face.item
                        property: "icon"
                        value: entry.model.decoration
                    }
                    Binding {
                        target: face.item
                        property: "pressed"
                        value: entry.model.IsActive === true
                    }
                    Binding {
                        target: face.item
                        property: "bevel"
                        value: Plasmoid.configuration.bevel
                    }
                    Binding {
                        target: face.item
                        property: "look"
                        when: !root.isLuna
                        value: Plasmoid.configuration.look
                    }
                    // The pointer resting on the button: the window's title in the classic flat tooltip and, with a
                    // preview size chosen in the Control Panel, a live picture of the window above it (TaskToolTip.qml).
                    // The drag area sits inside the tooltip area, as the Quick Launch cell's does: a hover-enabled
                    // mouse area on top of the tooltip area would take every hover and the tooltip would never show.
                    PlasmaCore.ToolTipArea {
                        anchors.fill: parent
                        interactive: false
                        mainItem: Loader {
                            id: tip
                            property string title: entry.model.display
                            property var windowId: entry.model.WinIdList ? entry.model.WinIdList[0] : null
                            property int previewSize: Plasmoid.configuration.previewSize ?? 0
                            property string bevel: Plasmoid.configuration.bevel
                            property color face: Kirigami.Theme.backgroundColor
                            source: Qt.resolvedUrl(root.isLuna ? "luna/TaskToolTip.qml" : "TaskToolTip.qml")
                            Binding {
                                target: tip.item
                                property: "title"
                                value: tip.title
                            }
                            Binding {
                                target: tip.item
                                property: "windowId"
                                value: tip.windowId
                            }
                            Binding {
                                target: tip.item
                                property: "previewSize"
                                value: tip.previewSize
                            }
                            Binding {
                                target: tip.item
                                property: "bevel"
                                value: tip.bevel
                            }
                            Binding {
                                target: tip.item
                                property: "face"
                                value: tip.face
                            }
                        }
                        DragSortArea {
                            anchors.fill: parent
                            layoutParent: root
                            origin: root.tasksX
                            pitch: root.buttonWidth + root.gap
                            count: root.windowCount
                            slot: entry.index - root.launcherCount
                            itemWidth: root.buttonWidth
                            onDraggingChanged: entry.dragging = dragging
                            onSlidesChanged: entry.slides = slides
                            onDragXChanged: entry.dragX = dragX
                            onMoved: (from, to) => tasksModel.move(root.launcherCount + from, root.launcherCount + to)
                            onTapped: (mouseButton, clickX, clickY) => {
                                if (mouseButton === Qt.RightButton) {
                                    windowMenu.visualParent = button;
                                    windowMenu.task = entry.modelIndex;
                                    windowMenu.window = WindowMenu.windowState(entry.model);
                                    windowMenu.launcher = entry.model.LauncherUrlWithoutIcon;
                                    windowMenu.open(clickX, clickY);
                                } else if (entry.model.IsActive) {
                                    tasksModel.requestToggleMinimized(entry.modelIndex);
                                } else {
                                    tasksModel.requestActivate(entry.modelIndex);
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    PlasmaExtras.Menu {
        id: launcherMenu
        property var launcher
        PlasmaExtras.MenuItem {
            text: i18n("Remove from Quick Launch")
            onClicked: tasksModel.requestRemoveLauncher(launcherMenu.launcher)
        }
    }

    PlasmaExtras.Menu {
        id: windowMenu
        property var task
        property var launcher
        property var window: WindowMenu.windowState({})
        readonly property var enabledItems: WindowMenu.enabledItems(window)

        PlasmaExtras.MenuItem {
            text: i18n("Restore")
            enabled: windowMenu.enabledItems.restore
            onClicked: windowMenu.window.minimized ? tasksModel.requestActivate(windowMenu.task) : tasksModel.requestToggleMaximized(windowMenu.task)
        }
        PlasmaExtras.MenuItem {
            text: i18n("Move")
            enabled: windowMenu.enabledItems.move
            onClicked: tasksModel.requestMove(windowMenu.task)
        }
        PlasmaExtras.MenuItem {
            text: i18n("Size")
            enabled: windowMenu.enabledItems.size
            onClicked: tasksModel.requestResize(windowMenu.task)
        }
        PlasmaExtras.MenuItem {
            text: i18n("Minimize")
            enabled: windowMenu.enabledItems.minimize
            onClicked: tasksModel.requestToggleMinimized(windowMenu.task)
        }
        PlasmaExtras.MenuItem {
            text: i18n("Maximize")
            enabled: windowMenu.enabledItems.maximize
            onClicked: tasksModel.requestToggleMaximized(windowMenu.task)
        }
        PlasmaExtras.MenuItem {
            separator: true
        }
        PlasmaExtras.MenuItem {
            text: i18n("Add to Quick Launch")
            visible: root.showQuickLaunch && String(windowMenu.launcher || "") !== "" && tasksModel.launcherPosition(windowMenu.launcher) === -1
            onClicked: tasksModel.requestAddLauncher(windowMenu.launcher)
        }
        PlasmaExtras.MenuItem {
            separator: true
        }
        PlasmaExtras.MenuItem {
            text: i18n("Close")
            enabled: windowMenu.enabledItems.close
            onClicked: tasksModel.requestClose(windowMenu.task)
        }
    }
}
