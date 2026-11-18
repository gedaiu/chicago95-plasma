import QtQuick
import QtQuick.Window
import org.kde.ksvg as KSvg

// The Windows 7 Start orb: the Aero style's glass sphere with the logo Setup chose laid over its middle, glowing in
// the logo's colours under the pointer and while held.
Item {
    id: button
    property string text // the orb has no lettering
    property url logoSource
    property bool hovered: pointer.hovered
    property bool held
    property string look: "1995"
    property string bevel: "1995"
    property color face: "#000000"
    property color textColor: "#ffffff"

    readonly property int logoSize: 20
    implicitWidth: orb.implicitWidth

    HoverHandler {
        id: pointer
    }

    // DWM's glass streaks (widgets/reflection) lie over the whole screen, stretched to it; the bar shows its own
    // rows of them. Drawn first, under everything on the bar, from the screen's top-left corner: the panel window's
    // origin here, less where the window sits on the screen (at its foot).
    property point screenOrigin: Qt.point(0, 0)
    function measure() {
        const window = button.Window.window;
        if (!window)
            return;
        const windowOrigin = button.mapFromItem(null, 0, 0);
        button.screenOrigin = Qt.point(windowOrigin.x, windowOrigin.y - (Screen.height - window.height));
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
        imagePath: "widgets/startbutton" // the whole picture: the orb sits in it where Windows 7's does
        implicitWidth: 58
        implicitHeight: 40
        anchors.verticalCenter: parent.verticalCenter
        x: 0
        width: implicitWidth
        height: implicitHeight
    }
    LogoGlow {
        y: orb.y
        source: button.logoSource
        logoSize: button.logoSize
        active: button.hovered || button.held
    }
    Image {
        x: 27 - width / 2
        y: orb.y + 20 - height / 2
        width: button.logoSize
        height: button.logoSize
        sourceSize: Qt.size(2 * button.logoSize, 2 * button.logoSize)
        source: button.logoSource
        fillMode: Image.PreserveAspectFit
        smooth: true
    }
}
