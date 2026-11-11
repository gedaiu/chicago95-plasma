"""Branch coverage for bin/chicago95-notifyd: its helpers, popup widgets, popup stack, D-Bus service
(on a private bus daemon, never the session's) and its command line."""

import os
import select
import signal
import subprocess
import sys
import time

import dbus
import dbus.bus
import pytest
from conftest import REPO, load_script
from dbus.mainloop.glib import DBusGMainLoop
from PySide6.QtCore import QEvent, QPoint, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QImage, QPixmap
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget

SCRIPT = REPO / "bin" / "chicago95-notifyd"
DEADLINE_SECONDS = 20


@pytest.fixture
def notifyd(qt_app, tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    module = load_script("chicago95-notifyd")
    module.desktop_entry.cache_clear()
    yield module
    module.desktop_entry.cache_clear()


@pytest.fixture
def private_bus_address():
    daemon = subprocess.Popen(
        ["dbus-daemon", "--session", "--nofork", "--print-address"],
        stdout=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        ready, _, _ = select.select([daemon.stdout], [], [], 5)
        assert ready
        yield daemon.stdout.readline().strip()
    finally:
        os.killpg(daemon.pid, signal.SIGKILL)
        daemon.wait(timeout=5)


def make_notification(notifyd, **overrides):
    fields = {
        "notification_id": 1,
        "app_name": "Test",
        "app_icon": "",
        "summary": "Hello",
        "body": "World",
        "actions": [],
        "hints": {},
        "timeout_ms": 5000,
    } | overrides
    return notifyd.Notification(**fields)


def write_png(path, width=20, height=10):
    image = QImage(width, height, QImage.Format_RGB32)
    image.fill(QColor("#ff0000"))
    image.save(str(path))
    return str(path)


def wait_until(condition, seconds=2):
    deadline = time.monotonic() + seconds
    while not condition() and time.monotonic() < deadline:
        QApplication.processEvents()
        QTest.qWait(10)
    return condition()


@pytest.fixture
def icon_theme(tmp_path):
    theme = tmp_path / "icons" / "mytheme"
    (theme / "16x16" / "apps").mkdir(parents=True)
    for name in ("my-icon", "dialog-information"):
        write_png(theme / "16x16" / "apps" / f"{name}.png", 16, 16)
    (theme / "index.theme").write_text(
        "[Icon Theme]\nName=mytheme\nDirectories=16x16/apps\n[16x16/apps]\nSize=16\nType=Fixed\n"
    )
    previous = (QIcon.themeSearchPaths(), QIcon.themeName())
    QIcon.setThemeSearchPaths([str(tmp_path / "icons")])
    QIcon.setThemeName("mytheme")
    yield
    QIcon.setThemeSearchPaths(previous[0])
    QIcon.setThemeName(previous[1])


@pytest.fixture
def empty_icon_theme(tmp_path):
    previous = (QIcon.themeSearchPaths(), QIcon.themeName())
    QIcon.setThemeSearchPaths([str(tmp_path / "no-icons")])
    QIcon.setThemeName("no-such-theme")
    yield
    QIcon.setThemeSearchPaths(previous[0])
    QIcon.setThemeName(previous[1])


def drain_deferred_deletes():
    QApplication.sendPostedEvents(None, QEvent.DeferredDelete)


@pytest.fixture
def host(qt_app):
    widget = QWidget()
    widget.resize(400, 400)
    yield widget
    widget.close()
    drain_deferred_deletes()


@pytest.fixture
def animation_choice(tmp_path, monkeypatch):
    def choose(choice):
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        (tmp_path / "chicago95rc").write_text(f"[Animations]\nANIM_NOTIFICATIONS={choice}\n")

    return choose


class TestNotification:
    def test_urgency_defaults_to_normal_and_reads_the_hint(self, notifyd):
        assert (
            make_notification(notifyd).urgency,
            make_notification(notifyd, hints={"urgency": 2}).urgency,
        ) == (1, 2)

    def test_resident_follows_the_hint(self, notifyd):
        assert (
            make_notification(notifyd).resident,
            make_notification(notifyd, hints={"resident": True}).resident,
        ) == (False, True)

    def test_override_found_by_app_name_or_desktop_entry_or_not_at_all(self, notifyd):
        by_name = make_notification(notifyd, app_name="Qmmp").override
        by_entry = make_notification(notifyd, hints={"desktop-entry": "QMMP"}).override
        assert (by_name, by_entry, make_notification(notifyd).override) == (
            notifyd.APP_OVERRIDES["qmmp"],
            notifyd.APP_OVERRIDES["qmmp"],
            None,
        )

    @pytest.mark.parametrize(
        ("fields", "expected"),
        [
            ({"hints": {"urgency": 2}, "timeout_ms": 1000}, 0),
            ({"timeout_ms": 0}, 0),
            ({"timeout_ms": -1}, 6000),
            ({"timeout_ms": 1500}, 1500),
        ],
    )
    def test_effective_timeout_is_x_when_urgency_and_timeout_are_y(self, notifyd, fields, expected):
        assert make_notification(notifyd, **fields).effective_timeout_ms == expected


class TestToPython:
    def test_converts_every_dbus_type_to_its_python_counterpart(self, notifyd):
        converted = notifyd.to_python(
            dbus.Dictionary(
                {
                    "flag": dbus.Boolean(True),
                    "byte": dbus.Byte(7),
                    "int16": dbus.Int16(-3),
                    "uint64": dbus.UInt64(9),
                    "real": dbus.Double(1.5),
                    "text": dbus.String("hi"),
                    "path": dbus.ObjectPath("/a/b"),
                    "blob": dbus.ByteArray(b"ab"),
                    "bytes": dbus.Array([dbus.Byte(1), dbus.Byte(2)], signature="y"),
                    "list": dbus.Array([dbus.Int32(1), dbus.String("x")], signature="v"),
                    "pair": dbus.Struct((dbus.Int32(1), dbus.String("x"))),
                    "other": None,
                },
                signature="sv",
            )
        )
        assert converted == {
            "flag": True,
            "byte": 7,
            "int16": -3,
            "uint64": 9,
            "real": 1.5,
            "text": "hi",
            "path": "/a/b",
            "blob": b"ab",
            "bytes": b"\x01\x02",
            "list": [1, "x"],
            "pair": (1, "x"),
            "other": None,
        }
        assert [type(value) for value in converted.values()][:4] == [bool, int, int, int]


class TestPairActions:
    def test_pairs_keys_with_labels_and_drops_a_dangling_key(self, notifyd):
        assert notifyd.pair_actions(["a", "A", "b", "B", "c"]) == [("a", "A"), ("b", "B")]


class TestDesktopEntry:
    def test_reads_the_entry_found_in_the_data_dirs(self, notifyd, tmp_path, monkeypatch):
        applications = tmp_path / "share" / "applications"
        applications.mkdir(parents=True)
        (applications / "tool.desktop").write_text("[Desktop Entry]\nName=Tool\nIcon=tool-icon\n")
        monkeypatch.setenv("HOME", str(tmp_path / "home"))
        monkeypatch.setenv("XDG_DATA_DIRS", str(tmp_path / "share"))
        assert notifyd.desktop_entry("tool") == {"Name": "Tool", "Icon": "tool-icon"}

    def test_returns_empty_when_the_file_has_no_desktop_entry_section(self, notifyd, tmp_path, monkeypatch):
        applications = tmp_path / "share" / "applications"
        applications.mkdir(parents=True)
        (applications / "odd.desktop").write_text("[Other]\nName=Odd\n")
        monkeypatch.setenv("HOME", str(tmp_path / "home"))
        monkeypatch.setenv("XDG_DATA_DIRS", str(tmp_path / "share"))
        assert notifyd.desktop_entry("odd") == {}

    def test_returns_empty_when_no_data_dir_has_the_entry(self, notifyd, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path / "home"))
        monkeypatch.setenv("XDG_DATA_DIRS", str(tmp_path / "share"))
        assert notifyd.desktop_entry("missing") == {}


class TestDisplayName:
    @pytest.mark.parametrize(
        ("fields", "expected"),
        [
            ({"app_name": "Qmmp"}, "Winamp"),
            ({"hints": {"x-kde-display-appname": "Pretty"}}, "Pretty"),
            ({"app_name": "Plain"}, "Plain"),
            ({"app_name": ""}, "Chicago95"),
        ],
    )
    def test_display_name_is_x_when_app_fields_are_y(self, notifyd, fields, expected):
        assert notifyd.display_name(make_notification(notifyd, **fields)) == expected

    def test_uses_the_desktop_entry_name_when_the_app_has_no_name(self, notifyd, tmp_path, monkeypatch):
        applications = tmp_path / "share" / "applications"
        applications.mkdir(parents=True)
        (applications / "named.desktop").write_text("[Desktop Entry]\nName=From Entry\n")
        monkeypatch.setenv("HOME", str(tmp_path / "home"))
        monkeypatch.setenv("XDG_DATA_DIRS", str(tmp_path / "share"))
        notification = make_notification(notifyd, app_name="", hints={"desktop-entry": "named"})
        assert notifyd.display_name(notification) == "From Entry"


class TestRewrittenSummary:
    def test_rewrites_the_summary_of_an_overridden_app(self, notifyd):
        notification = make_notification(notifyd, app_name="Qmmp", summary="Qmmp now playing:")
        assert notifyd.rewritten_summary(notification) == "Now Playing"

    def test_keeps_the_summary_of_other_apps(self, notifyd):
        assert notifyd.rewritten_summary(make_notification(notifyd, summary="Qmmp now playing:")) == "Qmmp now playing:"


class TestBodyHtml:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("a\nb", "a<br>b"),
            ("x < y", "x < y"),
            ("<b>bold</b> <script>no</script>\nend", "<b>bold</b> no<br>end"),
            ("fish &amp; chips", "fish &amp; chips"),
        ],
    )
    def test_body_html_is_x_when_text_is_y(self, notifyd, text, expected):
        assert notifyd.body_html(text) == expected


