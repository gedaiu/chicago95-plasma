"""Our taskbar's pieces against the originals' taskbars (win95desktop3.png, win98notepad.png, w2kadmin.png).

Plasma lays the taskbar out at run time, so the pieces Chicago95 draws are compared one by one at the
originals' sizes: the panel's top edge and face (plasma-style panel-background.svg), the Start button
(the Start plasmoid's StartButton.qml), raised and pressed task buttons (tasks.svg "normal" and "focus"),
each with the look's colours as chicago95-sync-colors writes them. Icons and labels are the user's
programs' and are masked; the pressed button's checkerboard is compared in either phase (the originals
align it to the screen, Plasma to the button).
"""
import configparser
import shutil
import subprocess
import sys

import pytest

from aurorae_model import LOOKS
from conftest import REPO, needs_ui_font
from framesvg import render_frame
from reference import bounding_box, close, differing_pixels, qimage_to_pil, screenshot

TASKBARS = {"1995": "win95desktop3", "1998": "win98notepad", "2000": "w2kadmin"}
TOP, HEIGHT = 452, 28
# look: (Start button's left, right), [(task button left, right, pressed)], inclusive, from each screenshot.
BUTTONS = {
    "1995": ((2, 55), [(60, 154, False), (158, 252, False), (256, 350, True), (354, 448, False)]),
    "1998": ((2, 55), [(176, 335, False), (339, 498, True)]),
    "2000": ((2, 56), [(155, 314, True), (318, 477, False)]),
}
BUTTON_TOP, BUTTON_HEIGHT = 4, 22             # in the taskbar
LOGO = (4, 4, 20, 18)                         # in the Start button
TASK_ICON_AND_LABEL = (3, 3, -3, -3)          # inset from the task button's edges
PRESSED_INSIDE = (2, 3, -2, -2)               # the pressed button's checkerboard, compared in either phase below
TASK_LABEL_FROM = 22                          # right of the task button's icon


def taskbar(look):
    image = screenshot(TASKBARS[look])
    return image.crop((0, TOP, image.width, TOP + HEIGHT))


@pytest.fixture(scope="module")
def styles(tmp_path_factory):
    """Our Plasma style per look, written by the generator with the look's bevel colours."""
    built = {}
    for look, colours in LOOKS.items():
        out = tmp_path_factory.mktemp(f"plasma-style-{look}")
        shutil.copy(REPO / "plasma-style/theme/colors", out / "colors")   # as installed: the generator rewrites it
        arguments = [f"--{key}={colours[key]}" for key in ("face", "light", "shadow", "dark")]
        subprocess.run([sys.executable, str(REPO / "plasma-style/make_chicago95_plasmastyle.py"), "--out", str(out), *arguments],
                       check=True, capture_output=True)
        built[look] = out
    return built


PLASMOIDS = REPO / "plasmoids"
STRIP = """import QtQuick
import "%s"
Rectangle {
    width: 640; height: %d
    %s { objectName: "item"; x: %d; y: 2; width: implicitWidth; height: parent.height - 4 }   // Plasma's applet rows: 2 to 25
}
"""


def render_on_strip(qt_app, folder, plasmoid, component, x, face, properties, width=None):
    """A plasmoid's QML component on a taskbar-high strip of the face colour, bottom-aligned at x; also
    returns the component's own width once laid out."""
    from PySide6.QtCore import QTimer, QUrl
    from PySide6.QtQuick import QQuickItem, QQuickView
    (folder / "strip.qml").write_text(STRIP % ((PLASMOIDS / plasmoid / "contents/ui").as_uri(), HEIGHT, component, x))
    view = QQuickView()
    view.setSource(QUrl.fromLocalFile(str(folder / "strip.qml")))
    assert [error.toString() for error in view.errors()] == []
    view.rootObject().setProperty("color", face)
    item = view.rootObject().findChild(QQuickItem, "item")
    for key, value in properties.items():
        item.setProperty(key, value)
    if width:
        item.setProperty("width", width)
    view.show()
    QTimer.singleShot(200, qt_app.quit)
    qt_app.exec()
    image = qimage_to_pil(view.grabWindow())
    natural = int(item.property("implicitWidth"))   # read once the layout has run
    view.close()
    return image, natural


def start_button(qt_app, look, folder, width=None):
    """StartButton.qml with "Start" and the flag, in the look's colours, at the originals' x."""
    from PySide6.QtCore import QUrl
    colours = LOOKS[look]
    properties = {key: colours[key] for key in ("face", "light", "shadow", "dark")}
    properties.update(look=look, text="Start", logoSource=QUrl.fromLocalFile(str(PLASMOIDS / "org.chicago95.start/contents/images/logo-flag-16.png")))
    return render_on_strip(qt_app, folder, "org.chicago95.start", "StartButton", 2, colours["face"], properties, width)


