"""The Aero superbar's Plasma style: task button faces against aero.msstyles' TASKITEM and the bar against Windows 7."""

import importlib.util

import pytest
from aero_sprites import requires_sprites
from conftest import REPO
from fit_aero_stops import DRAWN_TASK_STATES, TASK_STATES, task_image
from PIL import Image
from test_aero_buttons import rendered

spec = importlib.util.spec_from_file_location(
    "make_aero_plasmastyle", REPO / "aero/plasma-style/make_aero_plasmastyle.py"
)
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)
BAR_GLASS = (72, 132, 181, 255)


def over_bar(image):
    base = Image.new("RGBA", image.size, BAR_GLASS)
    base.alpha_composite(image)
    return base.convert("RGB")


@requires_sprites
@pytest.mark.parametrize("state", DRAWN_TASK_STATES)
def test_task_button_face_matches_its_sprite_over_the_bar_within_four_levels_in_every_column(
    qt_app, state, exact_original
):
    # Column by column, so a gloss drawn in the wrong place cannot hide in the whole face's average.
    sprite = task_image(TASK_STATES.index(state))
    ours = over_bar(rendered(generator.task_face_svg(state), sprite.size))
    theirs = over_bar(sprite)
    exact_original(theirs, ours)
    columns = [
        sum(
            max(abs(a - b) for a, b in zip(ours.getpixel((x, y)), theirs.getpixel((x, y)), strict=True))
            for y in range(sprite.height)
        )
        / sprite.height
        for x in range(sprite.width)
    ]

    assert max(columns) <= 4


THEME = REPO / "aero/plasma-style/theme"


def test_committed_plasma_style_equals_generator_output(tmp_path):
    generator.write_theme(tmp_path)

    assert {path.relative_to(tmp_path).as_posix(): path.read_bytes() for path in tmp_path.rglob("*.*")} == {
        path.relative_to(THEME).as_posix(): path.read_bytes() for path in THEME.rglob("*.*")
    }


def test_bar_glass_streaks_and_edge_lines_are_windows_7s_within_a_level_and_a_half_on_average(qt_app):
    # Built as DWM builds it: the panel's glass over the desktop, the streaks stretched over the screen, and the
    # bar's dark line and highlight over both; compared on win7dragedge.png's empty columns, all 40 rows. The streaks
    # are one profile across their bands, so a band's sharp edge can land a pixel or two off: eight levels at most.
    from aero_model import REFERENCE_DESKTOP
    from reference import screenshot

    glass = rendered((THEME / "translucent/widgets/panel-background.svg").read_text(), (28, 40)).crop((0, 0, 10, 40))
    streaks = rendered(generator.reflection_svg(), (1024, 768)).crop((0, 728, 1024, 768))
    edges = rendered((THEME / "widgets/baredge.svg").read_text(), (1024, 2))
    windows_7 = screenshot("win7dragedge").crop((0, 728, 1024, 768))
    columns = [
        x
        for x in range(320, 800)
        if all(
            sum(abs(a - b) for a, b in zip(windows_7.getpixel((x, y)), windows_7.getpixel((x, 20)), strict=True)) < 25
            for y in range(4, 37)
        )
    ]
    seen = Image.new("RGBA", (1024, 40), REFERENCE_DESKTOP)
    seen.alpha_composite(glass.resize((1024, 40)))
    seen.alpha_composite(streaks)
    seen.alpha_composite(edges)
    differences = [
        max(abs(a - b) for a, b in zip(seen.getpixel((x, y))[:3], windows_7.getpixel((x, y)), strict=True))
        for x in columns
        for y in range(40)
    ]

    assert (sum(differences) / len(differences) <= 1.5, max(differences) <= 8) == (True, True)


ORB_CENTRE, ORB_RADIUS = (27.0, 20.0), 19.0  # in the taskbar's rows: win7dragedge.png's orb at x 27, y 748


