"""Our Shut Down dialogs against the originals.

2000 (w2kshutdown.png) is full size, so its client area is compared pixel by pixel outside the banner
artwork, icon and lettering, plus the measured layout. 1995 and 1998 are half-size thumbnails
(win95shutdownsm.png, win98shutsm.png), so for those the client size and option spacing are measured
at half scale and compared within a pixel of the thumbnail.
"""
import pytest

from conftest import needs_ui_font
from reference import LOOK_2000_KDEGLOBALS, bounding_box, close, differing_pixels, installed_look, qimage_to_pil, screenshot

CLIENT_2000 = (115, 91, 524, 337)
# Thumbnail crop of the dialog, and the rows (in the crop) where the option buttons are.
# The 2000 banner, in client coordinates: the generated mark (its logo box left out, since the logo is the
# user's; the name's lettering too, which sits over the mark's blue glow), and where each line of
# lettering is searched for.
BANNER_MARK = (36, 4, 160, 68)
BANNER_LOGO = (48, 12, 96, 52)
BANNER_LETTERING = (100, 0, 409, 46)
MARK_BLOCK, MARK_TOLERANCE = 4, 45
BANNER_LINES = {"company": (98, 4, 175, 15), "name": (98, 18, 345, 46), "edition": (150, 46, 345, 70), "corner": (332, 2, 409, 22)}
LETTERING_SLACK = 2
THUMBNAILS = {"1995": ("win95shutdownsm", (74, 60, 246, 180), (36, 78)), "1998": ("win98shutsm", (80, 46, 240, 152), (36, 74))}


def dialog_for(shutdown, qt_app, style, banner="Chicago95", company=""):
    dialog = shutdown.ShutDownDialog({"style": style, "bannerText": banner, "osName": banner, "osCompany": company,
                                      "edition": "Professional", "osLogo": "", "companyLogo": ""})
    dialog.show()
    qt_app.processEvents()
    return dialog


@pytest.fixture(scope="module")
def ours_2000(shutdown, qt_app):
    with installed_look(qt_app, "[StartMenu]\nstyle=2000\n", LOOK_2000_KDEGLOBALS):
        dialog = dialog_for(shutdown, qt_app, "2000", banner="Windows 2000", company="Microsoft")
        image = qimage_to_pil(dialog.grab().toImage())
        dialog.close()
    return image


@pytest.fixture(scope="module")
def reference_2000():
    return screenshot("w2kshutdown").crop(CLIENT_2000)


def test_2000_dialog_is_409_by_246_like_the_original(reference_2000, ours_2000):
    assert ours_2000.size == reference_2000.size == (409, 246)


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
    blocks = [(x, y) for y in range(BANNER_MARK[1], BANNER_MARK[3], MARK_BLOCK) for x in range(BANNER_MARK[0], BANNER_MARK[2], MARK_BLOCK)
              if not overlaps(BANNER_LOGO, x, y) and not overlaps(BANNER_LETTERING, x, y)]
    differing = [(x, y) for x, y in blocks
                 if max(abs(a - b) for a, b in zip(block_average(reference_2000, x, y), block_average(ours_2000, x, y))) > MARK_TOLERANCE]
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
    dark = lambda c: sum(c) < 220   # black on 1995/1998, #404040 on 2000
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
        return bounding_box(image, lambda c: close(c, (132, 132, 132), 16) or close(c, (128, 128, 128), 16), (60, 340), (105, 135))
    assert frame(ours_2000) == frame(reference_2000)


@needs_ui_font
def test_2000_everything_but_artwork_and_lettering_matches(reference_2000, ours_2000, tmp_path):
    masks = [(0, 1, 409, 72),            # banner artwork and name
             (0, 72, 409, 78),           # strip: dithered in the 256-colour original; its colours have their own test
             (15, 82, 60, 125),          # icon
             (60, 86, 400, 106),         # question
             (314, 124, 334, 152),       # the original screenshot's mouse pointer
             (67, 112, 330, 131),        # dropdown contents and focus highlight
             (60, 133, 409, 175),        # description (same words with OS name "Windows"; letter shapes differ)
             (163, 211, 409, 234)]       # button captions sit inside the compared button frames
    count = differing_pixels(reference_2000, ours_2000, masks, tmp_path / "shutdown-2000-diff.png", threshold=0.15)
    assert count == 0, f"{count} pixels differ; see {tmp_path}"


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
def test_radio_dialog_has_the_originals_size(shutdown, qt_app, style):
    expected = thumbnail_layout(*THUMBNAILS[style])
    dialog = dialog_for(shutdown, qt_app, style)
    assert abs(dialog.width() - expected["width"]) <= 4 and abs(dialog.height() - expected["height"]) <= 4, (dialog.size(), expected)
    dialog.close()


@pytest.mark.parametrize("style", ["1995", "1998"])
def test_radio_dialog_lists_four_options_spaced_like_the_original(shutdown, qt_app, style):
    expected = thumbnail_layout(*THUMBNAILS[style])["options"]
    expected_pitch = (expected[-1] - expected[0]) * 2 / (len(expected) - 1)
    dialog = dialog_for(shutdown, qt_app, style)
    tops = [radio.mapTo(dialog, radio.rect().topLeft()).y() for radio in dialog.radios]
    pitch = (tops[-1] - tops[0]) / (len(tops) - 1)
    dialog.close()
    assert (len(tops), len(expected)) == (4, 4) and abs(pitch - expected_pitch) <= 2, (pitch, expected_pitch)


def test_2000_description_names_the_os_from_the_look(shutdown, qt_app):
    dialog = dialog_for(shutdown, qt_app, "2000", banner="Fedora 44")
    text = dialog.description.text()
    dialog.close()
    assert text == "Ends your session and shuts down Fedora so that you can safely turn off power."
