import QtQuick 2.15
import "../sddm"

// What Windows XP shows after a log on from the Welcome screen, while the desktop loads: the same screen,
// with only the chosen user's tile, "Loading your personal settings..." where its password box was.
LunaLogin {
    id: welcome
    property string userName
    property url userPicture
    property var branding: ({})

    theme: branding
    selectedName: userName
    loadingStatus: "Loading your personal settings..."
    users: ListModel {
        id: oneUser
    }

    function showUser() {
        oneUser.clear();
        oneUser.append({
            name: userName,
            realName: userName,
            icon: String(userPicture)
        });
    }
    onUserNameChanged: showUser()
    onUserPictureChanged: showUser()
    Component.onCompleted: showUser()
}
