"""Our Shut Down dialogs against the originals.

2000 (w2kshutdown.png) is full size, so its client area is compared pixel by pixel outside the banner
artwork, icon and lettering, plus the measured layout. 1995 and 1998 are half-size thumbnails
(win95shutdownsm.png, win98shutsm.png), so for those the client size and option spacing are measured
at half scale and compared within a pixel of the thumbnail.
"""

import pytest
from conftest import needs_ui_font
from reference import (
    LOOK_2000_KDEGLOBALS,
    bounding_box,
    close,
    differing_pixels,
    installed_look,
    qimage_to_pil,
    screenshot,
)

CLIENT_2000 = (115, 91, 524, 337)
DIALOG_2000 = (111, 70, 528, 339)  # the whole dialog: its 3px frame, the 18px title, the client area
BODY_2000 = (CLIENT_2000[0] - DIALOG_2000[0], CLIENT_2000[1] - DIALOG_2000[1])  # the client area in the dialog
FRAME, TITLE = 3, 18
# The dialogs with their frames, measured on the half-size thumbnails' frame edges (x 73.5-246 and
# y 64-175 for 1995, x 78.5-240 and y 49.5-146 for 1998), doubled.
FRAMED_SIZES = {"1995": (346, 224), "1998": (324, 196)}
# Thumbnail crop of the dialog, and the rows (in the crop) where the option buttons are.
# The 2000 banner, in client coordinates: the generated mark (its logo box left out, since the logo is the
# user's; the name's lettering too, which sits over the mark's blue glow), and where each line of
# lettering is searched for.
BANNER_MARK = (36, 4, 160, 68)
BANNER_LOGO = (48, 12, 96, 52)
BANNER_LETTERING = (100, 0, 409, 46)
MARK_BLOCK, MARK_TOLERANCE = 4, 45
BANNER_LINES = {
    "company": (98, 4, 175, 15),
    "name": (98, 18, 345, 46),
    "edition": (150, 46, 345, 70),
    "corner": (332, 2, 409, 22),
}
LETTERING_SLACK = 2
THUMBNAILS = {
    "1995": ("win95shutdownsm", (74, 60, 246, 180), (36, 78)),
    "1998": ("win98shutsm", (80, 46, 240, 152), (36, 74)),
}


def dialog_for(shutdown, qt_app, style, banner="Chicago95", company=""):
    dialog = shutdown.ShutDownDialog(
        {
            "style": style,
            "bannerText": banner,
            "osName": banner,
            "osCompany": company,
            "edition": "Professional",
            "osLogo": "",
            "companyLogo": "",
        }
    )
    dialog.show()
    qt_app.processEvents()
    return dialog


@pytest.fixture(scope="module")
def whole_2000(shutdown, qt_app, tmp_path_factory):
    """Our 2000 dialog with the frame and title it draws, its close button from our 2000 decoration."""
    import chicago95ui
    from aurorae_model import build_theme

    chicago95ui.DECORATION = build_theme(tmp_path_factory.mktemp("aurorae-2000"), "2000")
    with installed_look(qt_app, "[StartMenu]\nstyle=2000\n", LOOK_2000_KDEGLOBALS):
        dialog = dialog_for(shutdown, qt_app, "2000", banner="Windows 2000", company="Microsoft")
        image = qimage_to_pil(dialog.grab().toImage())
        dialog.close()
    return image


@pytest.fixture(scope="module")
def ours_2000(whole_2000):
    """The client area, inside the frame and under the title."""
    return whole_2000.crop((*BODY_2000, BODY_2000[0] + 409, BODY_2000[1] + 246))


@pytest.fixture(scope="module")
def reference_2000():
    return screenshot("w2kshutdown").crop(CLIENT_2000)


def test_2000_dialog_is_417_by_269_with_its_frame_and_title_like_the_original(whole_2000):
    assert whole_2000.size == (DIALOG_2000[2] - DIALOG_2000[0], DIALOG_2000[3] - DIALOG_2000[1]) == (417, 269)


def test_2000_frame_and_close_button_match_the_original_pixel_for_pixel(whole_2000):
    original = screenshot("w2kshutdown").crop(DIALOG_2000)
    w, h = original.size
    ring = [(x, y) for x in range(w) for y in range(h) if min(x, y, w - 1 - x, h - 1 - y) < FRAME]
    close_button = [(x, y) for x in range(w - FRAME - 2 - 16, w - FRAME - 2) for y in range(FRAME + 2, FRAME + 2 + 14)]
    assert [
        point for point in ring + close_button if not close(whole_2000.getpixel(point), original.getpixel(point))
    ] == []


def test_2000_title_shades_like_the_original_and_holds_its_end_colour_behind_the_button(whole_2000):
    """Column averages below the caption's lettering (rows 17 to 20), every 12px across the title."""
    original = screenshot("w2kshutdown").crop(DIALOG_2000)

    def column(image, x):
        pixels = [image.getpixel((x, y)) for y in range(FRAME + 14, FRAME + TITLE)]
        return tuple(sum(pixel[channel] for pixel in pixels) / len(pixels) for channel in range(3))

    xs = range(FRAME, original.width - FRAME, 12)
    assert all(close(column(whole_2000, x), column(original, x), 12) for x in xs), [
        (x, column(whole_2000, x), column(original, x)) for x in xs
    ]


