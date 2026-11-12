from pathlib import Path

import pytest
from conftest import REPO, run_bash_with_steps
from PySide6.QtCore import QObject, Qt, QTimer, QUrl, Signal, Slot
from PySide6.QtQuick import QQuickView
from PySide6.QtTest import QTest
from reference import bounding_box, qimage_to_pil, screenshot
from test_install import dry_run_log

from .luna_profile import horizontal_profile, vertical_profile
from .luna_qml import HARNESS, garbage_collection_paused, render_qml
from .test_luna_login import ALL_COLUMNS, FIELD_AREA, TEXT_FREE_COLUMNS, is_frame_colour, is_white, tolerated

PREVIEW_DIR = Path(
    "/tmp/claude-1000/-home-gedaiu-workspace-chicago95-plasma/6679116e-4ef6-4478-b441-c6cd1dc95f4a/scratchpad/luna-preview"
)
LOCK_SCREEN_UI = REPO / "lockscreen/lockscreen/LockScreenUi.qml"
FIELD_BOX = (496, 303, 656, 329)


class Authenticator(QObject):
    failed = Signal(int)

    def __init__(self):
        super().__init__()
        self.responses = []

    @Slot(str)
    def respond(self, password):
        self.responses.append(password)


@pytest.fixture(scope="module")
def welcome_reference():
    return screenshot("xplogin")


@pytest.fixture(scope="module")
def ours(qt_app):
    image = render_qml(qt_app, "LunaLockScreenHarness.qml", (800, 600), {"lockAuthenticator": Authenticator()})
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    image.save(PREVIEW_DIR / "lockscreen.png")
    return image


def typed_screen(qt_app, keys):
    authenticator = Authenticator()
    with garbage_collection_paused():
        view = QQuickView()
        view.rootContext().setContextProperty("lockAuthenticator", authenticator)
        view.setResizeMode(QQuickView.SizeRootObjectToView)
        view.resize(800, 600)
        view.setSource(QUrl.fromLocalFile(str(HARNESS / "LunaLockScreenHarness.qml")))
        view.show()
        QTimer.singleShot(300, qt_app.quit)
        qt_app.exec()
        for key in keys:
            QTest.keyClick(view, Qt.Key_Return if key == "\r" else key)
        QTimer.singleShot(100, qt_app.quit)
        qt_app.exec()
        image = qimage_to_pil(view.grabWindow())
        view.close()
    return authenticator, image


def test_screen_bands_match_the_welcome_reference_in_text_free_columns(
    welcome_reference,
    ours,
):
    rows = range(600)
    assert all(
        tolerated(vertical_profile(welcome_reference, [x], rows), vertical_profile(ours, [x], rows))
        for x in TEXT_FREE_COLUMNS
    )


@pytest.mark.parametrize(
    "rows", [[78], [79], [504], [505]], ids=["top rule 78", "top rule 79", "bottom 504", "bottom 505"]
)
def test_rule_rows_match_the_welcome_reference_within_12(welcome_reference, ours, rows):
    assert tolerated(
        horizontal_profile(welcome_reference, ALL_COLUMNS, rows), horizontal_profile(ours, ALL_COLUMNS, rows)
    )


def test_divider_profile_matches_the_welcome_reference_within_12(welcome_reference, ours):
    rows = range(80, 504)
    assert tolerated(vertical_profile(welcome_reference, [398], rows), vertical_profile(ours, [398], rows))


def test_tile_frame_box_is_within_2_pixels_of_the_reference(welcome_reference, ours):
    expected, actual = (
        bounding_box(image, is_frame_colour, (420, 500), (240, 340)) for image in (welcome_reference, ours)
    )
    assert all(abs(a - e) <= 2 for a, e in zip(actual, expected, strict=True)), (actual, expected)


def test_password_field_box_is_the_reference_white_box(welcome_reference, ours):
    assert (
        bounding_box(ours, is_white, *FIELD_AREA) == bounding_box(welcome_reference, is_white, *FIELD_AREA) == FIELD_BOX
    )


def test_typing_a_password_and_enter_hands_it_to_the_authenticator(qt_app):
    authenticator, _image = typed_screen(qt_app, "secret")
    assert authenticator.responses == []

    authenticator, _image = typed_screen(qt_app, "secret\r")
    assert authenticator.responses == ["secret"]


def test_typed_characters_show_as_dots_in_the_password_field(qt_app):
    _authenticator, image = typed_screen(qt_app, "secret")
    field = image.crop((500, 306, 650, 326))

    assert len(field.getcolors()) > 1


def test_lock_screen_ui_loads_the_luna_screen_only_when_the_look_is_luna():
    assert (
        'source: lockScreenUi.luna ? "luna/lockscreen/LunaLockScreen.qml" : "classic/ClassicLockScreen.qml"'
        in LOCK_SCREEN_UI.read_text()
    )


def test_setup_installs_the_luna_trees_next_to_each_other_inside_the_lockscreen_package(tmp_path):
    log = dry_run_log(tmp_path, "--components=lockscreen", "--look=luna").replace(str(tmp_path), "~")

    assert [
        f"lockscreen/luna/{tree}" in log
        for tree in ("qml/XpWordmark.qml", "sddm/LunaLogin.qml", "lockscreen/LunaLockScreen.qml")
    ] == [True, True, True]


def test_setup_writes_the_look_into_the_lock_screen_settings(tmp_path):
    run_bash_with_steps(tmp_path, f"SETUP_DRY_RUN=0 SETUP_START_MENU_STYLE=luna; write_lockscreen_settings {tmp_path}")

    assert (tmp_path / "settings.js").read_text().startswith('.pragma library\nvar look = "luna";\n')


def bright_pixel_count(image, area):
    return sum(count for count, colour in image.crop(area).getcolors() if min(colour[:3]) > 150)


def test_locked_screen_has_the_unlock_prompt_one_tile_and_no_session_link_or_help_text(ours):
    session_link, help_text, prompt = (465, 572, 620, 592), (465, 520, 760, 560), (90, 332, 365, 360)

    assert (
        bright_pixel_count(ours, session_link),
        bright_pixel_count(ours, help_text),
        bright_pixel_count(ours, prompt) > 0,
        bounding_box(ours, is_white, (490, 665), (301, 600)),
    ) == (0, 0, True, FIELD_BOX)
