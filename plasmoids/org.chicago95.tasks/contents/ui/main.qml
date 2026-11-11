import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.extras as PlasmaExtras
import org.kde.plasma.plasma5support as Plasma5Support
import org.kde.kirigami as Kirigami
import org.kde.taskmanager as TaskManager
import "sizing.js" as Sizing
import "launchers.js" as Launchers
import "quickLaunch.js" as QuickLaunch
import "quickLaunchBand.js" as Band

// The taskbar between the Start button and the tray, as the originals lay it out
// (tests/test_plasma_taskbar_reference.py): with Quick Launch entries, a separator, their 23px cells
// and another separator; then one button per window in the order they opened, 3px apart, as wide as
// the look allows and narrower when many share the taskbar. The originals have no gap before this
// part, so it starts over the gap Plasma's panel leaves between applets.
// A click on a window's button activates it, or minimizes it when it is already active; the right
// button opens the classic window menu, with "Add to Quick Launch". A Quick Launch entry's menu removes
// it; programs dropped on the Quick Launch are added. Whether it shows is Setup's option (quickLaunch.js).
// Its separator docks it beside the Start button or at the taskbar's end, by where it is let go; the
// separator beside the window buttons sets how many launchers show, and a chevron opens the rest
// (quickLaunchBand.js).
PlasmoidItem {
    id: root

    preferredRepresentation: fullRepresentation
    Plasmoid.backgroundHints: PlasmaCore.Types.NoBackground
    Layout.fillWidth: true
    Layout.fillHeight: true

    readonly property int contentX: -Kirigami.Units.smallSpacing   // the panel's gap between applets
    readonly property bool showQuickLaunch: QuickLaunch.shown(Plasmoid.configuration.quickLaunch, Plasmoid.configuration.look)
    readonly property int maxButtonWidth: Sizing.maxButtonWidth(Plasmoid.configuration.maxButtonWidth, Plasmoid.configuration.look)
    readonly property var metrics: Band.metrics()
    readonly property int gap: metrics.taskButtonGap
    readonly property int launcherCount: tasksModel.launcherCount
    readonly property int windowCount: tasksModel.count - launcherCount
    readonly property int lead: Plasmoid.configuration.look === "2000" ? metrics.separatorLeadAfterStart2000 : metrics.separatorLead
    readonly property string dock: Plasmoid.configuration.quickLaunchDock === "right" ? "right" : "left"
    // While a separator is dragged: the cells the band would show, and where a separator that would dock it is.
    property int liveCells: -2
    property int floatingGripX: -1
    readonly property int cells: liveCells !== -2 ? liveCells : Plasmoid.configuration.quickLaunchCells
    readonly property var band: Band.layout(width, contentX, lead, launcherCount, cells, dock)
    readonly property int shownLaunchers: band.shown
    readonly property int firstShown: band.firstShown   // the launchers before it are behind the chevron
    readonly property int quickLaunchX: band.cellsX
    readonly property int quickLaunchEnd: quickLaunchX + Band.cellsWidth(shownLaunchers)
    readonly property int tasksX: band.tasksX
    readonly property int buttonWidth: windowCount === 0 ? 0 : Math.min(maxButtonWidth, Math.floor((band.tasksEnd - tasksX + gap) / windowCount) - gap)

    function bandSettled(result) {
        liveCells = -2;
        floatingGripX = -1;
        Plasmoid.configuration.quickLaunchDock = result.dock;
        Plasmoid.configuration.quickLaunchCells = result.cells;
    }
    function quickLaunchGripResult(gripX) {
        return Band.quickLaunchGripReleased(gripX, width, contentX, lead, launcherCount, Plasmoid.configuration.quickLaunchCells, dock);
    }
    function taskGripResult(gripX) {
        return Band.taskGripReleased(gripX, width, contentX, lead, launcherCount, Plasmoid.configuration.quickLaunchCells, dock);
    }
    // The separator stays on the taskbar: it follows the pointer only along it.
    function onTaskbar(gripX, gripWidth) {
        return Math.max(contentX, Math.min(width - gripWidth, gripX));
    }

    Plasmoid.contextualActions: [
        PlasmaCore.Action {
            // qmllint disable unqualified
            // i18n() is injected into the applet context by Plasma.
            text: i18n("Properties")
            // qmllint enable unqualified
            icon.name: "preferences-system"
            onTriggered: runner.connectSource(root.controlPanelCommand)
        }
    ]
    readonly property string controlPanelCommand: "systemd-run --user --scope --quiet --collect @HOME@/.local/bin/chicago95-control-panel --page taskbar"

    // Programs start in their own systemd scope: Setup restarts plasmashell, and stopping its service
    // stops every process started inside it (tests/test_plasmoid_launches.py).
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
        // Entries added or removed here are saved; the setting's changes come back in.
        onLauncherListChanged: {
            if (root.showQuickLaunch && launcherList.join() !== Plasmoid.configuration.launchers.join())
                Plasmoid.configuration.launchers = launcherList;
        }
    }
    function loadLaunchers() {
        tasksModel.launcherList = showQuickLaunch ? Plasmoid.configuration.launchers : [];
    }
    Component.onCompleted: loadLaunchers()
    onShowQuickLaunchChanged: loadLaunchers()
    Connections {
        target: Plasmoid.configuration
        function onLaunchersChanged() {
            if (Plasmoid.configuration.launchers.join() !== tasksModel.launcherList.join())
                root.loadLaunchers();
        }
    }

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

    // While a Quick Launch entry is dragged: its icon follows the pointer and a bar marks the gap it would drop into.
    property int draggedIndex: -1
    property var draggedIcon
    property point dragPoint
    readonly property bool dragInsideTaskbar: Launchers.dragResult(draggedIndex, dragPoint.x, dragPoint.y, width, height, quickLaunchX, shownLaunchers).action !== "remove"
    Rectangle {
        visible: root.draggedIndex >= 0 && root.dragInsideTaskbar
        x: root.quickLaunchX + Launchers.insertionIndexAt(root.dragPoint.x, root.quickLaunchX, root.shownLaunchers) * root.metrics.cellWidth - 1
        y: 3
        width: 2
        height: root.height - 6
        color: "black"
        z: 10
    }
    Kirigami.Icon {
        visible: root.draggedIndex >= 0
        source: root.draggedIcon
        x: root.dragPoint.x - 8
        y: root.dragPoint.y - 8
        width: 16
        height: 16
        opacity: root.dragInsideTaskbar ? 1 : 0.5
        z: 11
    }

    Separator {
        id: quickLaunchGrip
        visible: root.launcherCount > 0
        x: root.floatingGripX >= 0 ? root.floatingGripX : root.band.quickLaunchGripX
        z: 5
        height: parent.height
        lead: root.dock === "left" ? root.lead : root.metrics.separatorLead
        draggable: true
        onDragged: gripX => {
            const result = root.quickLaunchGripResult(gripX);
            const resizing = result.dock === "right" && root.dock === "right";
            root.liveCells = resizing ? result.cells : -2;
            root.floatingGripX = resizing ? -1 : root.onTaskbar(gripX, width);
        }
        onReleased: gripX => root.bandSettled(root.quickLaunchGripResult(gripX))
    }
    Separator {
        id: taskGrip
        visible: root.launcherCount > 0
        x: root.band.taskGripX
        height: parent.height
        lead: root.dock === "left" ? root.metrics.separatorLead : root.lead
        draggable: root.dock === "left"
        onDragged: gripX => root.liveCells = root.taskGripResult(gripX).cells
        onReleased: gripX => root.bandSettled(root.taskGripResult(gripX))
    }
    Chevron {
        id: chevron
        visible: root.band.chevronX >= 0
        x: root.band.chevronX
        height: parent.height
        pointsRight: root.dock === "left"
        hovered: chevronArea.containsMouse
        held: chevronArea.pressed && chevronArea.containsMouse
        MouseArea {
            id: chevronArea
            anchors.fill: parent
            hoverEnabled: true
            onClicked: root.openChevronMenu()
        }
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
        Band.hiddenLaunchers(launcherCount, cells, dock).forEach(index => {
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
            x: launcher ? root.quickLaunchX + Band.cellsWidth(index - root.firstShown) : root.tasksX + (index - root.launcherCount) * (root.buttonWidth + root.gap)
            width: launcher ? root.metrics.cellWidth : root.buttonWidth
            height: root.height
            visible: !launcher || (index >= root.firstShown && index < root.firstShown + root.shownLaunchers)
            sourceComponent: launcher ? launcherCell : windowButton

            Component {
                id: launcherCell
                QuickLaunchButton {
                    icon: entry.model.decoration
                    hovered: launcherArea.containsMouse
                    held: launcherArea.pressed && launcherArea.containsMouse
                    PlasmaCore.ToolTipArea {
                        anchors.fill: parent
                        mainText: entry.model.display
                        icon: entry.model.decoration
                        MouseArea {
                            id: launcherArea
                            anchors.fill: parent
                            hoverEnabled: true
                            acceptedButtons: Qt.LeftButton | Qt.RightButton
                            property point pressPoint
                            property bool dragging: false
                            property bool dragEndedClick: false
                            onPressed: mouse => pressPoint = Qt.point(mouse.x, mouse.y)
                            onPositionChanged: mouse => {
                                if (!(pressedButtons & Qt.LeftButton))
                                    return;
                                const travelled = Math.abs(mouse.x - pressPoint.x) + Math.abs(mouse.y - pressPoint.y);
                                if (!dragging && travelled < Qt.styleHints.startDragDistance)
                                    return;
                                dragging = true;
                                root.draggedIcon = entry.model.decoration;
                                root.draggedIndex = entry.index - root.firstShown;
                                root.dragPoint = mapToItem(root, mouse.x, mouse.y);
                            }
                            onReleased: mouse => {
                                if (!dragging)
                                    return;
                                dragging = false;
                                dragEndedClick = true;
                                const result = Launchers.dragResult(entry.index - root.firstShown, root.dragPoint.x, root.dragPoint.y, root.width, root.height, root.quickLaunchX, root.shownLaunchers);
                                root.draggedIndex = -1;
                                if (result.action === "remove")
                                    tasksModel.requestRemoveLauncher(entry.model.LauncherUrlWithoutIcon);
                                else if (result.action === "move")
                                    tasksModel.move(entry.index, root.firstShown + result.to);
                            }
                            onClicked: mouse => {
                                if (dragEndedClick) {
                                    dragEndedClick = false;
                                    return;
                                }
                                if (mouse.button === Qt.RightButton) {
                                    launcherMenu.launcher = entry.model.LauncherUrlWithoutIcon;
                                    launcherMenu.visualParent = parent;
                                    launcherMenu.openRelative();
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
                TaskButton {
                    id: button
                    text: entry.model.display
                    icon: entry.model.decoration
                    pressed: entry.model.IsActive === true
                    look: Plasmoid.configuration.look
                    MouseArea {
                        anchors.fill: parent
                        acceptedButtons: Qt.LeftButton | Qt.RightButton
                        onClicked: mouse => {
                            if (mouse.button === Qt.RightButton) {
                                windowMenu.visualParent = button;
                                windowMenu.task = entry.modelIndex;
                                windowMenu.launcher = entry.model.LauncherUrlWithoutIcon;
                                windowMenu.openRelative();
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

    PlasmaExtras.Menu {
        id: launcherMenu
        property var launcher
        placement: PlasmaExtras.Menu.TopPosedLeftAlignedPopup
        PlasmaExtras.MenuItem {
            text: i18n("Remove from Quick Launch")
            onClicked: tasksModel.requestRemoveLauncher(launcherMenu.launcher)
        }
    }

    PlasmaExtras.Menu {
        id: windowMenu
        property var task
        property var launcher
        placement: PlasmaExtras.Menu.TopPosedLeftAlignedPopup

        PlasmaExtras.MenuItem {
            text: i18n("Restore")
            onClicked: tasksModel.requestActivate(windowMenu.task)
        }
        PlasmaExtras.MenuItem {
            text: i18n("Minimize")
            onClicked: tasksModel.requestToggleMinimized(windowMenu.task)
        }
        PlasmaExtras.MenuItem {
            text: i18n("Maximize")
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
            onClicked: tasksModel.requestClose(windowMenu.task)
        }
    }
}
