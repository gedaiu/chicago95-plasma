"""The log-on theme (sddm/Chicago95Plasma) outside SDDM: stand-ins for what SDDM gives a theme (config,
sddm, userModel, sessionModel, keyboard and the SddmComponents module), so the Control Panel can preview
the dialog and the tests can compare it with the original screenshots."""

import shutil
from pathlib import Path

from PySide6.QtCore import Property, QObject, Qt, Signal, Slot
from PySide6.QtGui import QStandardItem, QStandardItemModel

NAME_ROLE = Qt.UserRole + 1
LOGGED_IN_ROLE = NAME_ROLE + 3
UI_FONT = Path.home() / ".local/share/fonts/MSW98UI-Regular.otf"


class Greeter(QObject):
    """sddm: the host name, what the machine can do, login() and the power actions, the loginFailed signal."""

    loginFailed = Signal()
    loginAttempted = Signal(str, int)
    powerRequested = Signal(str)

    def __init__(self, host_name, can_sleep):
        super().__init__()
        self._host_name, self._can_sleep = host_name, can_sleep

    @Property(str, constant=True)
    def hostName(self):
        return self._host_name

    @Property(bool, constant=True)
    def canSuspend(self):
        return self._can_sleep

    @Property(bool, constant=True)
    def canHibernate(self):
        return self._can_sleep

    @Slot()
    def suspend(self):
        self.powerRequested.emit("Suspend")

    @Slot()
    def hibernate(self):
        self.powerRequested.emit("Hibernate")

    @Slot(str, str, int)
    def login(self, _user, _password, _session):
        self.loginAttempted.emit(_user, _session)

    @Slot()
    def powerOff(self):
        self.powerRequested.emit("Power off")

    @Slot()
    def reboot(self):
        self.powerRequested.emit("Restart")


class Users(QStandardItemModel):
    """userModel: the users (role "name") and the last one who logged in."""

    def __init__(self, names, last_user):
        super().__init__()
        self._last_user = last_user
        self.setItemRoleNames(
            {NAME_ROLE: b"name", NAME_ROLE + 1: b"realName", NAME_ROLE + 2: b"icon", LOGGED_IN_ROLE: b"loggedIn"}
        )
        for entry in names:
            values = entry if isinstance(entry, dict) else {"name": entry}
            item = QStandardItem()
            item.setData(values["name"], NAME_ROLE)
            item.setData(values.get("realName", values["name"]), NAME_ROLE + 1)
            item.setData(values.get("icon", ""), NAME_ROLE + 2)
            item.setData(bool(values.get("loggedIn", False)), LOGGED_IN_ROLE)
            self.appendRow(item)

    @Property(str, constant=True)
    def lastUser(self):
        return self._last_user


class Layout(QObject):
    def __init__(self, short_name, long_name):
        super().__init__()
        self._short_name, self._long_name = short_name, long_name

    @Property(str, constant=True)
    def shortName(self):
        return self._short_name

    @Property(str, constant=True)
    def longName(self):
        return self._long_name


class Keyboard(QObject):
    """keyboard: the layouts to pick from and the current one, Num Lock and Caps Lock."""

    currentLayoutChanged = Signal()
    lockChanged = Signal()

    def __init__(self, layouts, caps_lock):
        super().__init__()
        self._layouts = [Layout(short, long) for short, long in layouts]
        self._current = 0
        self._num_lock, self._caps_lock = False, caps_lock

    def get_num_lock(self):
        return self._num_lock

    def set_num_lock(self, on):
        self._num_lock = on
        self.lockChanged.emit()

    numLock = Property(bool, get_num_lock, set_num_lock, notify=lockChanged)

    @Property(bool, notify=lockChanged)
    def capsLock(self):
        return self._caps_lock

    @Property("QVariantList", constant=True)
    def layouts(self):
        return self._layouts

    def get_current(self):
        return self._current

    def set_current(self, index):
        self._current = index
        self.currentLayoutChanged.emit()

    currentLayout = Property(int, get_current, set_current, notify=currentLayoutChanged)


class Sessions(QStandardItemModel):
    def __init__(self, names):
        super().__init__()
        self.setItemRoleNames({NAME_ROLE: b"name"})
        for name in names:
            item = QStandardItem()
            item.setData(name, NAME_ROLE)
            self.appendRow(item)

    @Property(int, constant=True)
    def lastIndex(self):
        return 0


def theme_settings(theme_source, **overrides):
    """theme.conf's [General] values, with overrides."""
    settings = {}
    for line in (Path(theme_source) / "theme.conf").read_text().splitlines():
        if "=" in line and not line.startswith("#") and not line.startswith("["):
            key, value = line.split("=", 1)
            settings[key] = value
    return {**settings, **overrides}


def prepare_login_theme(theme_source, folder, banner=None, icon=None):
    """A copy of the theme in folder/theme, as Setup installs it: with the UI font when installed, the 2000
    banner and the dialog's picture when given, and the SddmComponents stand-in under folder/imports.
    Returns the main.qml to load."""
    folder = Path(folder)
    shutil.copytree(theme_source, folder / "theme", dirs_exist_ok=True)
    if UI_FONT.exists():
        shutil.copy(UI_FONT, folder / "theme")
    if banner:
        shutil.copy(banner, folder / "theme/brand-banner.png")
    if icon:
        shutil.copy(icon, folder / "theme" / f"login-icon{Path(icon).suffix}")
    stub = folder / "imports/SddmComponents"
    stub.mkdir(parents=True, exist_ok=True)
    (stub / "qmldir").write_text("module SddmComponents\nTextConstants 2.0 TextConstants.qml\n")
    (stub / "TextConstants.qml").write_text("import QtQuick 2.15\nQtObject {}\n")
    return folder / "theme/main.qml"


def login_context(
    theme_source,
    host_name="WINDOWS",
    user="user",
    users=("user",),
    layouts=(("us", "English (US)"),),
    caps_lock=False,
    can_sleep=True,
    sessions=("Plasma (Wayland)",),
    **settings,
):
    """The context objects SDDM gives the theme, as {name: object}; the caller keeps them alive."""
    return {
        "config": theme_settings(theme_source, **{"previewMode": True, **settings}),
        "sddm": Greeter(host_name, can_sleep),
        "userModel": Users(users, user),
        "sessionModel": Sessions(sessions),
        "keyboard": Keyboard(layouts, caps_lock),
    }
