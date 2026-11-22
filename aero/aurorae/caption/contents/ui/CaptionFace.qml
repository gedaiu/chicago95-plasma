import QtQuick
import org.kde.ksvg as KSvg

Item {
    id: face
    required property string artwork
    required property bool activeWindow
    required property bool hovered
    required property bool held
    required property bool closeButton
    readonly property bool hot: enabled && hovered && !held
    readonly property string suffix: activeWindow ? "" : "-inactive"
    property real highlight: hot ? 1 : 0
    Behavior on highlight {
        id: fade
        enabled: face.enabled && !face.held
        NumberAnimation {
            duration: fade.targetValue === 1 ? (face.closeButton ? 40 : 80) : (face.closeButton ? 176 : 160)
        }
    }
    // The native halo falls to about three quarters of its previous opacity
    // per pixel outside the bottom edge. Paint the rings outside the face.
    Item {
        anchors.fill: parent
        opacity: face.highlight
        visible: opacity > 0
        Repeater {
            model: 12
            delegate: Rectangle {
                required property int index
                readonly property real pixel: face.height / 20
                anchors.fill: parent
                anchors.margins: -(index + 1) * pixel
                radius: (4 + index) * pixel
                color: "transparent"
                border.width: pixel
                border.color: face.closeButton ? "#ff805e" : "#60d2ff"
                opacity: face.closeButton ? 0.66 * Math.pow(0.71, index) : 0.8 * Math.pow(0.76, index)
            }
        }
    }
    KSvg.FrameSvgItem {
        anchors.fill: parent
        imagePath: face.artwork
        prefix: !face.enabled ? "deactivated" + face.suffix : face.held ? "pressed" + face.suffix
                : face.activeWindow ? "active" : "inactive"
        // Compensate for the translucent hot face composited over this layer.
        opacity: (1 - face.highlight) / (1 - 0.85 * face.highlight)
    }
    KSvg.FrameSvgItem {
        anchors.fill: parent
        imagePath: face.artwork
        prefix: "hover" + face.suffix
        opacity: face.highlight
    }
}
