import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore

// The separator around the quick launch icons, drawn by Separator.qml.
PlasmoidItem {
    id: root

    preferredRepresentation: fullRepresentation
    Plasmoid.backgroundHints: PlasmaCore.Types.NoBackground

    Layout.minimumWidth: separator.implicitWidth
    Layout.preferredWidth: separator.implicitWidth
    Layout.maximumWidth: separator.implicitWidth
    Layout.fillHeight: true

    Separator {
        id: separator
        anchors.fill: parent
    }
}
