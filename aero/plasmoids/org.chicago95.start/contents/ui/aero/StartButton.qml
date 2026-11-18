import QtQuick
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
        x: 27.5 - width / 2
        y: orb.y + 20 - height / 2
        width: button.logoSize
        height: button.logoSize
        sourceSize: Qt.size(2 * button.logoSize, 2 * button.logoSize)
        source: button.logoSource
        fillMode: Image.PreserveAspectFit
        smooth: true
    }
}
