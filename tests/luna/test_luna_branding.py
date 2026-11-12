"""The XP boot and log-on screens with the user's branding (Control Panel > Passwords > Branding): their logo, name,
company and edition in the place of the Windows XP wordmark (luna/qml/XpWordmark.qml), as the 1995..2000 screens
show them. Without a name the screens keep the XP wordmark itself."""

import pytest
from PIL import Image

from .luna_qml import render_luna_login, render_luna_splash

RED = (255, 0, 0)


@pytest.fixture(scope="module")
def logo(tmp_path_factory):
    path = tmp_path_factory.mktemp("logo") / "logo.png"
    Image.new("RGB", (64, 64), RED).save(path)
    return path


def branding(logo):
    return {"brandText": "Windows2026", "brandLogo": str(logo), "company": "KDE", "edition": "Professional"}


def reds(image, box):
    left, top, right, bottom = box
    return sum(image.getpixel((x, y))[:3] == RED for x in range(left, right) for y in range(top, bottom))


def whites(image, box):
    left, top, right, bottom = box
    return sum(min(image.getpixel((x, y))[:3]) > 200 for x in range(left, right) for y in range(top, bottom))


# The branded mark on the splash: 220 units wide at 1.85, centred on x 320 (from x 116.5), y 124; its logo takes
# units 0..40 across and 4..40 down, the name starts at unit 44 with its baseline at 44.
SPLASH_LOGO = (120, 135, 185, 195)
SPLASH_NAME = (200, 160, 520, 208)


def test_the_boot_screen_draws_the_users_logo_where_the_xp_flag_was(qt_app, logo):
    image = render_luna_splash(qt_app, properties=branding(logo))

    assert reds(image, SPLASH_LOGO) > 1500


def test_the_boot_screen_writes_the_users_name_beside_the_logo(qt_app, logo):
    image = render_luna_splash(qt_app, properties=branding(logo))

    assert whites(image, SPLASH_NAME) > 300


def test_without_a_name_the_boot_screen_keeps_the_xp_wordmark(qt_app, logo):
    image = render_luna_splash(qt_app, properties={**branding(logo), "brandText": ""})

    assert reds(image, (0, 0, 640, 480)) == 0


# The wordmark on the 800x600 log-on screen ends 21 units left of the divider (x 398): a branded one is 220 units
# wide, so it starts at x 157; y 233, one unit a pixel.
LOGIN_LOGO = (159, 240, 195, 271)


def test_the_log_on_screen_draws_the_users_logo_from_the_themes_settings(qt_app, logo):
    image = render_luna_login(qt_app, settings=branding(logo))

    assert reds(image, LOGIN_LOGO) > 600


def test_without_a_name_the_log_on_screen_keeps_the_xp_wordmark(qt_app, logo):
    image = render_luna_login(qt_app, settings={**branding(logo), "brandText": ""})

    assert reds(image, (0, 0, 800, 600)) == 0


def ink_rows(image, box):
    left, top, right, bottom = box
    return [y for y in range(top, bottom) if any(min(image.getpixel((x, y))[:3]) > 200 for x in range(left, right))]


def test_the_boot_screens_name_keeps_its_full_size_however_long(qt_app, logo):
    """26 units at the splash's 1.85: capitals about 35 pixels high, not shrunk into the XP wordmark's narrow box."""
    image = render_luna_splash(qt_app, properties=branding(logo))
    rows = ink_rows(image, (200, 150, 520, 215))

    assert rows[-1] - rows[0] >= 28


def test_the_boot_screen_names_the_users_company_in_its_corner_instead_of_microsoft(qt_app, logo):
    image = render_luna_splash(qt_app, properties=branding(logo))

    assert (whites(image, (546, 441, 590, 465)), whites(image, (600, 441, 636, 465)) > 20) == (0, True)


def test_the_log_on_screens_wordmark_ends_where_the_xp_one_does_left_of_the_divider(qt_app, logo):
    image = render_luna_login(qt_app, settings=branding(logo))
    name_ink = [x for x in range(200, 398) if any(min(image.getpixel((x, y))[:3]) > 230 for y in range(255, 285))]

    assert 370 <= name_ink[-1] <= 377


def test_the_boot_screens_branded_mark_is_centred_as_the_xp_wordmark_is(qt_app, logo):
    image = render_luna_splash(qt_app, properties=branding(logo))
    ink = [x for x in range(640) if any(sum(image.getpixel((x, y))[:3]) > 150 for y in range(130, 240))]

    assert abs((ink[0] + ink[-1]) / 2 - 331) <= 12  # the XP wordmark's own centre (x 209, 244 wide on Plymouth)
