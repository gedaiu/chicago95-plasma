import importlib.util
import os
import subprocess
import time
from pathlib import Path

import chicago95ui
import pytest
from conftest import REPO
from PySide6.QtCore import QEvent, QPoint, QPointF, QRect, Qt
from PySide6.QtGui import QColor, QFont, QImage, QMouseEvent, QPainter, QPixmap
from PySide6.QtNetwork import QLocalSocket
from PySide6.QtWidgets import (
    QApplication,
    QCommonStyle,
    QSlider,
    QStyle,
    QStyleOptionComboBox,
    QStyleOptionSlider,
    QStyleOptionSpinBox,
    QTabBar,
)

EVENT_DEADLINE_SECONDS = 2


def fresh_ui_module():
    spec = importlib.util.spec_from_file_location("chicago95ui_fresh", REPO / "lib/chicago95ui.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def process_events_until(condition):
    deadline = time.monotonic() + EVENT_DEADLINE_SECONDS
    while not condition() and time.monotonic() < deadline:
        QApplication.processEvents()
    return condition()


def canvas(width=40, height=40):
    image = QImage(width, height, QImage.Format_ARGB32)
    image.fill(QColor("#C0C0C0"))
    return image


def click_event(kind, point, buttons=Qt.LeftButton):
    position = QPointF(point)
    return QMouseEvent(kind, position, position, Qt.LeftButton, buttons, Qt.NoModifier)


def test_compositor_is_unreachable_when_nobody_listens_on_the_wayland_socket(short_runtime_dir, monkeypatch):
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-gone")
    (Path(short_runtime_dir) / "wayland-gone").touch()

    assert chicago95ui.compositor_reachable() is False


def test_compositor_is_reachable_when_the_wayland_socket_is_listening(listening_compositor):
    assert chicago95ui.compositor_reachable() is True


def test_compositor_is_reachable_through_an_absolute_wayland_socket_path(listening_compositor, short_runtime_dir, monkeypatch):
    monkeypatch.setenv("WAYLAND_DISPLAY", os.path.join(short_runtime_dir, "wayland-test"))
    monkeypatch.setenv("XDG_RUNTIME_DIR", "/nonexistent")

    assert chicago95ui.compositor_reachable() is True


def test_compositor_is_unreachable_when_the_x_display_has_no_socket(monkeypatch):
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.setenv("DISPLAY", ":9999")

    assert chicago95ui.compositor_reachable() is False


def test_detect_scale_is_1_when_kscreen_doctor_times_out(monkeypatch, listening_compositor):
    fresh = fresh_ui_module()

    def hang(*_arguments, **_options):
        raise subprocess.TimeoutExpired("kscreen-doctor", 3)

    monkeypatch.setattr(fresh.subprocess, "run", hang)

    assert fresh.detect_scale() == "1"


def test_detect_scale_is_1_when_kscreen_doctor_is_missing_from_path(monkeypatch, tmp_path, listening_compositor):
    fresh = fresh_ui_module()
    monkeypatch.setenv("PATH", str(tmp_path))

    assert fresh.detect_scale() == "1"


def test_detect_scale_reads_the_scale_from_kscreen_doctor_output(monkeypatch, tmp_path, listening_compositor):
    fresh = fresh_ui_module()
    tool = tmp_path / "kscreen-doctor"
    tool.write_text("#!/bin/sh\nprintf '\\033[32mScale: 1.5\\033[0m\\n'\n")
    tool.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tmp_path}:/usr/bin:/bin")

    assert fresh.detect_scale() == "1.5"


def test_scale_factor_is_left_alone_when_platform_is_not_offscreen(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "minimal")
    monkeypatch.setenv("QT_SCALE_FACTOR", "7")

    fresh_ui_module()

    assert os.environ["QT_SCALE_FACTOR"] == "7"


def test_single_instance_ignores_a_connection_that_sends_nothing(qt_app, short_runtime_dir):
    messages = []
    instance = chicago95ui.SingleInstance("silent", messages.append)
    arrivals = []
    instance.server.newConnection.connect(lambda: arrivals.append(1))
    client = QLocalSocket()
    client.connectToServer(chicago95ui.instance_socket("silent"))
    connected = client.waitForConnected(500)
    handled = process_events_until(lambda: bool(arrivals))
    client.disconnectFromServer()
    instance.server.close()

    assert (connected, handled, messages) == (True, True, [])


