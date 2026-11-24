import QtQuick
import org.kde.kwin.decoration

MouseArea {
    id: input
    required property int buttonType
    readonly property bool maximize: buttonType === DecorationOptions.DecorationButtonMaximizeRestore
    readonly property bool minimize: buttonType === DecorationOptions.DecorationButtonMinimize
    readonly property bool close: buttonType === DecorationOptions.DecorationButtonClose
    enabled: maximize ? decoration.client.maximizeable
        : minimize ? decoration.client.minimizeable : close && decoration.client.closeable
    acceptedButtons: maximize ? Qt.LeftButton | Qt.MiddleButton | Qt.RightButton : Qt.LeftButton
    hoverEnabled: true

    onReleased: function (mouse) {
        // Aurorae can forward hover movement without the pressed button state.
        // The release itself carries the position used to decide whether to act.
        if (!enabled || mouse.x < 0 || mouse.y < 0 || mouse.x >= width || mouse.y >= height)
            return;
        if (maximize)
            decoration.requestToggleMaximization(mouse.button);
        else if (minimize)
            decoration.requestMinimize();
        else if (close)
            decoration.requestClose();
    }
}
