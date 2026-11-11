import QtQuick
import org.kde.kirigami as Kirigami
import "../quickLaunchBand.js" as Band

Item {
    id: cell
    property var icon
    property bool hovered
    property bool held

    readonly property var metrics: Band.metrics("luna")
    readonly property int cellTop: 4
    readonly property int cellHeight: 22

    implicitWidth: metrics.cellWidth
    implicitHeight: cellTop + cellHeight

    BandHover {
        y: cell.cellTop
        width: cell.width
        height: cell.cellHeight
        visible: cell.hovered || cell.held
        held: cell.held
    }
    Kirigami.Icon {
        x: cell.metrics.iconInset + (cell.held ? 1 : 0)
        y: cell.cellTop + cell.metrics.iconInset + (cell.held ? 1 : 0)
        width: 16
        height: 16
        source: cell.icon
        roundToIconSize: false
    }
}