def test_start_orb_outside_its_logo_is_windows_7s_within_five_levels(qt_app):
    from reference import screenshot

    windows_7 = screenshot("win7dragedge")
    behind_orb = windows_7.crop((2, 728, 3, 768)).resize((58, 40)).convert("RGBA")  # the bar, darkened there
    ours = Image.alpha_composite(behind_orb, rendered(generator.orb_svg(), (58, 40))).convert("RGB")
    theirs = windows_7.crop((0, 728, 58, 768))
    cx, cy = ORB_CENTRE
    ring = [
        (x, y)
        for x in range(58)
        for y in range(40)
        if 14**2 <= (x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2 <= ORB_RADIUS**2  # Windows 7's logo reaches 14
    ]
    differences = [
        abs(a - b) for x, y in ring for a, b in zip(ours.getpixel((x, y)), theirs.getpixel((x, y)), strict=True)
    ]

    assert sum(differences) / len(differences) < 5


@requires_sprites
@pytest.mark.parametrize("state", ["normal", "hover", "pressed"])
def test_show_desktop_face_is_its_sprite_as_drawn_15_wide_within_six_levels(qt_app, state, exact_original):
    from fit_aero_stops import SHOW_DESKTOP_STATES, show_desktop_image

    sprite = show_desktop_image(SHOW_DESKTOP_STATES.index(state))
    ours = over_bar(rendered(generator.show_desktop_face_svg(state), sprite.size))
    theirs = over_bar(sprite)
    exact_original(theirs, ours)
    differences = [
        abs(a - b)
        for p, q in zip(ours.get_flattened_data(), theirs.get_flattened_data(), strict=True)
        for a, b in zip(p, q, strict=True)
    ]

    assert (tuple(generator.stops.SHOW_DESKTOP_FACES[state]["size"]), sum(differences) / len(differences) < 6) == (
        sprite.size,
        True,
    )


@pytest.mark.parametrize("rim", [(8, 20), (27, 1), (27, 38)])
def test_start_orb_rim_is_white_glass_at_thirty_percent(qt_app, rim):
    # win7dragedge.png's rim is (112, 143, 170) over the (52, 97, 134) bar behind the orb: white at 30%.
    red, green, blue, alpha = rendered(generator.orb_svg(), (58, 40)).getpixel(rim)

    assert (min(red, green, blue) >= 240, abs(alpha - 77) <= 13) == (True, True)


def test_start_orb_paints_nothing_outside_its_rim(qt_app):
    orb = rendered(generator.orb_svg(), (58, 40))
    cx, cy = ORB_CENTRE
    outside = [
        orb.getpixel((x, y))[3]
        for x in range(58)
        for y in range(40)
        if (x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2 > (ORB_RADIUS + 1) ** 2
    ]

    assert max(outside) == 0


def test_start_shade_over_the_bar_is_windows_7s_darkening_behind_the_orb_within_four_levels(qt_app):
    # Windows 7 darkens the bar's glass behind the orb and fades it out under the first pinned program, sooner in
    # the upper rows than at the foot. Compared where neither the orb nor Internet Explorer's pinned icon lies, over
    # the bar as it shows at x 120, past the darkening.
    from reference import screenshot

    shade_top = generator.palette.START_SHADE_TOP
    shade = Image.new("RGBA", (120, 40 - shade_top))
    shade.paste(rendered(generator.start_shade_svg(), (generator.palette.START_SHADE["reach"], 40 - shade_top)))
    windows_7 = screenshot("win7screenres")
    differences = []
    for y in range(shade_top, 40):
        glass = windows_7.getpixel((120, 728 + y))
        for x in range(120):
            if 69 <= x <= 108 and y <= 37 or (x - 27) ** 2 + (y - 20) ** 2 <= 20.5**2:
                continue
            red, green, blue, alpha = shade.getpixel((x, y - shade_top))
            seen = [
                round(c * alpha / 255 + g * (1 - alpha / 255)) for c, g in zip((red, green, blue), glass, strict=True)
            ]
            differences += [abs(a - b) for a, b in zip(seen, windows_7.getpixel((x, 728 + y)), strict=True)]

    assert max(differences) <= 4


def test_tray_shade_over_the_bar_is_windows_7s_darkening_at_the_notification_area_within_four_levels(qt_app):
    # Windows 7 darkens the bar from before the notification area to the Show desktop strip. Compared on the median of
    # each 2-row, 8-column cell's brightness where no icon or lettering lies (pixels within 30 levels of the
    # cell's median).
    import statistics

    from aero_model import streaked_glass
    from reference import screenshot

    shade_svg = generator.tray_shade_svg()
    width = generator.tray_shade.WIDTH - generator.tray_shade.STRIP  # the darkening, up to the Show desktop strip
    top = generator.palette.START_SHADE_TOP
    shade = rendered(shade_svg, (generator.tray_shade.WIDTH, 40 - top))
    windows_7 = screenshot("win7screenres")
    glass = streaked_glass("win7screenres")
    left = 1024 - 15 - width  # it ends where the Show desktop strip begins
    errors = []
    for y0 in range(top, 40, 2):
        for x0 in range(0, width, 8):
            cell = [(x, y) for x in range(x0, min(x0 + 8, width)) for y in range(y0, min(y0 + 2, 40))]
            theirs = [windows_7.getpixel((left + x, 728 + y)) for x, y in cell]
            middle = [statistics.median(channel) for channel in zip(*theirs, strict=True)]
            kept = [
                (pixel, (x, y))
                for pixel, (x, y) in zip(theirs, cell, strict=True)
                if max(abs(a - b) for a, b in zip(pixel, middle, strict=True)) <= 30
            ]
            # A black darkening changes only brightness: compare the cell's median brightness, in levels per channel.
            if 2 * len(kept) < len(cell):  # mostly icon or lettering, with their smoothed edges: no bar to compare
                continue
            reference = statistics.median(sum(pixel) for pixel, _ in kept) / 3
            if (
                not 0 <= 1 - reference * 3 / sum(glass(left + x0, y0)) <= 0.35
            ):  # an icon's or the lettering's own colours
                continue
            seen = []
            for _, (x, y) in kept:
                alpha = shade.getpixel((x, y - top))[3] / 255
                seen.append(sum(glass(left + x, y)) * (1 - alpha) / 3)
            errors.append(abs(statistics.median(seen) - reference))

    assert max(errors) <= 4


def test_glass_streaks_stretched_to_the_screen_are_windows_7s_on_the_bar_within_one_level_and_two_and_a_half_at_edges(
    qt_app,
):
    # DWM stretches its reflection map over the screen; on win7screenres.png's bar (rows 4..36, x 320..799, where
    # no icon or band lies) the streaks drawn over the bar's glass (as palette.TASKBAR_GLASS shows it over the
    # references' desktop) are Windows 7's, column by column.
    import statistics

    from aero_model import REFERENCE_DESKTOP
    from reference import screenshot

    streaks = rendered(generator.reflection_svg(), (1024, 768))
    bar = rendered((THEME / "translucent/widgets/panel-background.svg").read_text(), (28, 40)).crop((0, 0, 10, 40))
    seen = Image.new("RGBA", bar.size, REFERENCE_DESKTOP)
    seen.alpha_composite(bar)
    windows_7, glass = screenshot("win7screenres"), [seen.getpixel((5, y))[:3] for y in range(40)]
    rows = range(4, 37)
    errors = []
    for x in range(320, 800):
        theirs = [windows_7.getpixel((x, 728 + y)) for y in rows]
        if max(abs(sum(pixel) - sum(theirs[16])) for pixel in theirs) > 25:  # an icon or button
            continue
        ours = []
        for y in rows:
            red, green, blue, alpha = streaks.getpixel((x, 728 + y))
            ours.append(
                sum(c * alpha / 255 + g * (1 - alpha / 255) for c, g in zip((red, green, blue), glass[y], strict=True))
            )
        errors.append((statistics.mean(ours) - statistics.mean(sum(pixel) for pixel in theirs)) / 3)

    # A streak's sharp edge, placed a fraction of a pixel off, strays most.
    assert (max(abs(error) for error in errors) <= 2.5, statistics.pstdev(errors) <= 1) == (True, True)


GROUP_SPRITES = {"group-2": ("TASKITEMGROUP", 1), "group-3": ("TASKITEMGROUP", 2)}
GROUP_SPRITES |= {f"group-selected-{n}": ("TASKITEMGROUPSELECTED", state) for n, state in (("2", 1), ("3", 2))}


@requires_sprites
@pytest.mark.parametrize("state", GROUP_SPRITES)
def test_group_stack_matches_its_sprite_over_the_bar_within_four_levels_in_every_column(qt_app, state, exact_original):
    # A combined button's stacked edges: one card for two windows, two for three or more, brighter when focused.
    from fit_aero_stops import group_image

    sprite = group_image(*GROUP_SPRITES[state])
    ours = over_bar(rendered(generator.group_face_svg(state), sprite.size))
    theirs = over_bar(sprite)
    exact_original(theirs, ours)
    columns = [
        sum(
            max(abs(a - b) for a, b in zip(ours.getpixel((x, y)), theirs.getpixel((x, y)), strict=True))
            for y in range(sprite.height)
        )
        / sprite.height
        for x in range(sprite.width)
    ]

    assert max(columns) <= 4


ARROW_SIZE = (17, 20)  # SM_CXVSCROLL wide, half the bar tall: no reference shows the superbar's scroll arrows


def scroll_arrow_image(state, size):
    """TaskBand2Composited::ScrollBar ARROWBTN as Windows draws it: the face nine-sliced to the button (margins 2)
    and the glyph centred over it."""
    from aero_sprites import part, sprite_dir, straight

    arrow = part("TaskBand2Composited::ScrollBar", "ARROWBTN")
    index = generator.SCROLL_ARROW_STATES.index(state)
    face_strip = straight(Image.open(sprite_dir() / arrow.image_file).convert("RGBA"))
    glyph_strip = straight(Image.open(sprite_dir() / arrow.properties["GLYPHIMAGEFILE"]).convert("RGBA"))
    face_height, glyph_height = face_strip.height // arrow.image_count, glyph_strip.height // arrow.image_count
    face = face_strip.crop((0, index * face_height, face_strip.width, (index + 1) * face_height))
    glyph = glyph_strip.crop((0, index * glyph_height, glyph_strip.width, (index + 1) * glyph_height))
    width, height = size
    image = Image.new("RGBA", size)
    edge = 2
    columns = [(0, edge, 0, edge), (edge, face.width - edge, edge, width - edge)]
    columns.append((face.width - edge, face.width, width - edge, width))
    rows = [(0, edge, 0, edge), (edge, face.height - edge, edge, height - edge)]
    rows.append((face.height - edge, face.height, height - edge, height))
    for sx0, sx1, dx0, dx1 in columns:
        for sy0, sy1, dy0, dy1 in rows:
            image.alpha_composite(face.crop((sx0, sy0, sx1, sy1)).resize((dx1 - dx0, dy1 - dy0)), (dx0, dy0))
    image.alpha_composite(glyph, ((width - glyph.width) // 2, (height - glyph.height) // 2))
    return image


def level_difference(ours, theirs, pixels):
    return [max(abs(a - b) for a, b in zip(ours.getpixel(xy), theirs.getpixel(xy), strict=True)) for xy in pixels]


@requires_sprites
@pytest.mark.parametrize(
    "state", ["up-normal", "up-hot", "down-pressed", "down-disabled", "left-disabled", "right-hover"]
)
def test_scroll_arrow_frame_is_its_sprite_within_a_level_and_its_glyph_within_six_on_average(
    qt_app, state, exact_original
):
    theirs = over_bar(scroll_arrow_image(state, ARROW_SIZE))
    ours = over_bar(rendered(generator.scroll_arrow_svg(state, ARROW_SIZE), ARROW_SIZE))
    exact_original(theirs, ours)
    width, height = ARROW_SIZE
    # The glyph's cell and the pixel around it, where its antialiased edges fall.
    left, top = (width - generator.GLYPH_SIZE[0]) // 2 - 1, (height - generator.GLYPH_SIZE[1]) // 2 - 1
    right, bottom = left + generator.GLYPH_SIZE[0] + 2, top + generator.GLYPH_SIZE[1] + 2
    pixels = [(x, y) for x in range(width) for y in range(height)]
    glyph = [(x, y) for x, y in pixels if left <= x < right and top <= y < bottom]
    frame = [xy for xy in pixels if xy not in glyph]
    glyph_differences = level_difference(ours, theirs, glyph)

    assert (max(level_difference(ours, theirs, frame)), sum(glyph_differences) / len(glyph_differences) <= 6) == (
        1,
        True,
    )


TRAY_BUTTONS = [f"{kind}{state}" for kind in ("", "open-") for state in ("normal", "hot", "pressed")]


@requires_sprites
@pytest.mark.parametrize("state", TRAY_BUTTONS)
def test_tray_button_is_its_sprite_over_the_bar_within_three_levels_on_average_and_48_at_a_stair_corner(
    qt_app, state, exact_original
):
    # A straight-edged triangle cannot land on every corner of the sprite's 1-3-5-7 pixel stair.
    from fit_aero_stops import tray_button_image

    kind, look = ("open-", state[5:]) if state.startswith("open-") else ("", state)
    sprite = tray_button_image(kind, look)
    ours = over_bar(rendered(generator.tray_button_svg(state), sprite.size))
    exact_original(over_bar(sprite), ours)
    pixels = [(x, y) for x in range(sprite.width) for y in range(sprite.height)]
    differences = level_difference(ours, over_bar(sprite), pixels)

    assert (sum(differences) / len(differences) <= 3, max(differences) <= 48) == (True, True)


def grip_image(height):
    """TaskBar::Rebar GRIPPER at its own 12-pixel width, as Windows tiles it down a band's height: its top and bottom
    4 rows (sizing margins) kept, the 4 rows between them repeated."""
    from aero_sprites import part, sprite_dir, straight

    gripper = part("TaskBar::Rebar", "GRIPPER")
    tile = straight(Image.open(sprite_dir() / gripper.properties["IMAGEFILE1"]).convert("RGBA"))
    top, bottom = gripper.margins.top, gripper.margins.bottom
    image = Image.new("RGBA", (tile.width, height))
    image.paste(tile.crop((0, 0, tile.width, top)), (0, 0))
    middle = tile.crop((0, top, tile.width, tile.height - bottom))
    for y in range(top, height - bottom, middle.height):
        image.paste(middle.crop((0, 0, tile.width, min(middle.height, height - bottom - y))), (0, y))
    image.paste(tile.crop((0, tile.height - bottom, tile.width, tile.height)), (0, height - bottom))
    return image


@requires_sprites
def test_taskbar_grip_is_its_sprite_tiled_down_the_bar_within_a_level(qt_app, exact_original):
    theirs = over_bar(grip_image(40))
    ours = over_bar(rendered(generator.grip_svg(), (12, 40)))
    exact_original(theirs, ours)

    assert max(level_difference(ours, theirs, [(x, y) for x in range(12) for y in range(40)])) <= 1


def test_fractional_scale_preserves_the_start_orbs_fitted_glass(qt_app):
    svg = generator.orb_svg()
    assert "<image" not in svg and "data:image" not in svg
    # Compare against a supersampled vector reference at the same physical size.
    expected = rendered(svg, (174, 120)).resize((87, 60), Image.Resampling.LANCZOS)
    scaled = rendered(generator.orb_svg(), (87, 60))
    errors = [
        abs(a - b)
        for x in range(87)
        for y in range(60)
        if 21**2 < (x + 0.5 - 40.5) ** 2 + (y + 0.5 - 30) ** 2 < 25**2
        for a, b in zip(scaled.getpixel((x, y))[:3], expected.getpixel((x, y))[:3], strict=True)
    ]
    assert sum(errors) / len(errors) < 4
