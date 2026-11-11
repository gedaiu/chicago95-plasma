import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore

// The tray as the originals draw it (tests/test_plasma_taskbar_reference.py), around Plasma's system
// tray, which follows this applet, and the clock after it: the tray's icons 16px, 17px apart, on row 7
// of the taskbar, the last one just before the clock's cell (1px; 4px on 2000); the sunken box from
// 3px before the first icon (4px on 2000) to the end of the clock's cell.
// Plasma's tray draws its icons at 22px in cells of its own; each item is resized and placed here: its
// icon at 16px when the item shows one (programs' icons, most applets), else its whole 22px icon area
// scaled to 16px (applets that draw something else).
PlasmoidItem {
    id: root

    preferredRepresentation: fullRepresentation
    Plasmoid.backgroundHints: PlasmaCore.Types.NoBackground

    Layout.minimumWidth: 1
    Layout.preferredWidth: 1
    Layout.maximumWidth: 1
    Layout.fillHeight: true

    readonly property bool look2000: Plasmoid.configuration.look === "2000"
    readonly property int iconSize: 16
    readonly property int iconPitch: 17
    readonly property int iconTop: 7
    readonly property int clockGap: look2000 ? 4 : 1
    readonly property int boxPadding: look2000 ? 4 : 3

    // The panel layout holds one container per applet: ours, the tray's and the clock's.
    property Item container: null
    property Item row: null
    property Item trayItem: null
    property Item clockItem: null
    property real boxLeft: 0
    property real boxRight: 0

    function locate() {
        let child = root
        let up = root.parent
        const wide = Math.max(root.height, 10) * 8
        while (up && up.width < wide && up.parent) {
            child = up
            up = up.parent
        }
        if (!up || up.width < wide) return
        container = child
        row = up
    }
    Component.onCompleted: locate()
    onParentChanged: locate()

    function nextAfter(item) {
        let next = null
        for (let i = 0; i < row.children.length; i++) {
            const candidate = row.children[i]
            if (candidate.visible && candidate.width > 0 && candidate.x > item.x && (next === null || candidate.x < next.x)) next = candidate
        }
        return next
    }

    function find(item, depth, kind) {   // the first visible item of the kind, depth first
        if (!item || depth > 12) return null
        if (item.toString().indexOf(kind) === 0 && item.visible && item.width > 0) return item
        for (let i = 0; i < item.children.length; i++) {
            const found = find(item.children[i], depth + 1, kind)
            if (found) return found
        }
        return null
    }

    readonly property string arrowIcon: "@HOME@/.local/share/chicago95/icons/tray-chevron.png"
    function restyleArrow(arrow) {   // the chevron at its own size, on the icons' row
        for (let i = 0; i < arrow.children.length; i++) {
            const icon = arrow.children[i]
            if (icon.toString().indexOf("Icon") !== 0) continue
            if (icon.source !== arrowIcon) { icon.source = arrowIcon; icon.smooth = false }
            icon.anchors.fill = undefined
            icon.anchors.centerIn = undefined
            icon.width = iconSize
            icon.height = iconSize
            icon.x = Math.round((arrow.width - iconSize) / 2)
            icon.y = Math.round(icon.parent.mapFromItem(null, 0, iconTop).y)
        }
    }

    function shift(item, by) {
        if (item.transform.length !== 1) item.transform = [Qt.createQmlObject("import QtQuick; Translate {}", item)]
        if (item.transform[0].x !== by) item.transform[0].x = by
    }

    function placeIcons() {
        if (!row) locate()
        if (!row || !container) return
        trayItem = nextAfter(container)
        clockItem = trayItem ? nextAfter(trayItem) : null
        if (!trayItem) return
        // The "show hidden icons" arrow: a chevron first in the tray box, as the originals have it. Plasma
        // lays it out after the icons; the tray grows by its width (else it lies over the clock, which takes
        // its clicks) and it trades places with the icons, by transforms, which move their clicks too.
        const arrow = find(trayItem, 0, "ExpanderArrow")
        const arrowWidth = arrow ? arrow.width : 0
        const grid = find(trayItem, 0, "QQuickGridView")
        if (!grid || !grid.contentItem) return
        if (grid.cellWidth !== iconPitch) grid.cellWidth = iconPitch
        shift(grid, arrowWidth)
        if (arrow) {
            restyleArrow(arrow)
            shift(arrow, -(arrow.x - grid.x))
        }
        // Each tray entry holds its icon area in a focus scope; the grid's own helper items have none.
        const icons = []
        for (let i = 0; i < grid.contentItem.children.length; i++) {
            const delegate = grid.contentItem.children[i]
            const area = delegate.visible && delegate.width > 0 ? find(delegate, 0, "QQuickFocusScope") : null
            if (area) icons.push({ delegate: delegate, area: area, icon: find(area, 0, "Icon") })
        }
        icons.sort((a, b) => a.delegate.x - b.delegate.x)
        const clockX = clockItem ? clockItem.mapToItem(null, 0, 0).x : trayItem.mapToItem(null, trayItem.width, 0).x
        const firstX = clockX - clockGap - iconSize - (icons.length - 1) * iconPitch
        icons.forEach(({ area, icon }, index) => {
            const x = firstX + index * iconPitch
            if (icon) {
                const spot = icon.parent.mapFromItem(null, x, iconTop)
                icon.anchors.fill = undefined
                icon.width = iconSize
                icon.height = iconSize
                icon.x = Math.round(spot.x)
                icon.y = Math.round(spot.y)
            } else {
                const base = area.parent.mapToItem(null, area.x, area.y)   // without the area's own transform
                if (area.transform.length !== 2)   // a scale from the top-left corner, then a shift into the cell
                    area.transform = [Qt.createQmlObject("import QtQuick; Scale {}", area), Qt.createQmlObject("import QtQuick; Translate {}", area)]
                const scale = area.transform[0], shift = area.transform[1]
                scale.xScale = scale.yScale = iconSize / Math.max(1, area.width)
                shift.x = Math.round(x - base.x)
                shift.y = Math.round(iconTop - base.y)
            }
        })
        const wanted = icons.length * iconPitch + arrowWidth
        if (trayItem.Layout && trayItem.Layout.maximumWidth !== wanted) {
            trayItem.Layout.minimumWidth = wanted
            trayItem.Layout.preferredWidth = wanted
            trayItem.Layout.maximumWidth = wanted
        }
        const origin = root.mapToItem(null, 0, 0).x
        boxLeft = firstX - arrowWidth - boxPadding - origin
        boxRight = (clockItem ? clockX + clockItem.width : clockX) - origin
    }

    Timer { interval: 500; running: true; repeat: true; onTriggered: root.placeIcons() }

    TrayBox {
        z: -1
        x: root.boxLeft
        width: root.boxRight - root.boxLeft + 1
        height: root.height
    }
}
