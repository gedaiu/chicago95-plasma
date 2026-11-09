import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore

PlasmoidItem {
    id: root

    preferredRepresentation: fullRepresentation
    Plasmoid.backgroundHints: PlasmaCore.Types.NoBackground

    readonly property int gripWidth: 7
    Layout.minimumWidth: gripWidth
    Layout.preferredWidth: gripWidth
    Layout.maximumWidth: gripWidth
    Layout.fillHeight: true

    Rectangle { x: 2; y: 1; width: 1; height: parent.height - 2; color: "#FFFFFF" }
    Rectangle { x: 3; y: 1; width: 1; height: parent.height - 2; color: "#808080" }
    Rectangle { x: 2; y: 1; width: 2; height: 1; color: "#FFFFFF" }
    Rectangle { x: 2; y: parent.height - 2; width: 2; height: 1; color: "#808080" }
}