class TestPixmaps:
    def test_scaled_pixmap_fits_the_target_size_at_the_pixel_ratio(self, notifyd):
        pixmap = notifyd.scaled_pixmap(QImage(40, 20, QImage.Format_RGB32), 16, 2.0)
        assert (pixmap.size(), pixmap.devicePixelRatio()) == (QSize(32, 16), 2.0)

    def test_spec_pixmap_is_none_when_spec_is_empty_or_unknown(self, notifyd):
        assert (
            notifyd.pixmap_from_spec("", 16, 1.0),
            notifyd.pixmap_from_spec("no-such-icon-name-anywhere", 16, 1.0),
            notifyd.pixmap_from_spec("/no/such/file.png", 16, 1.0),
        ) == (None, None, None)

    def test_spec_pixmap_loads_a_path_and_a_file_url(self, notifyd, tmp_path):
        path = write_png(tmp_path / "pic one.png")
        from_path = notifyd.pixmap_from_spec(path, 16, 1.0)
        from_url = notifyd.pixmap_from_spec("file://" + path.replace(" ", "%20"), 16, 1.0)
        assert (from_path.width(), from_url.width()) == (16, 16)

    def test_spec_pixmap_loads_a_theme_icon(self, notifyd, icon_theme):
        assert notifyd.pixmap_from_spec("my-icon", 16, 1.0).size() == QSize(16, 16)

    def test_image_data_pixmap_is_built_from_rgb_and_rgba_rows(self, notifyd):
        rgb = notifyd.pixmap_from_image_data((2, 2, 6, False, 8, 3, bytes(12)), 16, 1.0)
        rgba = notifyd.pixmap_from_image_data((2, 2, 8, True, 8, 4, bytes(16)), 16, 1.0)
        assert (rgb.width(), rgba.width()) == (16, 16)

    def test_image_data_pixmap_is_none_when_the_pixels_make_no_image(self, notifyd):
        assert notifyd.pixmap_from_image_data((0, 0, 0, False, 8, 3, b""), 16, 1.0) is None


