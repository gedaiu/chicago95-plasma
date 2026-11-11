import gc
from contextlib import contextmanager
from pathlib import Path

from conftest import REPO
from login_preview import login_context
from PySide6.QtCore import QTimer, QUrl
from PySide6.QtQuick import QQuickView
from reference import qimage_to_pil

HARNESS = Path(__file__).parent / "harness"
SDDM_THEME = REPO / "sddm/Chicago95Plasma"


@contextmanager
def garbage_collection_paused():
    gc.collect()
    gc.disable()
    try:
        yield
    finally:
        gc.enable()


def render_qml(app, harness_name, size, context_objects=None, properties=None, wait_ms=400):
    with garbage_collection_paused():
        return render_paused(app, harness_name, size, context_objects, properties, wait_ms)


def render_paused(app, harness_name, size, context_objects, properties, wait_ms):
    view = QQuickView()
    for name, value in (context_objects or {}).items():
        view.rootContext().setContextProperty(name, value)
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    view.resize(*size)
    view.setSource(QUrl.fromLocalFile(str(HARNESS / harness_name)))
    errors = [error.toString() for error in view.errors()]
    assert errors == [], errors
    for name, value in (properties or {}).items():
        view.rootObject().setProperty(name, value)
    view.show()
    QTimer.singleShot(wait_ms, app.quit)
    app.exec()
    image = qimage_to_pil(view.grabWindow())
    view.close()
    return image


def render_luna_login(app, size=(800, 600), user="Administrator", users=("Administrator",), properties=None):
    context = login_context(SDDM_THEME, user=user, users=users)
    return render_qml(app, "LunaLoginHarness.qml", size, context, properties)


def render_luna_splash(app, size=(640, 480), properties=None):
    return render_qml(app, "LunaSplashHarness.qml", size, None, properties)
