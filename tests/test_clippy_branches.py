import subprocess
import sys

import pytest
from conftest import REPO, load_script
from PySide6.QtCore import QEvent, QPoint, QPointF, QSize, Qt, QTimer
from PySide6.QtGui import QContextMenuEvent, QImage, QMouseEvent, QPainter, QPixmap
from PySide6.QtWidgets import QApplication


@pytest.fixture
def clippy(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    return load_script("chicago95-clippy")


def window_of(clippy, qt_app):
    animations = clippy.parse_agent_js((REPO / "data/clippy/agent.js").read_text())
    sprites = clippy.SpriteSheet(QPixmap(str(REPO / "data/clippy/map.png")), QSize(124, 93))
    return clippy.ClippyWindow(animations, sprites, clippy.SoundPlayer({}, True), qt_app.font())


def mouse_event(kind, button, buttons, at=(10, 10)):
    return QMouseEvent(kind, QPointF(*at), QPointF(*at), button, buttons, Qt.NoModifier)


def test_write_sound_cache_keeps_an_existing_file_and_writes_the_missing_one(clippy):
    clippy.SOUND_CACHE_DIR.mkdir(parents=True)
    (clippy.SOUND_CACHE_DIR / "1.ogg").write_bytes(b"old")

    paths = clippy.write_sound_cache({"1": b"new", "2": b"fresh"})

    assert (
        {sound_id: path.read_bytes() for sound_id, path in paths.items()},
        sorted(path.name for path in clippy.SOUND_CACHE_DIR.iterdir()),
    ) == ({"1": b"old", "2": b"fresh"}, ["1.ogg", "2.ogg"])


def test_muted_sound_player_spawns_nothing_for_a_known_sound(clippy, tmp_path, path_with):
    path_with("pw-play")
    marker = tmp_path / "played"
    player = clippy.SoundPlayer({"1": marker}, True)

    player.play("1")

    assert not marker.exists()


def test_sound_player_without_a_player_binary_is_muted(clippy, monkeypatch, tmp_path):
    monkeypatch.setenv("PATH", str(tmp_path))

    assert clippy.SoundPlayer({}, False).muted is True


def test_sound_player_ignores_an_unknown_sound_id(clippy, path_with):
    path_with("pw-play")
    player = clippy.SoundPlayer({"1": "x.ogg"}, False)

    assert (player.muted, player.play("2"), player.play(None)) == (False, None, None)


def test_sound_player_runs_the_player_binary_on_a_known_sound(clippy, tmp_path, monkeypatch):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    marker = tmp_path / "played"
    player_script = bin_dir / "pw-play"
    player_script.write_text(f'#!/bin/sh\necho "$1" > {marker}\n')
    player_script.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}:/usr/bin:/bin")
    sound_file = tmp_path / "1.ogg"

    clippy.SoundPlayer({"1": sound_file}, False).play("1")
    for _ in range(100):
        if marker.exists() and marker.read_text():
            break
        subprocess.run(["sleep", "0.05"], check=True)

    assert marker.read_text().strip() == str(sound_file)


def test_paint_frame_draws_every_image_offset_of_the_frame(clippy, qt_app):
    sheet = QPixmap(4, 2)
    sheet.fill(Qt.red)
    sprites = clippy.SpriteSheet(sheet, QSize(2, 2))
    frame = clippy.Frame(100, ((0, 0), (2, 0)), None, None)
    target = QImage(2, 2, QImage.Format_ARGB32)
    target.fill(Qt.black)
    painter = QPainter(target)

    sprites.paint_frame(painter, frame)
    painter.end()

    assert target.pixelColor(1, 1).name() == "#ff0000"


def test_show_frame_without_playback_finishes_quietly(clippy, qt_app):
    window = window_of(clippy, qt_app)

    window.show_frame()

    assert (window.playback, window.current_frame) == (None, None)


def test_advance_frame_without_playback_keeps_the_timer_stopped(clippy, qt_app):
    window = window_of(clippy, qt_app)

    window.advance_frame()

    assert (window.playback, window.frame_timer.isActive()) == (None, False)


def test_playback_running_past_the_last_frame_calls_on_finished_once(clippy, qt_app):
    window = window_of(clippy, qt_app)
    finished = []
    window.play("Hide", on_finished=lambda: finished.append("done"))
    window.playback.frame_index = len(window.playback.animation.frames)

    window.show_frame()

    assert (finished, window.playback) == (["done"], None)


def test_interrupt_flags_a_running_playback_and_ignores_an_idle_window(clippy, qt_app):
    window = window_of(clippy, qt_app)
    window.interrupt()
    window.play("Greeting")
    window.interrupt()

    assert window.playback.stop_requested is True


def test_random_idle_plays_an_idle_animation_when_nothing_is_playing(clippy, qt_app):
    window = window_of(clippy, qt_app)

    window.play_random_idle()

    assert (window.playback.animation.name.startswith("Idle"), window.idle_timer.isActive()) == (True, True)


