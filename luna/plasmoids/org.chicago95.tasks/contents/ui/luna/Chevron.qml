import QtQuick
import "../quickLaunchBand.js" as Band

Item {
    id: chevron
    property bool hovered
    property bool held
    property bool pointsRight: true

    readonly property int cellTop: 4
    readonly property int cellHeight: 22
    readonly property int arrowHeight: 5
    readonly property int arrowPitch: 4
    readonly property int arrowRow: 2
    readonly property color glyphColor: "#7BB6E8"

    implicitWidth: Band.metrics("luna").chevronWidth
    implicitHeight: cellTop + cellHeight

    BandHover {
        y: chevron.cellTop
        width: chevron.width
        height: chevron.cellHeight
        visible: chevron.hovered || chevron.held
        held: chevron.held
    }
    Repeater {
        model: 10

        Rectangle {
            required property int index
            readonly property int arrow: Math.floor(index / chevron.arrowHeight)
            readonly property int row: index % chevron.arrowHeight
            readonly property int reach: Math.min(row, chevron.arrowHeight - 1 - row)
            x: Math.round((chevron.width - 2 * chevron.arrowPitch) / 2) + arrow * chevron.arrowPitch + (chevron.pointsRight ? reach : 2 - reach) + (chevron.held ? 1 : 0)
            y: chevron.cellTop + chevron.arrowRow + row + (chevron.held ? 1 : 0)
            width: 2
            height: 1
            color: chevron.hovered || chevron.held ? "#FFFFFF" : chevron.glyphColor
        }
    }
}
