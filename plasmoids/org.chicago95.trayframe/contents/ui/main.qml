import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore

PlasmoidItem {
    id: root

    preferredRepresentation: fullRepresentation
    Plasmoid.backgroundHints: PlasmaCore.Types.NoBackground

    readonly property int gap: 6
    Layout.minimumWidth: gap
    Layout.preferredWidth: gap
    Layout.maximumWidth: gap
    Layout.fillHeight: true

    // The panel layout holds one container per applet; find ours and that layout.
    property Item container: null
    property Item row: null

    function locate() {
        let child = root
        let up = root.parent
        const wide = Math.max(root.height, 10) * 8
        while (up && up.width < wide && up.parent) {
            child = up
            up = up.parent
        }
        if (!up || up.width < wide) return false
        container = child
        row = up
        return true
    }
    Component.onCompleted: locate()
    onParentChanged: locate()

    // Plasma's tray never draws icons below 22px: tighten its grid cells and scale each icon to 16px.
    readonly property real trayScale: 16 / 22
    readonly property int trayCell: 24
    property Item trayItem: null
    property bool gridNudged: false

    function shrinkTray() {
        if (!row || !container) return
        let tray = null
        for (let i = 0; i < row.children.length; i++) {
            const item = row.children[i]
            if (item !== container && item.x > container.x && (tray === null || item.x < tray.x)) tray = item
        }
        trayItem = tray
        nudgeClock()
        restyleTray()
    }

    // The clock sits a pixel high against the tray icons; shift it down to the Win95 baseline.
    property bool clockNudged: false
    function nudgeClock() {
        if (clockNudged || !trayItem) return
        let clock = null
        for (let i = 0; i < row.children.length; i++) {
            const item = row.children[i]
            if (item.x > trayItem.x && (clock === null || item.x < clock.x)) clock = item
        }
        if (clock) {
            const shift = Qt.createQmlObject("import QtQuick; Translate { y: 3 }", clock)
            clock.transform = [shift]
            clockNudged = true
        }
    }

    readonly property string arrowIcon: "@HOME@/.local/share/chicago95/icons/tray-arrow-up.png"
    function restyleArrow(item, depth) {
        if (!item || depth > 8) return
        if (item.toString().indexOf("ExpanderArrow") === 0) {
            for (let i = 0; i < item.children.length; i++) {
                const icon = item.children[i]
                if (icon.toString().indexOf("Icon") === 0 && icon.source !== arrowIcon) { icon.source = arrowIcon; icon.smooth = false }
            }
            return
        }
        for (let i = 0; i < item.children.length; i++) restyleArrow(item.children[i], depth + 1)
    }

    function findGridView(item, depth) {
        if (!item || depth > 8) return null
        if (item.toString().indexOf("QQuickGridView") === 0) return item
        for (let i = 0; i < item.children.length; i++) {
            const found = findGridView(item.children[i], depth + 1)
            if (found) return found
        }
        return null
    }

    function restyleTray() {
        const grid = findGridView(trayItem, 0)
        if (!grid) return
        if (grid.cellWidth !== trayCell) grid.cellWidth = trayCell
        if (!gridNudged) {
            grid.transform = [Qt.createQmlObject("import QtQuick; Translate { y: 1 }", grid)]
            gridNudged = true
        }
        const wanted = Math.round(grid.width + trayCell + 22 - 8)
        if (trayItem.Layout && trayItem.Layout.maximumWidth !== wanted) {
            trayItem.Layout.minimumWidth = wanted
            trayItem.Layout.preferredWidth = wanted
            trayItem.Layout.maximumWidth = wanted
        }
        restyleArrow(trayItem, 0)
        const content = grid.contentItem
        if (!content) return
        for (let i = 0; i < content.children.length; i++) {
            const delegate = content.children[i]
            if (delegate.scale !== trayScale) {
                delegate.transformOrigin = Item.Center
                delegate.scale = trayScale
            }
        }
    }

    Timer { interval: 1000; running: true; repeat: true; onTriggered: { if (!root.row) root.locate(); if (root.row && !root.trayItem) root.shrinkTray(); else if (root.trayItem) root.restyleTray(); if (root.row) root.restyleTasks() } }

    // Win95 task buttons: 16px icon, vertically centred, bold label on the active window.
    readonly property int taskIconSize: 16
    readonly property int taskInsetTop: 4
    readonly property int taskInsetBottom: 2
    property var boundLabels: []

    function isTaskItem(item) {
        return item && item.hasOwnProperty("smartLauncherItem") && item.hasOwnProperty("model")
    }

    function restyleTask(task) {
        for (let i = 0; i < task.children.length; i++) {
            const child = task.children[i]
            const kind = child.toString()
            if (kind.indexOf("QQuickLoader") === 0 && child.width > 0 && child.height > 0 && child.width !== taskIconSize) {
                child.anchors.top = undefined
                child.anchors.verticalCenter = task.verticalCenter
                child.anchors.verticalCenterOffset = 1
                child.anchors.leftMargin = 5
                child.width = taskIconSize
                child.height = taskIconSize
            } else if (kind.indexOf("FrameSvgItem") >= 0) {
                if (child.anchors.topMargin !== taskInsetTop) {
                    child.anchors.topMargin = taskInsetTop
                    child.anchors.bottomMargin = taskInsetBottom
                }
            } else if (kind.indexOf("Label") >= 0 || kind.indexOf("QQuickText") === 0) {
                if (boundLabels.indexOf(child) < 0) {
                    child.font.bold = Qt.binding(function() { return task.model && task.model.IsActive === true })
                    child.anchors.topMargin = child.anchors.topMargin + 2
                    child.anchors.leftMargin = Qt.binding(function() { return 5 + taskIconSize + 4 })
                    boundLabels.push(child)
                }
            }
        }
    }

    function walkTasks(item, depth) {
        if (!item || depth > 12) return
        if (isTaskItem(item)) { restyleTask(item); return }
        for (let i = 0; i < item.children.length; i++) walkTasks(item.children[i], depth + 1)
    }

    function restyleTasks() {
        for (let i = 0; i < row.children.length; i++) walkTasks(row.children[i], 0)
    }

    Item {
        id: frame
        z: -1
        y: 2
        height: root.height - 2
        x: 2
        width: row && container ? Math.max(0, row.width - container.x - 4) : root.width

        Rectangle { anchors { top: parent.top; left: parent.left; right: parent.right } height: 1; color: "#808080" }
        Rectangle { anchors { top: parent.top; left: parent.left; bottom: parent.bottom } width: 1; color: "#808080" }
        Rectangle { anchors { bottom: parent.bottom; left: parent.left; right: parent.right } height: 1; color: "#FFFFFF" }
        Rectangle { anchors { top: parent.top; right: parent.right; bottom: parent.bottom } width: 1; color: "#FFFFFF" }
    }
}
