"""Pixel tests: the window status bar against Windows 95's Control Panel and Windows 2000's Administrative Tools
(tests/references/win95controlpanel.png, tests/references/w2kadmin.png).

Colours are classed: W white, . the face, S the shadow grey, K black. Both originals agree on everything that does
not depend on the font: the panes start 2 rows down and reach the bar's bottom edge, each in a one pixel sunken
frame (shadow top and left, white bottom and right), two face columns apart; the last pane runs to the window's
right edge; the size grip is the same 13 by 13 square in its bottom right corner, cutting the pane's white edges.
Windows 95 uses our font's metrics (MS Sans Serif), so its bar is the one our heights and text follow.
"""

import pytest
from conftest import REPO, load_script
from PIL import Image
from reference import qimage_to_pil

WIN95_BAR = (4, 413, 440, 432)  # left, top, right, bottom (exclusive) of the original's status bar
W2K_BAR = (284, 410, 624, 430)
WIN95_TEXT = "Changes settings for your keyboard."


def classed(colour):
    brightness = sum(colour[:3]) // 3
    if brightness >= 245:
        return "W"
    if brightness < 40:
        return "K"
    if 100 <= brightness <= 150:
        return "S"
    return "." if 175 <= brightness <= 215 else "?"


def rows(image, box):
    left, top, right, bottom = box
    return ["".join(classed(image.getpixel((x, y))) for x in range(left, right)) for y in range(top, bottom)]


def runs(line):
    """A row's runs, each written out when it is one or two pixels long and as its class and * when longer."""
    pieces, start = [], 0
    for end in range(1, len(line) + 1):
        if end == len(line) or line[end] != line[start]:
            length = end - start
            pieces.append(line[start] * length if length <= 2 else line[start] + "*")
            start = end
    return "".join(pieces)


def bottom_right(lines, width, height):
    return [line[-width:] for line in lines[-height:]]


@pytest.fixture(scope="session")
def originals():
    return {
        name: rows(Image.open(REPO / f"tests/references/{name}.png").convert("RGB"), box)
        for name, box in (("win95controlpanel", WIN95_BAR), ("w2kadmin", W2K_BAR))
    }


@pytest.fixture
def ours(qt_app, tmp_path):
    control_panel = load_script("chicago95-control-panel")
    actions = control_panel.Actions(
        start_process=lambda program, arguments: None,
        run_setup=lambda parent, command: None,
        show_message=lambda parent, title, text: None,
        ask_to_apply=lambda parent: "cancel",
    )
    window = control_panel.ControlPanel(settings_path=tmp_path / "setup.conf", actions=actions)
    window.resize(WIN95_BAR[2] - WIN95_BAR[0], 300)
    window.show()
    window.status_message.setText(WIN95_TEXT)
    qt_app.processEvents()
    bar = window.statusBar()
    yield rows(qimage_to_pil(bar.grab().toImage()), (0, 0, bar.width(), bar.height()))
    window.close()


def test_the_originals_have_the_same_13_by_13_size_grip_in_their_last_panes_corner(originals):
    assert bottom_right(originals["win95controlpanel"], 16, 14) == bottom_right(originals["w2kadmin"], 16, 14)


def test_our_size_grip_and_the_corner_round_it_match_the_original_pixel_for_pixel(ours, originals):
    assert bottom_right(ours, 16, 17) == bottom_right(originals["win95controlpanel"], 16, 17)


def test_our_status_bar_rows_match_the_original_down_an_empty_part_of_a_pane(ours, originals):
    def down(lines, x):
        return "".join(line[x] for line in lines)

    assert down(ours, -40) == down(originals["win95controlpanel"], -40)


@pytest.mark.parametrize("edge", ["top", "bottom"])
def test_our_three_panes_are_parted_and_end_like_the_windows_2000_originals(ours, originals, edge):
    row = {"top": 2, "bottom": -1}[edge]
    assert runs(ours[row]) == runs(originals["w2kadmin"][row])


def test_our_status_text_ink_sits_where_the_originals_does(ours, originals):
    def ink(lines):
        inked = [(x, y) for y, line in enumerate(lines) for x, mark in enumerate(line[:200]) if mark == "K"]
        return (min(x for x, _ in inked), min(y for _, y in inked), max(y for _, y in inked))

    assert ink(ours) == ink(originals["win95controlpanel"])
