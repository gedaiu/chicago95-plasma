"""Renders the login theme (sddm/Chicago95Plasma) without SDDM, with lib/login_preview's stand-ins for the
objects SDDM gives a theme, so tests can compare the dialog with the original screenshots."""

from contextlib import contextmanager
from pathlib import Path

from conftest import REPO
from login_preview import login_context, prepare_login_theme
from PySide6.QtCore import QTimer, QUrl
from PySide6.QtQuick import QQuickView

THEME = REPO / "sddm/Chicago95Plasma"


@contextmanager
def login_view(
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
    failed=False,
    **settings,
):
    """The login screen shown in a QQuickView, 300ms after it loaded (and after a failed log on, when failed);
    folder receives a copy of the theme (with the UI font, when installed, and the banner picture, when given,
    as Setup puts them there) and the stand-in module."""
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
    if failed:
        context_objects["sddm"].loginFailed.emit()
    QTimer.singleShot(300, app.quit)
    app.exec()
    try:
        yield view
    finally:
        view.close()


def render_login(app, folder, **options):
    """The login screen as a PIL image (login_view's options)."""
    from reference import qimage_to_pil

    with login_view(app, folder, **options) as view:
        return qimage_to_pil(view.grabWindow())


CONTROLS = ("RetroButton", "RetroField", "RetroCombo", "RetroCheck", "ArrowButton", "PopupList")
LEAVES = ("RetroLabel", "QQuickText", "QQuickImage", "QQuickCanvasItem")


def shown_items(item):
    """Every visible control, text and picture under item, as a reader sees them: a control counts as one
    (its own caption and frame are inside it), a text only when it has some."""
    found = []
    for child in item.childItems():
        if not child.isVisible() or child.width() <= 0 or child.height() <= 0:
            continue
        kind = child.metaObject().className()
        if kind.startswith(CONTROLS):
            found.append(child)
        elif kind.startswith(LEAVES):
            if not kind.startswith(("RetroLabel", "QQuickText")) or child.property("text"):
                found.append(child)
        else:
            found += shown_items(child)
    return found


def scene_rect(item):
    from PySide6.QtCore import QRectF

    return item.mapRectToScene(QRectF(0, 0, item.width(), item.height()))


def raised_popup(item):
    """The popup (a balloon, a list, a message box: an item raised above its siblings) item is in, or None."""
    while item is not None:
        if item.z() > 0:
            return item
        item = item.parentItem()
    return None


def overlapping_pairs(root):
    """The pairs of shown items whose rectangles cross, each as two descriptions. A popup covers what lies
    under it, so only the items of one popup, or of none, are compared with each other."""
    items = shown_items(root)
    pairs = []
    for index, first in enumerate(items):
        for second in items[index + 1 :]:
            if raised_popup(first) is raised_popup(second) and scene_rect(first).intersects(scene_rect(second)):
                pairs.append((describe(first), describe(second)))
    return pairs


def describe(item):
    rect = scene_rect(item)
    label = item.property("text") or item.property("label") or item.objectName() or item.metaObject().className()
    return f"{label!s:.30} at {rect.x():.0f},{rect.y():.0f} {rect.width():.0f}x{rect.height():.0f}"


def shown_texts(item):
    """The texts a reader sees under item, walking the items as they are drawn (delegates included)."""
    texts = []
    for child in item.childItems():
        if not child.isVisible():
            continue
        if child.metaObject().className().startswith("QQuickText") and child.property("text"):
            texts.append(child.property("text"))
        texts += shown_texts(child)
    return texts
