import QtQuick
import org.kde.plasma.core as PlasmaCore
import org.kde.kwin as KWin
import "settings.js" as Settings

// Alt+Tab as the originals showed it: a grey box in the middle of the screen with the windows' icons in a row
// and the chosen window's title under them (SwitcherBox.qml), or, with a preview size chosen in the Control
// Panel, live previews of the windows in the same box. KWin moves the choice; a click picks a window.
KWin.TabBoxSwitcher {
    id: tabBox

    currentIndex: (instantiator.object as SwitcherDialog)?.currentIndex ?? currentIndex

    Instantiator {
        id: instantiator
        active: tabBox.visible
        delegate: SwitcherDialog {}
    }

    component SwitcherDialog: PlasmaCore.Dialog {
        property alias currentIndex: box.currentIndex
        location: PlasmaCore.Types.Floating
        visible: tabBox.visible
        flags: Qt.ToolTip | Qt.X11BypassWindowManagerHint
        backgroundHints: PlasmaCore.Dialog.NoBackground
        x: tabBox.screenGeometry.x + Math.round((tabBox.screenGeometry.width - box.width) / 2)
        y: tabBox.screenGeometry.y + Math.round((tabBox.screenGeometry.height - box.height) / 2)

        mainItem: SwitcherBox {
            id: box
            model: tabBox.model
            currentIndex: tabBox.currentIndex
            previewSize: Settings.previewSize
            look: Settings.look
            face: Settings.face
            widest: Math.floor(tabBox.screenGeometry.width * 0.9)
            onActivated: index => tabBox.model.activate(index)
        }
    }
}