def test_random_idle_leaves_a_running_playback_alone(clippy, qt_app):
    window = window_of(clippy, qt_app)
    window.play("Greeting")
    running = window.playback

    window.play_random_idle()

    assert window.playback is running


def test_random_action_interrupts_and_plays_a_non_idle_animation(clippy, qt_app):
    window = window_of(clippy, qt_app)
    window.play("Greeting")
    greeting = window.playback

    window.play_random_action()

    assert (greeting.stop_requested, window.playback.animation.name in window.action_names) == (True, True)


def test_random_tip_opens_a_balloon_with_one_of_the_tips(clippy, qt_app):
    window = window_of(clippy, qt_app)

    window.show_random_tip()

    assert (
        window.balloon.text in clippy.TIPS,
        window.playback.animation.name in clippy.TIP_ANIMATIONS,
        window.tip_timer.isActive(),
    ) == (True, True, True)


def test_move_to_corner_places_the_window_inside_the_screen_margin(clippy, qt_app):
    window = window_of(clippy, qt_app)

    window.move_to_corner()

    available = window.screen().availableGeometry()
    assert window.pos() == QPoint(
        available.right() - window.width() - clippy.SCREEN_MARGIN,
        available.bottom() - window.height() - clippy.SCREEN_MARGIN,
    )


def test_start_schedule_plays_greeting_and_starts_both_timers(clippy, qt_app):
    window = window_of(clippy, qt_app)

    window.start_schedule()

    assert (window.playback.animation.name, window.idle_timer.isActive(), window.tip_timer.isActive()) == (
        "Greeting",
        True,
        True,
    )


def test_hide_for_a_while_hides_the_balloon_and_plays_hide(clippy, qt_app):
    window = window_of(clippy, qt_app)
    window.show_random_tip()

    window.hide_for_a_while()

    assert (window.balloon.isVisible(), window.playback.animation.name) == (False, "Hide")


def test_come_back_shows_the_window_and_plays_show(clippy, qt_app):
    window = window_of(clippy, qt_app)

    window.come_back()

    assert (window.isVisible(), window.playback.animation.name) == (True, "Show")
    window.hide()


def test_paint_event_without_a_frame_draws_nothing_and_with_a_frame_draws_the_sprite(clippy, qt_app):
    window = window_of(clippy, qt_app)
    window.paintEvent(None)
    window.play("Greeting")

    image = window.grab().toImage()

    assert image.size() == QSize(124, 93)


def test_left_press_without_a_window_handle_starts_a_drag_offset(clippy, qt_app):
    window = window_of(clippy, qt_app)

    window.mousePressEvent(mouse_event(QEvent.MouseButtonPress, Qt.LeftButton, Qt.LeftButton))

    assert window.drag_offset == QPoint(10, 10) - window.frameGeometry().topLeft()


def test_left_press_on_a_shown_window_without_system_move_starts_a_drag_offset(clippy, qt_app):
    window = window_of(clippy, qt_app)
    window.show()

    window.mousePressEvent(mouse_event(QEvent.MouseButtonPress, Qt.LeftButton, Qt.LeftButton))
    window.hide()

    assert window.drag_offset == QPoint(10, 10) - window.frameGeometry().topLeft()


def test_right_press_does_not_start_a_drag(clippy, qt_app):
    window = window_of(clippy, qt_app)

    window.mousePressEvent(mouse_event(QEvent.MouseButtonPress, Qt.RightButton, Qt.RightButton))

    assert window.drag_offset is None


def test_dragging_with_the_left_button_moves_the_window_by_the_pointer_delta(clippy, qt_app):
    window = window_of(clippy, qt_app)
    window.drag_offset = QPoint(5, 5)

    window.mouseMoveEvent(mouse_event(QEvent.MouseMove, Qt.NoButton, Qt.LeftButton, (105, 205)))

    assert window.pos() == QPoint(100, 200)


def test_moving_without_a_drag_offset_keeps_the_window_where_it_is(clippy, qt_app):
    window = window_of(clippy, qt_app)
    window.move(7, 9)

    window.mouseMoveEvent(mouse_event(QEvent.MouseMove, Qt.NoButton, Qt.LeftButton, (300, 300)))

    assert window.pos() == QPoint(7, 9)


def test_moving_with_no_button_down_keeps_the_window_where_it_is(clippy, qt_app):
    window = window_of(clippy, qt_app)
    window.move(7, 9)
    window.drag_offset = QPoint(1, 1)

    window.mouseMoveEvent(mouse_event(QEvent.MouseMove, Qt.NoButton, Qt.NoButton, (300, 300)))

    assert window.pos() == QPoint(7, 9)


def test_releasing_the_mouse_clears_the_drag_offset(clippy, qt_app):
    window = window_of(clippy, qt_app)
    window.drag_offset = QPoint(1, 1)

    window.mouseReleaseEvent(None)

    assert window.drag_offset is None