def test_ui_font_is_left_to_the_application_when_its_family_is_not_installed(qt_app, monkeypatch):
    monkeypatch.setattr(chicago95ui, "UI_FONT_FAMILY", "No Such Family Anywhere")

    font = chicago95ui.ui_font(11)

    assert (font.family(), font.styleStrategy()) == ("Noto Sans", QFont.PreferDefault)


def test_task_button_without_an_icon_paints_a_caption_only(qt_app):
    image = canvas(80, 24)
    painter = QPainter(image)
    chicago95ui.paint_task_button(painter, QRect(0, 0, 80, 24), "Caption", None, False, "98")
    painter.end()

    assert image != canvas(80, 24)


def test_slider_handle_pointing_at_its_start_only_has_two_cells_for_a_tall_thin_slot():
    cells = chicago95ui.slider_handle_inside(6, 8, False, True, False)

    assert cells == [(3, 3), (3, 4)]


def test_slider_handle_pointing_at_its_end_only_has_two_cells_for_a_tall_thin_slot():
    cells = chicago95ui.slider_handle_inside(6, 8, False, False, True)

    assert cells == [(2, 3), (2, 4)]


def test_disabled_slider_paints_its_handle_dithered(qt_app):
    slider = QSlider(Qt.Horizontal)
    slider.setStyle(chicago95ui.classic_style())
    slider.setEnabled(False)
    slider.resize(120, 30)
    enabled_slider = QSlider(Qt.Horizontal)
    enabled_slider.setStyle(chicago95ui.classic_style())
    enabled_slider.resize(120, 30)

    assert slider.grab().toImage() != enabled_slider.grab().toImage()


def test_drop_down_light_edges_skip_the_button_edges_when_sunken(qt_app):
    option = QStyleOptionComboBox()
    option.rect = QRect(0, 0, 40, 20)
    sunken_image, raised_image = canvas(), canvas()
    for image, state in ((sunken_image, QStyle.State_Sunken), (raised_image, QStyle.State_None)):
        option.state = QStyle.State_Enabled | state
        painter = QPainter(image)
        chicago95ui.classic_style().paint_drop_down_light_edges(option, painter, QRect(24, 2, 16, 16))
        painter.end()

    assert sunken_image != raised_image


def test_spin_box_sub_control_outside_its_four_parts_is_left_to_the_base_style(qt_app):
    option = QStyleOptionSpinBox()
    option.rect = QRect(0, 0, 60, 22)

    rect = chicago95ui.classic_style().subControlRect(QStyle.CC_SpinBox, option, QStyle.SC_None)

    assert rect == QRect()


def test_horizontal_slider_groove_is_a_four_pixel_strip_at_the_groove_top(qt_app):
    option = QStyleOptionSlider()
    option.orientation = Qt.Horizontal
    option.rect = QRect(5, 10, 100, 30)

    rect = chicago95ui.classic_style().subControlRect(QStyle.CC_Slider, option, QStyle.SC_SliderGroove)

    assert rect == QRect(5, 10 + chicago95ui.SLIDER_GROOVE_TOP, 100, 4)


@pytest.fixture
def dialog(qt_app, tmp_path, monkeypatch):
    monkeypatch.setattr(chicago95ui, "DECORATION", str(tmp_path))
    classic_dialog = chicago95ui.ClassicDialog("Title", "98", (200, 80), help_button=True)
    yield classic_dialog
    classic_dialog.hide()
    classic_dialog.deleteLater()


def test_dialog_paints_without_button_artwork_when_the_decoration_is_not_installed(dialog):
    assert dialog.grab().toImage().size() == dialog.size()


def test_dialog_pressing_the_close_button_holds_it(dialog):
    dialog.mousePressEvent(click_event(QEvent.MouseButtonPress, dialog.close_rect().center()))

    assert dialog.held is True


def test_dialog_pressing_the_title_away_from_the_buttons_leaves_the_close_button_up(dialog):
    title_point = QPoint(dialog.title_rect().left() + 4, dialog.title_rect().center().y())
    dialog.show()
    dialog.mousePressEvent(click_event(QEvent.MouseButtonPress, title_point))

    assert dialog.held is False


def test_dialog_pressing_the_title_before_it_is_shown_does_nothing(dialog):
    title_point = QPoint(dialog.title_rect().left() + 4, dialog.title_rect().center().y())
    dialog.mousePressEvent(click_event(QEvent.MouseButtonPress, title_point))

    assert dialog.held is False


def test_dialog_moving_off_the_held_close_button_lifts_it(dialog):
    dialog.held = True
    dialog.mouseMoveEvent(click_event(QEvent.MouseMove, QPoint(2, dialog.height() - 2)))

    assert dialog.held is False


