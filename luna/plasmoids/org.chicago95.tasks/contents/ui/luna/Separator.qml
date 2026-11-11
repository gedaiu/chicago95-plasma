import QtQuick
import "../quickLaunchBand.js" as Band

Item {
    id: separator
    property bool draggable: false
    signal dragged(int x)
    signal released(int x)

    property int lead: Band.metrics("luna").separatorLead
    readonly property int gripTop: 6
    readonly property int dotPitch: 3
    readonly property int dotCount: 7
    readonly property int dotSize: 2
    readonly property color dotShade: "#082EA0"
    readonly property color dotLight: "#1590E6"

    implicitWidth: Band.separatorWidth(lead, Band.metrics("luna"))
    implicitHeight: 30

    Repeater {
        model: separator.dotCount

        Item {
            required property int index
            x: separator.lead + (index % 2) * separator.dotPitch
            y: separator.gripTop + index * separator.dotPitch
            Rectangle {
                x: 1
                y: 1
                width: separator.dotSize
                height: separator.dotSize
                color: separator.dotLight
            }
            Rectangle {
                width: separator.dotSize
                height: separator.dotSize
                color: separator.dotShade
            }
        }
    }

    MouseArea {
        anchors.fill: parent
        enabled: separator.draggable
        hoverEnabled: true
        preventStealing: true
        cursorShape: Qt.SizeHorCursor
        property int grabbedAt
        function leftEdge(mouse) {
            return Math.round(mapToItem(separator.parent, mouse.x - grabbedAt, 0).x);
        }
        onPressed: mouse => grabbedAt = mouse.x
        onPositionChanged: mouse => {
            if (pressed)
                separator.dragged(leftEdge(mouse));
        }
        onReleased: mouse => separator.released(leftEdge(mouse))
    }
}
