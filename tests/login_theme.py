"""Renders the login theme (sddm/Chicago95Plasma) without SDDM, with lib/login_preview's stand-ins for the
objects SDDM gives a theme, so tests can compare the dialog with the original screenshots."""

from pathlib import Path

from conftest import REPO
from login_preview import login_context, prepare_login_theme
from PySide6.QtCore import QTimer, QUrl
from PySide6.QtQuick import QQuickView

THEME = REPO / "sddm/Chicago95Plasma"


def render_login(
    app,
    folder,
    size=(640, 480),
    user="user",
    host_name="WINDOWS",
    banner=None,
    show_options=False,
    layouts=(("us", "English (US)"),),
    users=("user",),
    caps_lock=False,
    can_sleep=True,
    **settings,
):
    """The login screen as a PIL image; folder receives a copy of the theme (with the UI font, when
    installed, and the banner picture, when given, as Setup puts them there) and the stand-in module."""
    from reference import qimage_to_pil

    folder = Path(folder)
    main_qml = prepare_login_theme(THEME, folder, banner=banner)
    context_objects = login_context(
        THEME,
        host_name=host_name,
        user=user,
        users=users,
        layouts=layouts,
        caps_lock=caps_lock,
        can_sleep=can_sleep,
        **settings,
    )
    view = QQuickView()
    view.engine().addImportPath(str(folder / "imports"))
    for name, value in context_objects.items():
        view.rootContext().setContextProperty(name, value)
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    view.resize(*size)
    view.setSource(QUrl.fromLocalFile(str(main_qml)))
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
