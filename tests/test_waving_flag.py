"""The cut-out of the waving flag from the Commons logo (setup/fetch-waving-flag.py), on made-up pictures."""

import pytest
from conftest import REPO

ORANGE, BLACK, PAPER = (208, 88, 0), (0, 0, 0), (248, 248, 248)


@pytest.fixture(scope="module")
def waving_flag():
    import importlib.util

    spec = importlib.util.spec_from_file_location("fetch_waving_flag", REPO / "setup/fetch-waving-flag.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_paper_white_becomes_transparent(waving_flag):
    assert waving_flag.without_paper(*PAPER) == (0, 0, 0, 0)


def test_black_stays_opaque_black(waving_flag):
    assert waving_flag.without_paper(*BLACK) == (0, 0, 0, 255)


def test_grey_edge_becomes_half_transparent_black(waving_flag):
    assert waving_flag.without_paper(124, 124, 124) == (0, 0, 0, 128)


def test_frame_beside_the_flag_is_dropped_but_the_flag_outline_over_it_kept(waving_flag):
    x, y = waving_flag.FRAME_OVERLAP[0] + 2, 200
    assert (waving_flag.flag_pixel(x, y, *ORANGE), waving_flag.flag_pixel(x, y, *BLACK)) == (
        (0, 0, 0, 0),
        (*BLACK, 255),
    )


def test_registered_mark_is_dropped(waving_flag):
    left, top = waving_flag.REGISTERED_MARK[:2]
    assert waving_flag.flag_pixel(left, top, *BLACK) == (0, 0, 0, 0)


def test_cut_out_is_cropped_to_the_flag_and_squeezed_to_139_by_113(waving_flag, qt_app):
    from PySide6.QtGui import QColor, QImage

    logo = QImage(1778, 524, QImage.Format_ARGB32)
    logo.fill(QColor(*PAPER))
    for y in range(100, 378):
        for x in range(100, 378):
            logo.setPixelColor(x, y, QColor(*BLACK))
    flag = waving_flag.cut_flag(logo)
    assert (flag.width(), flag.height(), flag.pixelColor(0, 0).alpha()) == (278, round(278 * 113 / 139), 255)
