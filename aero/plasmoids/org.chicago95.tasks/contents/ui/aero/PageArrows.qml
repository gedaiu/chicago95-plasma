import QtQuick
import org.kde.ksvg as KSvg

// The superbar's paging arrows (TaskBand2Composited::ScrollBar, widgets/scrollarrow): up to the page before, down to
// the page after, one over the other at the band's end; an arrow with no page to go to is disabled.
Item {
    id: arrows
    property int page
    property int pages
    signal moved(int page)

    implicitWidth: 17

    Repeater {
        model: [
            { direction: "up", step: -1 },
            { direction: "down", step: 1 }
        ]

        KSvg.SvgItem {
            id: arrow
            required property var modelData
            required property int index
            readonly property bool enabled: arrows.page + modelData.step >= 0 && arrows.page + modelData.step < arrows.pages
            y: index * arrows.height / 2
            width: arrows.width
            height: arrows.height / 2
            imagePath: "widgets/scrollarrow"
            elementId: modelData.direction + "-" + (!enabled ? "disabled" : area.pressed ? "pressed" : area.containsMouse ? "hot" : hover.hovered ? "hover" : "normal")

            MouseArea {
                id: area
                anchors.fill: parent
                hoverEnabled: true
                enabled: arrow.enabled
                onClicked: arrows.moved(arrows.page + arrow.modelData.step)
            }
        }
    }
    HoverHandler {
        id: hover
    }
}
