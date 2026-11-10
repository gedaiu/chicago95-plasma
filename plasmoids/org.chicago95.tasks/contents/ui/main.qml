import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.extras as PlasmaExtras
import org.kde.kirigami as Kirigami
import org.kde.taskmanager as TaskManager

// The taskbar between the Start button and the tray, as the originals lay it out
// (tests/test_plasma_taskbar_reference.py): with Quick Launch entries, a separator, their 23px cells
// and another separator; then one button per window in the order they opened, 3px apart, as wide as
// the look allows and narrower when many share the taskbar. The originals have no gap before this
// part, so it starts over the gap Plasma's panel leaves between applets.
// A click on a window's button activates it, or minimizes it when it is already active; the right
// button opens the classic window menu.
PlasmoidItem {
    id: root

    preferredRepresentation: fullRepresentation
    Plasmoid.backgroundHints: PlasmaCore.Types.NoBackground
    Layout.fillWidth: true
    Layout.fillHeight: true

    readonly property int contentX: -Kirigami.Units.smallSpacing   // the panel's gap between applets
    readonly property int gap: 3
    readonly property int gapWithoutQuickLaunch: 4
    readonly property int launcherCount: tasksModel.launcherCount
    readonly property int windowCount: tasksModel.count - launcherCount
    readonly property int quickLaunchX: contentX + leadingSeparator.width
    readonly property int quickLaunchEnd: quickLaunchX + launcherCount * 23
    readonly property int tasksX: launcherCount > 0 ? trailingSeparator.x + trailingSeparator.width : contentX + gapWithoutQuickLaunch
    readonly property int buttonWidth: windowCount === 0 ? 0
        : Math.min(Plasmoid.configuration.maxButtonWidth, Math.floor((width - tasksX + gap) / windowCount) - gap)

    TaskManager.VirtualDesktopInfo { id: virtualDesktopInfo }
    TaskManager.ActivityInfo { id: activityInfo }

    TaskManager.TasksModel {
        id: tasksModel
        screenGeometry: Plasmoid.containment.screenGeometry
        activity: activityInfo.currentActivity
        virtualDesktop: virtualDesktopInfo.currentDesktop
        filterByVirtualDesktop: true
        filterByActivity: true
        groupMode: TaskManager.TasksModel.GroupDisabled
        sortMode: TaskManager.TasksModel.SortManual
        separateLaunchers: true
        hideActivatedLaunchers: false
        launcherList: Plasmoid.configuration.launchers
    }

    Separator {
        id: leadingSeparator
        visible: root.launcherCount > 0
        x: root.contentX
        height: parent.height
        lead: Plasmoid.configuration.look === "2000" ? 3 : 2   // after 2000's wider Start button
    }
    Separator {
        id: trailingSeparator
        visible: root.launcherCount > 0
        x: root.quickLaunchEnd + 2
        height: parent.height
    }

    Repeater {
        model: tasksModel

        Loader {
            id: entry
            required property var model
            required property int index
            readonly property bool launcher: index < root.launcherCount
            readonly property var modelIndex: tasksModel.makeModelIndex(index)
            x: launcher ? root.quickLaunchX + index * 23 : root.tasksX + (index - root.launcherCount) * (root.buttonWidth + root.gap)
            width: launcher ? 23 : root.buttonWidth
            height: root.height
            sourceComponent: launcher ? launcherCell : windowButton

            Component {
                id: launcherCell
                QuickLaunchButton {
                    icon: entry.model.decoration
                    hovered: launcherArea.containsMouse
                    held: launcherArea.pressed && launcherArea.containsMouse
                    MouseArea {
                        id: launcherArea
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: tasksModel.requestNewInstance(entry.modelIndex)
                    }
                }
            }
            Component {
                id: windowButton
                TaskButton {
                    id: button
                    text: entry.model.display
                    icon: entry.model.decoration
                    pressed: entry.model.IsActive === true
                    look: Plasmoid.configuration.look
                    MouseArea {
                        anchors.fill: parent
                        acceptedButtons: Qt.LeftButton | Qt.RightButton
                        onClicked: mouse => {
                            if (mouse.button === Qt.RightButton) {
                                windowMenu.visualParent = button
                                windowMenu.task = entry.modelIndex
                                windowMenu.openRelative()
                            } else if (entry.model.IsActive) {
                                tasksModel.requestToggleMinimized(entry.modelIndex)
                            } else {
                                tasksModel.requestActivate(entry.modelIndex)
                            }
                        }
                    }
                }
            }
        }
    }

    PlasmaExtras.Menu {
        id: windowMenu
        property var task
        placement: PlasmaExtras.Menu.TopPosedLeftAlignedPopup

        PlasmaExtras.MenuItem {
            text: i18n("Restore")
            onClicked: tasksModel.requestActivate(windowMenu.task)
        }
        PlasmaExtras.MenuItem {
            text: i18n("Minimize")
            onClicked: tasksModel.requestToggleMinimized(windowMenu.task)
        }
        PlasmaExtras.MenuItem {
            text: i18n("Maximize")
            onClicked: tasksModel.requestToggleMaximized(windowMenu.task)
        }
        PlasmaExtras.MenuItem { separator: true }
        PlasmaExtras.MenuItem {
            text: i18n("Close")
            onClicked: tasksModel.requestClose(windowMenu.task)
        }
    }
}
