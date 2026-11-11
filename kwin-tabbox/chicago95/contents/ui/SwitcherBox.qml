import QtQuick
import org.kde.kirigami as Kirigami
import org.kde.kwin as KWin

// The switcher's box as the 1995 original's (tests/references/win95alttab.png, tests/test_switcher.py): a raised
// 2px frame around a 379px-wide face; 48px cells for the windows' 32px icons, seven to a row and a single row
// centred, the chosen one in a 1px navy frame; under them a 27px sunken field, 16px in from the sides, with the
// chosen window's title in bold. With a preview size, each cell holds a live preview of the window, 4:3, in a
// 1px sunken frame with the icon over its lower right corner, as many to a row as nine tenths of the screen take.
Item {
    id: box

    property var model
    property int currentIndex: 0
    property int previewSize: 0
    property string look: "1995"
    property color face: "#C0C0C0"
    property int widest: 1200   // the box never grows wider than this (the screen's nine tenths)

    signal activated(int index)

    readonly property int frame: 2
    readonly property int sidePad: 19
    readonly property int topPad: 18
    readonly property int iconSize: 32
    readonly property int iconCell: 48
    readonly property int perRow: 7
    readonly property int classicWidth: 379
    readonly property int captionGap: 10
    readonly property int captionHeight: 27
    readonly property int captionInset: 16
    readonly property int bottomPad: 9
    readonly property int previewHeight: Math.round(previewSize * 3 / 4)
    readonly property bool previews: previewSize > 0
    readonly property int cellWidth: previews ? previewSize + 10 : iconCell
    readonly property int cellHeight: previews ? previewHeight + 10 : iconCell
    readonly property int count: model ? (model.rowCount ? model.rowCount() : model.count) : 0
    readonly property int columns: Math.max(1, Math.min(count, previews ? Math.floor((widest - 2 * (frame + sidePad)) / cellWidth) : perRow))
    readonly property int rows: Math.max(1, Math.ceil(count / columns))
    readonly property int rowWidth: columns * cellWidth

    // The bevel as the look draws it: 1995 and 1998 light a shade above the face with a black dark line,
    // 2000 the face itself with #404040 (lib/chicago95ui.py bevel_colors).
    readonly property color light: look === "2000" ? face : Qt.lighter(face, 1.16)
    readonly property color shadow: "#808080"
    readonly property color dark: look === "2000" ? "#404040" : "#000000"
    readonly property color navy: "#000080"

    width: previews ? 2 * (frame + sidePad) + rowWidth : classicWidth
    height: frame + topPad + rows * cellHeight + captionGap + captionHeight + bottomPad + frame

    Rectangle {
        anchors.fill: parent
        color: box.face
    }
    // Raised frame: light and white along the top and left, dark and shadow along the bottom and right.
    Rectangle { x: 0; y: 0; width: parent.width - 1; height: 1; color: box.light }
    Rectangle { x: 0; y: 0; width: 1; height: parent.height - 1; color: box.light }
    Rectangle { x: 1; y: 1; width: parent.width - 3; height: 1; color: "#FFFFFF" }
    Rectangle { x: 1; y: 1; width: 1; height: parent.height - 3; color: "#FFFFFF" }
    Rectangle { x: 0; y: parent.height - 1; width: parent.width; height: 1; color: box.dark }
    Rectangle { x: parent.width - 1; y: 0; width: 1; height: parent.height; color: box.dark }
    Rectangle { x: 1; y: parent.height - 2; width: parent.width - 2; height: 1; color: box.shadow }
    Rectangle { x: parent.width - 2; y: 1; width: 1; height: parent.height - 2; color: box.shadow }

    GridView {
        id: grid
        // A single row sits centred; rows that wrap start at the left pad, as the originals' did.
        x: box.rows === 1 ? Math.floor((box.width - box.rowWidth) / 2) : box.frame + box.sidePad
        y: box.frame + box.topPad
        width: box.rowWidth
        height: box.rows * box.cellHeight
        cellWidth: box.cellWidth
        cellHeight: box.cellHeight
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
            width: box.cellWidth
            height: box.cellHeight

            // The chosen window's 1px navy frame on the cell's edge.
            Rectangle {
                anchors.fill: parent
                color: "transparent"
                border.width: 1
                border.color: box.navy
                visible: cell.chosen
            }
            Kirigami.Icon {
                visible: !box.previews
                x: (box.iconCell - box.iconSize) / 2
                y: (box.iconCell - box.iconSize) / 2
                width: box.iconSize
                height: box.iconSize
                source: cell.model.icon
                roundToIconSize: false
            }
            Item {
                visible: box.previews
                x: 5
                y: 5
                width: box.previewSize
                height: box.previewHeight
                // Sunken 1px frame: shadow above and left, white below and right.
                Rectangle { x: 0; y: 0; width: parent.width; height: 1; color: box.shadow }
                Rectangle { x: 0; y: 0; width: 1; height: parent.height; color: box.shadow }
                Rectangle { x: 0; y: parent.height - 1; width: parent.width; height: 1; color: "#FFFFFF" }
                Rectangle { x: parent.width - 1; y: 0; width: 1; height: parent.height; color: "#FFFFFF" }
                KWin.WindowThumbnail {
                    anchors.fill: parent
                    anchors.margins: 1
                    wId: cell.model.windowId
                }
                Kirigami.Icon {
                    x: parent.width - 16 - 3
                    y: parent.height - 16 - 3
                    width: 16
                    height: 16
                    source: cell.model.icon
                    roundToIconSize: false
                }
            }
            MouseArea {
                anchors.fill: parent
                onClicked: box.activated(cell.index)
            }
        }
    }

    // The chosen window's title, bold, in a sunken field on the face under the grid.
    Item {
        id: caption
        x: box.captionInset
        y: grid.y + grid.height + box.captionGap
        width: box.width - 2 * box.captionInset
        height: box.captionHeight
        Rectangle { x: 0; y: 0; width: parent.width; height: 1; color: box.shadow }
        Rectangle { x: 0; y: 0; width: 1; height: parent.height; color: box.shadow }
        Rectangle { x: 1; y: 1; width: parent.width - 2; height: 1; color: box.dark }
        Rectangle { x: 1; y: 1; width: 1; height: parent.height - 2; color: box.dark }
        Rectangle { x: 0; y: parent.height - 1; width: parent.width; height: 1; color: "#FFFFFF" }
        Rectangle { x: parent.width - 1; y: 0; width: 1; height: parent.height; color: "#FFFFFF" }
        Rectangle { x: 1; y: parent.height - 2; width: parent.width - 2; height: 1; color: box.light }
        Rectangle { x: parent.width - 2; y: 1; width: 1; height: parent.height - 2; color: box.light }
        Text {
            x: 4
            y: 9
            width: parent.width - 8
            text: grid.currentItem ? grid.currentItem.model.caption : ""
            font.family: "MS W98 UI"
            font.pixelSize: 11
            font.bold: true
            color: "#000000"
            elide: Text.ElideRight
            renderType: Text.NativeRendering
            antialiasing: false
        }
    }
}
