"""Our 2000 login screen against the original log on dialog (w2klogon.png, 640x480).

The dialog's frame, title bar, fields and buttons must match pixel for pixel outside the lettering; the
banner, drawn by the Shut Down banner's code (tests/test_shutdown_reference.py tests its artwork), must
put each line of lettering where the original does. The original's Options show one row (a dial-up
check box); ours show two (the session list, then the Num Lock and Show password boxes), so the dialog
is compared above those rows as it is, and below them one row (27 pixels) lower.
"""

import pytest
from conftest import needs_ui_font
from login_theme import render_login
from reference import LOOK_2000_KDEGLOBALS, bounding_box, close, differing_pixels, installed_look, screenshot

DIALOG = (111, 74, 528, 330)
OPTION_ROWS_TOP, ORIGINAL_ROWS_BOTTOM, EXTRA_ROW = 258, 282, 27
LOOK = {
    "style": "2000",
    "bannerText": "Windows 2000",
    "osName": "Windows 2000",
    "osCompany": "Microsoft",
    "edition": "Professional",
    "osLogo": "",
    "companyLogo": "",
    "tagline": "Built on NT Technology",
}
BANNER_LINES = {
    "company": (212, 98, 300, 112),
    "name": (212, 110, 480, 142),
    "edition": (280, 143, 460, 165),
    "tagline": (280, 166, 460, 182),
    "corner": (440, 98, 522, 118),
}
LETTERING_SLACK = 2
MASKS = [
    (114, 96, 525, 189),  # banner: its artwork and lettering have their own tests
    (116, 78, 300, 93),  # title text
    (118, 204, 190, 276),  # labels
    (200, 206, 440, 249),  # field contents and the original's mouse pointer
    (198, 294, 516, 315),
]  # button captions (the frames are compared)


@pytest.fixture(scope="module")
def reference():
    return screenshot("w2klogon")


@pytest.fixture(scope="module")
def ours(qt_app, shutdown, tmp_path_factory):
    folder = tmp_path_factory.mktemp("login")
    shutdown.render_login_banner(LOOK, folder / "banner.png")
    with installed_look(qt_app, "[StartMenu]\nstyle=2000\n", LOOK_2000_KDEGLOBALS):
        return render_login(
            qt_app,
            folder,
            banner=folder / "banner.png",
            show_options=True,
            loginStyle="2000",
            titleActive="#0A246A,#A6CAF0",
            loginTitle="Log On to Windows",
        )


def masks_in(area):
    return [(left - area[0], top - area[1], right - area[0], bottom - area[1]) for left, top, right, bottom in MASKS]


@needs_ui_font
def test_dialog_above_the_option_rows_matches_the_original(reference, ours, tmp_path):
    area = (DIALOG[0], DIALOG[1], DIALOG[2], OPTION_ROWS_TOP)
    count = differing_pixels(
        reference.crop(area), ours.crop(area), masks_in(area), tmp_path / "login-top-diff.png", threshold=0.15
    )
    assert count == 0, f"{count} pixels differ; see {tmp_path}"


@needs_ui_font
def test_dialog_below_the_option_rows_matches_the_original_one_row_lower(reference, ours, tmp_path):
    area = (DIALOG[0], ORIGINAL_ROWS_BOTTOM, DIALOG[2], DIALOG[3])
    lower = (area[0], area[1] + EXTRA_ROW, area[2], area[3] + EXTRA_ROW)
    count = differing_pixels(
        reference.crop(area), ours.crop(lower), masks_in(area), tmp_path / "login-bottom-diff.png", threshold=0.15
    )
    assert count == 0, f"{count} pixels differ; see {tmp_path}"


@pytest.mark.parametrize("line", BANNER_LINES.values(), ids=BANNER_LINES.keys())
def test_banner_lettering_covers_the_original_lines_within_2_pixels(reference, ours, line):
    def ink(image):
        return bounding_box(image, lambda c: sum(c) < 250, (line[0], line[2]), (line[1], line[3]))

    expected, actual = ink(reference), ink(ours)
    assert all(abs(a - e) <= LETTERING_SLACK for a, e in zip(actual, expected, strict=False)), (actual, expected)


