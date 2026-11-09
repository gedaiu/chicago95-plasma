import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.plasma5support as Plasma5Support

PlasmoidItem {
    id: root

    preferredRepresentation: fullRepresentation
    Plasmoid.backgroundHints: PlasmaCore.Types.NoBackground

    readonly property string menuCommand: "@HOME@/.local/bin/chicago95-startmenu"
    readonly property real aspect: startImage.sourceSize.height > 0 ? startImage.sourceSize.width / startImage.sourceSize.height : 2.5

    readonly property int bottomInset: 0
    readonly property int topInset: 2
    Layout.minimumWidth: Math.round((height - bottomInset - topInset) * aspect)
    Layout.preferredWidth: Layout.minimumWidth
    Layout.maximumWidth: Layout.minimumWidth
    Layout.fillHeight: true

    Plasma5Support.DataSource {
        id: runner
        engine: "executable"
        connectedSources: []
        onNewData: (sourceName, data) => disconnectSource(sourceName)
    }

    function toggleMenu() {
        runner.connectSource(root.menuCommand)
    }

    Connections {
        target: Plasmoid
        function onActivated() { root.toggleMenu() }
    }

    Image {
        id: startImage
        anchors.fill: parent
        anchors.bottomMargin: root.bottomInset
        anchors.topMargin: root.topInset
        source: Qt.resolvedUrl("../images/start-button.png")
        fillMode: Image.Stretch
        smooth: false
        mipmap: false
    }

    Image {
        anchors.fill: parent
        anchors.bottomMargin: root.bottomInset
        anchors.topMargin: root.topInset
        source: Qt.resolvedUrl("../images/start-button-pressed.png")
        fillMode: Image.Stretch
        smooth: false
        visible: clickArea.pressed
    }

    MouseArea {
        id: clickArea
        anchors.fill: parent
        onClicked: root.toggleMenu()
    }
}
