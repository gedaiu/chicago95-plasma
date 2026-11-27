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
import "styleParts.js" as Parts
import "grouping.js" as Grouping
import "paging.js" as Paging

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
    // Windows 7's superbar has no Quick Launch band to drag: its pinned programs have no separators.
    readonly property bool showsSeparators: launcherCount > 0 && Plasmoid.configuration.taskbarStyle !== "aero"
    // Unlocked, Windows 7's taskbar shows a grip (TaskBar::Rebar GRIPPER) where its band began, the band after it.
    readonly property bool showsGrip: Plasmoid.configuration.taskbarStyle === "aero" && !Plasmoid.configuration.locked
    readonly property int gripWidth: 12
    readonly property int bandStart: -Kirigami.Units.smallSpacing   // the panel's gap between applets
    readonly property int contentX: bandStart + (showsGrip ? gripWidth : 0)
    readonly property bool showQuickLaunch: QuickLaunch.shown(Plasmoid.configuration.quickLaunch, Plasmoid.configuration.look)
    readonly property int maxButtonWidth: Sizing.maxButtonWidth(Plasmoid.configuration.maxButtonWidth, Plasmoid.configuration.look)
    readonly property int styledMaxButtonWidth: Sizing.styledButtonWidth(
        maxButtonWidth, Plasmoid.configuration.maxButtonWidth, Plasmoid.configuration.taskbarStyle,
        Plasmoid.configuration.referenceDpi)
    readonly property var metrics: Band.metrics(
        Plasmoid.configuration.taskbarStyle, Plasmoid.configuration.look, Plasmoid.configuration.referenceDpi)
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
    readonly property var band: Band.layout(width, contentX, lead, pagesButtons ? 0 : launcherCount, size, dock, metrics)
    readonly property int bandShift: bandCarried ? Band.carriedShift(carriedGripX, band, dock, width, contentX, metrics) : 0
    readonly property int shownLaunchers: band.shown
    readonly property int firstShown: band.firstShown   // the launchers before it are behind the chevron
    readonly property int quickLaunchX: band.cellsX + bandShift
    readonly property int quickLaunchEnd: quickLaunchX + Band.cellsWidth(shownLaunchers, metrics)
    readonly property int tasksX: band.tasksX
    // "Group similar taskbar buttons": a program's windows combine into one button always, once more windows are open
    // than buttons fit at their full width, or never (grouping.js).
    readonly property string groupingMode: Grouping.mode(Plasmoid.configuration.grouping, Plasmoid.configuration.taskbarStyle)
    readonly property int fittingButtons: Math.floor((band.tasksEnd - tasksX + gap) / (styledMaxButtonWidth + gap))
    // Windows 7's superbar keeps its buttons whole and pages them (paging.js); the older taskbars narrow them to fit.
    readonly property bool pagesButtons: Plasmoid.configuration.taskbarStyle === "aero"
    readonly property int pageArrowsWidth: 17
    readonly property var paging: pagesButtons ? Paging.layout(tasksModel.count, {
        room: band.tasksEnd - tasksX,
        buttonWidth: styledMaxButtonWidth,
        gap: gap,
        arrowWidth: pageArrowsWidth
    }) : {
        perPage: windowCount,
        pages: 1
    }
    readonly property int pageStart: shownPage * paging.perPage
    readonly property int pageCount: Math.min(paging.perPage, tasksModel.count - pageStart)
    property int page: 0
    readonly property int shownPage: Paging.clamped(page, paging.pages)
    readonly property int buttonWidth: pagesButtons ? styledMaxButtonWidth : windowCount === 0 ? 0 : Math.min(styledMaxButtonWidth, Math.floor((band.tasksEnd - tasksX + gap) / windowCount) - gap)

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
            id: quickLaunchAction
            text: i18n("Quick Launch")
            checkable: true
            checked: root.showQuickLaunch
            onTriggered: Plasmoid.configuration.quickLaunch = quickLaunchAction.checked ? "yes" : "no"
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
            id: lockAction
            text: i18n("Lock the taskbar")
            visible: Plasmoid.configuration.taskbarStyle === "aero"   // only Windows 7's taskbar has a grip to show
            checkable: true
            checked: Plasmoid.configuration.locked
            onTriggered: Plasmoid.configuration.locked = lockAction.checked
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

    Component { id: jumpItem; PlasmaExtras.MenuItem {} }
    function jumpCommand(args) {
        const path = decodeURIComponent(Qt.resolvedUrl("jumpList.py").toString().replace(/^file:\/\//, ""));
        return ["python3", path, ...args].map(arg => "'" + String(arg).replace(/'/g, "'\\''") + "'").join(" ");
    }
    function openTaskMenu(menu, first, x, y) {
        if (!root.pagesButtons) { menu.open(x, y); return; }
        for (const item of menu.jumpItems) {
            menu.removeMenuItem(item);
            item.destroy();
        }
        menu.jumpItems = [];
        const launcher = String(menu.launcher || "");
        const command = jumpCommand([launcher]);
        jumpReader.pending = {menu, first, launcher, command, x, y};
        jumpReader.connectSource(command);
    }
    Plasma5Support.DataSource {
        id: jumpReader
        engine: "executable"
        property var pending
        onNewData: (source, data) => {
            disconnectSource(source);
            const request = pending;
            if (!request || source !== request.command) return;
            pending = null;
            if (!request.menu.visualParent || String(request.menu.launcher || "") !== request.launcher) return;
            let entries = [];
            try { entries = JSON.parse(data.stdout); } catch (error) {}
            let lastSection = "";
            for (const entry of entries) {
                const heading = entry.uri ? i18n("Recent") : i18n("Tasks");
                if (heading !== lastSection) {
                    const section = jumpItem.createObject(request.menu, {text: heading, enabled: false});
                    request.menu.addMenuItem(section, request.first);
                    request.menu.jumpItems.push(section);
                    lastSection = heading;
                }
                const item = jumpItem.createObject(request.menu, {text: entry.label.replace(/&/g, "&&")});
                item.clicked.connect(() => runner.connectSource(root.jumpCommand([request.launcher,
                    entry.action ? "action" : "uri", entry.action || entry.uri])));
                request.menu.addMenuItem(item, request.first);
                request.menu.jumpItems.push(item);
            }
            if (entries.length) {
                const divider = jumpItem.createObject(request.menu, {separator: true});
                request.menu.addMenuItem(divider, request.first);
                request.menu.jumpItems.push(divider);
            }
            request.menu.open(request.x, request.y);
        }
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
        groupMode: root.groupingMode === "never" ? TaskManager.TasksModel.GroupDisabled : TaskManager.TasksModel.GroupApplications
        groupInline: false
        groupingWindowTasksThreshold: Grouping.threshold(root.groupingMode, root.fittingButtons)
        sortMode: TaskManager.TasksModel.SortManual
        separateLaunchers: !root.pagesButtons
        launchInPlace: root.pagesButtons
        hideActivatedLaunchers: root.pagesButtons
        // The launchers go in once the applet is complete. Given while it loads, Plasma never counts them: it counts
        // launchers when rows change, and with the windows already there (a login restoring the last session) no row
        // changes until a window opens, so the cells draw as window buttons until then.
        launcherList: (root.pagesButtons || root.completed) ? QuickLaunch.launchers(root.showQuickLaunch, Plasmoid.configuration.launchers) : []
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
        x: root.pagesButtons ? root.contentX : root.quickLaunchX
        width: root.pagesButtons ? root.width - x : Math.max(root.metrics.cellWidth, root.quickLaunchEnd - root.quickLaunchX)
        height: parent.height
        onDropped: drop => {
            const insertAt = root.pagesButtons ? root.pageStart + Math.min(root.pageCount, Math.round(drop.x / root.metrics.cellWidth)) : root.firstShown + Launchers.insertionIndexAt(x + drop.x, root.quickLaunchX, root.shownLaunchers, root.metrics.cellWidth);
            drop.urls.forEach((url, offset) => {
                const before = tasksModel.count;
                tasksModel.requestAddLauncher(url);
                if (tasksModel.count > before) {
                    tasksModel.move(root.pagesButtons ? before : tasksModel.launcherCount - 1, insertAt + offset);
                    tasksModel.syncLaunchers();
                }
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
        visible: root.showsSeparators
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
        visible: root.showsSeparators
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
        source: Qt.resolvedUrl(Parts.path(Plasmoid.configuration.taskbarStyle, "Chevron.qml"))
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
        Band.chevronLaunchers({
            count: launcherCount,
            size: size,
            dock: dock
        }, metrics).forEach(index => {
            const modelIndex = tasksModel.makeModelIndex(index);
            chevronMenu.addMenuItem(chevronEntry.createObject(chevronMenu, {
                launcher: index,
                text: tasksModel.data(modelIndex, Qt.DisplayRole),
                icon: tasksModel.data(modelIndex, Qt.DecorationRole)
            }));
        });
        chevronMenu.openRelative();
    }

    KSvg.SvgItem {
        visible: root.showsGrip
        x: root.bandStart
        width: root.gripWidth
        height: root.height
        imagePath: "widgets/grip"
        elementId: "grip"
    }
    Loader {
        active: root.paging.pages > 1
        x: root.tasksX + root.paging.perPage * (root.buttonWidth + root.gap)
        width: root.pageArrowsWidth
        height: root.height
        source: Qt.resolvedUrl(Parts.path(Plasmoid.configuration.taskbarStyle, "PageArrows.qml"))
        onLoaded: {
            item.page = Qt.binding(() => root.shownPage);
            item.pages = Qt.binding(() => root.paging.pages);
            item.moved.connect(page => root.page = page);
        }
    }
    // Restored windows can arrive before their launchers. Rebuild the saved superbar order once
    // all pinned rows exist, including pins represented by running windows.
    Timer {
        id: restorePins
        interval: 150
        onTriggered: {
            if (!root.pagesButtons || root.pinsPlaced || !tasksModel.launcherList.length)
                return;
            const saved = Array.from(tasksModel.launcherList, url => String(url).split(/[/:]/).pop());
            const rows = Array.from({
                length: entries.count
            }, (_, i) => {
                const row = entries.itemAt(i);
                return String(row?.model.LauncherUrlWithoutIcon ?? "").split(/[/:]/).pop();
            });
            if (!saved.every(id => rows.includes(id)))
                return;
            root.pinsPlaced = true;
            saved.forEach((id, to) => {
                const from = rows.indexOf(id, to);
                if (from > to) {
                    tasksModel.move(from, to);
                    rows.splice(to, 0, rows.splice(from, 1)[0]);
                }
            });
        }
    }
    property bool pinsPlaced: false
    Repeater {
        id: entries
        model: tasksModel
        onItemAdded: if (root.pagesButtons && !root.pinsPlaced)
            restorePins.restart()

        Loader {
            id: entry
            required property var model
            required property int index
            readonly property bool launcher: root.pagesButtons ? model.IsLauncher === true : index < root.launcherCount
            readonly property var modelIndex: tasksModel.makeModelIndex(index)
            readonly property bool fileManager: ["thunar.desktop", "org.kde.dolphin.desktop"].includes(String(model.LauncherUrlWithoutIcon ?? "").split(/[/:]/).pop())
            readonly property real laidOutX: root.pagesButtons ? root.tasksX + slot % root.paging.perPage * (root.buttonWidth + root.gap) - (launcher ? 1 : 0) : launcher ? root.quickLaunchX + Band.cellsWidth(index - root.firstShown, root.metrics) : root.tasksX + slot % root.paging.perPage * (root.buttonWidth + root.gap)
            readonly property int slot: root.pagesButtons ? index : index - root.launcherCount
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
            visible: launcher && !root.pagesButtons ? index >= root.firstShown && index < root.firstShown + root.shownLaunchers : Math.floor(slot / root.paging.perPage) === root.shownPage
            sourceComponent: launcher ? launcherCell : windowButton

            Component {
                id: launcherCell
                Loader {
                    id: cell
                    anchors.fill: parent
                    source: Qt.resolvedUrl(Parts.path(Plasmoid.configuration.taskbarStyle, "QuickLaunchButton.qml"))
                    opacity: launcherArea.dragging && Launchers.releasedOffTaskbar(launcherArea.pointer.x, launcherArea.pointer.y, root.width, root.height) ? 0.5 : 1
                    Binding {
                        target: cell.item
                        property: "icon"
                        value: entry.model.decoration
                    }
                    Binding {
                        target: cell.item
                        property: "metrics"
                        when: Plasmoid.configuration.taskbarStyle === "classic"
                        value: root.metrics
                    }
                    Binding {
                        target: cell.item
                        property: "fileManager"
                        when: root.pagesButtons && cell.item?.fileManager !== undefined
                        value: entry.fileManager
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
                            origin: root.pagesButtons ? root.contentX : root.quickLaunchX
                            pitch: root.metrics.cellWidth
                            count: root.pagesButtons ? root.pageCount : root.shownLaunchers
                            slot: entry.index - (root.pagesButtons ? root.pageStart : root.firstShown)
                            itemWidth: root.metrics.cellWidth
                            onDraggingChanged: entry.dragging = dragging
                            onSlidesChanged: entry.slides = slides
                            onDragXChanged: entry.dragX = dragX
                            onMoved: (from, to) => tasksModel.move(entry.index - slot + from, entry.index - slot + to)
                            onDropped: (pointerX, pointerY) => {
                                tasksModel.syncLaunchers();
                                if (Launchers.releasedOffTaskbar(pointerX, pointerY, root.width, root.height))
                                    tasksModel.requestRemoveLauncher(entry.model.LauncherUrlWithoutIcon);
                            }
                            onTapped: (mouseButton, clickX, clickY) => {
                                if (mouseButton === Qt.RightButton) {
                                    launcherMenu.launcher = entry.model.LauncherUrlWithoutIcon;
                                    launcherMenu.visualParent = parent;
                                    root.openTaskMenu(launcherMenu, unpinItem, clickX, clickY);
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
                        source: Qt.resolvedUrl(Parts.path(Plasmoid.configuration.taskbarStyle, "TaskButton.qml"))
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
                        property: "fileManager"
                        when: root.pagesButtons && face.item?.fileManager !== undefined
                        value: entry.fileManager
                    }
                    Binding {
                        target: face.item
                        property: "pressed"
                        value: entry.model.IsActive === true
                    }
                    Binding {
                        target: face.item
                        property: "windows" // a combined button's stacked edges (aero/TaskButton.qml)
                        when: Plasmoid.configuration.taskbarStyle === "aero"
                        value: entry.model.IsGroupParent ? (entry.model.ChildCount ?? 0) : 1
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
                    Binding {
                        target: face.item
                        property: "referenceDpi"
                        when: Plasmoid.configuration.taskbarStyle === "classic"
                        value: Plasmoid.configuration.referenceDpi
                    }
                    // The pointer resting on the button: the window's title in the classic flat tooltip and, with a
                    // preview size chosen in the Control Panel, a live picture of the window above it (TaskToolTip.qml).
                    // The drag area sits inside the tooltip area, as the Quick Launch cell's does: a hover-enabled
                    // mouse area on top of the tooltip area would take every hover and the tooltip would never show.
                    PlasmaCore.ToolTipArea {
                        anchors.fill: parent
                        id: previews
                        interactive: root.pagesButtons
                        mainItem: Loader {
                            id: tip
                            property string title: entry.model.display
                            property var windowId: entry.model.WinIdList ? entry.model.WinIdList[0] : null
                            property int previewSize: Plasmoid.configuration.previewSize ?? 0
                            property string bevel: Plasmoid.configuration.bevel
                            property color face: Kirigami.Theme.backgroundColor
                            source: Qt.resolvedUrl(Parts.path(Plasmoid.configuration.taskbarStyle, "TaskToolTip.qml"))
                            onLoaded: {
                                if (root.pagesButtons && item.chooseWindow) {
                                    item.ids = Qt.binding(() => entry.model.WinIdList ?? []);
                                    item.titleAt = row => entry.model.IsGroupParent ? tasksModel.data(tasksModel.makeModelIndex(entry.index, row), Qt.DisplayRole) : entry.model.display;
                                    item.iconAt = row => entry.model.IsGroupParent ? tasksModel.data(tasksModel.makeModelIndex(entry.index, row), Qt.DecorationRole) : entry.model.decoration;
                                    item.closeWindow.connect(row => tasksModel.requestClose(entry.model.IsGroupParent ? tasksModel.makeModelIndex(entry.index, row) : entry.modelIndex));
                                    item.chooseWindow.connect(row => {
                                        previews.hideToolTip();
                                        tasksModel.requestActivate(entry.model.IsGroupParent ? tasksModel.makeModelIndex(entry.index, row) : entry.modelIndex);
                                    });
                                }
                            }
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
                                property: "look"
                                when: Plasmoid.configuration.taskbarStyle === "classic" && tip.item !== null
                                value: Plasmoid.configuration.look
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
                            count: root.pagesButtons ? root.pageCount : root.windowCount
                            slot: entry.index - (root.pagesButtons ? root.pageStart : root.launcherCount)
                            itemWidth: root.buttonWidth
                            onDraggingChanged: entry.dragging = dragging
                            onSlidesChanged: entry.slides = slides
                            onDragXChanged: entry.dragX = dragX
                            onMoved: (from, to) => tasksModel.move(entry.index - slot + from, entry.index - slot + to)
                            onDropped: if (root.pagesButtons)
                                tasksModel.syncLaunchers()
                            onTapped: (mouseButton, clickX, clickY) => {
                                if (mouseButton === Qt.RightButton) {
                                    windowMenu.visualParent = button;
                                    windowMenu.task = entry.modelIndex;
                                    windowMenu.window = WindowMenu.windowState(entry.model);
                                    windowMenu.launcher = entry.model.LauncherUrlWithoutIcon;
                                    root.openTaskMenu(windowMenu, restoreItem, clickX, clickY);
                                } else if (root.pagesButtons && entry.model.IsGroupParent) {
                                    previews.showToolTip();
                                } else if (entry.model.IsGroupParent) {
                                    const windows = tasksModel.rowCount(entry.modelIndex);
                                    const focused = [];
                                    for (let row = 0; row < windows; ++row)
                                        focused.push(tasksModel.data(tasksModel.makeModelIndex(entry.index, row), TaskManager.AbstractTasksModel.IsActive) === true);
                                    tasksModel.requestActivate(tasksModel.makeModelIndex(entry.index, Grouping.nextWindow(focused)));
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
        property var jumpItems: []
        property var launcher
        PlasmaExtras.MenuItem {
            id: unpinItem
            text: root.pagesButtons ? i18n("Unpin this program from taskbar") : i18n("Remove from Quick Launch")
            onClicked: tasksModel.requestRemoveLauncher(launcherMenu.launcher)
        }
    }

    PlasmaExtras.Menu {
        id: windowMenu
        property var jumpItems: []
        property var task
        property var launcher
        property var window: WindowMenu.windowState({})
        readonly property var enabledItems: WindowMenu.enabledItems(window)

        PlasmaExtras.MenuItem {
            id: restoreItem
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
            text: root.pagesButtons ? i18n("Pin this program to taskbar") : i18n("Add to Quick Launch")
            visible: root.showQuickLaunch && String(windowMenu.launcher || "") !== "" && tasksModel.launcherPosition(windowMenu.launcher) === -1
            onClicked: tasksModel.requestAddLauncher(windowMenu.launcher)
        }
        PlasmaExtras.MenuItem {
            text: root.pagesButtons ? i18n("Unpin this program from taskbar") : i18n("Remove from Quick Launch")
            visible: root.pagesButtons && root.showQuickLaunch && String(windowMenu.launcher || "") !== "" && tasksModel.launcherPosition(windowMenu.launcher) >= 0
            onClicked: tasksModel.requestRemoveLauncher(windowMenu.launcher)
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