def test_2000_strip_glows_like_the_original(reference_2000, ours_2000):
    xs = range(5, 400, 40)
    expected = [reference_2000.getpixel((x, 75)) for x in xs]
    actual = [ours_2000.getpixel((x, 75)) for x in xs]
    assert all(close(a, e, 40) for a, e in zip(actual, expected)), list(zip(xs, actual, expected))


def block_average(image, x, y):
    pixels = [image.getpixel((x + dx, y + dy)) for dx in range(MARK_BLOCK) for dy in range(MARK_BLOCK)]
    return tuple(sum(pixel[channel] for pixel in pixels) / len(pixels) for channel in range(3))


def overlaps(box, x, y):
    return box[0] - MARK_BLOCK < x < box[2] and box[1] - MARK_BLOCK < y < box[3]


def test_2000_banner_mark_matches_the_original_within_45_levels_per_4px_block(reference_2000, ours_2000):
    blocks = [
        (x, y)
        for y in range(BANNER_MARK[1], BANNER_MARK[3], MARK_BLOCK)
        for x in range(BANNER_MARK[0], BANNER_MARK[2], MARK_BLOCK)
        if not overlaps(BANNER_LOGO, x, y) and not overlaps(BANNER_LETTERING, x, y)
    ]
    differing = [
        (x, y)
        for x, y in blocks
        if max(abs(a - b) for a, b in zip(block_average(reference_2000, x, y), block_average(ours_2000, x, y)))
        > MARK_TOLERANCE
    ]
    assert differing == []


@pytest.mark.parametrize("line", BANNER_LINES.values(), ids=BANNER_LINES.keys())
def test_2000_banner_lettering_covers_the_original_lines_within_2_pixels(reference_2000, ours_2000, line):
    def ink(image):
        return bounding_box(image, lambda c: sum(c) < 250, (line[0], line[2]), (line[1], line[3]))

    expected, actual = ink(reference_2000), ink(ours_2000)
    assert all(abs(a - e) <= LETTERING_SLACK for a, e in zip(actual, expected)), (actual, expected)


def button_frames(image):
    """Each push button's black bottom edge, as (left, right, y), in the button row."""
    frames = []
    dark = lambda c: sum(c) < 220  # black on 1995/1998, #404040 on 2000
    y = max(y for y in range(200, 240) if sum(1 for x in range(image.width) if dark(image.getpixel((x, y)))) > 60)
    run = None
    for x in range(image.width + 1):
        edge = x < image.width and dark(image.getpixel((x, y)))
        if edge and run is None:
            run = x
        if not edge and run is not None:
            if x - run > 50:
                frames.append((run, x - 1, y))
            run = None
    return frames


def test_2000_buttons_sit_where_the_original_puts_them(reference_2000, ours_2000):
    assert button_frames(ours_2000) == button_frames(reference_2000)


def test_2000_dropdown_frame_matches(reference_2000, ours_2000):
    def frame(image):
        return bounding_box(
            image, lambda c: close(c, (132, 132, 132), 16) or close(c, (128, 128, 128), 16), (60, 340), (105, 135)
        )

    assert frame(ours_2000) == frame(reference_2000)


@needs_ui_font
def test_2000_everything_but_artwork_and_lettering_matches(reference_2000, ours_2000, tmp_path):
    masks = [
        (0, 1, 409, 72),  # banner artwork and name
        (0, 72, 409, 78),  # strip: dithered in the 256-colour original; its colours have their own test
        (15, 82, 60, 125),  # icon
        (60, 86, 400, 106),  # question
        (314, 124, 334, 152),  # the original screenshot's mouse pointer
        (67, 112, 330, 131),  # dropdown contents and focus highlight
        (60, 133, 409, 175),  # description (same words with OS name "Windows"; letter shapes differ)
        (163, 211, 409, 234),
    ]  # button captions sit inside the compared button frames
    count = differing_pixels(reference_2000, ours_2000, masks, tmp_path / "shutdown-2000-diff.png", threshold=0.15)
    assert count == 0, f"{count} pixels differ; see {tmp_path}"


def thumbnail_dialog(style):
    """The dialog cut from its half-size thumbnail at its frame: the face found in the thumbnail, and
    around it the frame (3px, a pixel and a half there) and the title (18px, 9)."""
    name, box, _options = THUMBNAILS[style]
    inside = screenshot(name).crop(box)
    face = lambda c: all(abs(v - 192) < 14 for v in c)
    rows = [
        y
        for y in range(inside.height)
        if sum(face(inside.getpixel((x, y))) for x in range(inside.width)) > inside.width * 0.6
    ]
    cols = [
        x
        for x in range(inside.width)
        if sum(face(inside.getpixel((x, y))) for y in range(inside.height)) > inside.height * 0.5
    ]
    return screenshot(name).crop(
        (box[0] + cols[0] - 2, box[1] + rows[0] - 13, box[0] + cols[-1] + 3, box[1] + rows[-1] + 3)
    )