def test_dialog_moving_back_onto_the_close_button_holds_it_again(dialog):
    dialog.mouseMoveEvent(click_event(QEvent.MouseMove, dialog.close_rect().center()))

    assert dialog.held is True


def test_dialog_moving_with_no_button_down_keeps_the_close_button_up(dialog):
    dialog.mouseMoveEvent(click_event(QEvent.MouseMove, dialog.close_rect().center(), Qt.NoButton))

    assert dialog.held is False


def test_dialog_releasing_over_the_held_close_button_rejects_it(dialog):
    results = []
    dialog.rejected.connect(lambda: results.append("rejected"))
    dialog.held = True
    dialog.mouseReleaseEvent(click_event(QEvent.MouseButtonRelease, dialog.close_rect().center(), Qt.NoButton))

    assert (dialog.held, results) == (False, ["rejected"])


def test_dialog_releasing_away_from_the_held_close_button_does_not_reject(dialog):
    results = []
    dialog.rejected.connect(lambda: results.append("rejected"))
    dialog.held = True
    dialog.mouseReleaseEvent(click_event(QEvent.MouseButtonRelease, QPoint(2, dialog.height() - 2), Qt.NoButton))

    assert (dialog.held, results) == (False, [])


def test_dialog_releasing_without_a_held_close_button_does_nothing(dialog):
    results = []
    dialog.rejected.connect(lambda: results.append("rejected"))
    dialog.mouseReleaseEvent(click_event(QEvent.MouseButtonRelease, dialog.close_rect().center(), Qt.NoButton))

    assert (dialog.held, results) == (False, [])


def test_disabled_vertical_slider_paints_its_handle_dithered(qt_app):
    sliders = []
    for enabled in (False, True):
        slider = QSlider(Qt.Vertical)
        slider.setStyle(chicago95ui.classic_style())
        slider.setEnabled(enabled)
        slider.resize(30, 120)
        sliders.append(slider)

    assert sliders[0].grab().toImage() != sliders[1].grab().toImage()


def test_slider_sub_control_other_than_handle_or_groove_is_left_to_the_base_style(qt_app):
    option = QStyleOptionSlider()
    option.orientation = Qt.Horizontal
    option.rect = QRect(0, 0, 100, 30)
    style = chicago95ui.classic_style()

    rect = style.subControlRect(QStyle.CC_Slider, option, QStyle.SC_SliderTickmarks)

    assert rect == QCommonStyle.subControlRect(style, QStyle.CC_Slider, option, QStyle.SC_SliderTickmarks)


def test_bevel_colors_of_the_2000_look_use_the_face_as_light(qt_app):
    colors = chicago95ui.bevel_colors("#D4D0C8", "2000")

    assert {name: color.name() for name, color in colors.items()} == {
        "light": "#d4d0c8",
        "shadow": "#808080",
        "dark": "#404040",
    }


def test_tab_bar_pixel_metrics_overlap_the_seam_and_never_shift_tabs(qt_app):
    style = chicago95ui.classic_style()

    assert [
        style.pixelMetric(metric)
        for metric in (
            QStyle.PM_TabBarBaseOverlap,
            QStyle.PM_TabBarTabOverlap,
            QStyle.PM_TabBarTabShiftHorizontal,
            QStyle.PM_TabBarTabShiftVertical,
        )
    ] == [chicago95ui.TAB_SEAM, 0, 0, 0]


def test_tab_bar_paints_every_tab_at_the_classic_height(qt_app):
    tabs = QTabBar()
    tabs.setStyle(chicago95ui.classic_style())
    for caption in ("General", "Details", "Extras"):
        tabs.addTab(caption)

    assert (tabs.sizeHint().height(), tabs.grab().toImage().isNull()) == (chicago95ui.TAB_HEIGHT, False)


def test_placeholders_are_filled_from_the_look(qt_app):
    look = {"osName": "Windows2026", "osCompany": "Acme", "edition": "Pro"}

    assert chicago95ui.fill_placeholders("{os}|{osname}|{company}|{edition}", look) == "Windows|Windows2026|Acme|Pro"


def test_banner_mark_with_an_empty_logo_paints_like_one_without(qt_app):
    plain, with_empty_logo = canvas(80, 80), canvas(80, 80)
    for image, logo in ((plain, None), (with_empty_logo, QPixmap())):
        painter = QPainter(image)
        chicago95ui.paint_banner_mark(painter, 0, 0, logo)
        painter.end()

    assert plain == with_empty_logo