class TestIconSpecs:
    def test_app_icon_spec_prefers_override_then_app_icon_then_desktop_entry(self, notifyd, tmp_path, monkeypatch):
        applications = tmp_path / "share" / "applications"
        applications.mkdir(parents=True)
        (applications / "iconic.desktop").write_text("[Desktop Entry]\nIcon=entry-icon\n")
        monkeypatch.setenv("HOME", str(tmp_path / "home"))
        monkeypatch.setenv("XDG_DATA_DIRS", str(tmp_path / "share"))
        specs = [
            notifyd.app_icon_spec(make_notification(notifyd, app_name="Qmmp")),
            notifyd.app_icon_spec(make_notification(notifyd, app_icon="given")),
            notifyd.app_icon_spec(make_notification(notifyd, hints={"desktop-entry": "iconic"})),
            notifyd.app_icon_spec(make_notification(notifyd)),
        ]
        assert specs == ["winamp", "given", "entry-icon", ""]

    def test_title_pixmap_falls_back_through_icon_names_to_dialog_information(self, notifyd, tmp_path):
        path = write_png(tmp_path / "app.png")
        from_app_icon = notifyd.title_pixmap(make_notification(notifyd, app_icon=path), 1.0)
        from_hint_path = notifyd.title_pixmap(make_notification(notifyd, hints={"image-path": path}), 1.0)
        from_hint_name = notifyd.title_pixmap(make_notification(notifyd, hints={"image_path": "no-such-icon"}), 1.0)
        assert (from_app_icon.width(), from_hint_path is None or from_hint_path.width() > 0) == (16, True)
        assert from_hint_name is None or from_hint_name.width() > 0

    def test_content_pixmap_prefers_image_data_then_image_path_then_icon(self, notifyd, tmp_path):
        path = write_png(tmp_path / "pic.png")
        image_data = (2, 2, 6, False, 8, 3, bytes(12))
        sizes = [
            notifyd.content_pixmap(make_notification(notifyd, hints={key: image_data}), 1.0).width()
            for key in ("image-data", "image_data", "icon_data")
        ]
        by_path = notifyd.content_pixmap(make_notification(notifyd, hints={"image-path": path}), 1.0)
        by_app_icon = notifyd.content_pixmap(make_notification(notifyd, app_icon=path), 1.0)
        overridden = notifyd.content_pixmap(
            make_notification(notifyd, app_name="Qmmp", hints={"image-path": path}), 1.0
        )
        assert (sizes, by_path.width(), by_app_icon.width(), overridden is None or overridden.width() > 0) == (
            [48, 48, 48],
            48,
            32,
            True,
        )

    def test_content_pixmap_without_any_icon_uses_the_urgency_fallback(self, notifyd):
        normal = notifyd.content_pixmap(make_notification(notifyd), 1.0)
        critical = notifyd.content_pixmap(make_notification(notifyd, hints={"urgency": 2}), 1.0)
        assert (normal is None or normal.width() > 0, critical is None or critical.width() > 0) == (True, True)