def text_rows(image):
    """The first row of each line of lettering and of the buttons in a half-size dialog, below the title
    and right of the icon: the question, the four options, then the buttons."""
    dark = [
        sum(1 for x in range(36, image.width - 8) if sum(image.getpixel((x, y))) < 330) for y in range(image.height)
    ]
    return [y for y in range(14, image.height - 3) if dark[y] >= 2 and dark[y - 1] < 2]


def thumbnail_layout(name, box, option_rows):
    image = screenshot(name).crop(box)
    w, h = image.size
    face = lambda c: all(abs(v - 192) < 14 for v in c)
    rows = [y for y in range(h) if sum(1 for x in range(w) if face(image.getpixel((x, y)))) > w * 0.6]
    cols = [x for x in range(w) if sum(1 for y in range(h) if face(image.getpixel((x, y)))) > h * 0.5]
    radio_rows = [y for y in range(*option_rows) if any(sum(image.getpixel((x, y))) > 700 for x in range(20, 32))]
    groups = [y for i, y in enumerate(radio_rows) if i == 0 or y - radio_rows[i - 1] > 2]
    return dict(width=(cols[-1] - cols[0] + 1) * 2, height=(rows[-1] - rows[0] + 1) * 2, options=groups)


@pytest.mark.parametrize("style", ["1995", "1998"])
def test_radio_dialog_with_its_frame_has_the_originals_size(shutdown, qt_app, style):
    dialog = dialog_for(shutdown, qt_app, style)
    size = (dialog.width(), dialog.height())
    dialog.close()
    assert all(abs(a - e) <= 2 for a, e in zip(size, FRAMED_SIZES[style])), (size, FRAMED_SIZES[style])


@needs_ui_font
@pytest.mark.parametrize("style", ["1995", "1998", "2000"])
def test_dialog_title_has_no_icon_and_its_caption_starts_where_the_icon_would(shutdown, qt_app, style):
    """The originals' dialogs show no icon: the caption's first stroke is 5px from the dialog's edge
    (2px into the title), as on 2000's full-size original."""
    original = screenshot("w2kshutdown").crop(DIALOG_2000)
    dialog = dialog_for(shutdown, qt_app, style)
    ours = qimage_to_pil(dialog.grab().toImage())
    dialog.close()

    def caption_left(image):
        return min(
            x for x in range(FRAME, 60) for y in range(FRAME, FRAME + TITLE) if min(image.getpixel((x, y))) > 230
        )

    assert caption_left(ours) == caption_left(original) == 5


@pytest.mark.parametrize("style", ["1995", "1998"])
def test_radio_dialog_lists_four_options_spaced_like_the_original(shutdown, qt_app, style):
    expected = thumbnail_layout(*THUMBNAILS[style])["options"]
    expected_pitch = (expected[-1] - expected[0]) * 2 / (len(expected) - 1)
    dialog = dialog_for(shutdown, qt_app, style)
    tops = [radio.mapTo(dialog, radio.rect().topLeft()).y() for radio in dialog.radios]
    pitch = (tops[-1] - tops[0]) / (len(tops) - 1)
    dialog.close()
    assert (len(tops), len(expected)) == (4, 4) and abs(pitch - expected_pitch) <= 2, (pitch, expected_pitch)


@needs_ui_font
@pytest.mark.parametrize("style", ["1995", "1998"])
def test_radio_dialog_rows_sit_where_the_originals_do(shutdown, qt_app, style):
    """The question, the four options and the buttons, each on the original's row within one row of the
    half-size thumbnail: ours halved the way a thumbnail is made, each pixel the average of four."""
    from PIL import Image

    dialog = dialog_for(shutdown, qt_app, style)
    ours = qimage_to_pil(dialog.grab().toImage())
    dialog.close()
    halved = ours.resize((ours.width // 2, ours.height // 2), Image.BOX)
    expected, actual = text_rows(thumbnail_dialog(style))[:6], text_rows(halved)[:6]
    assert len(actual) == 6 and all(abs(a - e) <= 1 for a, e in zip(actual, expected)), (actual, expected)


def test_2000_description_names_the_os_from_the_look(shutdown, qt_app):
    dialog = dialog_for(shutdown, qt_app, "2000", banner="Fedora 44")
    text = dialog.description.text()
    dialog.close()
    assert text == "Ends your session and shuts down Fedora so that you can safely turn off power."


@pytest.mark.parametrize("style", ["1995", "1998"])
def test_radio_dialog_opens_with_the_checked_option_focused(shutdown, qt_app, style):
    """The originals draw the focus rectangle around the chosen option, Shut down."""
    dialog = dialog_for(shutdown, qt_app, style)
    qt_app.processEvents()
    focused = dialog.focusWidget()
    dialog.close()
    assert focused is not None and focused.isChecked() and "Shut down" in focused.text().replace("&", "")