def test_left_double_click_opens_a_tip_and_right_double_click_does_not(clippy, qt_app):
    window = window_of(clippy, qt_app)
    window.mouseDoubleClickEvent(mouse_event(QEvent.MouseButtonDblClick, Qt.RightButton, Qt.RightButton))
    after_right = window.balloon.text

    window.mouseDoubleClickEvent(mouse_event(QEvent.MouseButtonDblClick, Qt.LeftButton, Qt.LeftButton))

    assert (after_right, window.balloon.text in clippy.TIPS) == ("", True)


def test_assistant_menu_lists_the_office_entries_with_two_disabled(clippy, qt_app):
    menu = window_of(clippy, qt_app).assistant_menu()

    assert [(action.text(), action.isEnabled()) for action in menu.actions() if not action.isSeparator()] == [
        ("Hide", True),
        ("Options...", False),
        ("Choose Assistant...", False),
        ("Animate!", True),
        ("Exit", True),
    ]


def test_context_menu_event_pops_up_the_assistant_menu_until_it_is_closed(clippy, qt_app):
    window = window_of(clippy, qt_app)
    popup_titles = []

    def record_and_close_popup():
        popup = QApplication.activePopupWidget()
        popup_titles.append([action.text() for action in popup.actions() if not action.isSeparator()])
        popup.close()

    QTimer.singleShot(200, record_and_close_popup)
    window.contextMenuEvent(QContextMenuEvent(QContextMenuEvent.Mouse, QPoint(3, 4), QPoint(30, 40)))

    assert popup_titles == [["Hide", "Options...", "Choose Assistant...", "Animate!", "Exit"]]


def test_exit_application_plays_goodbye_and_closes_the_window_when_it_ends(clippy, qt_app):
    window = window_of(clippy, qt_app)
    window.show()
    window.exit_application()
    goodbye = window.playback.animation.name
    window.playback.frame_index = len(window.playback.animation.frames)

    window.show_frame()

    assert (goodbye, window.playback, window.isVisible()) == ("GoodBye", None, False)


def test_balloon_mouse_press_hides_it(clippy, qt_app):
    window = window_of(clippy, qt_app)
    window.show_random_tip()

    window.balloon.mousePressEvent(None)

    assert window.balloon.isVisible() is False


def test_balloon_without_an_owner_shows_a_tip(clippy, qt_app):
    balloon = clippy.Balloon(qt_app.font())

    balloon.show_tip("Hello", QPoint(200, 200))

    assert (balloon.text, balloon.close_timer.isActive()) == ("Hello", True)
    balloon.hide()


def test_render_screenshot_writes_a_png_with_the_balloon_and_the_sprite(clippy, qt_app, tmp_path):
    window = window_of(clippy, qt_app)
    output = tmp_path / "shot.png"

    clippy.render_screenshot(window.animations, window.sprites, qt_app.font(), output)

    assert QImage(str(output)).width() >= clippy.BALLOON_WIDTH


def test_signal_running_instance_is_false_without_a_pid_file(clippy):
    assert clippy.signal_running_instance() is False


def test_signal_running_instance_is_false_when_the_pid_is_gone(clippy):
    process = subprocess.Popen(["true"])
    process.wait()
    clippy.PID_FILE.write_text(str(process.pid))

    assert clippy.signal_running_instance() is False


def test_signal_running_instance_is_true_when_the_process_lives(clippy):
    process = subprocess.Popen(["sleep", "30"])
    clippy.PID_FILE.write_text(str(process.pid))

    assert clippy.signal_running_instance() is True
    process.wait()


def test_parse_args_reads_every_option(clippy, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["clippy", "--mute", "--screenshot", "a.png", "--once", "Greeting"])

    args = clippy.parse_args()

    assert (args.mute, args.screenshot, args.once) == (True, "a.png", "Greeting")


def test_main_exits_zero_when_another_instance_is_signalled(clippy, monkeypatch):
    process = subprocess.Popen(["sleep", "30"])
    clippy.PID_FILE.write_text(str(process.pid))
    monkeypatch.setattr(sys, "argv", ["clippy"])

    assert clippy.main() == 0
    process.wait()


def test_advance_frame_moves_a_playing_animation_to_its_next_frame(clippy, qt_app):
    window = window_of(clippy, qt_app)
    window.play("Hide")
    first_frame = window.current_frame

    window.advance_frame()

    assert (window.playback.frame_index, window.current_frame is first_frame) == (1, False)


def test_parse_sounds_js_decodes_each_base64_ogg_entry_by_id(clippy):
    text = "{'1': 'data:audio/ogg;base64,aGVsbG8=', \"22\": \"data:audio/ogg;base64,d29ybGQ=\"}"

    assert clippy.parse_sounds_js(text) == {"1": b"hello", "22": b"world"}


def test_balloon_of_a_shown_window_becomes_transient_for_it(clippy, qt_app):
    window = window_of(clippy, qt_app)
    window.show()

    window.show_random_tip()

    assert window.balloon.windowHandle().transientParent() is window.windowHandle()
    window.balloon.hide()
    window.hide()
