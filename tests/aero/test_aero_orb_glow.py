"""The Start orb's glow (aero/LogoGlow.qml). In win7allprograms.png, with the Start menu open, the logo's colours
bloom out over the orb and past its panes; in win7dragedge.png, at rest, there is none."""

from conftest import REPO
from PIL import Image
from PySide6.QtGui import QColor, QImage

GLOW = REPO / "aero/plasmoids/org.chicago95.start/contents/ui/aero/LogoGlow.qml"


def red_logo(tmp_path):
    path = tmp_path / "logo.png"
    Image.new("RGBA", (20, 20), (240, 40, 20, 255)).save(path)
    return path


def glow(qt_app, logo, active):
    from PySide6.QtCore import QEventLoop, QTimer, QUrl
    from PySide6.QtQuick import QQuickView

    view = QQuickView()
    view.setColor(QColor(0, 0, 0, 0))
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    view.resize(58, 40)
    view.setSource(QUrl.fromLocalFile(str(GLOW)))
    assert not view.errors()
    view.rootObject().setProperty("source", QUrl.fromLocalFile(str(logo)).toString())
    view.rootObject().setProperty("active", active)
    view.show()
    loop = QEventLoop()
    QTimer.singleShot(400, loop.quit)
    loop.exec()
    image = view.grabWindow().convertToFormat(QImage.Format_RGBA8888)
    view.close()
    return Image.frombytes("RGBA", (58, 40), bytes(image.constBits()), "raw", "RGBA", image.bytesPerLine())


def test_orb_at_rest_has_no_glow(qt_app, tmp_path):
    assert glow(qt_app, red_logo(tmp_path), False).getextrema()[3] == (0, 0)


def test_active_orb_glows_in_the_logos_colour_beyond_the_logo(qt_app, tmp_path):
    # The logo is 20 pixels across the orb's centre (27.5, 20); 13 pixels out is past its edge, still on the orb.
    red, green, blue, alpha = glow(qt_app, red_logo(tmp_path), True).getpixel((27 + 13, 20))

    assert (alpha > 40, red > 2 * green, red > 2 * blue) == (True, True, True)


def test_dark_parts_of_the_logo_do_not_glow(qt_app, tmp_path):
    path = tmp_path / "black.png"
    Image.new("RGBA", (20, 20), (0, 0, 0, 255)).save(path)

    assert glow(qt_app, path, True).getextrema()[3][1] <= 8


def test_glow_fades_out_before_its_edges(qt_app, tmp_path):
    # The light spreads 30 pixels each way from the orb's centre: no hard square where it stops.
    image = glow(qt_app, red_logo(tmp_path), True)

    assert max(image.getpixel((x, 20))[3] for x in (0, 57)) <= 8
