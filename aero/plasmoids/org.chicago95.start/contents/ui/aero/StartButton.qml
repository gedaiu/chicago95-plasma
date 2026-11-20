import QtQuick
import QtQuick.Window
import QtCore
import org.kde.ksvg as KSvg
import org.kde.plasma.workspace.dbus as DBus

// The Windows 7 Start orb: the Aero style's glass sphere with the logo Setup chose laid over its middle, glowing in
// the logo's colours under the pointer and while held.
Item {
    id: button
    property string text // the orb has no lettering
    property url logoSource
    property bool hovered: pointer.hovered
    property bool windowsLogo: false
    property bool held
    property string look: "1995"
    property string bevel: "1995"
    property color face: "#000000"
    property color textColor: "#ffffff"

    readonly property int logoSize: 22
    readonly property bool engaged: held || menu.registered
    implicitWidth: orb.implicitWidth

    DBus.DBusServiceWatcher {
        id: menu
        busType: DBus.BusType.Session
        watchedService: "org.chicago95.StartMenuOpen"
    }

    HoverHandler {
        id: pointer
    }

    // DWM's glass streaks (widgets/reflection) lie over the whole screen, stretched to it; the bar shows its own
    // rows of them. Drawn first, under everything on the bar, from the screen's top-left corner: the panel window's
    // origin here, less where the window sits on the screen (at its foot).
    property point screenOrigin: Qt.point(0, 0)
    // The tray's "show hidden icons" button (the tray frame's aeroChevron), while it shows: Windows 7's darkening at the
    // notification area starts its width further left (win7peek.png against win7screenres.png).
    property int hiddenIconsButtonWidth: 0
    function shownChevron(item, depth) {
        if (!item || !item.visible || depth > 30)
            return null;
        if (item.objectName === "aeroChevron")
            return item;
        for (let i = 0; i < item.children.length; i++) {
            const found = shownChevron(item.children[i], depth + 1);
            if (found)
                return found;
        }
        return null;
    }
    function measure() {
        const window = button.Window.window;
        if (!window)
            return;
        const windowOrigin = button.mapFromItem(null, 0, 0);
        button.screenOrigin = Qt.point(windowOrigin.x, windowOrigin.y - (Screen.height - window.height));
        const chevron = shownChevron(window.contentItem, 0);
        button.hiddenIconsButtonWidth = chevron ? chevron.width : 0;
    }
    Timer {
        interval: 500
        running: true
        repeat: true
        triggeredOnStart: true
        onTriggered: button.measure()
    }
    KSvg.SvgItem {
        imagePath: "widgets/reflection"
        x: button.screenOrigin.x
        y: button.screenOrigin.y
        width: Screen.width
        height: Screen.height
    }
    // The bar's dark line and highlight lie over the glass and its streaks, along the whole bar.
    KSvg.SvgItem {
        imagePath: "widgets/baredge"
        x: button.screenOrigin.x
        y: orb.y
        width: Screen.width
        height: implicitHeight
    }

    // Explorer darkens the bar at its notification area, from before the icons to the Show desktop strip, and
    // lightens it behind the strip (widgets/trayshade, fitted to win7screenres.png). It is the bar's own shading,
    // under the task buttons and tray icons wherever they reach, so it is drawn here, from the screen's right edge.
    KSvg.SvgItem {
        imagePath: "widgets/trayshade"
        width: implicitWidth
        height: implicitHeight
        x: button.screenOrigin.x + Screen.width - width - button.hiddenIconsButtonWidth
        y: orb.y + 2 // below the bar's top line and highlight (palette.START_SHADE_TOP)
    }
    // Windows 7 darkens the bar behind the orb, fading out under the first pinned program, past the orb's slot.
    KSvg.SvgItem {
        imagePath: "widgets/startshade"
        x: 0
        y: orb.y + 2 // below the bar's top line and highlight (palette.START_SHADE_TOP)
        width: implicitWidth
        height: implicitHeight
    }
    KSvg.SvgItem {
        id: orb
        visible: !windowsFrames.ready
        imagePath: "widgets/startbutton" // the whole picture: the orb sits in it where Windows 7's does
        implicitWidth: 58
        implicitHeight: 40
        anchors.verticalCenter: parent.verticalCenter
        x: 0
        width: implicitWidth
        height: implicitHeight
    }
    WindowsOrb {
        id: windowsFrames
        y: orb.y
        source: button.windowsLogo ? StandardPaths.locate(StandardPaths.GenericDataLocation, "chicago95/icons/windows7-orb.svg") : ""
        hovered: button.hovered
        engaged: button.engaged
    }
    LogoGlow {
        visible: !windowsFrames.ready
        y: orb.y
        source: button.logoSource
        logoSize: button.logoSize
        active: button.hovered || button.engaged
        pressed: button.engaged
    }
    Image {
        visible: !windowsFrames.ready
        x: 27 - width / 2
        y: orb.y + 20 - height / 2
        width: button.logoSize
        height: button.logoSize
        sourceSize: Qt.size(2 * button.logoSize, 2 * button.logoSize)
        source: button.logoSource
        fillMode: Image.PreserveAspectFit
        smooth: true
    }
    // The glass darkens when pushed, including while the menu owns focus.
    Rectangle {
        visible: !windowsFrames.ready
        width: 36
        height: width
        x: 27 - width / 2
        y: orb.y + 20 - height / 2
        radius: width / 2
        antialiasing: true
        opacity: button.engaged ? 1 : 0
        color: "#40102d43"
        Behavior on opacity { NumberAnimation { duration: 85 } }
    }
}
