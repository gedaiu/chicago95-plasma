/*
 * Alt+Tab in Windows XP: a face-coloured box, 1px black outside and a 2px white line inside, 32px icons in 48px
 * cells seven to a row, the chosen window's cell a flat Luna selection blue square, and its title in
 * black Tahoma under the icons. No XP Alt+Tab screenshot is bundled (none found in lossless form), so the
 * layout follows the classic box's measured geometry (tests/test_switcher.py) in Luna colours.
 */
import QtQuick
import org.kde.kirigami as Kirigami

Item {
    id: box

    property var model
    property int currentIndex: 0

    signal activated(int index)

    readonly property color face: "#ECE9D8"
    readonly property color selection: "#316AC5"
    readonly property int frame: 3
    readonly property int sidePad: 19
    readonly property int topPad: 18
    readonly property int iconSize: 32
    readonly property int iconCell: 48
    readonly property int perRow: 7
    readonly property int minimumWidth: 379
    readonly property int captionGap: 10
    readonly property int captionHeight: 20
    readonly property int bottomPad: 9
    readonly property int count: model ? (model.rowCount ? model.rowCount() : model.count) : 0
    readonly property int columns: Math.max(1, Math.min(count, perRow))
    readonly property int rows: Math.max(1, Math.ceil(count / columns))
    readonly property int rowWidth: columns * iconCell

    width: minimumWidth
    height: frame + topPad + rows * iconCell + captionGap + captionHeight + bottomPad + frame

    Rectangle {
        anchors.fill: parent
        color: "#000000"
    }
    Rectangle {
        anchors.fill: parent
        anchors.margins: 1
        color: "#FFFFFF"
    }
    Rectangle {
        anchors.fill: parent
        anchors.margins: 3
        color: box.face
    }

    GridView {
        id: grid
        x: box.rows === 1 ? Math.floor((box.width - box.rowWidth) / 2) : box.frame + box.sidePad
        y: box.frame + box.topPad
        width: box.rowWidth
        height: box.rows * box.iconCell
        cellWidth: box.iconCell
        cellHeight: box.iconCell
        interactive: false
        model: box.model
        currentIndex: box.currentIndex
        highlightMoveDuration: 0
        highlightFollowsCurrentItem: false
        delegate: Item {
            id: cell
            required property int index
            required property var model
            readonly property bool chosen: index === grid.currentIndex
            width: box.iconCell
            height: box.iconCell

            Rectangle {
                anchors.fill: parent
                color: box.selection
                visible: cell.chosen
            }
            Kirigami.Icon {
                x: (box.iconCell - box.iconSize) / 2
                y: (box.iconCell - box.iconSize) / 2
                width: box.iconSize
                height: box.iconSize
                source: cell.model.icon
                roundToIconSize: false
            }
            MouseArea {
                anchors.fill: parent
                onClicked: box.activated(cell.index)
            }
        }
    }

    Text {
        x: box.frame + box.sidePad
        y: grid.y + grid.height + box.captionGap
        width: box.width - 2 * (box.frame + box.sidePad)
        height: box.captionHeight
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        text: grid.currentItem ? grid.currentItem.model.caption : ""
        font.family: "Tahoma"
        font.pixelSize: 11
        color: "#000000"
        elide: Text.ElideRight
    }
}