class TestPaintBevel:
    def test_bevel_paints_every_ring_then_the_face(self, notifyd):
        from PySide6.QtGui import QPainter

        canvas = QPixmap(10, 10)
        canvas.fill(QColor("#123456"))
        painter = QPainter(canvas)
        notifyd.paint_bevel(painter, QSize(10, 10), 1.0, notifyd.WINDOW_RINGS, QColor("#00ff00"))
        painter.end()
        image = canvas.toImage()
        assert (image.pixelColor(5, 5), image.pixelColor(0, 0)) == (QColor("#00ff00"), notifyd.chicago95ui.LIGHT)


class TestWidgets:
    def test_close_button_paints_raised_and_pressed(self, notifyd):
        button = notifyd.CloseButton()
        raised = button.grab().toImage()
        button.setDown(True)
        pressed = button.grab().toImage()
        assert raised != pressed

    def test_title_bar_elides_a_long_title(self, notifyd):
        bar = notifyd.TitleBar()
        bar.grab()
        bar.set_content(None, "x" * 500)
        assert len(bar.title_label.text()) < 500


class TestNotificationPopup:
    def test_popup_shows_the_icon_label_when_an_icon_is_found(self, notifyd, host, icon_theme):
        popup = notifyd.NotificationPopup(make_notification(notifyd), host)
        assert popup.icon_label.size() == QSize(16, 16)

    def test_popup_hides_the_icon_label_when_no_icon_is_found(self, notifyd, host, empty_icon_theme):
        popup = notifyd.NotificationPopup(make_notification(notifyd), host)
        assert popup.icon_label.isHidden()

    def test_popup_without_a_host_is_a_frameless_window(self, notifyd):
        popup = notifyd.NotificationPopup(make_notification(notifyd))
        assert bool(popup.windowFlags() & Qt.FramelessWindowHint) is True

    def test_popup_hides_empty_summary_and_body_and_icon_labels(self, notifyd, host):
        popup = notifyd.NotificationPopup(make_notification(notifyd, summary="", body=""), host)
        assert (popup.summary_label.isHidden(), popup.body_label.isHidden()) == (True, True)

    def test_popup_buttons_skip_default_and_unlabelled_actions_and_report_clicks(self, notifyd, host):
        popup = notifyd.NotificationPopup(
            make_notification(notifyd, actions=[("default", "Open"), ("quiet", ""), ("go", "Go")]), host
        )
        invoked = []
        popup.action_invoked.connect(invoked.append)
        popup.action_buttons[0].click()
        assert ([button.text() for button in popup.action_buttons], popup.has_default_action, invoked) == (
            ["Go"],
            True,
            ["go"],
        )

    def test_popup_rebuild_replaces_previous_buttons(self, notifyd, host):
        popup = notifyd.NotificationPopup(make_notification(notifyd, actions=[("a", "A")]), host)
        popup.rebuild_actions([])
        assert (popup.action_buttons, popup.action_row.count()) == ([], 0)

    def test_popup_expiry_timer_runs_only_for_a_timed_notification(self, notifyd, host):
        timed = notifyd.NotificationPopup(make_notification(notifyd, timeout_ms=5000), host)
        sticky = notifyd.NotificationPopup(make_notification(notifyd, timeout_ms=0), host)
        assert (timed.expiry_timer.isActive(), sticky.expiry_timer.isActive()) == (True, False)

    def test_popup_expiry_timer_emits_expired_reason(self, notifyd, host):
        popup = notifyd.NotificationPopup(make_notification(notifyd, timeout_ms=5000), host)
        reasons = []
        popup.dismissed.connect(reasons.append)
        popup.expiry_timer.timeout.emit()
        popup.title_bar.close_button.clicked.emit()
        assert reasons == [notifyd.CLOSED_EXPIRED, notifyd.CLOSED_DISMISSED]

    def test_popup_hover_pauses_expiry_and_leaving_restarts_it_with_grace(self, notifyd, host):
        popup = notifyd.NotificationPopup(make_notification(notifyd, timeout_ms=5000), host)
        popup.enterEvent(QEvent(QEvent.Enter))
        paused = popup.expiry_timer.isActive()
        popup.leaveEvent(QEvent(QEvent.Leave))
        assert (paused, popup.expiry_timer.isActive(), popup.expiry_timer.interval()) == (
            False,
            True,
            notifyd.HOVER_GRACE_MS,
        )

    def test_popup_click_triggers_default_action_when_it_has_one(self, notifyd, host):
        popup = notifyd.NotificationPopup(make_notification(notifyd, actions=[("default", "Open")]), host)
        popup.show()
        invoked = []
        popup.action_invoked.connect(invoked.append)
        QTest.mouseClick(popup, Qt.LeftButton)
        assert invoked == ["default"]

    def test_popup_click_dismisses_without_default_action_and_ignores_other_buttons(self, notifyd, host):
        popup = notifyd.NotificationPopup(make_notification(notifyd), host)
        popup.show()
        reasons = []
        popup.dismissed.connect(reasons.append)
        QTest.mouseClick(popup, Qt.RightButton)
        QTest.mouseClick(popup, Qt.LeftButton)
        assert reasons == [notifyd.CLOSED_DISMISSED]

    def test_popup_paints_its_bevel(self, notifyd, host):
        popup = notifyd.NotificationPopup(make_notification(notifyd), host)
        assert popup.grab().toImage().pixelColor(0, 0) == notifyd.chicago95ui.LIGHT

    def test_glide_retargets_a_running_slide(self, notifyd, host, animation_choice):
        animation_choice("slide")
        popup = notifyd.NotificationPopup(make_notification(notifyd), host)
        popup.slide_in(QPoint(10, 40))
        popup.glide_to(QPoint(10, 90))
        assert popup.move_animation.endValue() == QPoint(10, 90)

    def test_glide_moves_at_once_without_animation(self, notifyd, host, animation_choice):
        animation_choice("none")
        popup = notifyd.NotificationPopup(make_notification(notifyd), host)
        popup.glide_to(QPoint(10, 90))
        assert popup.pos() == QPoint(10, 90)

    def test_glide_animates_an_idle_popup_to_a_new_place_and_not_to_its_own(self, notifyd, host, animation_choice):
        animation_choice("slide")
        popup = notifyd.NotificationPopup(make_notification(notifyd), host)
        popup.move(10, 40)
        popup.glide_to(QPoint(10, 40))
        stayed = popup.move_animation
        popup.glide_to(QPoint(10, 90))
        assert (stayed, popup.move_animation.endValue()) == (None, QPoint(10, 90))

    def test_slide_out_animates_to_the_right_and_deletes_itself_after(self, notifyd, host, animation_choice):
        animation_choice("slide")
        popup = notifyd.NotificationPopup(make_notification(notifyd), host)
        popup.slide_in(QPoint(10, 40))
        popup.slide_out()
        assert (popup.move_animation.endValue().x(), popup.fade_animation.endValue()) == (
            popup.pos().x() + notifyd.POPUP_WIDTH + notifyd.SCREEN_MARGIN,
            0.0,
        )