@pytest.mark.parametrize("look", TASKBARS)
def test_taskbar_is_28_pixels_tall_with_a_light_and_a_white_line_on_top(styles, look):
    original = taskbar(look)
    ours = render_frame(styles[look] / "widgets/panel-background.svg", "", original.width, HEIGHT, borders={"top"})
    rows = (0, 1, 2, 3, HEIGHT - 2, HEIGHT - 1)
    assert all(close(ours.getpixel((x, y)), original.getpixel((x, y))) for x in range(original.width) for y in rows)


@pytest.mark.parametrize("look", TASKBARS)
def test_plasma_style_colours_take_the_looks_face(styles, look):
    """Plasma's widgets (the Start button, the clock) take their face from the style's colours."""
    colours = configparser.ConfigParser(interpolation=None)
    colours.optionxform = str
    colours.read(styles[look] / "colors")
    face = ",".join(str(int(LOOKS[look]["face"][i:i + 2], 16)) for i in (1, 3, 5))
    groups = ("Colors:Window", "Colors:Button", "Colors:Complementary", "Colors:Header")
    assert {(group, key): colours[group][key] for group in groups for key in ("BackgroundNormal", "BackgroundAlternate")} == \
        {(group, key): face for group in groups for key in ("BackgroundNormal", "BackgroundAlternate")}


def test_panel_layout_makes_the_taskbar_28_pixels_tall():
    assert "panel.height = 28;" in (REPO / "plasmoids/panel-layout.js").read_text()


@needs_ui_font
@pytest.mark.parametrize("look", TASKBARS)
def test_start_button_matches_the_original(qt_app, look, tmp_path):
    original = taskbar(look)
    (left, right), _ = BUTTONS[look]
    ours, _ = start_button(qt_app, look, tmp_path, width=right - left + 1)
    box = (left, BUTTON_TOP, right + 1, BUTTON_TOP + BUTTON_HEIGHT)
    # The lettering is compared by its box below: the original's letters are spaced unevenly.
    masks = [LOGO, (LOGO[2], 3, right - left - 2, BUTTON_HEIGHT - 3)]
    count = differing_pixels(original.crop(box), ours.crop(box), masks, tmp_path / "start-diff.png", threshold=0.1)
    assert count == 0, f"{count} pixels differ; see {tmp_path}"


@pytest.mark.parametrize("look", TASKBARS)
def test_start_logo_covers_the_originals_16_by_14_box(qt_app, look, tmp_path):
    """The flag's own art differs from the original's; its ink must fill the same box."""
    original = taskbar(look)
    (left, right), _ = BUTTONS[look]
    ours, _ = start_button(qt_app, look, tmp_path, width=right - left + 1)

    def ink(image):
        return bounding_box(image, lambda c: max(c) - min(c) > 60 or sum(c) < 100, (left + 3, left + LOGO[2] + 1), (BUTTON_TOP + 2, BUTTON_TOP + BUTTON_HEIGHT - 2))
    assert ink(ours) == ink(original)


@needs_ui_font
@pytest.mark.parametrize("look", ["1995", "1998"])
def test_start_lettering_covers_the_originals(qt_app, look, tmp_path):
    original = taskbar(look)
    (left, right), _ = BUTTONS[look]
    ours, _ = start_button(qt_app, look, tmp_path, width=right - left + 1)

    def ink(image):
        return bounding_box(image, lambda c: sum(c) < 100, (left + LOGO[2], right - 2), (BUTTON_TOP + 2, BUTTON_TOP + BUTTON_HEIGHT - 2))
    assert ink(ours) == ink(original)


@needs_ui_font
@pytest.mark.parametrize("look", TASKBARS)
def test_start_button_is_as_wide_as_the_original(qt_app, look, tmp_path):
    """2000's lettering is wider: its button has a pixel more face after the text."""
    (left, right), _ = BUTTONS[look]
    _, width = start_button(qt_app, look, tmp_path)
    assert width == right - left + 1


def task_buttons(look):
    return [(left, right, pressed) for left, right, pressed in BUTTONS[look][1]]


@pytest.mark.parametrize("look", TASKBARS)
def test_task_button_bevels_match_the_original(styles, look, tmp_path):
    original = taskbar(look)
    for left, right, pressed in task_buttons(look):
        width = right - left + 1
        ours = render_frame(styles[look] / "widgets/tasks.svg", "focus" if pressed else "normal", width, BUTTON_HEIGHT)
        box = (left, BUTTON_TOP, right + 1, BUTTON_TOP + BUTTON_HEIGHT)
        inset = PRESSED_INSIDE if pressed else TASK_ICON_AND_LABEL
        masks = [(inset[0], inset[1], width + inset[2], BUTTON_HEIGHT + inset[3])]
        count = differing_pixels(original.crop(box), ours, masks, tmp_path / f"task-{left}-diff.png", threshold=0.1)
        assert count == 0, f"button at {left}: {count} pixels differ; see {tmp_path}"


