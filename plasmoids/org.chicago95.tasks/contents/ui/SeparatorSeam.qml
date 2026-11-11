import QtQuick

Loader {
    id: seam
    property bool luna
    property int lead
    signal dragged(int gripX)
    signal released(int gripX)

    source: Qt.resolvedUrl(luna ? "luna/Separator.qml" : "Separator.qml")

    Binding {
        target: seam.item
        property: "lead"
        value: seam.lead
    }
    Binding {
        target: seam.item
        property: "draggable"
        value: true
    }
    Connections {
        target: seam.item
        function onDragged(gripX) {
            seam.dragged(seam.x + gripX);
        }
        function onReleased(gripX) {
            seam.released(seam.x + gripX);
        }
    }
}
