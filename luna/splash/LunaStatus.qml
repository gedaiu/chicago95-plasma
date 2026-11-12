import QtQuick 2.15
import "../sddm"

// The shared logoff/shutdown screen shown in the reference video at 0:37 and 0:42.
LunaLogin {
    property string statusText: "Windows is shutting down..."
    property var branding: ({})
    shuttingDown: true
    shutdownStatus: statusText
    theme: branding
}