@pytest.mark.parametrize("look", TASKBARS)
def test_pressed_task_button_has_a_white_row_then_a_checkerboard(styles, look):
    """Inside the sunken edge: a white row along the top, then white and face alternating, compared on
    the rows between the label and the bottom edge, right of the icon, in whichever phase the original's falls."""
    original = taskbar(look)
    left, right, _ = next(button for button in task_buttons(look) if button[2])
    width = right - left + 1
    ours = render_frame(styles[look] / "widgets/tasks.svg", "focus", width, BUTTON_HEIGHT)
    assert all(close(ours.getpixel((x, 2)), original.getpixel((left + x, BUTTON_TOP + 2))) for x in range(2, width - 2))
    rows = (BUTTON_HEIGHT - 4, BUTTON_HEIGHT - 3)
    for phase in (0, 1):
        if all(close(ours.getpixel((x + phase, y)), original.getpixel((left + x, BUTTON_TOP + y)))
               for x in range(TASK_LABEL_FROM, width - 3) for y in rows):
            return
    pytest.fail("the checkerboard differs in both phases")


# look: [(the separator's etched line's x, the next item's left)] in each screenshot
SEPARATORS = {"1998": [(58, 72 - 3), (165, 176)], "2000": [(60, 74 - 3), (144, 155)]}


@pytest.mark.parametrize("look", SEPARATORS)
def test_separators_match_the_originals_etched_line_and_grip(qt_app, look, tmp_path):
    """From the etched line on: shadow and white, 2px of face, the grip, then face up to the next item
    (the quick launch's first icon cell, 3px before its icon, or a task button)."""
    original = taskbar(look)
    lead = 2
    ours, width = render_on_strip(qt_app, tmp_path, "org.chicago95.tasks", "Separator", 0, LOOKS[look]["face"], {})
    for etched, next_item in SEPARATORS[look]:
        assert etched + width - lead == next_item, "the separator should end where the next item starts"
        for dx in range(width - lead):
            for y in range(2, HEIGHT):   # below the panel's own top lines
                assert close(ours.getpixel((lead + dx, y)), original.getpixel((etched + dx, y))), (etched, dx, y)


TRAYS = {"1995": (557, 637), "1998": (540, 637), "2000": (544, 637)}


@pytest.mark.parametrize("look", TRAYS)
def test_tray_box_matches_the_originals_edges(qt_app, look, tmp_path):
    original = taskbar(look)
    left, right = TRAYS[look]
    ours, _ = render_on_strip(qt_app, tmp_path, "org.chicago95.trayframe", "TrayBox", left, LOOKS[look]["face"], {}, width=right - left + 1)
    edges = [(x, y) for x in range(left - 1, right + 2) for y in range(2, HEIGHT)   # below the panel's own top lines
             if x in (left - 1, left, right, right + 1) or y in (BUTTON_TOP - 1, BUTTON_TOP, BUTTON_TOP + BUTTON_HEIGHT - 1, BUTTON_TOP + BUTTON_HEIGHT)]
    assert all(close(ours.getpixel(point), original.getpixel(point)) for point in edges)


CLOCKS = {"1995": ("6:23 PM", 38), "1998": ("12:46 PM", 44), "2000": ("10:18 PM", None)}   # 2000's is Tahoma
CLOCK_INK_HEIGHT = 9


@needs_ui_font
@pytest.mark.parametrize("look", CLOCKS)
def test_clock_lettering_is_the_originals_size(qt_app, look):
    """The clock plasmoid's font, measured on the original's time: 9px tall, as wide within 1px."""
    import re
    from PySide6.QtGui import QFont, QFontMetrics
    clock = (REPO / "plasmoids/org.chicago95.clock/contents/ui/main.qml").read_text()
    font = QFont(re.search(r'font.family: "([^"]+)"', clock).group(1))
    font.setPixelSize(int(re.search(r"font.pixelSize: (\d+)", clock).group(1)))
    font.setStyleStrategy(QFont.NoAntialias)
    text, width = CLOCKS[look]
    ink = QFontMetrics(font).tightBoundingRect(text)
    assert ink.height() - 1 <= CLOCK_INK_HEIGHT <= ink.height(), ink
    assert width is None or abs(ink.width() - width) <= 1, (ink, width)
