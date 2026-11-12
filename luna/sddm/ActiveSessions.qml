import QtQuick 2.15
import org.kde.plasma.workspace.dbus as DBus

// SDDM's sessionModel lists installed desktop types, not logged-on users.
// Read logind instead. Never activate/unlock sessions from this component.
Item {
    id: root
    property var users: ({})
    property bool refreshing: false

    function call(path, iface, member, args, success, failure) {
        DBus.SystemBus.asyncCall({
            service: "org.freedesktop.login1", path: path,
            iface: iface, member: member, arguments: args
        }, result => success(result.value), failure);
    }

    function value(raw) {
        // Plasma's D-Bus module preserves scalar signatures in value wrappers.
        return raw !== null && typeof raw === "object" && raw.value !== undefined ? raw.value : raw;
    }

    function isDesktopSession(info) {
        return (value(info.Type) === "wayland" || value(info.Type) === "x11")
            && (value(info.Class) === "user" || value(info.Class) === "user-early")
            && value(info.State) !== "closing" && !value(info.Remote);
    }

    function refresh() {
        if (refreshing) return;
        refreshing = true;
        call("/org/freedesktop/login1", "org.freedesktop.login1.Manager", "ListSessions", [], sessions => {
            const next = {};
            let remaining = sessions.length;
            function finished() {
                if (--remaining === 0) {
                    root.users = next;
                    root.refreshing = false;
                }
            }
            if (!remaining) {
                root.users = next;
                root.refreshing = false;
            }
            for (const session of sessions) {
                call(String(value(session[4])), "org.freedesktop.DBus.Properties", "GetAll",
                     ["org.freedesktop.login1.Session"], info => {
                    if (root.isDesktopSession(info)) next[String(value(session[2]))] = true;
                    finished();
                }, finished);
            }
        }, () => {
            root.users = {};
            root.refreshing = false;
        });
    }

    Timer {
        interval: 2000
        repeat: true
        running: root.visible
        triggeredOnStart: true
        onTriggered: root.refresh()
    }
}
