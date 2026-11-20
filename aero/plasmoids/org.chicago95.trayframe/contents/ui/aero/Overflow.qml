import QtQuick
import QtQuick.Controls.Basic as Controls
import QtQuick.Layouts
import QtQuick.Window

Item {
    id: overflow
    property var tray
    readonly property var grid: tray?.hiddenLayout
    readonly property var popup: grid?.Window.window?.mainItem
    readonly property bool showingIcons: !!popup && !tray?.systemTrayState?.activeApplet
    readonly property int columns: Math.min(4, Math.max(2, grid?.count ?? 0))
    readonly property int rows: Math.max(1, Math.ceil((grid?.count ?? 0) / columns))

    // The hidden view owns the real status notifier and applet delegates. Keep their mouse,
    // keyboard and accessibility actions while the icon grid is displayed.
    readonly property int popupWidth: Math.max(104, 12 + columns * 32)
    readonly property int popupHeight: 48 + Math.min(8, rows) * 32
    readonly property var window: grid?.Window.window
    readonly property var column: popup?.children.find(child => child.toString().startsWith("QQuickColumnLayout"))
    readonly property var heading: column?.children.find(child => child.toString().startsWith("QQuickRowLayout"))
    Binding { target: overflow.popup?.Layout ?? null; property: "minimumWidth"; value: overflow.popupWidth; when: overflow.showingIcons }
    Binding { target: overflow.popup?.Layout ?? null; property: "minimumHeight"; value: overflow.popupHeight; when: overflow.showingIcons }
    Binding { target: overflow.popup?.Layout ?? null; property: "maximumWidth"; value: overflow.popupWidth; when: overflow.showingIcons }
    Binding { target: overflow.popup?.Layout ?? null; property: "maximumHeight"; value: overflow.popupHeight; when: overflow.showingIcons }
    Binding { target: overflow.window ?? null; property: "width"; value: overflow.popupWidth + 8; when: overflow.showingIcons }
    Binding { target: overflow.window ?? null; property: "height"; value: overflow.popupHeight + 8; when: overflow.showingIcons }
    Binding { target: overflow.heading ?? null; property: "visible"; value: false; when: !!overflow.heading && overflow.showingIcons }
    Binding { target: overflow.column ?? null; property: "anchors.bottomMargin"; value: 26; when: !!overflow.column && overflow.showingIcons }

    Controls.Button {
        parent: overflow.popup ?? overflow
        visible: overflow.showingIcons
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        height: 26
        text: qsTr("Customize…")
        flat: true
        palette.buttonText: "#185389"
        onClicked: overflow.tray.plasmoid.internalAction("configure")?.trigger()
    }
    Binding { target: overflow.grid ?? null; property: "cellWidth"; value: 32; when: overflow.showingIcons }
    Binding { target: overflow.grid ?? null; property: "cellHeight"; value: 32; when: overflow.showingIcons }

    function fitDelegates() {
        if (!showingIcons || !grid?.Window.window?.visible) return;
        for (const loader of grid.contentItem.children) {
            const icon = loader.item?.iconContainer;
            if (!icon) continue;
            icon.implicitWidth = 16;
            icon.implicitHeight = 16;
            for (const child of icon.parent.children) {
                if (child !== icon && child.elide !== undefined) child.visible = false;
            }
        }
    }
}
