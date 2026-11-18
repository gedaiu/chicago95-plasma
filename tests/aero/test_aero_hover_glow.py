"""The superbar's hover light (aero/HoverGlow.qml): Windows 7 lights a hovered button in its icon's colour.

win7peek.png's hovered Explorer button is washed in the folder's yellow: about 85% at its foot under the pointer,
about half at its sides."""

import pytest
from conftest import REPO
from PIL import Image
from PySide6.QtGui import QColor, QImage

GLOW = REPO / "aero/plasmoids/org.chicago95.tasks/contents/ui/aero/HoverGlow.qml"


def glow(qt_app, tint, pointer_x):
    """The glow alone on a transparent window, with its alpha."""
    from PySide6.QtCore import QEventLoop, QTimer, QUrl
    from PySide6.QtQuick import QQuickView

    view = QQuickView()
    view.setColor(QColor(0, 0, 0, 0))
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    view.resize(60, 40)
    view.setSource(QUrl.fromLocalFile(str(GLOW)))
    assert not view.errors()
    view.rootObject().setProperty("tint", QColor(tint))
    view.rootObject().setProperty("pointerX", pointer_x)
    view.show()
    loop = QEventLoop()
    QTimer.singleShot(200, loop.quit)
    loop.exec()
    image = view.grabWindow().convertToFormat(QImage.Format_RGBA8888)
    view.close()
    return Image.frombytes(
        "RGBA", (image.width(), image.height()), bytes(image.constBits()), "raw", "RGBA", image.bytesPerLine()
    )


def test_hover_glow_under_the_pointer_at_the_foot_is_the_icon_colour_lightened_at_eighty_five_percent(qt_app):
    # An olive icon colour lights the button pale yellow, as the folder's does win7peek.png's: (249, 243, 223).
    red, green, blue, alpha = glow(qt_app, "#9A9040", 30).getpixel((30, 39))

    assert (red >= 250, red > green > blue, blue >= 150, abs(alpha - 217) <= 15) == (True, True, True, True)


@pytest.mark.parametrize("side", [1, 58])
def test_hover_glow_at_the_sides_is_about_half(qt_app, side):
    alpha = glow(qt_app, "#F0D970", 30).getpixel((side, 20))[3]

    assert 90 <= alpha <= 150


def test_hover_glow_follows_the_pointer(qt_app):
    image = glow(qt_app, "#3070F0", 10)

    assert image.getpixel((10, 39))[3] > image.getpixel((50, 39))[3]
