"""Renders the login theme (sddm/Chicago95Plasma) without SDDM: small stand-ins for the objects SDDM gives
a theme (config, sddm, userModel, sessionModel and the SddmComponents module), so tests can compare the
dialog with the original screenshots."""
import shutil
from pathlib import Path

from PySide6.QtCore import Property, QObject, QTimer, QUrl, Qt, Signal, Slot
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtQuick import QQuickView

from conftest import REPO

THEME = REPO / "sddm/Chicago95Plasma"
NAME_ROLE = Qt.UserRole + 1


class Greeter(QObject):
    """sddm: the host name, what the machine can do, login() and the power actions, the loginFailed signal."""
    loginFailed = Signal()

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
        pass

    @Slot()
    def hibernate(self):
        pass

    @Slot(str, str, int)
    def login(self, _user, _password, _session):
        pass

    @Slot()
    def powerOff(self):
        pass

    @Slot()
    def reboot(self):
        pass


class Users(QStandardItemModel):
    """userModel: the users (role "name") and the last one who logged in."""
    def __init__(self, names, last_user):
        super().__init__()
        self._last_user = last_user
        self.setItemRoleNames({NAME_ROLE: b"name"})
        for name in names:
            item = QStandardItem()
            item.setData(name, NAME_ROLE)
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


def theme_settings(**overrides):
    """theme.conf's [General] values, with overrides."""
    settings = {}
    for line in (THEME / "theme.conf").read_text().splitlines():
        if "=" in line and not line.startswith("#") and not line.startswith("["):
            key, value = line.split("=", 1)
            settings[key] = value
    return {**settings, **overrides}


UI_FONT = Path.home() / ".local/share/fonts/MSW98UI-Regular.otf"


def render_login(app, folder, size=(640, 480), user="user", host_name="WINDOWS", banner=None, show_options=False,
                 layouts=(("us", "English (US)"),), users=("user",), caps_lock=False, can_sleep=True, **settings):
    """The login screen as a PIL image; folder receives a copy of the theme (with the UI font, when
    installed, and the banner picture, when given, as Setup puts them there) and the stand-in module."""
    from reference import qimage_to_pil
    folder = Path(folder)
    shutil.copytree(THEME, folder / "theme", dirs_exist_ok=True)
    if UI_FONT.exists():
        shutil.copy(UI_FONT, folder / "theme")
    if banner:
        shutil.copy(banner, folder / "theme/brand-banner.png")
    stub = folder / "imports/SddmComponents"
    stub.mkdir(parents=True, exist_ok=True)
    (stub / "qmldir").write_text("module SddmComponents\nTextConstants 2.0 TextConstants.qml\n")
    (stub / "TextConstants.qml").write_text("import QtQuick 2.15\nQtObject {}\n")
    context_objects = {"config": theme_settings(**settings), "sddm": Greeter(host_name, can_sleep), "userModel": Users(users, user),
                       "sessionModel": Sessions(["Plasma (Wayland)"]), "keyboard": Keyboard(layouts, caps_lock)}
    view = QQuickView()
    view.engine().addImportPath(str(folder / "imports"))
    for name, value in context_objects.items():
        view.rootContext().setContextProperty(name, value)
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    view.resize(*size)
    view.setSource(QUrl.fromLocalFile(str(folder / "theme/main.qml")))
    errors = [error.toString() for error in view.errors()]
    if errors:
        raise AssertionError(errors)
    view.rootObject().setProperty("showOptions", show_options)
    view.show()
    QTimer.singleShot(300, app.quit)
    app.exec()
    image = qimage_to_pil(view.grabWindow())
    view.close()
    return image