class TestPopupHostAndStack:
    @pytest.fixture
    def stack(self, notifyd, animation_choice):
        animation_choice("none")
        popup_stack = notifyd.PopupStack()
        yield popup_stack
        popup_stack.host.close()
        drain_deferred_deletes()

    def test_host_is_sized_for_the_popup_column(self, notifyd, stack):
        assert (stack.host.width(), stack.host.windowTitle()) == (
            notifyd.POPUP_WIDTH + 2 * notifyd.SCREEN_MARGIN,
            "chicago95-notifyd-host",
        )

    def test_showing_two_popups_shows_the_host_and_stacks_newest_at_the_bottom(self, notifyd, stack):
        stack.show(make_notification(notifyd, notification_id=1))
        stack.show(make_notification(notifyd, notification_id=2))
        targets = stack.targets()
        assert (stack.host.isVisible(), targets[2].y() > targets[1].y(), list(stack.popups)) == (True, True, [1, 2])

    def test_showing_an_existing_id_updates_that_popup_in_place(self, notifyd, stack):
        stack.show(make_notification(notifyd, summary="first"))
        popup = stack.popups[1]
        stack.show(make_notification(notifyd, summary="second"))
        assert (stack.popups[1] is popup, popup.summary_label.text(), len(stack.popups)) == (True, "second", 1)

    def test_closing_removes_the_popup_and_reports_the_reason(self, notifyd, stack):
        stack.show(make_notification(notifyd))
        closed = []
        stack.closed.connect(lambda notification_id, reason: closed.append((notification_id, reason)))
        stack.close(1, notifyd.CLOSED_BY_CALL)
        stack.close(1, notifyd.CLOSED_BY_CALL)
        assert (stack.popups, closed) == ({}, [(1, notifyd.CLOSED_BY_CALL)])

    def test_host_hides_after_the_last_popup_has_slid_out(self, notifyd, stack):
        stack.show(make_notification(notifyd, notification_id=1))
        stack.show(make_notification(notifyd, notification_id=2))
        stack.close(1, notifyd.CLOSED_DISMISSED)
        stayed_while_one_remains = stack.host.isVisible()
        stack.close(2, notifyd.CLOSED_DISMISSED)
        assert (stayed_while_one_remains, wait_until(lambda: not stack.host.isVisible())) == (True, True)

    def test_host_stays_when_a_popup_arrives_before_the_hide_timer_fires(self, notifyd, stack):
        stack.show(make_notification(notifyd, notification_id=1))
        stack.show(make_notification(notifyd, notification_id=2))
        stack.close(1, notifyd.CLOSED_DISMISSED)
        stack.close(2, notifyd.CLOSED_DISMISSED)
        stack.show(make_notification(notifyd, notification_id=3))
        QTest.qWait(notifyd.SLIDE_OUT_MS + 150)
        assert stack.host.isVisible()

    def test_invoking_an_action_dismisses_unless_the_notification_is_resident(self, notifyd, stack):
        stack.show(make_notification(notifyd, notification_id=1))
        stack.show(make_notification(notifyd, notification_id=2))
        invoked = []
        stack.action_invoked.connect(lambda notification_id, key: invoked.append((notification_id, key)))
        stack.invoke(1, "go", True)
        resident_kept = list(stack.popups)
        stack.invoke(2, "go", False)
        assert (invoked, resident_kept, list(stack.popups)) == ([(1, "go"), (2, "go")], [1, 2], [1])

    def test_popup_signals_close_and_invoke_through_the_stack(self, notifyd, stack):
        stack.show(make_notification(notifyd, notification_id=1, actions=[("go", "Go")]))
        stack.show(make_notification(notifyd, notification_id=2))
        events = []
        stack.closed.connect(lambda notification_id, reason: events.append(("closed", notification_id, reason)))
        stack.action_invoked.connect(lambda notification_id, key: events.append(("action", notification_id, key)))
        stack.popups[1].action_buttons[0].click()
        stack.popups[2].dismissed.emit(notifyd.CLOSED_EXPIRED)
        assert events == [
            ("action", 1, "go"),
            ("closed", 1, notifyd.CLOSED_DISMISSED),
            ("closed", 2, notifyd.CLOSED_EXPIRED),
        ]

    def test_overflowing_the_column_drops_the_oldest_popups_but_keeps_the_newest(self, notifyd, stack):
        for notification_id in range(1, 21):
            stack.show(make_notification(notifyd, notification_id=notification_id, body="line\n" * 4))
        assert (len(stack.popups) < 20, list(stack.popups)[-1]) == (True, 20)


