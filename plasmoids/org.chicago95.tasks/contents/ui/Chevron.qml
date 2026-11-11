import QtQuick
import "quickLaunchBand.js" as Band

// The Quick Launch's chevron, shown when its band is too narrow for every launcher: Windows 2000's "»" at
// the band's end, or the tray's "«" when the band is docked right and the chevron leads it; a flat button
// like the launchers' that opens the rest.
Item {
    id: chevron
    property bool hovered
    property bool held
    property bool pointsRight: true
    property color shadow: "#808080"
    property color white: "#ffffff"

    readonly property int cellHeight: 22
    readonly property int iconInset: Band.metrics().iconInset

    implicitWidth: Band.metrics().chevronWidth
    implicitHeight: cellHeight

    Item {
        y: chevron.height - chevron.cellHeight
        width: chevron.width
        height: chevron.cellHeight

        Image {
            x: chevron.held ? 1 : 0
            y: chevron.iconInset + (chevron.held ? 1 : 0)
            width: 16
            height: 16
            source: "@HOME@/.local/share/chicago95/icons/tray-chevron.png"
            mirror: chevron.pointsRight
            smooth: false
        }
        Item {
            anchors.fill: parent
            visible: chevron.hovered || chevron.held
            Rectangle {
                width: parent.width
                height: 1
                color: chevron.held ? chevron.shadow : chevron.white
            }
            Rectangle {
                width: 1
                height: parent.height
                color: chevron.held ? chevron.shadow : chevron.white
            }
            Rectangle {
                y: parent.height - 1
                width: parent.width
                height: 1
                color: chevron.held ? chevron.white : chevron.shadow
            }
            Rectangle {
                x: parent.width - 1
                width: 1
                height: parent.height
                color: chevron.held ? chevron.white : chevron.shadow
            }
        }
    }
}
