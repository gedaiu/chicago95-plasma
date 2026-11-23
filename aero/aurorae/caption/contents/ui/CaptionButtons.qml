import QtQuick
import org.kde.kwin.decoration
import "."

Item {
    id: group
    required property var buttons
    required property var theme
    readonly property real outputScale: decoration.client.scale || 1
    implicitWidth: row.implicitWidth
    implicitHeight: row.implicitHeight

    // The halo can extend into a neighbouring button. Keep it behind every
    // face so hovering does not paint over the divider between them.
    Item {
        id: halos
        anchors.fill: parent
    }

    Row {
        id: row
        anchors.fill: parent
        spacing: group.theme.buttonSpacing * group.theme.buttonSizeFactor

        Repeater {
            model: group.buttons
            delegate: SystemDecorationButton {
                id: button
                required property int modelData
                buttonType: modelData
                readonly property bool closeButton: buttonType === DecorationOptions.DecorationButtonClose
                readonly property bool minimizeButton: buttonType === DecorationOptions.DecorationButtonMinimize
                width: (closeButton ? group.theme.buttonWidthClose : minimizeButton ? group.theme.buttonWidthMinimize
                                                                                  : group.theme.buttonWidthMaximizeRestore)
                       * group.theme.buttonSizeFactor
                height: group.theme.buttonHeight * group.theme.buttonSizeFactor
                CaptionFace {
                    // A maximized Aero frame loses the top device row of the
                    // button face at the screen edge. Keep the hit target full size.
                    y: decoration.client.maximized ? -1 / group.outputScale : 0
                    width: button.width
                    height: button.height
                    haloLayer: halos
                    haloPosition: Qt.point(button.x, button.y + y)
                    artwork: button.closeButton ? group.theme.closeButtonPath : button.minimizeButton ? group.theme.minimizeButtonPath
                             : decoration.client.maximized ? group.theme.restoreButtonPath : group.theme.maximizeButtonPath
                    activeWindow: decoration.client.active
                    hovered: button.hovered
                    held: button.pressed
                    closeButton: button.closeButton
                }
            }
        }
    }
}
