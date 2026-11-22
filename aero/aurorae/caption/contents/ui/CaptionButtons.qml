import QtQuick
import org.kde.kwin.decoration
import "."

Row {
    id: row
    required property var buttons
    required property var theme
    spacing: theme.buttonSpacing * theme.buttonSizeFactor

    Repeater {
        model: row.buttons
        delegate: SystemDecorationButton {
            id: button
            required property int modelData
            buttonType: modelData
            readonly property bool closeButton: buttonType === DecorationOptions.DecorationButtonClose
            readonly property bool minimizeButton: buttonType === DecorationOptions.DecorationButtonMinimize
            width: (closeButton ? row.theme.buttonWidthClose : minimizeButton ? row.theme.buttonWidthMinimize
                                                                              : row.theme.buttonWidthMaximizeRestore)
                   * row.theme.buttonSizeFactor
            height: row.theme.buttonHeight * row.theme.buttonSizeFactor
            z: caption.highlight
            CaptionFace {
                id: caption
                anchors.fill: parent
                artwork: button.closeButton ? row.theme.closeButtonPath : button.minimizeButton ? row.theme.minimizeButtonPath
                         : decoration.client.maximized ? row.theme.restoreButtonPath : row.theme.maximizeButtonPath
                activeWindow: decoration.client.active
                hovered: button.hovered
                held: button.pressed
                closeButton: button.closeButton
            }
        }
    }
}