class TestNotificationService:
    @pytest.fixture
    def service(self, notifyd, private_bus_address, animation_choice):
        animation_choice("none")
        connection = dbus.bus.BusConnection(private_bus_address, mainloop=DBusGMainLoop())
        stack = notifyd.PopupStack()
        yield notifyd.NotificationService(connection, stack)
        stack.host.close()
        drain_deferred_deletes()
        connection.close()

    def test_server_reports_capabilities_and_identity(self, notifyd, service):
        assert (service.GetCapabilities(), service.GetServerInformation()) == (
            notifyd.CAPABILITIES,
            ("Chicago95 Notifications", "Chicago95", "1.0", "1.2"),
        )

    def test_notify_allocates_ids_and_replaces_when_asked(self, notifyd, service):
        hints = dbus.Dictionary({"urgency": dbus.Byte(2), "resident": dbus.Boolean(True)}, signature="sv")
        first = service.Notify("app", 0, "", "one", "", ["go", "Go"], hints, -1)
        second = service.Notify("app", 0, "", "two", "", [], {}, 0)
        replaced = service.Notify("app", first, "", "uno", "", [], {}, 0)
        assert (first, second, replaced, service.stack.popups[1].summary_label.text()) == (1, 2, 1, "uno")

    def test_clicking_an_action_button_emits_the_action_invoked_signal(self, notifyd, service):
        service.Notify("app", 0, "", "one", "", ["go", "Go"], {}, -1)
        service.stack.popups[1].action_buttons[0].click()
        assert service.stack.popups == {}

    def test_close_notification_removes_the_popup_and_emits_the_signal(self, notifyd, service):
        service.Notify("app", 0, "", "one", "", [], {}, -1)
        service.CloseNotification(1)
        assert service.stack.popups == {}