def test_session_dropdown_is_drawn_like_the_shut_down_dropdown(ours):
    """Across the arrow button, three rows below its top, out to the field's outer edge: the same colours
    as the original Shut Down dialog's dropdown (w2kshutdown.png, client row 116,
    columns 306-324, right of its highlighted choice)."""
    original = screenshot("w2kshutdown").crop((115, 91, 524, 337))
    expected = [original.getpixel((x, 116)) for x in range(306, 325)]
    field_right, button_top = 111 + 87 + 243 - 1, 74 + 184 + 2
    actual = [ours.getpixel((x, button_top + 3)) for x in range(field_right - 18, field_right + 1)]
    assert all(close(a, e) for a, e in zip(actual, expected, strict=False)), list(zip(actual, expected, strict=False))


@pytest.mark.parametrize(
    "show_options, layouts, expected",
    [
        (False, (("us", "English (US)"),), (74, 229)),
        (True, (("us", "English (US)"),), (74, 283)),
        (True, (("us", "English (US)"), ("ro", "Romanian")), (74, 310)),
    ],
    ids=["collapsed", "session and check box rows", "session, keyboard and check box rows"],
)
def test_options_grows_the_dialog_down_by_27_pixels_per_row_from_the_same_top(
    qt_app, shutdown, tmp_path, show_options, layouts, expected
):
    shutdown.render_login_banner(LOOK, tmp_path / "banner.png")
    with installed_look(qt_app, "[StartMenu]\nstyle=2000\n", LOOK_2000_KDEGLOBALS):
        image = render_login(
            qt_app,
            tmp_path,
            banner=tmp_path / "banner.png",
            show_options=show_options,
            layouts=layouts,
            loginStyle="2000",
        )
    background = image.getpixel((5, 5))
    rows = [y for y in range(image.height) if image.getpixel((300, y)) != background]
    assert (rows[0], rows[-1] - rows[0] + 1) == expected


@pytest.mark.parametrize("caps_lock, expected", [(True, True), (False, False)], ids=["caps lock on", "caps lock off"])
def test_caps_lock_balloon_shows_under_the_password_only_while_caps_lock_is_on(qt_app, tmp_path, caps_lock, expected):
    image = render_login(qt_app, tmp_path, caps_lock=caps_lock, loginStyle="2000")
    balloon = bounding_box(image, lambda c: c == (255, 255, 225), (DIALOG[0], DIALOG[2]), (DIALOG[1], DIALOG[3] + 60))
    assert (balloon is not None) == expected


@pytest.mark.parametrize("look", ("95", "98"))
def test_9x_login_geometry_icon_and_bevels_match_original(qt_app, tmp_path, look):
    from PIL import ImageChops, ImageDraw

    original = screenshot(f"win{look}login")
    ours = render_login(
        qt_app,
        tmp_path,
        users=(),
        loginStyle="classic",
        loginTitle="Welcome to Windows",
        loginMessage="Type a user name and password to log on to Windows.",
        titleActive="#000080" if look == "95" else "#000080,#1084d0",
    )
    difference = ImageChops.difference(original, ours.convert("RGB"))
    # Dynamic username/caret and font glyphs have separate typography requirements.
    # Keep all window, field and button edges, key artwork and surrounding backdrop.
    for box in [
        (94, 93, 507, 110),
        (183, 122, 445, 145),
        (180, 155, 245, 216),
        (257, 159, 388, 177),
        (257, 189, 388, 208),
        (478, 125, 523, 143),
        (473, 155, 524, 173),
        (511, 95, 543, 107),
    ]:
        ImageDraw.Draw(difference).rectangle(box, fill=(0, 0, 0))
    difference.save(tmp_path / "9x-login-difference.png")
    # GDI's 98 caption gradient is quantised differently from Qt Quick (at most
    # two channel levels). The window/control edges and key remain exact to one.
    assert max(high for _, high in difference.crop((93, 92, 546, 110)).getextrema()) <= 2
    ImageDraw.Draw(difference).rectangle((93, 92, 545, 109), fill=(0, 0, 0))
    assert max(high for _, high in difference.getextrema()) <= 1


def test_xp_classic_logon_uses_the_xp_banner_not_the_2000_banner(qt_app, shutdown, tmp_path):
    from PIL import Image

    path = tmp_path / "banner.png"
    assert shutdown.render_login_banner({"style": "2001", "osName": "Windows XP", "osCompany": "Microsoft"}, path)
    expected = screenshot("xpclassiclogin").crop((71, 131, 482, 224))
    actual = Image.open(path).convert("RGB").resize(expected.size, Image.Resampling.NEAREST)
    assert actual.tobytes() == expected.tobytes()
