import os
import subprocess
import sys

import chicago95ui
from conftest import REPO
from PySide6.QtCore import QRect
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QFrame, QLineEdit, QStyleOptionTab


def tab_option(position, selected):
    option = QStyleOptionTab()
    option.position = position
    option.rect = QRect(10, 20, 80, 24)
    if selected:
        option.state |= chicago95ui.QStyle.State_Selected
    return option


def test_detect_scale_is_1_without_a_display(monkeypatch):
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.delenv("DISPLAY", raising=False)

    assert chicago95ui.detect_scale() == "1"


def test_detect_scale_is_1_when_kscreen_doctor_is_not_installed(monkeypatch, tmp_path, listening_compositor):
    monkeypatch.setenv("PATH", str(tmp_path))

    assert chicago95ui.detect_scale() == "1"


def test_offscreen_platform_without_scale_factor_gets_one_set_on_import():
    environment = {key: value for key, value in os.environ.items() if key != "QT_SCALE_FACTOR"}
    environment["QT_QPA_PLATFORM"] = "offscreen"
    environment.pop("DISPLAY", None)
    environment.pop("WAYLAND_DISPLAY", None)
    result = subprocess.run(
        [sys.executable, "-c", "import chicago95ui, os; print(os.environ['QT_SCALE_FACTOR'])"],
        capture_output=True,
        text=True,
        env={**environment, "PYTHONPATH": str(REPO / "lib")},
        check=False,
    )

    assert result.stdout == "1\n"


def test_slider_tick_values_use_the_page_step_when_single_steps_would_crowd():
    assert chicago95ui.slider_tick_values(0, 100, 0, 1, 25, 50) == [0, 25, 50, 75, 100]


def test_slider_tick_values_use_the_interval_when_it_is_set():
    assert chicago95ui.slider_tick_values(0, 10, 5, 1, 2, 500) == [0, 5, 10]


def test_selected_only_tab_spreads_two_pixels_over_its_neighbours(qt_app):
    option = tab_option(QStyleOptionTab.TabPosition.OnlyOneTab, selected=True)

    shape, caption = chicago95ui.tab_rects(option)

    assert (shape.getRect(), caption.getRect()) == ((10, 20, 80, 22), (12, 20, 76, 22))


def test_unselected_middle_tab_starts_two_rows_down_without_insets(qt_app):
    option = tab_option(QStyleOptionTab.TabPosition.Middle, selected=False)

    shape, caption = chicago95ui.tab_rects(option)

    assert (shape.getRect(), caption.getRect()) == ((10, 22, 80, 20), (10, 22, 80, 20))


def test_read_only_field_shows_text_on_the_window_colour(qt_app):
    field = chicago95ui.read_only_field(QLineEdit("result"))

    assert (field.isReadOnly(), field.palette().color(QPalette.Base)) == (
        True,
        field.palette().color(QPalette.Window),
    )


def test_sunken_panel_is_a_two_pixel_sunken_frame(qt_app):
    panel = chicago95ui.sunken_panel()

    assert (panel.frameStyle(), panel.lineWidth()) == (QFrame.Panel | QFrame.Sunken, 2)


def test_etched_line_is_a_sunken_horizontal_line(qt_app):
    line = chicago95ui.etched_line()

    assert (line.frameShape(), line.frameShadow()) == (QFrame.HLine, QFrame.Sunken)


def test_classic_style_is_made_again_after_the_shared_one_was_deleted(qt_app):
    import shiboken6

    styles_in_use = list(chicago95ui._CLASSIC_STYLE)
    stale_style = chicago95ui.ClassicStyle("Windows")
    chicago95ui._CLASSIC_STYLE[:] = [stale_style]
    shiboken6.delete(stale_style)

    renewed_style = chicago95ui.classic_style()
    outcome = (shiboken6.isValid(renewed_style), renewed_style is chicago95ui._CLASSIC_STYLE[0])
    chicago95ui._CLASSIC_STYLE[:] = styles_in_use

    assert outcome == (True, True)


def test_classic_style_is_shared_while_it_is_alive(qt_app):
    assert chicago95ui.classic_style() is chicago95ui.classic_style()


def test_ui_font_pixel_size_follows_the_request(qt_app):
    assert chicago95ui.ui_font(13, bold=True).pixelSize() == 13