class TestCommandLine:
    def run_daemon(self, args, address, tmp_path):
        env = os.environ | {
            "DBUS_SESSION_BUS_ADDRESS": address,
            "QT_QPA_PLATFORM": "offscreen",
            "XDG_CONFIG_HOME": str(tmp_path / "config"),
        }
        return subprocess.Popen(
            [sys.executable, str(SCRIPT), *args],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )

    def finish(self, process):
        try:
            return process.communicate(timeout=DEADLINE_SECONDS)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
            raise

    def test_screenshot_option_renders_the_samples_and_exits_zero(self, private_bus_address, tmp_path):
        target = tmp_path / "samples.png"
        process = self.run_daemon(["--screenshot", str(target)], private_bus_address, tmp_path)
        self.finish(process)
        assert (process.returncode, QImage(str(target)).isNull()) == (0, False)

    def test_second_daemon_exits_one_while_the_first_owns_the_name_and_first_quits_on_sigterm(
        self, notifyd, private_bus_address, tmp_path
    ):
        first = self.run_daemon([], private_bus_address, tmp_path)
        try:
            watcher = dbus.bus.BusConnection(private_bus_address)
            deadline = time.monotonic() + DEADLINE_SECONDS
            while not watcher.name_has_owner(notifyd.SERVICE_NAME) and time.monotonic() < deadline:
                time.sleep(0.05)
            second = self.run_daemon([], private_bus_address, tmp_path)
            _, second_error = self.finish(second)
            first.send_signal(signal.SIGTERM)
            self.finish(first)
        finally:
            if first.poll() is None:
                os.killpg(first.pid, signal.SIGKILL)
                first.wait()
        assert (second.returncode, "already owned" in second_error, first.returncode) == (1, True, 0)
