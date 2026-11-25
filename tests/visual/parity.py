"""Exact Windows comparisons. Run explicitly with pytest tests/visual/parity.py."""

import configparser
import json
import math
import os
import shutil
import subprocess
import sys
from functools import cache
from pathlib import Path
from shlex import quote

import numpy as np
import pytest
from aurorae_model import Window
from conftest import REPO, load_script
from original_pixels import compare
from PIL import Image, ImageChops, ImageColor, ImageFilter
from plasma_session import (
    CHICAGO95_SRC,
    HOME_AFTER_SETUP,
    hover_steps,
    install,
    missing_programs,
    right_click_at,
    run_session,
    show,
    work_folder,
)
from reference import REFERENCES, bounding_box, qimage_to_pil, render_start_menu, rgb555, rgb565, theme_references
from showcase import start_menus, themed
from test_caption_states_reference import (
    BUTTONS,
    CLASSIC,
    DISABLED_CLOSE_MATTES,
    STATES,
    build_caption_themes,
    caption_pixels,
    caption_reference,
    disabled_close_matte,
    face_region,
    state_buttons,
    visible_pixels,
)
from visual_tolerances import tolerance_for

THEMES = {folder.name: (folder, metadata) for folder, metadata in theme_references(REFERENCES)}
EXPECTED_THEMES = {"win95", "win98", "win2k", "winxp-classic", "winxp", "win7"}
CAPTION_STATES = STATES[:-1]
GTK_STATES = dict(zip(CAPTION_STATES, ("normal", "hovered", "pressed", "disabled", "restore"), strict=True))
RADIO_BACKDROPS = {"luna": "#fffbf7", "aero": "#ffffff"}
CAPTION_RENDERERS = {
    "svg": STATES,
    "kwin": STATES,
    "gtk3": CAPTION_STATES,
    "gtk4": CAPTION_STATES,
}
COMPONENTS = (
    "caption",
    "run",
    "desktop",
    "taskbar",
    "start-menu",
    "control-panel",
    "device-manager",
    "display-properties",
    "file-manager",
    "widget-controls",
    "boot",
    "sign-in",
    "post-login",
    "lock-screen",
    "shutdown",
    "motion",
)
WINDOW = (160, 150, 559, 449)
PRESS_WINDOWS = (WINDOW, (160, 470, 559, 699), (610, 470, 1009, 699))
PRESS_TITLES = ("Caption parity", "Caption parity maximize press", "Caption parity close press")
DISABLED_WINDOW = (610, 150, 1009, 449)
DISABLED_TITLE = "Caption parity disabled"
DISABLED_APP = "org.chicago95.test.caption-disabled"
AERO_MATTES = {"dark": "#181818", "light": "#E8E8E8", "blue": "#446688"}


class AeroCaptionWindow(Window):
    RC_NAME = "Chicago95Aerorc"

    def __init__(self, theme, width, height, scale=1):
        super().__init__(theme, width, height)
        # Match Theme.js in the installed QML decoration. The plain SVG
        # fallback uses the spacing from Chicago95Aerorc.
        if scale >= 1.5:
            self.layout["ButtonSpacing"] = 0
            self.layout["ButtonWidthMaximizeRestore"] = 40 / 1.5


@pytest.fixture(scope="module")
def installed():
    folders = []

    @cache
    def prepare(look, setup_scale=1, *, aero_background="#4395D1", screen=(1024, 768), components=(), launchers=0):
        missing = missing_programs()
        assert not missing, f"Missing live-render dependencies: {', '.join(missing)}"
        folder = work_folder(f"parity-{look}")
        folders.append(folder)
        background = (
            {"settings": [("BACKGROUND_MODE", "color"), ("BACKGROUND_COLOR", aero_background)]}
            if look == "aero" and aero_background
            else {}
        )
        if background and "background" not in components:
            components = (*components, "background")
        return install(
            look, folder, screen=screen, launchers=launchers, setup_scale=setup_scale, components=components, **background
        )

    yield prepare
    for folder in folders:
        shutil.rmtree(folder, ignore_errors=True)


@pytest.fixture(scope="module")
def live_kwin(installed, visual_output):
    @cache
    def capture(theme, artwork):
        _, metadata = THEMES[theme]
        look, scale = metadata["look"], metadata["caption_scale"]
        left, top, right, bottom = WINDOW
        model = kwin_window(artwork, look, right - left + 1, bottom - top + 1)
        rects = model.button_rects()
        points = [f"move:{left + rects[key].center().x()},{top + rects[key].center().y()}" for key in "IAX"]
        steps = [
            "move:750,250",
            "click:left",
            "move:600,110",
            "wait:0.6",
            "snapshot:caption-disabled",
        ]
        disabled_left, disabled_top = DISABLED_WINDOW[:2]
        for index in state_buttons("disabled"):
            button = rects["IAX"[index]].center()
            steps.extend(
                [
                    f"move:{disabled_left + button.x()},{disabled_top + button.y()}",
                    "wait:0.3",
                    f"snapshot:caption-disabled-hover-{index}",
                    "press:left",
                    "wait:0.2",
                    f"snapshot:caption-disabled-pressed-{index}",
                    "release:left",
                    "wait:0.3",
                    f"snapshot:caption-disabled-clicked-{index}",
                ]
            )
        steps.extend(["move:350,270", "click:left", "move:600,110", "wait:0.6", "snapshot:caption-rest"])
        for index, point in enumerate(points):
            steps.extend([point, "wait:0.3", f"snapshot:caption-hover-{index}"])
        session = installed(look, scale) if look == "luna" else installed(look)
        maximized = kwin_maximized_window(artwork, look, *session.screen)
        restore = maximized.button_rects()["A"].center()
        steps.extend(
            [
                points[1],
                "click:left",
                "move:700,400",
                "wait:0.6",
                "snapshot:caption-restore",
                f"move:{restore.x()},{restore.y()}",
                "click:left",
                "wait:0.6",
            ]
        )
        # A release can still activate a caption action. Use a separate
        # window for each press and leave Maximize until the end.
        for index in (0, 2, 1):
            x, y, _, _ = PRESS_WINDOWS[index]
            button = rects["IAX"[index]].center()
            steps.extend(
                [
                    f"move:{x + 45},{y + 55}",
                    "click:left",
                    "wait:0.3",
                    f"move:{x + button.x()},{y + button.y()}",
                    "wait:0.3",
                    "press:left",
                    "wait:0.2",
                    f"snapshot:caption-pressed-{index}",
                    f"move:{x + 45},{y + 55}",
                    "wait:0.2",
                    f"snapshot:caption-held-outside-{index}",
                    "release:left",
                    "wait:0.6",
                    f"snapshot:caption-cancelled-{index}",
                ]
            )
        rules_path = session.work / HOME_AFTER_SETUP / ".config/kwinrulesrc"
        rules = configparser.ConfigParser(interpolation=None)
        rules.optionxform = str
        rules.read(rules_path)
        if "General" not in rules:
            rules.add_section("General")
        groups = [group for group in rules["General"].get("rules", "").split(",") if group]
        rules["General"]["rules"] = ",".join([*groups, DISABLED_APP])
        rules[DISABLED_APP] = {
            "wmclass": DISABLED_APP,
            "wmclassmatch": "1",
            "closeable": "false",
            "closeablerule": "2",
        }
        with rules_path.open("w") as stream:
            rules.write(stream, space_around_delimiters=False)
        screen = show(
            session,
            windows=[
                *((title, "qt", bounds) for title, bounds in zip(PRESS_TITLES, PRESS_WINDOWS, strict=True)),
                (DISABLED_TITLE, "qt-fixed", DISABLED_WINDOW, DISABLED_APP),
            ],
            scale=scale,
            pointer_steps=steps,
            window_state=True,
        )
        records = [
            json.loads(line.split("c95-window ", 1)[1])
            for line in screen.info["kwin_log"].splitlines()
            if "c95-window " in line
        ]
        disabled = next(
            (record for record in records if record["phase"] == "after" and record["title"] == DISABLED_TITLE), None
        )
        assert disabled is not None, f"KWin did not report the fixed-size caption fixture: {records}"
        assert disabled["closeable"] is False and disabled["maximizable"] is False, disabled
        assert tuple(disabled["bounds"][:2]) == DISABLED_WINDOW[:2], disabled
        output = visual_output / theme / "caption" / "kwin" / "cancelled"
        output.mkdir(parents=True, exist_ok=True)
        (output / "window-state.json").write_text(json.dumps(records, indent=2) + "\n")
        for index, button in enumerate(BUTTONS):
            for state in ("held-outside", "cancelled"):
                snapshot = session.work / f"caption-{state}-{index}.png"
                shutil.copyfile(snapshot, output / f"{button}-{state}.png")
        output = visual_output / theme / "caption" / "kwin" / "disabled"
        output.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(session.work / "caption-disabled.png", output / "screen.png")
        return session.work, disabled["bounds"]

    return capture


def compositor_radio(look, scale):
    return look == "aero" or look in (*CLASSIC, "luna") and scale == 1.25


@pytest.fixture(scope="module")
def live_gtk(installed, visual_output):
    @cache
    def capture(look, scale, component="caption"):
        session = installed(look, scale) if component == "caption" or look in (*CLASSIC, "luna") else installed(look)
        home = session.work / "home"
        script = session.work / f"{component}-gtk.sh"
        commands = ["#!/bin/sh", "set -eu"]
        for version in ("3.0", "4.0"):
            settings = configparser.ConfigParser()
            settings.read(home / ".config" / f"gtk-{version}" / "settings.ini")
            theme = settings["Settings"]["gtk-theme-name"]
            directory = session.work / f"{component}-gtk-{version}"
            command = (
                f"{quote(sys.executable)} {quote(str(REPO / 'tests/gtk_showcase.py'))} "
                f"{version} {quote(theme)} {quote(str(directory))} --consistency --only {quote(component)}"
            )
            if component == "caption":
                command += " --caption-crops --compositor-captions"
            elif component == "radio" and compositor_radio(look, scale):
                command += " --compositor-radios"
                if look in RADIO_BACKDROPS:
                    command += f" --radio-backdrop {quote(RADIO_BACKDROPS[look])}"
            commands.append(command)
        script.write_text("\n".join(commands) + "\n")
        env = {
            **session.environment,
            "GDK_BACKEND": "wayland",
            "GTK_A11Y": "none",
            "CHICAGO95_RENDER_SCALE": str(scale),
        }
        run_session(session.work, script, env, session.screen, scale=scale)
        for version in ("3.0", "4.0"):
            manifest = "caption-crops.json" if component == "caption" else "manifest.json"
            if not (session.work / f"{component}-gtk-{version}" / manifest).is_file():
                theme = next(name for name, (_, metadata) in THEMES.items() if metadata["look"] == look)
                logs = visual_output / theme / f"{component}-gtk-capture-logs"
                logs.mkdir(parents=True, exist_ok=True)
                for log in session.work.glob("kwin-*.log"):
                    shutil.copyfile(log, logs / log.name)
                if component == "caption":
                    # Preserve the failed compositor frame so a missing marker can be diagnosed.
                    capture_folder = session.work / f"{component}-gtk-{version}"
                    screenshots = sorted(capture_folder.glob("*-compositor.png"), key=lambda image: image.stat().st_mtime)
                    if screenshots:
                        shutil.copyfile(screenshots[-1], logs / f"gtk-{version}-last-frame.png")
                pytest.fail(f"GTK {version} capture incomplete. See {logs}")
        return session.work

    return capture


def kwin_window(theme, look, width, height, aero_scale=1):
    if look == "luna":
        from luna.luna_model import LunaWindow

        return LunaWindow(width, height)
    if look == "aero":
        return AeroCaptionWindow(theme, width, height, aero_scale)
    return Window(theme, width, height)


def kwin_maximized_window(theme, look, width, height, aero_scale=1):
    model = kwin_window(theme, look, width, height, aero_scale)
    for key in ("TitleEdgeTop", "TitleEdgeLeft", "TitleEdgeRight"):
        model.layout[key] = model.layout[key + "Maximized"]
    model.layout["ButtonMarginTop"] = model.layout.get("ButtonMarginTopMaximized", 0)
    return model


def kwin_face(capture, theme, look, scale, state, index):
    def pixel(position):
        return math.floor(position * scale + 0.5)

    directory, disabled = capture
    suffix = f"-{index}" if state in ("hover", "pressed", "cancelled") or state.startswith("disabled-") else ""
    path = directory / f"caption-{state}{suffix}.png"
    assert path.is_file(), f"Missing nested KWin capture {path.name}"
    with Image.open(path) as frame:
        screen = frame.convert("RGB")
    config = configparser.ConfigParser()
    config.read(directory / "home/.config/kwinrc")
    decoration = config.get("org.kde.kdecoration2", "theme", fallback="")
    aero_scale = scale if decoration == "org.chicago95.aero" else 1
    if state == "restore":
        left, top = 0, 0
        model = kwin_maximized_window(theme, look, round(screen.width / scale), round(screen.height / scale), aero_scale)
    elif state.startswith("disabled"):
        left, top, right, bottom = disabled
        model = kwin_window(theme, look, round(right - left), round(bottom - top), aero_scale)
    else:
        left, top, right, bottom = PRESS_WINDOWS[index] if state in ("pressed", "cancelled") else WINDOW
        model = kwin_window(theme, look, right - left + 1, bottom - top + 1, aero_scale)
    rect = model.button_rects()["IAX"[index]]
    if state == "restore" and decoration == "org.chicago95.aero":
        rect.translate(0, -1 / scale)
    if decoration == "org.chicago95.aero":
        # The Aero wrapper snaps the row before the compositor places the
        # window. Snap its origin and the frame origin independently.
        x = pixel(left) + pixel(rect.left())
        y = pixel(top) + pixel(rect.top())
        right = x + round(rect.width() * scale)
        bottom = y + round(rect.height() * scale)
        return screen.crop((x, max(0, y), right, bottom))
    if (look in CLASSIC and scale == 1.25) or (look == "luna" and scale % 1):
        wrapper = "classic" if look in CLASSIC else "luna"
        if decoration == f"org.chicago95.{wrapper}":
            # KWin places the snapped decoration on the separately snapped window origin.
            x = pixel(left) + pixel(rect.left())
            y = pixel(top) + pixel(rect.top())
            if look in CLASSIC:
                x += 3 if index == 2 else 0
                y += 1
                face = screen.crop((x, y, x + 20, y + 18))
                return rgb565(face) if look in ("2000", "2001") else face
            return screen.crop((x, y, x + math.ceil(rect.width() * scale), y + math.ceil(rect.height() * scale)))
    if look in CLASSIC:
        rect.adjust(2 if index == 2 else 0, 1, 0, -1)
    return screen.crop(
        tuple(
            max(0, round(edge * scale))
            for edge in (
                left + rect.left(),
                top + rect.top(),
                left + rect.right(),
                top + rect.bottom(),
            )
        )
    )


def marker_bounds(image, colour):
    mask = np.all(np.asarray(image) == ImageColor.getrgb(colour), axis=-1)
    counts = mask.sum(axis=1)
    assert counts.max() > 0, "GTK compositor capture is missing the geometry marker"
    # A handful of coincident pixels in the frame or a transition can have
    # the marker's color. Find the solid client rectangle they surround.
    rows = np.flatnonzero(counts * 2 >= counts.max())
    columns = np.flatnonzero(mask[rows].sum(axis=0) * 2 >= len(rows))
    assert len(columns) > 0, "GTK compositor geometry marker is fragmented"
    return columns[0], rows[0], columns[-1] + 1, rows[-1] + 1


def test_caption_capture_marker_ignores_matching_frame_pixels():
    frame = Image.new("RGB", (40, 30))
    marker = "#e10ccf"
    frame.paste(marker, (6, 10, 36, 25))
    frame.paste(marker, (2, 2, 5, 3))
    frame.paste(marker, (38, 15, 39, 17))
    assert marker_bounds(frame, marker) == (6, 10, 36, 25)


def gtk_compositor_frame(directory, record):
    with Image.open(directory / record["frame"]) as frame:
        marker = marker_bounds(frame.convert("RGB"), record["marker"])
    with Image.open(directory / record["compositor"]) as captured:
        screen = captured.convert("RGB")
    placed = marker_bounds(screen, record["marker"])
    for dimension in (0, 1):
        assert abs((placed[dimension + 2] - placed[dimension]) - (marker[dimension + 2] - marker[dimension])) <= 1
    return screen, placed[0] - marker[0], placed[1] - marker[1]


def gtk_face(directory, state, index):
    records = json.loads((directory / "caption-crops.json").read_text())
    suffix = f"-{BUTTONS[index]}" if state in ("hover", "pressed") else ""
    record = records[f"caption {GTK_STATES[state]}{suffix}"]
    box = record["faces"][BUTTONS[index]]
    if "compositor" not in record:
        with Image.open(directory / record["frame"]) as frame:
            return frame.crop(box).convert("RGB")
    screen, dx, dy = gtk_compositor_frame(directory, record)
    x0, y0, x1, y1 = box
    return screen.crop((x0 + dx, y0 + dy, x1 + dx, y1 + dy))


def gtk_caption_cluster_spacing(directory):
    record = json.loads((directory / "caption-crops.json").read_text())["caption normal"]
    screen, dx, dy = gtk_compositor_frame(directory, record)
    starts = []
    for kind in BUTTONS:
        left, top, _, bottom = record["faces"][kind]
        # The left bevel is the strongest rise in brightness near the
        # button origin, even on GTK 3's fractionally scaled output.
        crop = screen.crop((left + dx - 2, top + dy + 2, left + dx + 4, bottom + dy - 2))
        strength = np.diff(np.asarray(crop, dtype=int).mean(axis=(0, 2)))
        starts.append(left + dx - 1 + int(strength.argmax()))
    return np.diff(starts)


def native_caption_cluster_spacing(folder, highlight):
    with Image.open(folder / "caption/cluster.png") as reference:
        top = np.asarray(reference.convert("RGB"))[0]
    highlights = np.flatnonzero(np.min(top, axis=-1) >= highlight)
    starts = highlights[np.r_[True, np.diff(highlights) > 1]]
    assert len(starts) == len(BUTTONS)
    return np.diff(starts)


@pytest.mark.parametrize("theme", [name for name, (_, metadata) in THEMES.items() if "caption_cluster_scale" in metadata])
def test_classic_gtk3_caption_button_spacing_matches_windows(theme, live_gtk):
    folder, metadata = THEMES[theme]
    scale = metadata["caption_cluster_scale"]
    directory = live_gtk(metadata["look"], scale) / "caption-gtk-3.0"
    gaps = gtk_caption_cluster_spacing(directory)
    reference_gaps = native_caption_cluster_spacing(folder, 255)
    # GTK 3 allocates integer logical positions, so one physical pixel can
    # move between the gaps at fractional output scale.
    tolerance = int(scale != 1)
    assert np.all(np.abs(gaps - reference_gaps) <= tolerance), (gaps, reference_gaps)
    assert gaps.sum() == reference_gaps.sum()


@pytest.mark.parametrize("version", ("3.0", "4.0"))
def test_winxp_luna_gtk_caption_button_spacing_matches_windows(version, live_gtk):
    folder, metadata = THEMES["winxp"]
    directory = live_gtk(metadata["look"], metadata["caption_scale"]) / f"caption-gtk-{version}"
    gaps = gtk_caption_cluster_spacing(directory)
    reference_gaps = native_caption_cluster_spacing(folder, 225)
    assert np.all(np.abs(gaps - reference_gaps) <= int(version == "3.0")), (gaps, reference_gaps)
    assert abs(gaps.sum() - reference_gaps.sum()) <= int(version == "3.0")


def test_win7_gtk4_caption_button_spacing_matches_windows(live_gtk):
    _, metadata = THEMES["win7"]
    look = metadata["look"]
    directory = live_gtk(look, metadata["caption_scale"]) / "caption-gtk-4.0"
    # The original matte capture has Minimize, Maximize and Close flush.
    native = caption_reference(look)
    expected = [face_region(native, look, "rest", index)[0].width for index in (0, 1)]
    assert gtk_caption_cluster_spacing(directory).tolist() == expected


@pytest.fixture(scope="module")
def visual_output(tmp_path_factory):
    return tmp_path_factory.getbasetemp() / "visual"


def exact(expected, actual, directory, mask=None):
    directory.mkdir(parents=True, exist_ok=True)
    actual.save(directory / "rendered.png")
    compare(
        expected, actual, directory / "comparison.png", mask, record_metrics=True,
        tolerance=tolerance_for(directory, expected.size),
    )


@pytest.fixture(scope="module")
def svg_themes(qt_app, tmp_path_factory):
    return build_caption_themes(tmp_path_factory)


@pytest.mark.parametrize("theme", THEMES)
@pytest.mark.parametrize(
    ("renderer", "state", "index"),
    [
        pytest.param(renderer, state, index, id=f"{renderer}-{state}-{BUTTONS[index]}")
        for renderer, states in CAPTION_RENDERERS.items()
        for state in states
        for index in state_buttons(state)
    ],
)
def test_caption_matches_windows_pixels(theme, renderer, state, index, svg_themes, live_kwin, live_gtk, visual_output):
    _folder, metadata = THEMES[theme]
    look, scale = metadata["look"], metadata["caption_scale"]
    expected, glass = face_region(caption_reference(look), look, state, index)
    button = "restore" if state == "restore" else BUTTONS[index]
    if renderer == "svg":
        actual = caption_pixels(svg_themes[look], button, state, look, glass.resize(expected.size))
    elif renderer == "kwin":
        theme_art = svg_themes[look]
        actual = kwin_face(live_kwin(theme, theme_art), theme_art, look, scale, state, index)
    else:
        version = {"gtk3": "3.0", "gtk4": "4.0"}[renderer]
        actual = gtk_face(live_gtk(look, scale) / f"caption-gtk-{version}", state, index)
        if look in ("2000", "2001"):
            actual = rgb565(actual)
    directory = visual_output / theme / "caption" / renderer / state / button
    exact(expected, actual, directory, visible_pixels(look, state, expected.size))


@pytest.mark.parametrize("theme", THEMES)
def test_kwin_releasing_outside_the_caption_button_cancels_the_action(theme, svg_themes, live_kwin, visual_output):
    _, metadata = THEMES[theme]
    live_kwin(theme, svg_themes[metadata["look"]])
    source = visual_output / theme / "caption" / "kwin" / "cancelled" / "window-state.json"
    records = json.loads(source.read_text())
    initial_windows = {record["title"]: record for record in records if record["phase"] == "before"}
    final_windows = {record["title"]: record for record in records if record["phase"] == "after"}
    for button, title in zip(BUTTONS, PRESS_TITLES, strict=True):
        assert title in initial_windows, f"KWin did not open {title}"
        assert title in final_windows, f"{title} closed after releasing the caption button outside"
        record = final_windows[title]
        assert record["minimized"] is False, record
        if button == "maximize":
            assert record["bounds"] == pytest.approx(
                initial_windows[title]["bounds"], abs=1 / metadata["caption_scale"]
            ), record


@pytest.mark.parametrize("state", ("rest", "hover", "pressed", "disabled"))
def test_luna_svg_close_glyph_core_matches_windows_pixels(state, svg_themes, visual_output):
    expected, background = face_region(caption_reference("luna"), "luna", state, BUTTONS.index("close"))
    ink = expected.getpixel((expected.width // 2, expected.height // 2))
    solid = np.all(np.asarray(expected) == ink, axis=-1)
    # One pixel of clearance isolates the solid X from its antialiasing and the face outline.
    core = np.asarray(Image.fromarray(solid.astype("uint8") * 255).filter(ImageFilter.MinFilter(3))) == 255
    actual = caption_pixels(svg_themes["luna"], "close", state, "luna", background.resize(expected.size))
    exact(expected, actual, visual_output / "winxp" / "caption" / "svg" / state / "close" / "glyph-core", core)


@pytest.mark.parametrize(
    ("state", "index"), [(state, index) for state in CAPTION_STATES for index in state_buttons(state)]
)
def test_luna_gtk3_caption_keeps_native_size_and_sharper_detail(state, index, live_gtk):
    look, scale = THEMES["winxp"][1]["look"], THEMES["winxp"][1]["caption_scale"]
    expected, _ = face_region(caption_reference(look), look, state, index)
    actual = gtk_face(live_gtk(look, scale) / "caption-gtk-3.0", state, index)
    assert actual.size == expected.size
    mask = visible_pixels(look, state, expected.size)
    difference = np.abs(np.asarray(expected, dtype=int) - np.asarray(actual, dtype=int))
    assert difference[mask].mean() < 22


@pytest.mark.parametrize(
    ("state", "index"), [(state, index) for state in CAPTION_STATES for index in state_buttons(state)]
)
def test_luna_kwin_preserves_the_authored_120dpi_pixels(state, index, svg_themes, live_kwin, visual_output):
    look, scale = THEMES["winxp"][1]["look"], THEMES["winxp"][1]["caption_scale"]
    theme = svg_themes[look]
    button = "restore" if state == "restore" else BUTTONS[index]
    face, background = face_region(caption_reference(look), look, state, index)
    artwork = caption_pixels(theme, button, state, look, background.resize(face.size))
    live = kwin_face(live_kwin("winxp", theme), theme, look, scale, state, index)
    # The corners blend with the live title bar. The opaque interior must
    # land on its authored grid without filtering the glyph or the face.
    mask = np.zeros((face.height, face.width), dtype=bool)
    mask[3:-3, 3:-3] = True
    exact(artwork, live, visual_output / "winxp" / "caption" / "kwin" / state / button / "rasterization", mask)


@pytest.mark.parametrize(("renderer", "limit"), (("kwin", 6), ("gtk4", 18)))
def test_win7_maximized_caption_matches_native_size_and_glass(renderer, limit, svg_themes, live_kwin, live_gtk):
    _, metadata = THEMES["win7"]
    look, scale = metadata["look"], metadata["caption_scale"]
    if renderer == "kwin":
        artwork = svg_themes[look]
        actual = kwin_face(live_kwin("win7", artwork), artwork, look, scale, "restore", 1)
    else:
        actual = gtk_face(live_gtk(look, scale) / "caption-gtk-4.0", "restore", 1)
    expected, _glass = face_region(caption_reference(look), look, "restore", 1)
    assert actual.size == expected.size
    error = np.abs(np.asarray(actual, dtype=int) - np.asarray(expected, dtype=int)).mean()
    assert error < limit, error


@pytest.fixture(scope="module", params=AERO_MATTES)
def aero_caption_matte(request, installed, visual_output):
    matte = request.param
    path = visual_output / "win7" / "caption" / "kwin" / "mattes" / matte
    path.mkdir(parents=True, exist_ok=True)
    session = installed("aero", aero_background=AERO_MATTES[matte], screen=(854, 640))
    scale = 1.5
    # Match the native capture's physical title-bar position. The logical
    # width rounds to a framebuffer one pixel wider than the VM.
    window = 160, 119, 669, 449
    image = show(session, windows=[("Caption matte", "qt", window)], scale=scale)
    image.save(path / "screen.png")
    (path / "effects.txt").write_text(image.info["loaded_effects"])
    return matte, path, image


@pytest.mark.parametrize("layer", ("glass", "buttons"))
def test_aero_kwin_caption_matches_windows_on_the_same_backdrop(layer, aero_caption_matte):
    matte, path, image = aero_caption_matte
    top = tuple(AERO_MATTES).index(matte) * 30
    # The PNG stores the flat background, a neighbouring glass column
    # and then the complete three-button cluster in that order.
    capture = REFERENCES / "win7-sp1-144dpi-caption-mattes.png"
    with Image.open(capture) as reference:
        if layer == "glass":
            expected = reference.crop((1, top, 2, top + 30)).convert("RGB")
            actual = image.crop((800, 181, 801, 211))
        else:
            expected = reference.crop((2, top, 162, top + 30)).convert("RGB")
            actual = image.crop((836, 181, 996, 211))
    exact(expected, actual, path / layer)


def test_aero_native_glass_keeps_the_vm_backdrop_response(aero_caption_matte):
    matte, path, image = aero_caption_matte
    if "'aeroglassblur'" not in image.info["loaded_effects"]:
        pytest.skip("requires the native Aero blur effect")
    top = tuple(AERO_MATTES).index(matte) * 30
    with Image.open(REFERENCES / "win7-sp1-144dpi-caption-mattes.png") as reference:
        regions = (
            ("glass", (1, top, 2, top + 30), (800, 181, 801, 211), 9),
            ("buttons", (2, top, 162, top + 30), (836, 181, 996, 211), 7),
        )
        for name, native_box, kwin_box, limit in regions:
            expected = reference.crop(native_box).convert("RGB")
            actual = image.crop(kwin_box)
            error = np.abs(np.asarray(expected, dtype=int) - np.asarray(actual, dtype=int)).mean()
            assert error < limit, (name, error, path)


@pytest.mark.parametrize("matte", DISABLED_CLOSE_MATTES)
@pytest.mark.parametrize("region", ("face", "lower-rim"))
def test_win7_disabled_close_over_native_glass_matches_windows_pixels(svg_themes, matte, region, visual_output):
    glass, expected = disabled_close_matte(matte)
    actual = caption_pixels(svg_themes["aero"], "close", "disabled", "aero", glass)
    output = visual_output / "win7" / "caption" / "svg" / "disabled" / "close" / matte
    if region == "lower-rim":
        # The straight join starts at Maximize; the opposite end curves up.
        box = (0, expected.height - 1, expected.width - 5, expected.height)
        expected, actual = expected.crop(box), actual.crop(box)
        output /= region
    exact(expected, actual, output)


@pytest.mark.parametrize("version", ("3.0", "4.0"), ids=("gtk3", "gtk4"))
def test_win7_gtk_disabled_close_keeps_its_gtk_geometry_and_clear_surround(version, live_gtk, visual_output):
    _, metadata = THEMES["win7"]
    directory = live_gtk(metadata["look"], metadata["caption_scale"]) / f"caption-gtk-{version}"
    records = json.loads((directory / "caption-crops.json").read_text())
    normal, disabled = (records[f"caption {state}"] for state in ("normal", "disabled"))
    for key in ("allocations", "faces"):
        assert normal[key]["close"] == disabled[key]["close"]
    left, top, right, bottom = normal["allocations"]["close"]
    _, y0, _, y1 = normal["faces"]["close"]
    assert top <= y0 < y1 <= bottom and (top < y0 or y1 < bottom)
    output = visual_output / "win7" / "caption" / f"gtk{version[0]}" / "disabled" / "close"
    with Image.open(directory / normal["frame"]) as before, Image.open(directory / disabled["frame"]) as after:
        for name, start, end in (("above-face", top, y0), ("below-face", y1, bottom)):
            if start < end:
                area = (left, start, right, end)
                exact(before.crop(area), after.crop(area), output / name)


@pytest.mark.parametrize("theme", THEMES)
@pytest.mark.parametrize("index", state_buttons("disabled"), ids=["maximize", "close"])
@pytest.mark.parametrize("action", ("hover", "pressed", "clicked"))
def test_kwin_disabled_caption_interior_matches_its_own_idle_state(
    theme, index, action, live_kwin, svg_themes, visual_output
):
    _, metadata = THEMES[theme]
    look, scale = metadata["look"], metadata["caption_scale"]
    artwork = svg_themes[look]
    capture = live_kwin(theme, artwork)
    idle = kwin_face(capture, artwork, look, scale, "disabled", index)
    state = f"disabled-{action}"
    actual = kwin_face(capture, artwork, look, scale, state, index)
    # Fractional-scale compositing can change the title pixels under the
    # antialiased edge. Here we compare the glyph and solid face.
    face = (3, 3, idle.width - 3, idle.height - 3)
    directory = visual_output / theme / "caption" / "kwin" / "pointer-invariance" / action / BUTTONS[index]
    exact(idle.crop(face), actual.crop(face), directory)


@pytest.mark.parametrize("index", state_buttons("disabled"), ids=["maximize", "close"])
def test_win7_kwin_disabled_caption_dims_the_glyph(index, svg_themes, live_kwin):
    _, metadata = THEMES["win7"]
    look, scale = metadata["look"], metadata["caption_scale"]
    artwork = svg_themes[look]
    capture = live_kwin("win7", artwork)
    reference = caption_reference(look)
    active, _ = face_region(reference, look, "rest", index)
    disabled, _ = face_region(reference, look, "disabled", index)
    active, disabled = (np.asarray(image, dtype=int) for image in (active, disabled))
    glyph = (active.min(axis=2) >= 230) & ((active - disabled).mean(axis=2) > 25)
    glyph[:4] = glyph[-4:] = False
    glyph[:, :7] = glyph[:, -7:] = False
    assert glyph.any()
    idle = np.asarray(kwin_face(capture, artwork, look, scale, "rest", index), dtype=int)
    unavailable = np.asarray(kwin_face(capture, artwork, look, scale, "disabled", index), dtype=int)
    assert (idle[glyph] - unavailable[glyph]).mean() > 20


@pytest.fixture(scope="module")
def aero_run_capture(tmp_path_factory):
    folder, metadata = THEMES["win7"]
    output = tmp_path_factory.mktemp("aero-run")
    subprocess.run(
        [
            sys.executable,
            str(REPO / "tests/aero/render_aero_dialogs.py"),
            str(output),
            str(metadata["run_scale"]),
            "--only-run",
        ],
        check=True,
        timeout=45,
    )
    with Image.open(folder / "run.png") as reference, Image.open(output / "run.png") as render:
        return reference.convert("RGB"), render.convert("RGB")


@pytest.fixture
def run_dialog_images(theme, qt_app, svg_themes, request, monkeypatch):
    import chicago95ui

    folder, metadata = THEMES[theme]
    look = metadata["look"]
    if look == "aero":
        return request.getfixturevalue("aero_run_capture")
    with Image.open(folder / "run.png") as reference:
        expected = reference.crop(metadata["run_crop"]) if "run_crop" in metadata else reference.convert("RGB")
    monkeypatch.setattr(chicago95ui, "DECORATION", svg_themes[look])
    with themed(qt_app, look):
        if metadata.get("run_states", {}).get("flat_title"):
            # Both Windows 98 captures use the guest's solid active caption.
            with Path(chicago95ui.KDEGLOBALS).open("a") as settings:
                settings.write("\n[WM]\nactiveBlend=0,0,128\n")
        dialog = load_script("chicago95-run").RunDialog({"style": look, "osName": "Windows"}, [], [], history=[])
        try:
            dialog.show()
            qt_app.processEvents()
            actual = qimage_to_pil(dialog.grab().toImage())
        finally:
            dialog.close()
    if look == "2000":
        actual = rgb565(actual)
    return expected, actual


@pytest.mark.parametrize("theme", THEMES)
def test_run_dialog(theme, run_dialog_images, visual_output):
    exact(*run_dialog_images, visual_output / theme / "run" / "qt")


@pytest.mark.parametrize("theme", ("win95", "win98"))
def test_run_9x_dialog_frame_and_caption_buttons_match_native(theme, run_dialog_images):
    expected, actual = run_dialog_images
    w, h = expected.size
    for name, bounds in {
        "top frame": (0, 0, w, 3),
        "left frame": (0, 3, 3, h),
        "right frame": (w - 3, 3, w, h),
        "bottom frame": (0, h - 3, w, h),
        "Help and Close": (w - 39, 5, w - 5, 19),
    }.items():
        assert np.array_equal(expected.crop(bounds), actual.crop(bounds)), name


@pytest.mark.parametrize("theme", ("win95", "win98"))
def test_run_9x_history_button_and_field_bevel_match_native(theme, run_dialog_images):
    expected, actual = run_dialog_images
    # Leave the blinking insertion caret outside the bevel comparison.
    bounds = (64, 82, 332, 103)
    assert np.array_equal(expected.crop(bounds), actual.crop(bounds))


@pytest.mark.parametrize("theme", ("win95", "win98"))
def test_run_9x_imported_font_matches_native_labels(theme, run_dialog_images):
    from PySide6.QtGui import QFontDatabase

    if f"Chicago95 Windows {theme[-2:]}" not in QFontDatabase.families():
        pytest.skip("Import the fonts from the reference VM with setup/import-win9x-fonts.py")
    expected, actual = run_dialog_images
    for bounds in ((4, 4, 35, 19), (55, 38, 333, 69), (10, 85, 49, 101), (109, 127, 331, 143)):
        np.testing.assert_array_equal(np.asarray(actual.crop(bounds)), np.asarray(expected.crop(bounds)))


@pytest.mark.parametrize("theme", ("win2k", "winxp-classic", "winxp"))
def test_run_tahoma_prompt_matches_native_pixels(theme, run_dialog_images):
    from PySide6.QtGui import QFontDatabase

    family = "Chicago95 Windows 2000 Tahoma" if theme == "win2k" else "Tahoma"
    if not QFontDatabase.hasFamily(family):
        pytest.skip("Import the VM fonts with setup/import-windows-nt-fonts.py")
    expected, actual = run_dialog_images
    bounds = (55, 19, 330, 48) if theme == "winxp" else (55, 38, 337, 69)
    np.testing.assert_array_equal(np.asarray(actual.crop(bounds)), np.asarray(expected.crop(bounds)))


@pytest.mark.parametrize("theme", ("win2k", "winxp-classic"))
def test_run_classic_browse_mnemonic_matches_native_pixels(theme, run_dialog_images):
    from PySide6.QtGui import QFontDatabase

    family = "Chicago95 Windows 2000 Tahoma" if theme == "win2k" else "Tahoma"
    if not QFontDatabase.hasFamily(family):
        pytest.skip("Import the VM fonts with setup/import-windows-nt-fonts.py")
    expected, actual = run_dialog_images
    bounds = (266, 142, 327, 154)
    np.testing.assert_array_equal(np.asarray(actual.crop(bounds)), np.asarray(expected.crop(bounds)))


def test_run_win7_browse_mnemonic_matches_native_underline(aero_run_capture):
    # The background gradient has its own comparison. Compare the dark
    # underline including the surrounding empty rows and columns.
    bounds = (449, 248, 469, 254)
    masks = [np.asarray(image.crop(bounds)).max(axis=2) < 96 for image in aero_run_capture]
    np.testing.assert_array_equal(*masks)


@pytest.mark.parametrize(
    ("bounds", "max_error"),
    [((187, 231, 246, 253), 6.8), ((310, 231, 392, 253), 10.6)],
    ids=("ok", "cancel"),
)
def test_run_win7_caption_pixels_align_with_native(aero_run_capture, bounds, max_error):
    data_home = Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local/share"))
    if not (data_home / "fonts/Chicago95/Windows7/segoeui.ttf").is_file():
        pytest.skip("Import the Windows 7 fonts with setup/import-windows-nt-fonts.py")
    expected, actual = (np.asarray(image.crop(bounds), dtype=np.int16) for image in aero_run_capture)
    # Sample the face left of each label so the separate gradient difference
    # does not dominate the glyph alignment measurement.
    expected_ink = np.maximum(np.median(expected[:, :3], axis=1, keepdims=True) - expected, 0)
    actual_ink = np.maximum(np.median(actual[:, :3], axis=1, keepdims=True) - actual, 0)
    assert np.abs(expected_ink - actual_ink).mean() < max_error


def test_run_win7_history_arrow_matches_native_geometry(aero_run_capture, visual_output):
    images = [image.crop((524, 127, 544, 138)) for image in aero_run_capture]
    bounds = [bounding_box(image, lambda rgb: max(rgb) < 128) for image in images]
    assert all(bounds), bounds
    original, generated = bounds
    assert all(abs(a - b) <= 1 for a, b in zip(original, generated, strict=True)), bounds
    expected, actual = (np.asarray(image, dtype=np.int16) for image in images)
    assert np.abs(expected - actual).mean() < 12
    output = visual_output / "win7" / "run" / "qt" / "history-arrow"
    output.mkdir(parents=True, exist_ok=True)
    images[0].save(output / "reference.png")
    images[1].save(output / "rendered.png")


def test_run_win7_white_pane_matches_native_edges(aero_run_capture, visual_output):
    expected, actual = aero_run_capture
    for side, bounds in {
        "top": (0, 0, 568, 2),
        "left": (0, 2, 2, 190),
        "right": (566, 2, 568, 190),
        "bottom": (0, 189, 568, 191),
    }.items():
        exact(expected.crop(bounds), actual.crop(bounds), visual_output / "win7/run/qt/pane" / side)


@pytest.mark.parametrize("left", (156, 291, 426), ids=("ok", "cancel", "browse"))
def test_run_win7_action_button_face_matches_native(aero_run_capture, left):
    # A strip clear of the caption, including both outer edges and the complete gradient.
    strip = (left + 8, 219, left + 18, 263)
    expected, actual = (np.asarray(image.crop(strip), dtype=np.int16) for image in aero_run_capture)
    assert np.abs(expected - actual).mean() < 3
    assert np.array_equal(expected[[0, 1, -2, -1]], actual[[0, 1, -2, -1]])


RUN_STATES = [
    (theme, state)
    for theme, (_, metadata) in THEMES.items()
    for state in metadata.get("run_states", {}).get("text", {})
]


@pytest.fixture(scope="module")
def native_run_states(tmp_path_factory):
    @cache
    def capture(theme, state):
        folder, metadata = THEMES[theme]
        scale = metadata["run_states"]["scale"]
        dpi = round(scale * 96)
        name = f"{dpi}dpi-{state}"
        with Image.open(folder / "run" / f"{name}.png") as reference:
            expected = reference.convert("RGB")
        frame = tmp_path_factory.mktemp("run-state") / "run.png"
        render_properties(folder, f"run-{state}", frame, expected.size, scale=scale)
        with Image.open(frame) as render:
            actual = rgb565(render) if metadata["run_states"].get("rgb565") else render.convert("RGB")
        return expected, actual, name

    return capture


@pytest.mark.parametrize(("theme", "state"), RUN_STATES)
def test_run_native_states(theme, state, native_run_states, visual_output):
    expected, actual, name = native_run_states(theme, state)
    exact(expected, actual, visual_output / theme / "run" / "qt" / name)


def test_run_luna_browse_mnemonic_matches_native_glyphs_at_120dpi(qt_app, native_run_states):
    from PySide6.QtGui import QFontDatabase

    if not QFontDatabase.hasFamily("Tahoma"):
        pytest.skip("Import the VM fonts with setup/import-windows-nt-fonts.py")
    expected, actual, _ = native_run_states("winxp", "empty")
    bounds = (308, 148, 373, 163)
    masks = [np.asarray(image.crop(bounds)).max(axis=2) < 96 for image in (actual, expected)]
    np.testing.assert_array_equal(*masks)


def test_run_win98_high_dpi_frame_keeps_native_pixel_width(native_run_states):
    expected, actual, _ = native_run_states("win98", "empty")
    w, h = expected.size
    for bounds in ((0, 0, w, 3), (0, 3, 4, h - 3), (w - 4, 3, w, h - 3), (0, h - 3, w, h)):
        np.testing.assert_array_equal(np.asarray(expected.crop(bounds)), np.asarray(actual.crop(bounds)))


def test_run_win98_high_dpi_caption_matches_native_font(qt_app, native_run_states):
    from PySide6.QtGui import QFontDatabase

    if "Chicago95 Windows 98 120 DPI" not in QFontDatabase.families():
        pytest.skip("Import the fonts from the reference VM with setup/import-win9x-fonts.py")
    expected, actual, _ = native_run_states("win98", "empty")
    bounds = (4, 4, 50, 25)
    np.testing.assert_array_equal(np.asarray(actual.crop(bounds)), np.asarray(expected.crop(bounds)))


@pytest.mark.parametrize("state", ("empty", "typed"))
def test_run_win98_high_dpi_button_labels_match_native(qt_app, native_run_states, state):
    from PySide6.QtGui import QFontDatabase

    if not QFontDatabase.hasFamily("Chicago95 Windows 98 120 DPI"):
        pytest.skip("Import the fonts from the reference VM with setup/import-win9x-fonts.py")
    expected, actual, _ = native_run_states("win98", state)
    for bounds in ((142, 158, 200, 176), (247, 158, 310, 177), (351, 158, 424, 181)):
        np.testing.assert_array_equal(np.asarray(actual.crop(bounds)), np.asarray(expected.crop(bounds)))


def test_winxp_run_focus_dots_match_native(native_run_states, visual_output):
    focused = native_run_states("winxp", "ok-focus")[:2]
    typed = native_run_states("winxp", "typed")[:2]
    bounds = (110, 140, 196, 167)
    deltas = [
        Image.fromarray(np.asarray(focus.crop(bounds)) ^ np.asarray(base.crop(bounds)))
        for focus, base in zip(focused, typed, strict=True)
    ]
    exact(*deltas, visual_output / "winxp/run/qt/ok-focus-dots")


def test_winxp_run_default_rim_follows_keyboard_focus(native_run_states, visual_output):
    for state in ("typed", "cancel-focus"):
        expected, actual, _ = native_run_states("winxp", state)
        for button, left in (("ok", 118), ("cancel", 211)):
            for edge, top, bottom in (("top", 141, 143), ("bottom", 164, 167)):
                bounds = (left, top, left + 10, bottom)
                output = visual_output / "winxp/run/qt/default-rim" / state / button / edge
                exact(expected.crop(bounds), actual.crop(bounds), output)


@pytest.mark.parametrize(
    ("theme", "state"),
    [(theme, state) for theme, state in RUN_STATES if "default_button_bevel" in THEMES[theme][1]["run_states"]],
)
def test_run_native_default_button_bevel(theme, state, native_run_states, visual_output):
    expected, actual, name = native_run_states(theme, state)
    bounds = THEMES[theme][1]["run_states"]["default_button_bevel"]
    for index, box in enumerate(bounds):
        output = visual_output / theme / "run" / "qt" / name / f"bevel-{index}"
        exact(expected.crop(box), actual.crop(box), output)


RUN_HISTORY_THEMES = [theme for theme, (folder, _) in THEMES.items() if (folder / "run/history.json").is_file()]


@pytest.fixture(scope="module")
def run_history_popup(tmp_path_factory):
    @cache
    def capture(theme, state):
        folder, metadata = THEMES[theme]
        scale = json.loads((folder / "run/history.json").read_text())["scale"]
        with Image.open(folder / "run" / f"history-{state}.png") as reference:
            expected = reference.convert("RGB")
        frame = tmp_path_factory.mktemp("run-history") / "popup.png"
        render_properties(folder, f"run-history-{state}", frame, expected.size, scale=scale)
        with Image.open(frame) as render:
            actual = render.convert("RGB")
        return expected, rgb565(actual) if metadata["look"] in ("2000", "2001", "luna") else actual

    return capture


@pytest.mark.parametrize("theme", RUN_HISTORY_THEMES)
@pytest.mark.parametrize("state", ("open", "down"))
def test_run_history_popup(theme, state, run_history_popup, visual_output):
    expected, actual = run_history_popup(theme, state)
    exact(expected, actual, visual_output / theme / "run/qt" / f"history-{state}")


@pytest.mark.parametrize(("theme", "font_suffix", "text_edge"), (("win95", "", 258), ("win98", " 120 DPI", 345)))
def test_run_history_matches_native_text_with_imported_font(theme, font_suffix, text_edge, qt_app, run_history_popup):
    from PySide6.QtGui import QFontDatabase

    if f"Chicago95 Windows {theme[-2:]}{font_suffix}" not in QFontDatabase.families():
        pytest.skip("Import the fonts from the reference VM with setup/import-win9x-fonts.py")
    for state in ("open", "down"):
        expected, actual = run_history_popup(theme, state)
        bounds = (0, 0, text_edge, expected.height)
        np.testing.assert_array_equal(np.asarray(actual.crop(bounds)), np.asarray(expected.crop(bounds)))


@pytest.mark.parametrize("theme", RUN_HISTORY_THEMES)
def test_run_history_native_frame_and_highlight_rows(theme, run_history_popup, visual_output):
    for state in ("open", "down"):
        expected, actual = run_history_popup(theme, state)
        assert actual.size == expected.size
        width, height = expected.size
        output = visual_output / theme / "run/qt" / f"history-{state}"
        for side, frame in {
            "top": (0, 0, width, 1),
            "bottom": (0, height - 1, width, height),
            "left": (0, 1, 1, height - 1),
            "right": (width - 1, 1, width, height - 1),
        }.items():
            exact(expected.crop(frame), actual.crop(frame), output / "frame" / side)
        # The first two commands leave this column blank, including when selected.
        bounds = (200, 0, 201, 2 * (13 if theme == "win95" else 16) + 2)
        exact(expected.crop(bounds), actual.crop(bounds), output / "highlight-rows")


def test_win98_run_history_labels_keep_the_native_origin_and_colours(run_history_popup):
    for state in ("open", "down"):
        expected, actual = run_history_popup("win98", state)
        for y in (1, 17):
            bounds = (1, y, 200, y + 16)
            measured = []
            for image in (expected, actual):
                pixels = np.asarray(image.crop(bounds))
                rows, columns = np.where(np.any(pixels != pixels[0, -1], axis=2))
                colours = np.unique(pixels.reshape(-1, 3), axis=0).tolist()
                measured.append((rows.min(), columns.min(), colours))
            assert measured[0] == measured[1]


def test_luna_run_history_disabled_scrollbar_matches_the_native_colours(run_history_popup):
    expected, actual = run_history_popup("winxp", "open")
    for box in ((303, 4, 315, 17), (303, 193, 315, 206)):
        left, right = (np.asarray(image.crop(box), dtype=int) for image in (expected, actual))
        assert np.abs(left - right).mean() < 8


@pytest.mark.parametrize(("theme", "extent"), (("win95", 16), ("win98", 20), ("win2k", 20), ("winxp-classic", 20)))
def test_classic_run_history_scrollbar_track_matches_the_native_pixels(theme, extent, run_history_popup, visual_output):
    expected, actual = run_history_popup(theme, "open")
    width, height = expected.size
    bounds = (width - extent - 1, extent + 1, width - 1, height - extent - 1)
    exact(expected.crop(bounds), actual.crop(bounds), visual_output / theme / "run/qt/history-open/scrollbar-track")


def test_run_history_wayland_uses_the_120dpi_field_and_popup(installed, visual_output):
    folder, metadata = THEMES["win2k"]
    spec = json.loads((folder / "run/history.json").read_text())
    session = installed(metadata["look"], spec["scale"], screen=(800, 600), components=("startmenu",))
    config = session.work / "home/.config"
    (config / "chicago95/run-history").write_text("\n".join(spec["entries"]) + "\n")
    (config / "kwinrulesrc").write_text(
        "[General]\nrules=run-capture\n[run-capture]\nwmclass=chicago95-run\nwmclassmatch=1\n"
        "position=80,60\npositionrule=2\nnoborder=true\nnoborderrule=2\n"
    )
    script = session.work / "run-history.sh"
    script.write_text(
        "#!/bin/sh\nset -eu\n"
        '"$HOME/.local/bin/chicago95-run" --dry-run >"$WORK/run-history-app.log" 2>&1 &\n'
        "for attempt in 1 2 3 4 5 6; do\n"
        '    sleep 1\n'
        '    spectacle -b -n -f -o "$WORK/run-history-closed.png"\n'
        "    python3 -c 'from PIL import Image; import sys; "
        'sys.exit(Image.open("run-history-closed.png").convert("RGB").getbbox() is None)\' && break\n'
        "done\n"
        'python3 "$WORK/eis_pointer.py" move:385,152 click:left move:60,40 wait:0.4 snapshot:run-history-open\n'
    )
    run_session(session.work, script, session.environment, session.screen, scale=spec["scale"])
    output = visual_output / "win2k/run/wayland/history"
    output.mkdir(parents=True, exist_ok=True)
    frames = []
    for state in ("closed", "open"):
        with Image.open(session.work / f"run-history-{state}.png") as frame:
            image = frame.convert("RGB")
        image.save(output / f"{state}.png")
        frames.append(image)
    before, after = frames
    changed = ImageChops.difference(before, after).getbbox()
    assert changed, output
    left, first, right, bottom = changed
    assert (right - left) == 320, (changed, output)
    # The last black line is invisible outside the window over the black desktop.
    for top in range(first, bottom):
        if after.crop((left, top, right, top + 1)).getbbox() is None:
            break
    else:
        pytest.fail(f"Run did not draw the popup's top edge. See {output}")
    popup = rgb565(after.crop((left, top, right, bottom + 1)))
    with Image.open(folder / "run/history-open.png") as frame:
        native = frame.convert("RGB")
    assert popup.size == native.size, (popup.size, native.size, output)
    rows = (200, 0, 201, 34)
    exact(native.crop(rows), popup.crop(rows), output / "highlight-rows")


@pytest.mark.parametrize("theme", THEMES)
def test_taskbar_band(theme, installed, visual_output):
    folder, metadata = THEMES[theme]
    with Image.open(folder / "taskbar-band.png") as reference:
        expected = reference.convert("RGB")
    size = tuple(metadata["taskbar_band_screen"])
    screen = show(installed(metadata["look"], screen=size), windows=[], tray_icons=0)
    assert screen.size == size
    x = metadata["taskbar_x"]
    actual = screen.crop((x, screen.height - expected.height, x + expected.width, screen.height))
    if metadata.get("taskbar_band_rgb565"):
        actual = rgb565(actual)
    elif metadata.get("taskbar_band_indexed_grey"):
        # The guest maps the light bevel to silver in its 256-colour mode.
        pixels = np.array(actual)
        pixels[np.all(pixels == 223, axis=2)] = 192
        actual = Image.fromarray(pixels)
    exact(expected, actual, visual_output / theme / "taskbar" / "plasma" / "empty-band")


@pytest.mark.parametrize("theme", [name for name, (_, data) in THEMES.items() if "taskbar_truecolor" in data])
def test_truecolor_taskbar_band(theme, installed, visual_output):
    folder, metadata = THEMES[theme]
    spec = metadata["taskbar_truecolor"]
    scale = spec["scale"]
    size = tuple(round(value / scale) for value in spec["screen"])
    frame = show(installed(metadata["look"], scale, screen=size), windows=[], tray_icons=0, scale=scale)
    assert frame.size == tuple(spec["screen"])
    with Image.open(folder / "taskbar/truecolor-band.png") as reference:
        expected = reference.convert("RGB")
    x = spec["x"]
    actual = frame.crop((x, frame.height - expected.height, x + expected.width, frame.height))
    exact(expected, actual, visual_output / theme / "taskbar/plasma/truecolor-band")


START_BUTTON_STATES = ("idle", "held-outside", "released-outside", "dismissed")
START_BUTTON_THEMES = [name for name, (_, data) in THEMES.items() if "start_button" in data]


@pytest.fixture(scope="module")
def start_button_states(installed):
    @cache
    def capture(theme):
        _folder, metadata = THEMES[theme]
        spec = metadata["start_button"]
        scale = spec["scale"]
        screen_size = tuple(round(value / scale) for value in spec["screen"])
        left, top, right, bottom = spec["bounds"]
        x, y = round((left + right) / (2 * scale)), round((top + bottom) / (2 * scale))
        away = f"move:{screen_size[0] * 3 // 4},{screen_size[1] // 4}"
        session = installed(metadata["look"], scale, screen=screen_size, components=("startmenu",))
        frame = show(
            session, windows=[], scale=scale,
            pointer_steps=(
                away, "wait:0.4", "snapshot:start-idle",
                f"move:{x},{y}", "press:left", "wait:0.4",
                away, "wait:0.4", "snapshot:start-held-outside",
                "release:left", "wait:0.4", "snapshot:start-released-outside",
                "click:left", "wait:0.6", "snapshot:start-dismissed",
            ),
        )
        assert frame.size == tuple(spec["screen"])
        captures = {}
        for state in START_BUTTON_STATES:
            with Image.open(session.work / f"start-{state}.png") as image:
                crop = image.convert("RGB").crop((left, top, right, bottom))
                captures[state] = rgb565(crop) if spec.get("rgb565") else crop
        return captures

    return capture


@pytest.mark.parametrize("theme", START_BUTTON_THEMES)
@pytest.mark.parametrize("state", START_BUTTON_STATES)
def test_start_button_states(theme, state, start_button_states, visual_output):
    folder, _metadata = THEMES[theme]
    with Image.open(folder / "taskbar" / "start-button" / f"{state}.png") as reference:
        expected = reference.convert("RGB")
    exact(expected, start_button_states(theme)[state], visual_output / theme / "taskbar/plasma/start-button" / state)


@pytest.mark.parametrize("theme", START_BUTTON_THEMES)
def test_start_button_stays_pressed_until_the_menu_closes(theme, start_button_states):
    folder, _metadata = THEMES[theme]
    captures = start_button_states(theme)

    def bevel(image):
        midpoint = image.width // 2
        return np.asarray(image, dtype=np.int16)[:, midpoint - 2 : midpoint + 3].mean(axis=(1, 2))

    def matches_state(captures):
        idle = bevel(captures["idle"])
        # Inspect the surface, independently of one-pixel artwork offsets in the full-crop checks.
        rows = slice(0, 5) if theme == "winxp" else slice(-2, None)
        for state in ("held-outside", "released-outside"):
            change = (bevel(captures[state]) - idle)[rows]
            if theme == "winxp":
                assert change.mean() < -15, state
            else:
                assert change.max() > 15, state
        assert np.max(np.abs((bevel(captures["dismissed"]) - idle)[rows])) < 5

    refs = {}
    for state in START_BUTTON_STATES:
        with Image.open(folder / "taskbar" / "start-button" / f"{state}.png") as reference:
            refs[state] = reference.convert("RGB")
    matches_state(refs)
    matches_state(captures)


@pytest.mark.parametrize("theme", ("win95", "win98"))
def test_start_button_focus_outline_follows_the_menu(theme, start_button_states):
    folder, _metadata = THEMES[theme]

    def dots(image):
        # This strip sits inside the top bevel and above the logo and label.
        ink = np.asarray(image)[2:5, 8:-8].max(axis=2) < 50
        return np.count_nonzero(ink[:, 1:] != ink[:, :-1], axis=1).max()

    reference_folder = folder / "taskbar" / "start-button"
    captures = start_button_states(theme)
    for state, visible in (("idle", False), ("held-outside", True), ("released-outside", True), ("dismissed", False)):
        with Image.open(reference_folder / f"{state}.png") as reference:
            assert (dots(reference.convert("RGB")) > 12) == visible
        assert (dots(captures[state]) > 12) == visible, state


@pytest.fixture(scope="module")
def desktop_scenes(installed, visual_output):
    @cache
    def capture(theme, scene, samples="desktop_samples"):
        _, metadata = THEMES[theme]
        spec = metadata[samples]
        look, scale = metadata["look"], spec["scale"]
        width, height = (round(value / scale) for value in spec["screen"])
        backdrop = "#4395D1" if look == "aero" and scene != "wallpaper" else None
        components = ("background", "desktop", "startmenu") if scene == "run" else ("background", "desktop")
        session = installed(
            look, scale, aero_background=backdrop, screen=(width, height),
            components=components, launchers=tuple(spec["launchers"]),
        )
        output = visual_output / theme / "desktop" / "plasma"
        if samples != "desktop_samples":
            output /= samples
        output.mkdir(parents=True, exist_ok=True)
        if scene in ("menu", "hover"):
            x, y = width // 3, height // 3
            opening = right_click_at(x, y)
            if scene == "hover":
                row_offset = 120 if look == "aero" else 100
                hovered = show(
                    session, windows=[], scale=scale,
                    pointer_steps=(*opening, *hover_steps((x + 100, y + row_offset))),
                )
                hovered.save(output / "hover-screen.png")
                return hovered
            steps = ("move:20,400", "wait:0.5", "snapshot:desktop-idle", *opening)
            menu = show(session, windows=[], scale=scale, pointer_steps=steps)
            idle = Image.open(session.work / "desktop-idle.png").convert("RGB")
            idle.save(output / "idle-screen.png")
            menu.save(output / "menu-screen.png")
            # The clock and desktop icons are outside the part occupied by the popup.
            region = (round(x * scale) - 10, 0, menu.width, menu.height - 52)
            changed = ImageChops.difference(idle.crop(region), menu.crop(region)).getbbox()
            assert changed is not None, f"The desktop right click opened no menu. See {output}"
            left, top, right, bottom = changed
            bounds = (left + region[0], top, right + region[0], bottom)
            return idle, menu.crop(bounds), bounds
        if scene == "run":
            history = session.work / HOME_AFTER_SETUP / ".config/chicago95/run-history"
            history.parent.mkdir(parents=True, exist_ok=True)
            history.write_text(spec["run"]["text"] + "\n")
            left, top, right, bottom = (round(value / scale) for value in spec["run"]["bounds"])
            result = show(
                session, windows=[("Run", "run", (left, top, right - 1, bottom - 1))], scale=scale,
                active_window="", window_state=True,
            )
            windows = [
                json.loads(line.split("c95-window ", 1)[1])
                for line in result.info["kwin_log"].splitlines() if "c95-window " in line
            ]
            assert any(window["phase"] == "after" and window["title"] == "Run" for window in windows), (
                "The native reference contains Run, but the live scene did not open it."
            )
        elif scene == "wallpaper":
            result = show(session, windows=[], scale=scale)
        else:
            title = "Screen Resolution" if look == "aero" else "Untitled - Notepad"
            icon = "preferences-desktop-display" if look == "aero" else "accessories-text-editor"
            bounds = (100, 60, min(699, width - 2), min(540, height - 85))
            result = show(session, windows=[(title, "qt", bounds, "org.chicago95.test.document", icon)], scale=scale)
        result.save(output / f"{scene}-screen.png")
        return result

    return capture


@pytest.mark.parametrize("theme", THEMES)
@pytest.mark.parametrize("state", ("idle", "context-menu", "populated-taskbar"))
def test_desktop_surface(theme, state, desktop_scenes, visual_output):
    folder, metadata = THEMES[theme]
    spec = metadata["desktop_samples"]
    mask = None
    if state == "populated-taskbar":
        reference = folder / "taskbar/populated.png"
        rendered = desktop_scenes(theme, "populated")
        with Image.open(reference) as image:
            actual = rendered.crop((0, rendered.height - image.height, image.width, rendered.height))
        output = visual_output / theme / "taskbar" / "plasma" / "populated"
    else:
        if state == "idle":
            reference = folder / "desktop.png"
            if "run" in spec:
                screen = desktop_scenes(theme, "run")
            else:
                screen = desktop_scenes(theme, "wallpaper") if theme == "win7" else desktop_scenes(theme, "menu")[0]
            with Image.open(reference) as image:
                actual = screen.crop((0, 0, *image.size))
            cursor = spec.get("cursor")
        else:
            reference = folder / "desktop/context-menu.png"
            actual = desktop_scenes(theme, "menu")[1]
            # The captured cursor was at the menu's top-left edge.
            cursor = (0, 0, 22, 24) if "cursor" in spec else None
        output = visual_output / theme / "desktop" / "plasma" / state
        if cursor:
            with Image.open(reference) as image:
                mask = np.ones((image.height, image.width), dtype=bool)
            left, top, right, bottom = cursor
            mask[top:bottom, left:right] = False
    with Image.open(reference) as image:
        expected = image.convert("RGB")
    if metadata["look"] in ("2000", "2001", "luna"):
        actual = rgb565(actual)
    exact(expected, actual, output, mask)


@pytest.mark.parametrize("theme", ("win2k", "winxp-classic"))
def test_classic_desktop_menu_face_matches_the_vm(theme, desktop_scenes):
    def face(image):
        colours = image.convert("RGB").getcolors(image.width * image.height)
        return max(colours)[1]

    folder, _ = THEMES[theme]
    with Image.open(folder / "desktop/context-menu.png") as expected:
        _, rendered, _ = desktop_scenes(theme, "menu")
        assert face(rgb565(rendered)) == face(expected)


def desktop_hover_row(theme, desktop_scenes, samples="desktop_samples"):
    _, idle, menu_bounds = desktop_scenes(theme, "menu", samples)
    highlighted = desktop_scenes(theme, "hover", samples).crop(menu_bounds)
    # The right gutter catches the colour and height of the row independently of its command label.
    x = idle.width - 20
    strip = (x, 0, x + 1, idle.height)
    bounds = ImageChops.difference(idle.crop(strip), highlighted.crop(strip)).getbbox()
    assert bounds, "Moving across the open desktop menu did not highlight a row"
    row = (0, bounds[1], idle.width, bounds[3])
    changes = ImageChops.difference(idle.crop(row), highlighted.crop(row)).getbbox()
    return highlighted.crop(row), changes


@pytest.mark.parametrize("theme", THEMES)
def test_desktop_menu_hover_band(theme, desktop_scenes, visual_output):
    folder, metadata = THEMES[theme]
    row, _changes = desktop_hover_row(theme, desktop_scenes)
    x = row.width - 20
    actual = row.crop((x, 0, x + 1, row.height))
    if metadata["look"] in ("2000", "2001", "luna"):
        actual = rgb565(actual)
    with Image.open(folder / "desktop/hover-band.png") as reference:
        exact(reference.convert("RGB"), actual, visual_output / theme / "desktop" / "plasma" / "hover-band")


def test_win95_desktop_menu_hover_at_96dpi(desktop_scenes, visual_output):
    row, _changes = desktop_hover_row("win95", desktop_scenes, "desktop_menu_96dpi")
    x = row.width - 20
    reference = THEMES["win95"][0] / "desktop/hover-band-96dpi.png"
    with Image.open(reference) as frame:
        expected = frame.convert("RGB")
    exact(expected, row.crop((x, 0, x + 1, row.height)), visual_output / "win95/desktop/plasma/hover-band-96dpi")


def test_win7_desktop_menu_hover_has_rounded_edges(desktop_scenes, visual_output):
    row, changes = desktop_hover_row("win7", desktop_scenes)
    right = changes[2]
    actual = row.crop((right - 4, 0, right, row.height))
    reference = THEMES["win7"][0] / "desktop/context-menu.png"
    with Image.open(reference) as frame:
        expected = frame.convert("RGB").crop((160, 159, 164, 181))
    assert actual.size == expected.size
    output = visual_output / "win7/desktop/plasma/hover-edge"
    output.mkdir(parents=True, exist_ok=True)
    expected.save(output / "reference.png")
    actual.save(output / "rendered.png")
    error = np.abs(np.asarray(actual, dtype=int) - np.asarray(expected, dtype=int)).mean()
    assert error < 1, (error, output)


def test_win7_desktop_menu_icon_gutter_matches_native_pixels(desktop_scenes, visual_output):
    _, actual, _ = desktop_scenes("win7", "menu")
    # The end of the icon gutter and the two separator lines beside the first command.
    bounds = (25, 4, 31, 24)
    with Image.open(THEMES["win7"][0] / "desktop/context-menu.png") as reference:
        native = reference.convert("RGB")
    expected = native.crop(bounds)
    exact(expected, actual.crop(bounds), visual_output / "win7/desktop/plasma/icon-gutter")
    # A translucent Plasma QMenu still needs an opaque two-pixel pad around the items.
    trim = (40, 1, 100, 3)
    error = np.abs(np.asarray(native.crop(trim), dtype=int) - np.asarray(actual.crop(trim), dtype=int))
    assert error.max() <= 5


def test_win7_desktop_menu_submenu_arrow(desktop_scenes, visual_output):
    _, menu, _ = desktop_scenes("win7", "menu")

    def arrow(frame):
        return frame.crop((frame.width - 24, 6, frame.width - 5, 21))

    with Image.open(THEMES["win7"][0] / "desktop/context-menu.png") as reference:
        expected = arrow(reference.convert("RGB"))
    actual = arrow(menu)
    output = visual_output / "win7/desktop/plasma/submenu-arrow"
    output.mkdir(parents=True, exist_ok=True)
    expected.save(output / "reference.png")
    actual.save(output / "rendered.png")
    wanted, drawn = np.asarray(expected), np.asarray(actual)
    # Compare the silhouette at half coverage and the solid ink inside the SVG arrow.
    assert np.array_equal(wanted[..., 0] < 140, drawn[..., 0] < 140), output
    assert np.array_equal(wanted[7, 8], drawn[7, 8]), output


@pytest.mark.parametrize("theme", THEMES)
def test_taskbar_has_the_native_panel_height_at_the_sampled_scale(theme, desktop_scenes):
    folder, metadata = THEMES[theme]
    frame = desktop_scenes(theme, "populated")
    x = frame.width // 2 + 10
    bottom = frame.height
    wallpaper = frame.getpixel((x, bottom - 64))

    def panel_row(y):
        red, green, blue = frame.getpixel((x, y))
        if metadata["look"] == "luna":
            return blue >= 140 and red <= 110 and blue - green > 50
        return (red, green, blue) != wallpaper

    start = next((y for y in range(bottom - 60, bottom) if panel_row(y)), None)
    assert start is not None, "The taskbar did not paint along the measured screen column"
    with Image.open(folder / "taskbar/populated.png") as native:
        # Plasma accepts whole logical pixels. At a fractional scale their physical position
        # can round to either neighbouring screen row.
        slack = int(metadata["desktop_samples"]["scale"] % 1 != 0)
        assert abs(bottom - start - native.height) <= slack, (bottom - start, native.height)


@pytest.mark.parametrize("theme", [theme for theme in THEMES if theme != "win7"])
def test_taskbar_single_active_button_width(theme, desktop_scenes):
    folder, _ = THEMES[theme]

    def painted_width(image):
        # Leave out the top seam and the bottom bevel. The third repeated sample
        # row separates the active button from thin letters and free-standing edges.
        pixels = np.asarray(image.convert("RGB"), dtype=int)[-24:-6, :410]
        same_row_background = pixels[:, 400:401]
        columns = np.flatnonzero((np.abs(pixels - same_row_background).max(axis=2) > 8).sum(axis=0) > 2)
        assert columns.size, "The active task button is missing"
        runs = np.split(columns, np.flatnonzero(np.diff(columns) > 1) + 1)
        return max(map(len, runs))

    with Image.open(folder / "taskbar/populated.png") as native:
        width = painted_width(desktop_scenes(theme, "populated"))
        expected = painted_width(native)
        # The sample spans the filled button and can exclude a 1px bevel on either side.
        assert abs(width - expected) <= 2, (width, expected)


def render_device_manager(look, scale, output, size=(), *,
                          refresh_states=False, console_tree_states=False, console_tree_origin=(),
                          aero_branches=False, root_context=False, scan_states=False):
    subprocess.run(
        [
            sys.executable,
            str(REPO / "tests/visual/render_device_manager.py"),
            look,
            str(scale),
            str(output),
            *map(str, size),
            *(["--refresh-states"] if refresh_states else []),
            *(["--console-tree-states"] if console_tree_states else []),
            *(["--console-tree-origin", *map(str, console_tree_origin)] if console_tree_origin else []),
            *(["--aero-branches"] if aero_branches else []),
            *(["--root-context"] if root_context else []),
            *(["--scan-states"] if scan_states else []),
        ],
        check=True,
        timeout=45,
    )


@pytest.fixture(scope="module", params=THEMES)
def device_manager_command_band(request, tmp_path_factory):
    theme = request.param
    folder, metadata = THEMES[theme]
    with Image.open(folder / "device-manager.png") as reference:
        expected = reference.convert("RGB")
    if "device_manager_crop" in metadata:
        expected = expected.crop(metadata["device_manager_crop"])
    look = metadata["look"]
    output = tmp_path_factory.mktemp(f"{theme}-device-manager-band") / "device-manager.png"
    render_device_manager(look, metadata["device_manager_scale"], output, root_context=look == "aero")
    with Image.open(output) as capture:
        if look in CLASSIC[:2]:
            actual = capture.convert("RGB")
        else:
            # Both regions start at the console client origin. A short render
            # stays short so the comparator reports the geometry difference.
            actual = capture.crop((0, 0, min(expected.width, capture.width), min(expected.height, capture.height)))
    if metadata.get("device_manager_rgb565"):
        actual = rgb565(actual)
    return theme, expected, actual


def test_device_manager(device_manager_command_band, visual_output):
    theme, expected, actual = device_manager_command_band
    exact(expected, actual, visual_output / theme / "device-manager" / "qt")


def test_device_manager_blank_band(device_manager_command_band, visual_output):
    theme, expected, actual = device_manager_command_band
    bounds = THEMES[theme][1].get("device_manager_blank_band")
    if bounds is None:
        pytest.skip("No blank command band reference")
    exact(expected.crop(bounds), actual.crop(bounds), visual_output / theme / "device-manager" / "qt" / "blank-band")


@pytest.fixture(scope="module", params=("96dpi", "120dpi"))
def device_manager_luna_bands(request, tmp_path_factory):
    density = request.param
    folder, metadata = THEMES["winxp"]
    high_dpi = density == "120dpi"
    if high_dpi:
        reference = folder / "device-manager" / "command-bands-120dpi.png"
        seam, bottom, height = 27, 50, 411
    else:
        reference = folder / "device-manager.png"
        seam, bottom, height = 23, 46, 417
    output = tmp_path_factory.mktemp(f"luna-bands-{density}") / "device-manager.png"
    render_device_manager(metadata["look"], 1.25 if high_dpi else 1, output, (632, height))
    with Image.open(reference) as original, Image.open(output) as render:
        expected = original.convert("RGB").crop((240, 0, 620, bottom))
        actual = (rgb565(render) if high_dpi else render.convert("RGB")).crop((240, 0, 620, bottom))
    return density, seam, expected, actual


@pytest.mark.parametrize("part", ("menu", "toolbar", "bevels"))
def test_device_manager_luna_bands(device_manager_luna_bands, part, visual_output):
    density, seam, expected, actual = device_manager_luna_bands
    width, height = expected.size
    mask = None
    if part == "bevels":
        mask = np.zeros((height, width), dtype=bool)
        mask[[seam - 1, seam, height - 1]] = True
    else:
        top, bottom = (0, seam) if part == "menu" else (seam, height)
        expected, actual = (image.crop((0, top, width, bottom)) for image in (expected, actual))
    exact(expected, actual, visual_output / "winxp" / "device-manager" / "qt" / density / part, mask)


@pytest.mark.parametrize("device_manager_command_band", ["win2k"], indirect=True)
def test_device_manager_mmc_grips_and_separators(device_manager_command_band, visual_output):
    theme, expected, actual = device_manager_command_band
    mask = np.zeros((expected.height, expected.width), dtype=bool)
    for left, right in ((0, 12), (108, 124), (168, 180), (222, 232)):
        mask[:, left:right] = True
    exact(expected, actual, visual_output / theme / "device-manager" / "qt" / "grips-and-separators", mask)


@pytest.mark.parametrize("device_manager_command_band", ["win7"], indirect=True)
def test_device_manager_aero_toolbar_interior(device_manager_command_band, visual_output):
    theme, expected, actual = device_manager_command_band
    # Compare the unused interior and all three separators at their native positions.
    mask = np.zeros((expected.height, expected.width), dtype=bool)
    mask[23:46, 200:777] = True
    for left in (49, 80, 134):
        mask[23:46, left:left + 2] = True
    exact(expected, actual, visual_output / theme / "device-manager" / "qt" / "toolbar-interior", mask)


@pytest.mark.parametrize(
    ("device_manager_command_band", "command", "origin"),
    [
        ("win2k", "back", (126, 4)),
        ("win2k", "forward", (149, 4)),
        ("win2k", "up-one-level", (181, 4)),
        ("win2k", "console-tree", (203, 4)),
        ("win2k", "help", (234, 4)),
        ("winxp", "help", (90, 27)),
        ("winxp-classic", "help", (90, 28)),
        ("win7", "back", (4, 27)),
        ("win7", "forward", (27, 27)),
        ("win7", "console-tree", (58, 27)),
        ("win7", "help", (89, 27)),
        ("win7", "action-pane", (112, 27)),
        ("win7", "scan-for-hardware", (143, 27)),
    ],
    indirect=["device_manager_command_band"],
)
def test_device_manager_mmc_command_icon(device_manager_command_band, command, origin, visual_output):
    theme, expected, actual = device_manager_command_band
    left, top = origin
    box = (left, top, left + 16, top + 16)
    output = visual_output / theme / "device-manager" / "qt" / "icons" / command
    exact(expected.crop(box), actual.crop(box), output)


@pytest.fixture(scope="module", params=[theme for theme, (_, m) in THEMES.items() if m.get("device_manager_actions_scale")])
def device_manager_actions(request, tmp_path_factory):
    theme = request.param
    folder, metadata = THEMES[theme]
    output = tmp_path_factory.mktemp(f"{theme}-device-manager-actions")
    render_device_manager(
        metadata["look"], metadata["device_manager_actions_scale"],
        output / "actions-120dpi.png", refresh_states=True,
    )
    return theme, folder / "device-manager", output


@pytest.mark.parametrize("state", ("actions-120dpi", "refresh-states"))
@pytest.mark.parametrize("face_only", (False, True), ids=("full", "face"))
def test_device_manager_actions(device_manager_actions, state, face_only, visual_output):
    theme, reference, output = device_manager_actions
    with Image.open(reference / f"{state}.png") as original, Image.open(output / f"{state}.png") as capture:
        expected, actual = original.convert("RGB"), capture.convert("RGB")
    mask = np.ones((expected.height, expected.width), dtype=bool)
    if state == "refresh-states":
        # The QEMU cursor appears over the hovered and held mouse states.
        mask[10:, 170:187] = False
        mask[11:, 616:632] = False
    folder = visual_output / theme / "device-manager" / "qt" / state
    if face_only:
        # Keep the full bevels, focus frames, and gaps. Captions still have their full comparison above.
        if state == "refresh-states":
            for left in range(0, expected.width, 112):
                mask[5:23, left + 28:left + 84] = False
        else:
            for left in range(0, expected.width, 120):
                mask[5:23, left + 10:left + 102] = False
        folder = folder.with_name(f"{state}-face")
    exact(expected, actual, folder, mask)


@pytest.fixture(scope="module", params=[theme for theme, (_, m) in THEMES.items() if m.get("device_manager_console_states")])
def device_manager_console_states(request, tmp_path_factory):
    theme = request.param
    folder, metadata = THEMES[theme]
    settings = metadata["device_manager_console_states"]
    path = tmp_path_factory.mktemp(f"{theme}-console-tree-states") / "console-tree-states.png"
    render_device_manager(
        metadata["look"], settings["scale"], path, settings.get("client_size", ()),
        console_tree_states=True, console_tree_origin=settings.get("origin", ()),
    )
    with Image.open(folder / "device-manager" / path.name) as original, Image.open(path) as render:
        expected = original.convert("RGB")
        actual = render.convert("RGB") if theme == "win7" else rgb565(render)
    return theme, expected, actual, settings["cursor"]


def test_device_manager_console_tree_return_to_idle(device_manager_console_states):
    theme, expected, actual, cursor = device_manager_console_states
    # Compare the same part of each tile, clear of the pointer in both source states.
    pointer_free_height = min(top for _, top, _, _ in cursor)
    for strip in (expected, actual):
        idle, hover, pressed, held_outside, cancelled, checked, restored = [
            strip.crop((left, 0, left + 27, strip.height)).tobytes()
            for left in range(0, strip.width, 27)
        ]
        assert idle == held_outside == cancelled == restored
        limit = 27 * pointer_free_height * 3
        if theme == "win7":
            assert len({tile[:limit] for tile in (idle, hover, pressed)}) == 3
            assert checked[:limit] not in {idle[:limit], hover[:limit]}
        else:
            assert len({tile[:limit] for tile in (idle, hover, pressed, checked)}) == 4


def toolbar_pointer_mask(image, cursor):
    mask = np.ones((image.height, image.width), dtype=bool)
    for tile, (left, top, right, bottom) in zip((1, 2), cursor, strict=True):
        mask[top:bottom, 27 * tile + left:27 * tile + right] = False
    return mask


def test_device_manager_console_states(device_manager_console_states, visual_output):
    theme, expected, actual, cursor = device_manager_console_states
    mask = toolbar_pointer_mask(expected, cursor)
    exact(expected, actual, visual_output / theme / "device-manager" / "qt" / "console-tree-states", mask)


@pytest.mark.parametrize("device_manager_console_states", ["winxp", "winxp-classic"], indirect=True)
def test_device_manager_console_tree_icon_frame(device_manager_console_states):
    _, expected, actual, cursor = device_manager_console_states
    mask = toolbar_pointer_mask(expected, cursor)

    def frame(image):
        red, green, blue = np.asarray(image).transpose(2, 0, 1)
        return (red < 45) & (green < 45) & (blue > 80) & mask

    np.testing.assert_array_equal(frame(actual), frame(expected))


@pytest.mark.parametrize("device_manager_console_states", ["win2k", "winxp-classic"], indirect=True)
def test_device_manager_console_tree_bevels(device_manager_console_states, visual_output):
    theme, expected, actual, cursor = device_manager_console_states
    mask = np.zeros((expected.height, expected.width), dtype=bool)
    for left in range(0, expected.width, 27):
        mask[1:23, left + 4:left + 27] = True
        mask[6:19, left + 8:left + 23] = False  # The glyph has its own full-state comparison.
    mask &= toolbar_pointer_mask(expected, cursor)
    exact(expected, actual, visual_output / theme / "device-manager" / "qt" / "console-tree-bevels", mask)


def test_device_manager_xp_classic_bands_120dpi(tmp_path, visual_output):
    folder, metadata = THEMES["winxp-classic"]
    with Image.open(folder / "device-manager" / "command-bands-120dpi.png") as original:
        expected = original.convert("RGB")
    output = tmp_path / "device-manager.png"
    client = metadata["device_manager_console_states"]
    render_device_manager(metadata["look"], client["scale"], output, client["client_size"])
    with Image.open(output) as render:
        actual = rgb565(render).crop((0, 0, expected.width, expected.height))
    mask = np.zeros((expected.height, expected.width), dtype=bool)
    mask[:, :2] = mask[:, 240:620] = mask[:, -2:] = True
    exact(expected, actual, visual_output / "winxp-classic" / "device-manager" / "qt" / "120dpi" / "blank-band", mask)


@pytest.fixture(scope="module")
def device_manager_scan_reference(tmp_path_factory):
    folder, metadata = THEMES["win7"]
    output = tmp_path_factory.mktemp("win7-hardware-scan")
    render_device_manager(metadata["look"], 1, output / "scan-states.png", (778, 518), scan_states=True)
    return folder / "device-manager", output


@pytest.mark.parametrize("state", ("unselected", "states"))
def test_device_manager_scan(device_manager_scan_reference, state, visual_output):
    reference, output = device_manager_scan_reference
    filename = f"scan-{state}.png"
    with Image.open(reference / filename) as original, Image.open(output / filename) as capture:
        expected, actual = original.convert("RGB"), capture.convert("RGB")
    mask = toolbar_pointer_mask(expected, ((14, 8, 27, 23), (14, 8, 27, 23))) if state == "states" else None
    exact(expected, actual, visual_output / "win7" / "device-manager" / "qt" / f"scan-{state}", mask)


@pytest.mark.parametrize(
    ("region", "bounds"),
    (("dialog", None), ("blank-message-panel", (8, 55, 274, 80)), ("bottom-frame", (0, 80, 282, 88))),
)
def test_device_manager_scan_progress(device_manager_scan_reference, region, bounds, visual_output):
    reference, output = device_manager_scan_reference
    with Image.open(reference / "scan-progress.png") as original, Image.open(output / "scan-progress.png") as capture:
        expected, actual = original.convert("RGB"), capture.convert("RGB")
    mask = None
    if bounds is not None:
        assert actual.size == expected.size
        expected, actual = expected.crop(bounds), actual.crop(bounds)
    else:
        mask = np.ones((expected.height, expected.width), dtype=bool)
        # The window underneath shows through the two rounded corners.
        mask[:6, :6] = mask[:6, -6:] = False
    exact(expected, actual, visual_output / "win7" / "device-manager" / "qt" / "scan-progress" / region, mask)


@pytest.fixture(scope="module", params=[theme for theme, (_, m) in THEMES.items() if m.get("device_manager_tree_frame")])
def device_manager_tree(request, tmp_path_factory):
    theme = request.param
    folder, metadata = THEMES[theme]
    with Image.open(folder / "device-manager/tree-frame.png") as frame:
        expected = frame.convert("RGB")
    output = tmp_path_factory.mktemp(f"{theme}-device-manager") / "device-manager.png"
    render_device_manager(metadata["look"], metadata["device_manager_scale"], output, expected.size)
    with Image.open(output) as frame:
        actual = frame.convert("RGB")
    return theme, expected, actual


def test_device_manager_tree_frame(device_manager_tree, visual_output):
    theme, expected, actual = device_manager_tree
    # The devices are supplied by Linux on the live window. The tree surround occupies the same client coordinates.
    mask = np.ones((expected.height, expected.width), dtype=bool)
    mask[:46] = False
    mask[54:516, 1:400] = False
    exact(expected, actual, visual_output / theme / "device-manager" / "qt" / "tree-frame", mask)


@pytest.mark.parametrize(
    ("state", "bounds"),
    [("expanded", (6, 59, 19, 70)), ("collapsed", (26, 77, 39, 88))],
)
def test_device_manager_tree_branches(device_manager_tree, state, bounds, visual_output):
    theme, expected, actual = device_manager_tree
    exact(expected.crop(bounds), actual.crop(bounds), visual_output / theme / "device-manager" / "qt" / state)


@pytest.fixture(scope="module")
def device_manager_aero_branches(tmp_path_factory):
    folder, metadata = THEMES["win7"]
    path = tmp_path_factory.mktemp("aero-tree-branches") / "tree-branch-hover.png"
    render_device_manager(metadata["look"], metadata["device_manager_scale"], path, (778, 518), aero_branches=True)
    with Image.open(folder / "device-manager" / path.name) as reference, Image.open(path) as render:
        return reference.convert("RGB"), render.convert("RGB")


@pytest.mark.parametrize(("state", "left"), [("expanded", 0), ("collapsed", 13), ("held-open", 26)])
def test_device_manager_tree_branch_hover(device_manager_aero_branches, state, left, visual_output):
    expected, actual = device_manager_aero_branches
    box = (left, 0, left + 13, 11)
    exact(expected.crop(box), actual.crop(box), visual_output / "win7" / "device-manager" / "qt" / f"{state}-hover")


@pytest.fixture(scope="module")
def aero_start_search_strip(tmp_path_factory):
    output = tmp_path_factory.mktemp("aero-start-search")
    subprocess.run(
        [sys.executable, str(REPO / "tests/aero/render_aero_dialogs.py"), str(output), "1"],
        check=True,
        timeout=45,
    )
    folder, _ = THEMES["win7"]
    with Image.open(folder / "start-menu.png") as reference, Image.open(output / "start.png") as capture:
        # Search and All Programs sit in the opaque pane. Anchor the crop
        # to the menu's bottom edge as in the SP1 taskbar capture.
        actual = capture.crop((8, capture.height - 53, 260, capture.height - 7)).convert("RGB")
        return reference.convert("RGB"), actual


@pytest.mark.parametrize("theme", THEMES)
def test_start_menu(theme, qt_app, tmp_path, visual_output, monkeypatch, request):
    from render_report import MENU_EXTRA_TOP, MENU_SETTINGS

    folder, metadata = THEMES[theme]
    look = metadata["look"]
    directory = visual_output / theme / "start-menu" / "qt"
    if look == "aero":
        exact(*request.getfixturevalue("aero_start_search_strip"), directory)
        return
    with Image.open(folder / "start-menu.png") as reference:
        expected = reference.convert("RGB")
    if look == "luna":
        with themed(qt_app, look):
            _label, _reference, actual = start_menus(qt_app, look, tmp_path)[0]
    else:
        settings, colours = MENU_SETTINGS[look]
        startmenu = load_script("chicago95-startmenu")
        suspend = metadata.get("start_menu_suspend", False)
        monkeypatch.setattr(startmenu, "suspend_available", lambda: suspend)
        if user := metadata.get("start_menu_user"):
            monkeypatch.setattr(startmenu.getpass, "getuser", lambda: user)
        actual = render_start_menu(
            startmenu,
            qt_app,
            tmp_path,
            settings,
            colours,
            without=("&Log Off...",),
            active=metadata.get("start_menu_active"),
            extra_top=MENU_EXTRA_TOP.get(look, ()),
        )
        if metadata.get("start_menu_rgb555"):
            assert rgb555(expected).tobytes() == expected.tobytes()
            actual = rgb555(actual)
    exact(expected, actual, directory)


def test_win7_start_menu_search_horizontal_borders(aero_start_search_strip, visual_output):
    expected, actual = aero_start_search_strip
    output = visual_output / "win7/start-menu/qt/search-frame"
    for edge, row in (("top", 11), ("bottom", 32)):
        bounds = (16, row, 232, row + 1)
        exact(expected.crop(bounds), actual.crop(bounds), output / edge)


@pytest.fixture(scope="module")
def start_menu_interactions(tmp_path_factory):
    @cache
    def render(theme):
        folder, _metadata = THEMES[theme]
        output = tmp_path_factory.mktemp(f"start-menu-{theme}")
        subprocess.run(
            [sys.executable, str(REPO / "tests/visual/render_start_menu.py"), str(folder / "manifest.json"), str(output)],
            check=True,
            timeout=30,
        )
        return output

    return render


@pytest.mark.parametrize(
    ("theme", "state"),
    [
        pytest.param(theme, path.stem, id=f"{theme}-{path.stem}")
        for theme, (folder, _metadata) in THEMES.items()
        for path in sorted((folder / "start-menu").glob("*.png"))
    ],
)
def test_start_menu_interaction(theme, state, start_menu_interactions, visual_output):
    folder, _metadata = THEMES[theme]
    with (
        Image.open(folder / "start-menu" / f"{state}.png") as native,
        Image.open(start_menu_interactions(theme) / f"{state}.png") as rendered,
    ):
        exact(native.convert("RGB"), rendered.convert("RGB"), visual_output / theme / "start-menu" / state)


def render_properties(folder, component, output, size, *, scale=None):
    subprocess.run(
        [
            sys.executable,
            str(REPO / "tests/visual/render_properties.py"),
            str(folder / "manifest.json"),
            component,
            str(output),
            str(size[0]),
            str(size[1]),
            *([str(scale)] if scale is not None else []),
        ],
        check=True,
        timeout=45,
    )


@pytest.mark.parametrize("theme", THEMES)
@pytest.mark.parametrize("component", ["control-panel", "display-properties"])
def test_properties(theme, component, tmp_path, visual_output):
    folder, metadata = THEMES[theme]
    with Image.open(folder / f"{component}.png") as frame:
        expected = frame.convert("RGB")
    output = tmp_path / f"{component}.png"
    render_properties(folder, component, output, expected.size)
    with Image.open(output) as frame:
        actual = rgb565(frame) if metadata.get("properties_rgb565") else frame.convert("RGB")
    exact(expected, actual, visual_output / theme / component / "qt")


@pytest.mark.parametrize(
    ("theme", "page"),
    [(theme, page) for theme, (_, data) in THEMES.items() for page in data.get("display_pages", {})],
)
def test_display_properties_tabs(theme, page, tmp_path, visual_output):
    expected, actual = display_page_images(theme, page, tmp_path)
    exact(expected, actual, visual_output / theme / "display-properties" / "qt" / page)


def test_win7_taskbar_properties(tmp_path, visual_output):
    folder, _ = THEMES["win7"]
    with Image.open(REFERENCES / "win7-sp1-aero-taskbar-properties.png") as native:
        expected = native.convert("RGB")
    output = tmp_path / "taskbar-properties.png"
    render_properties(folder, "taskbar-properties", output, expected.size, scale=1)
    with Image.open(output) as frame:
        actual = frame.convert("RGB")
    exact(expected, actual, visual_output / "win7/taskbar/qt/properties")


def display_page_images(theme, page, tmp_path):
    folder, metadata = THEMES[theme]
    with Image.open(folder / "display-properties" / f"{page}.png") as frame:
        expected = frame.convert("RGB")
    output = tmp_path / f"{page}.png"
    render_properties(folder, f"display-properties-{page}", output, expected.size)
    with Image.open(output) as frame:
        actual = rgb565(frame) if metadata.get("properties_rgb565") else frame.convert("RGB")
    return expected, actual


def test_winxp_blank_saver_preview_and_keyboard_selection(tmp_path, visual_output):
    images = display_page_images("winxp", "screen-saver-blank", tmp_path)
    output = visual_output / "winxp/display-properties/qt/screen-saver-blank"
    bounds = (164, 70, 358, 222)
    masks = [
        Image.fromarray(np.uint8(np.all(np.asarray(image.crop(bounds)) == 0, axis=2)) * 255).convert("RGB")
        for image in images
    ]
    exact(*masks, output / "screen-opening")
    selection = (100, 288, 200, 296)
    exact(*(image.crop(selection) for image in images), output / "selection-fill")


@pytest.fixture(scope="module")
def control_panel_icons(request, tmp_path_factory):
    theme = request.param
    folder, metadata = THEMES[theme]
    output = tmp_path_factory.mktemp(f"{theme}-control-panel-icons") / "control-panel.png"
    with Image.open(folder / "control-panel.png") as frame:
        expected = frame.convert("RGB")
    render_properties(folder, "control-panel", output, expected.size)
    with Image.open(output) as frame:
        actual = rgb565(frame) if metadata.get("properties_rgb565") else frame.convert("RGB")
    return theme, metadata["control_panel_icons"], expected, actual


@pytest.mark.parametrize(
    ("control_panel_icons", "icon"),
    [(theme, icon) for theme, (_, data) in THEMES.items() for icon in data.get("control_panel_icons", {})],
    indirect=["control_panel_icons"],
)
def test_control_panel_icons(control_panel_icons, icon, visual_output):
    theme, crops, expected, actual = control_panel_icons
    crop = crops[icon]
    directory = visual_output / theme / "control-panel" / "qt" / "icons" / icon
    exact(expected.crop(crop), actual.crop(crop), directory)


@pytest.mark.parametrize("theme", [theme for theme, (_, data) in THEMES.items() if data.get("control_panel_end")])
def test_control_panel_end(theme, tmp_path, visual_output):
    folder, metadata = THEMES[theme]
    with Image.open(folder / "control-panel" / "end.png") as frame:
        expected = frame.convert("RGB")
    output = tmp_path / "end.png"
    render_properties(folder, "control-panel-end", output, expected.size)
    with Image.open(output) as frame:
        actual = rgb565(frame) if metadata.get("properties_rgb565") else frame.convert("RGB")
    exact(expected, actual, visual_output / theme / "control-panel" / "qt" / "end")


@pytest.fixture(scope="module", params=[theme for theme, (_, data) in THEMES.items() if data.get("control_panel_category")])
def xp_category_render(request, tmp_path_factory):
    theme = request.param
    folder, metadata = THEMES[theme]
    with Image.open(folder / "control-panel" / "category.png") as frame:
        expected = frame.convert("RGB")
    output = tmp_path_factory.mktemp(f"{theme}-category") / "category.png"
    render_properties(folder, "control-panel-category", output, expected.size)
    with Image.open(output) as frame:
        actual = rgb565(frame) if metadata.get("properties_rgb565") else frame.convert("RGB")
    return theme, expected, actual


def test_control_panel_category(xp_category_render, visual_output):
    theme, expected, actual = xp_category_render
    exact(expected, actual, visual_output / theme / "control-panel" / "qt" / "category")


def test_control_panel_category_background(xp_category_render, visual_output):
    theme, expected, actual = xp_category_render
    # The right end of the banner leaves the category page color exposed.
    band = (590, 120, 776, 151)
    exact(expected.crop(band), actual.crop(band), visual_output / theme / "control-panel/qt/category/background")


@pytest.mark.parametrize("icon", THEMES["winxp"][1]["control_panel_category_icons"])
def test_control_panel_category_icon(xp_category_render, icon, visual_output):
    theme, expected, actual = xp_category_render
    bounds = THEMES[theme][1]["control_panel_category_icons"][icon]
    exact(expected.crop(bounds), actual.crop(bounds), visual_output / theme / "control-panel/qt/category/icons" / icon)


@pytest.mark.parametrize("theme", ("winxp", "winxp-classic"))
def test_control_panel_category_link_hover(theme, tmp_path, visual_output):
    folder, _metadata = THEMES[theme]
    with Image.open(folder / "control-panel/category.png") as client:
        size = client.size
    output = tmp_path / "link.png"
    render_properties(folder, "control-panel-category-link", output, size)
    directory = visual_output / theme / "control-panel/qt/category/link"
    directory.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(output, directory / "rendered.png")
    with Image.open(folder / "control-panel/category-link-hover.png") as native, Image.open(output) as rendered:
        strips = native.convert("RGB"), rgb565(rendered)
    assert strips[0].getpixel((0, 0)) == strips[1].getpixel((0, 0))
    strokes = []
    for strip in strips:
        idle, hover, exit_frame = (np.asarray(strip.crop((x, 0, x + 100, 30))) for x in (0, 100, 200))
        assert np.array_equal(idle, exit_frame)
        # The underline is the solid row across this sample where the idle
        # label had no ink. The separate full view keeps its glyph comparison.
        plain = np.all(idle == idle[0, 0], axis=(1, 2))
        solid = np.all(hover == hover[:, :1], axis=(1, 2))
        changed = np.any(idle != hover, axis=(1, 2))
        rows = np.flatnonzero(plain & solid & changed)
        assert len(rows) == 1
        strokes.append(Image.fromarray(hover[rows]))
    exact(*strokes, directory / "underline")


@pytest.mark.parametrize("theme", [theme for theme, (_, data) in THEMES.items() if data.get("control_panel_selection")])
def test_control_panel_selection(theme, tmp_path, visual_output):
    folder, metadata = THEMES[theme]
    state = f"{metadata['control_panel_selection'].lower()}-selected"
    with Image.open(folder / "control-panel" / f"{state}.png") as frame:
        expected = frame.convert("RGB")
    output = tmp_path / "selected.png"
    render_properties(folder, "control-panel-selection", output, expected.size)
    with Image.open(output) as frame:
        actual = rgb565(frame) if metadata.get("properties_rgb565") else frame.convert("RGB")
    exact(expected, actual, visual_output / theme / "control-panel" / "qt" / state)


@pytest.mark.parametrize("theme", [theme for theme, (_, data) in THEMES.items() if "display_resolution_picker" in data])
@pytest.mark.parametrize("state", ["open", "up", "click"])
def test_display_resolution_picker(theme, state, tmp_path, visual_output):
    folder, metadata = THEMES[theme]
    with Image.open(folder / "display-properties/resolution-picker.png") as sheet:
        height = sheet.height // 3
        top = ["open", "up", "click"].index(state) * height
        expected = sheet.crop((0, top, sheet.width, top + height)).convert("RGB")
    output = tmp_path / f"{state}.png"
    render_properties(
        folder, f"display-resolution-picker-{state}", output, expected.size,
        scale=metadata["display_resolution_picker"]["scale"],
    )
    with Image.open(output) as actual:
        exact(expected, actual, visual_output / theme / "display-properties" / "qt" / "resolution-picker" / state)


def shutdown_chooser_images(theme, tmp_path, source, scale):
    folder, metadata = THEMES[theme]
    with Image.open(folder / source) as frame:
        expected = frame.convert("RGB")
    output = tmp_path / "shutdown.png"
    render_properties(folder, "shutdown", output, expected.size, scale=scale)
    with Image.open(output) as frame:
        actual = rgb565(frame) if metadata.get("shutdown_rgb565") else frame.convert("RGB")
    return expected, actual


def check_shutdown_chooser(theme, tmp_path, visual_output, *, source="shutdown.png", scale=None):
    expected, actual = shutdown_chooser_images(theme, tmp_path, source, scale)
    mask = None
    cursor = THEMES[theme][1].get("shutdown_cursor") if source == "shutdown.png" else None
    if cursor:
        left, top, right, bottom = cursor
        mask = np.ones((expected.height, expected.width), dtype=bool)
        mask[top:bottom, left:right] = False
    directory = visual_output / theme / "shutdown" / "qt"
    if scale is not None:
        directory /= f"{round(scale * 96)}dpi"
    exact(expected, actual, directory, mask)


@pytest.mark.parametrize("theme", THEMES)
def test_shutdown_chooser(theme, tmp_path, visual_output):
    check_shutdown_chooser(theme, tmp_path, visual_output)


@pytest.mark.parametrize(
    "theme,dpi,source",
    [
        (theme, dpi, metadata[key])
        for theme, (_, metadata) in THEMES.items()
        for dpi, key in ((96, "shutdown_standard_dpi"), (120, "shutdown_120dpi"))
        if key in metadata
    ],
)
def test_shutdown_chooser_additional_dpi(theme, dpi, source, tmp_path, visual_output):
    check_shutdown_chooser(theme, tmp_path, visual_output, source=source, scale=dpi / 96)


@pytest.mark.parametrize(("dpi", "source"), ((96, "shutdown-96dpi.png"), (120, "shutdown.png")))
def test_winxp_shutdown_frame_matches_native_at_both_dpis(dpi, source, tmp_path, visual_output):
    expected, actual = shutdown_chooser_images("winxp", tmp_path, source, dpi / 96)
    mask = np.ones((expected.height, expected.width), dtype=bool)
    mask[1:-1, 1:-1] = False
    exact(expected, actual, visual_output / f"winxp/shutdown/qt/{dpi}dpi/frame", mask)


def shutdown_button_state_images(theme, tmp_path, name="button-states"):
    folder, metadata = THEMES[theme]
    with Image.open(folder / "shutdown" / f"{name}.png") as frame:
        expected = frame.convert("RGB")
    output = tmp_path / f"{name}.png"
    render_properties(folder, f"shutdown-{name}", output, expected.size, scale=metadata.get("shutdown_button_scale"))
    with Image.open(output) as frame:
        actual = rgb565(frame) if metadata.get("shutdown_rgb565") else frame.convert("RGB")
    return expected, actual


@pytest.mark.parametrize("theme", [theme for theme, (_, m) in THEMES.items() if "shutdown_button_crops" in m])
def test_shutdown_button_states(theme, tmp_path, visual_output):
    expected, actual = shutdown_button_state_images(theme, tmp_path)
    exact(expected, actual, visual_output / theme / "shutdown" / "qt" / "button-states")


def test_winxp_shutdown_cancel_states(tmp_path, visual_output):
    expected, actual = shutdown_button_state_images("winxp", tmp_path, "cancel-states")
    exact(expected, actual, visual_output / "winxp/shutdown/qt/cancel-states")


@pytest.mark.parametrize("name", ["stand-by", "turn-off", "restart", "cancel"])
def test_winxp_shutdown_keyboard_focus(name, tmp_path, visual_output):
    component = f"keyboard-focus-{name}"
    expected, actual = shutdown_button_state_images("winxp", tmp_path, component)
    exact(expected, actual, visual_output / "winxp/shutdown/qt" / component)


def hover_settled_ms(samples):
    final_colour = samples[-1][1]
    for index in range(len(samples) - 2, -1, -1):
        if samples[index][1] != final_colour:
            return samples[index + 1][0]
    raise AssertionError("No change in the sampled button colour")


def test_shutdown_win7_button_hover_timing(tmp_path, visual_output):
    folder, _ = THEMES["win7"]
    original = json.loads((folder / "shutdown/button-hover-timing.json").read_text())
    output = tmp_path / "button-hover-timing.json"
    render_properties(folder, "shutdown-button-hover", output, (1, 1))
    actual = json.loads(output.read_text())
    directory = visual_output / "win7" / "shutdown" / "qt"
    directory.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(output, directory / "button-hover-timing.json")
    assert actual["enter"][0][1] == actual["leave"][-1][1]
    for state, samples in actual.items():
        times = [hover_settled_ms(trial[state]) for trial in original]
        # Compare the first presented frame at the new steady colour, allowing one capture interval.
        measured = hover_settled_ms(samples)
        assert min(times) - 60 <= measured <= max(times) + 60, (state, measured, times)
        native = original[0][state][-1][1]
        assert max(abs(a - b) for a, b in zip(samples[-1][1], native, strict=True)) <= 5
        assert len({tuple(rgb) for _, rgb in samples}) > 2


@pytest.mark.parametrize(
    "theme,label,columns",
    [
        ("win95", (10, 6, 70, 19), (2,)),
        ("win98", (10, 6, 96, 24), (2,)),
        ("win2k", (10, 7, 80, 24), (0, 2)),
        ("winxp-classic", (10, 7, 80, 24), (0, 2)),
    ],
)
def test_shutdown_button_frames_match_native_pixels(theme, label, columns, tmp_path, visual_output):
    expected, actual = shutdown_button_state_images(theme, tmp_path)
    width = expected.width // 3
    mask = np.ones((expected.height, width), dtype=bool)
    left, top, right, bottom = label
    for y in range(0, expected.height, expected.height // 3):
        mask[y + top : y + bottom, left:right] = False
    for column in columns:
        box = (column * width, 0, (column + 1) * width, expected.height)
        state = "held-frames" if column == 2 else "idle-frames"
        exact(expected.crop(box), actual.crop(box), visual_output / theme / "shutdown" / "qt" / state, mask)


@pytest.mark.parametrize("theme", ["win95", "win98", "win2k", "winxp-classic"])
def test_shutdown_classic_buttons_keep_their_idle_appearance_on_hover(theme, tmp_path):
    for sheet in shutdown_button_state_images(theme, tmp_path):
        width = sheet.width // 3
        assert sheet.crop((0, 0, width, sheet.height)).tobytes() == sheet.crop(
            (width, 0, 2 * width, sheet.height)
        ).tobytes()


@pytest.mark.parametrize("theme", [theme for theme, (_, metadata) in THEMES.items() if "shutdown_radio_states" in metadata])
def test_shutdown_radio_states(theme, tmp_path, visual_output):
    folder, metadata = THEMES[theme]
    with Image.open(folder / "shutdown/radio-states.png") as frame:
        expected = frame.convert("RGB")
    output = tmp_path / "radio-states.png"
    render_properties(folder, "shutdown-radio-states", output, expected.size, scale=metadata["shutdown_radio_states"]["scale"])
    with Image.open(output) as frame:
        actual = rgb565(frame) if metadata.get("shutdown_rgb565") else frame.convert("RGB")
    exact(expected, actual, visual_output / theme / "shutdown" / "qt" / "radio-states")


def test_shutdown_win98_radio_indicators_match_native_pixels(tmp_path, visual_output):
    folder, metadata = THEMES["win98"]
    with Image.open(folder / "shutdown/radio-states.png") as reference:
        expected = reference.convert("RGB")
    output = tmp_path / "radio-states.png"
    render_properties(folder, "shutdown-radio-states", output, expected.size, scale=metadata["shutdown_radio_states"]["scale"])
    with Image.open(output) as frame:
        actual = frame.convert("RGB")
    # The first 20 columns contain the three native radio indicators in every keyboard state.
    bounds = (0, 0, 20, expected.height)
    exact(expected.crop(bounds), actual.crop(bounds), visual_output / "win98/shutdown/qt/radio-indicators")


@pytest.mark.parametrize(
    "theme,dpi,name,bounds",
    (
        ("win95", 96, "shutdown-96dpi.png", (59, 63, 74, 124)),
        ("win95", 120, "shutdown.png", (78, 79, 93, 150)),
        ("win98", 96, "shutdown.png", (59, 63, 74, 122)),
        ("win98", 120, "shutdown-120dpi.png", (78, 79, 93, 146)),
    ),
)
def test_shutdown_9x_compact_indicators_match_native_pixels(theme, dpi, name, bounds, tmp_path, visual_output):
    folder, _ = THEMES[theme]
    with Image.open(folder / name) as reference:
        expected = reference.convert("RGB")
    output = tmp_path / "shutdown.png"
    render_properties(folder, "shutdown", output, expected.size, scale=dpi / 96)
    with Image.open(output) as frame:
        actual = frame.convert("RGB")
    exact(expected.crop(bounds), actual.crop(bounds), visual_output / theme / "shutdown/qt" / f"radios-{dpi}dpi")


def shutdown_combo_state_images(theme, state, tmp_path):
    folder, metadata = THEMES[theme]
    with Image.open(folder / "shutdown" / f"{state}.png") as frame:
        expected = frame.convert("RGB")
    output = tmp_path / f"{state}.png"
    render_properties(folder, f"shutdown-{state}", output, expected.size, scale=metadata["shutdown_combo_states"]["scale"])
    with Image.open(output) as frame:
        actual = rgb565(frame) if metadata.get("shutdown_rgb565") else frame.convert("RGB")
    return expected, actual


@pytest.mark.parametrize("theme", [theme for theme, (_, metadata) in THEMES.items() if "shutdown_combo_states" in metadata])
@pytest.mark.parametrize("state", ["dropdown", "choices"])
def test_shutdown_combo_states(theme, state, tmp_path, visual_output):
    expected, actual = shutdown_combo_state_images(theme, state, tmp_path)
    exact(expected, actual, visual_output / theme / "shutdown" / "qt" / state)


@pytest.mark.parametrize("theme", ("win2k", "winxp-classic"))
def test_shutdown_nt_dropdown_highlight_matches_native_pixels(theme, tmp_path, visual_output):
    expected, actual = shutdown_combo_state_images(theme, "dropdown", tmp_path)
    bounds = (100, 14, 220, 36)
    exact(expected.crop(bounds), actual.crop(bounds), visual_output / theme / "shutdown/qt/dropdown-highlight")


@pytest.mark.parametrize("theme", ("win2k", "winxp-classic"))
def test_shutdown_nt_dropdown_labels_start_on_the_native_column(theme, tmp_path):
    images = shutdown_combo_state_images(theme, "dropdown", tmp_path)
    rows = tuple(range(1, images[0].height - 1, 16))
    for row, y in enumerate(rows):
        ink = (255, 255, 255) if row == 1 else (0, 0, 0)
        bounds = [
            bounding_box(image.crop((2, y + 2, 90, y + 15)), lambda rgb, ink=ink: rgb == ink)
            for image in images
        ]
        assert all(bounds), (row, bounds)
        assert bounds[0][0] == bounds[1][0], (row, bounds)


SHUTDOWN_DROPDOWN_KEY_STATES = [
    pytest.param((theme, state), id=f"{theme}-{state}")
    for theme, (_, metadata) in THEMES.items()
    for state in metadata.get("shutdown_combo_states", {}).get("highlighted_rows", ())
]


@pytest.fixture(scope="module", params=SHUTDOWN_DROPDOWN_KEY_STATES)
def shutdown_dropdown_key_images(request, tmp_path_factory, visual_output):
    theme, state = request.param
    scratch = tmp_path_factory.mktemp(f"{theme}-shutdown-dropdown")
    expected, actual = shutdown_combo_state_images(theme, f"dropdown-{state}", scratch)
    return expected, actual, visual_output / theme / "shutdown/qt/dropdown-keys" / state


def test_shutdown_dropdown_keyboard_highlights(shutdown_dropdown_key_images):
    expected, actual, directory = shutdown_dropdown_key_images
    # Check the selected face and its focus dots through the item list, clear of its labels and frame.
    bounds = (100, 1, 220, expected.height - 1)
    exact(expected.crop(bounds), actual.crop(bounds), directory / "highlight")


def test_shutdown_dropdown_keyboard_full_frame(shutdown_dropdown_key_images):
    expected, actual, directory = shutdown_dropdown_key_images
    exact(expected, actual, directory)


def test_shutdown_win7_dropdown_matches_native_pixels_outside_labels(tmp_path, visual_output):
    expected, actual = shutdown_combo_state_images("win7", "dropdown", tmp_path)
    mask = np.ones((expected.height, expected.width), dtype=bool)
    mask[1:-1, 1:80] = False
    exact(expected, actual, visual_output / "win7" / "shutdown" / "qt" / "dropdown-frame", mask)


def test_shutdown_win7_selector_focus_and_arrow(tmp_path, visual_output):
    folder, _ = THEMES["win7"]
    source = folder / "shutdown.png"
    output = tmp_path / "shutdown.png"
    with Image.open(source) as frame:
        expected = frame.convert("RGB")
    render_properties(folder, "shutdown", output, expected.size)
    with Image.open(output) as frame:
        actual = frame.convert("RGB")

    # ClearType affects the label. The focus dots and arrow can be checked independently.
    def ink(frame):
        return frame.convert("L").point(lambda value: 0 if value < 80 else 255).convert("RGB")

    for name, rect in (("focus", (130, 108, 363, 123)), ("arrow", (363, 109, 381, 122))):
        exact(ink(expected.crop(rect)), ink(actual.crop(rect)), visual_output / "win7/shutdown/qt" / name)


@pytest.fixture(scope="module", params=[theme for theme, (_, m) in THEMES.items() if "control_panel_hover_scale" in m])
def category_hover(request, tmp_path_factory):
    theme = request.param
    folder, _metadata = THEMES[theme]
    outputs = tmp_path_factory.mktemp(f"{theme}-control-panel-hover")
    with Image.open(folder / "control-panel/hover.png") as reference:
        render_properties(folder, "control-panel-hover", outputs / "hover.png", reference.size)
    return theme, folder / "control-panel", outputs


@pytest.mark.parametrize("state", ["hover", "hover-opening"])
def test_control_panel_hover(category_hover, state, visual_output):
    theme, references, outputs = category_hover
    with Image.open(references / f"{state}.png") as original, Image.open(outputs / f"{state}.png") as render:
        expected, actual = original.convert("RGB"), render.convert("RGB")
    if state == "hover":
        # Compare the unobstructed outline, bevel and fill at the right edge at native scale.
        expected, actual = (
            image.crop((image.width - 24, 0, image.width, image.height)) for image in (expected, actual)
        )
    exact(expected, actual, visual_output / theme / "control-panel" / "qt" / state)


def test_control_panel_hover_outline(category_hover, visual_output):
    theme, references, outputs = category_hover
    if not (references / "hover-outline.png").is_file():
        pytest.skip("No native capture matching the full card width")
    with Image.open(references / "hover-outline.png") as original, Image.open(outputs / "hover.png") as render:
        expected, actual = original.convert("RGB"), render.convert("RGB")
    outline = np.ones((expected.height, expected.width), dtype=bool)
    outline[2:-2, 2:-2] = False
    exact(expected, actual, visual_output / theme / "control-panel" / "qt" / "hover-outline", outline)


@pytest.mark.parametrize("theme", [theme for theme, (_, m) in THEMES.items() if m.get("control_panel_hover_exit")])
def test_control_panel_hover_exit(theme, tmp_path, visual_output):
    folder, _metadata = THEMES[theme]
    with Image.open(folder / "control-panel.png") as client:
        size = client.size
    output = tmp_path / "hover-exit.png"
    render_properties(folder, "control-panel-hover-exit", output, size)
    with Image.open(folder / "control-panel/hover-exit.png") as expected, Image.open(output) as actual:
        for image in (expected, actual):
            assert image.size == (60, 36)
            for top in range(0, image.height, 12):
                frames = [image.crop((x, top, x + 12, top + 12)).tobytes() for x in range(0, image.width, 12)]
                assert frames[0] != frames[1] and all(frame == frames[1] for frame in frames[2:])
        exact(expected, actual, visual_output / theme / "control-panel" / "qt" / "hover-exit")


@pytest.fixture(scope="module", params=[theme for theme, (_, m) in THEMES.items() if m.get("control_panel_category_press")])
def category_press(request, tmp_path_factory):
    theme = request.param
    folder, _metadata = THEMES[theme]
    references = folder / "control-panel"
    outputs = tmp_path_factory.mktemp(f"{theme}-category-press")
    with Image.open(references / "category-press.png") as frame:
        render_properties(folder, "control-panel-category-press", outputs / "category-press.png", frame.size)
    return theme, references, outputs


@pytest.mark.parametrize("state", ("category-press", "category-focus"))
def test_control_panel_category_press(category_press, state, visual_output):
    theme, references, outputs = category_press
    with Image.open(references / f"{state}.png") as frame:
        expected = frame.convert("RGB")
    with Image.open(outputs / f"{state}.png") as frame:
        actual = frame.convert("RGB")
    exact(expected, actual, visual_output / theme / "control-panel" / "qt" / state)


def test_control_panel_category_focus_dots(category_press, visual_output):
    theme, references, outputs = category_press

    def focus_dots(path):
        with Image.open(path / "category-focus.png") as image:
            # The label's descenders overlap the bottom line of the focus rectangle.
            dark = np.asarray(image.convert("RGB"))[:19].max(axis=2) < 100
        return Image.fromarray(dark).convert("RGB")

    exact(focus_dots(references), focus_dots(outputs), visual_output / theme / "control-panel/qt/focus-dots")


def test_control_panel_category_focus_background(category_press, visual_output):
    theme, references, outputs = category_press
    with Image.open(references / "category-focus.png") as native, Image.open(outputs / "category-focus.png") as render:
        # A focused heading should leave the card face idle after a cancelled click.
        blank = (160, 0, 165, 24)
        exact(
            native.convert("RGB").crop(blank),
            render.convert("RGB").crop(blank),
            visual_output / theme / "control-panel/qt/focus-background",
        )


def test_theme_inventory():
    assert set(THEMES) == EXPECTED_THEMES


@pytest.mark.parametrize("theme", ("win98", "win2k", "winxp-classic"))
@pytest.mark.parametrize("state", ("normal", "checked"))
def test_classic_radio_svg_matches_windows(theme, state, qt_app, tmp_path, visual_output):
    from gtk_inputs import classic_radio_css
    from PySide6.QtGui import QColor, QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer

    folder, metadata = THEMES[theme]
    classic_radio_css(tmp_path, metadata["look"])
    with Image.open(folder / "widget-controls" / f"radio-{state}.png") as native:
        expected = native.convert("RGB")
    frame = QImage(*expected.size, QImage.Format_RGB32)
    frame.fill(QColor(*expected.getpixel((0, 0))))
    source = tmp_path / ("radio-checked.svg" if state == "checked" else "radio.svg")
    painter = QPainter(frame)
    QSvgRenderer(str(source)).render(painter)
    painter.end()
    actual = qimage_to_pil(frame)
    if metadata.get("radio_rgb565"):
        actual = rgb565(actual)
    exact(expected, actual, visual_output / theme / "widget-controls" / "svg" / state)


@pytest.mark.parametrize(
    ("state", "version", "theme"),
    [
        pytest.param(state, version, theme, id=f"{state}-gtk{version[0]}-{theme}")
        for theme, (_, metadata) in THEMES.items()
        if "radio_scale" in metadata
        for state in ("normal", "checked", *metadata.get("radio_extra_states", ()))
        for version in ("3.0", "4.0")
    ],
)
def test_radio_indicator(theme, version, state, live_gtk, visual_output):
    folder, metadata = THEMES[theme]
    directory = live_gtk(metadata["look"], metadata["radio_scale"], "radio") / f"radio-gtk-{version}"
    inventory = json.loads((directory / "manifest.json").read_text())
    name = next(name for _, label, name in inventory if label == f"radio {state}")
    with Image.open(folder / "widget-controls" / f"radio-{state}.png") as native:
        expected = native.convert("RGB")
    with Image.open(directory / name) as rendered:
        gtk = rendered.convert("RGBA")
        if compositor_radio(metadata["look"], metadata["radio_scale"]):
            pixels = np.asarray(gtk)
            position = int(name.removesuffix(".png"))
            rows, columns = np.where(np.all(pixels == (225, 12, (207 + position) % 256, 255), axis=2))
            assert len(rows), f"Missing GTK radio capture marker in {rendered.filename}"
            # The marker starts at (12, 36) and the indicator at (12, 12).
            scale = metadata["radio_scale"]
            x, y = int(columns.min()), int(rows.min())
            gtk = gtk.crop((x - 3, y - round(28 * scale), x + round(22 * scale), y - round(5 * scale)))
        elif version == "3.0":
            # GTK 3 captures the decorated window's client, including the showcase margins.
            margin = round(12 * metadata["radio_scale"])
            client = gtk.getpixel((margin // 2, margin // 2))
            gtk = Image.alpha_composite(Image.new("RGBA", gtk.size, client), gtk)
            gtk = gtk.crop((margin, margin, gtk.width - margin, gtk.height - margin))
        # Find the indicator's painted bounds against the background or the transparent GTK 4 snapshot.
        background = gtk.getpixel((0, 0))
        rows, columns = np.where(np.any(np.asarray(gtk) != background, axis=2))
        assert len(rows), f"Missing GTK radio face in {rendered.filename}"
        face = gtk.crop((columns.min(), rows.min(), columns.max() + 1, rows.max() + 1))
        backdrop = Image.new("RGBA", face.size, expected.getpixel((0, 0)))
        backdrop.alpha_composite(face)
    actual = backdrop.convert("RGB")
    if metadata.get("radio_rgb565"):
        actual = rgb565(actual)
    exact(expected, actual, visual_output / theme / "widget-controls" / f"gtk{version[0]}" / state)


@pytest.mark.parametrize("state", ("normal", "checked", *THEMES["winxp"][1]["radio_extra_states"]))
def test_winxp_luna_radio_indicator_qt(state, qt_app, visual_output):
    from chicago95luna import INDICATOR_SIZE
    from PySide6.QtCore import QRect
    from PySide6.QtGui import QColor, QImage, QPainter
    from PySide6.QtWidgets import QStyle, QStyleOptionButton

    folder, metadata = THEMES["winxp"]
    with Image.open(folder / "widget-controls" / f"radio-{state}.png") as native:
        expected = native.convert("RGB")
    option = QStyleOptionButton()
    option.rect = QRect(4, 4, INDICATOR_SIZE, INDICATOR_SIZE)
    option.state = QStyle.State_Enabled
    if state.startswith("checked"):
        option.state |= QStyle.State_On
    if state.endswith("hovered"):
        option.state |= QStyle.State_MouseOver
    if state.endswith("pressed"):
        option.state |= QStyle.State_Sunken
    frame = QImage(32, 32, QImage.Format_RGB32)
    frame.setDevicePixelRatio(metadata["radio_scale"])
    background = expected.getpixel((0, 0))
    frame.fill(QColor(*background))
    with themed(qt_app, "luna"):
        painter = QPainter(frame)
        qt_app.style().drawPrimitive(QStyle.PE_IndicatorRadioButton, option, painter)
        painter.end()
    actual = rgb565(qimage_to_pil(frame))
    bounds = ImageChops.difference(actual, Image.new("RGB", actual.size, background)).getbbox()
    assert bounds is not None
    exact(expected, actual.crop(bounds), visual_output / "winxp/widget-controls/qt" / state)


@pytest.mark.parametrize("theme", [name for name, (_, meta) in THEMES.items() if "file_manager_scale" in meta])
def test_file_manager_navigation(theme, installed, visual_output):
    assert shutil.which("thunar"), "The GTK 3 file manager comparison requires Thunar"
    folder, metadata = THEMES[theme]
    scale = metadata["file_manager_scale"]
    look = metadata["look"]
    session = installed(look, scale, components=("explorer",))
    config = session.work / "home/.config"
    settings = configparser.ConfigParser()
    settings.read(config / "gtk-3.0/settings.ini")
    icons = "Windows-7-SVG" if look == "aero" else "Chicago95-Toolbar"
    settings["Settings"].setdefault("gtk-icon-theme-name", icons)
    with (config / "gtk-3.0/settings.ini").open("w") as stream:
        settings.write(stream)
    # Compare the client at a known origin so caption differences stay in their own tests.
    (config / "kwinrulesrc").write_text(
        "[General]\nrules=thunar\n[thunar]\nwmclass=thunar\nwmclassmatch=2\n"
        "position=0,0\npositionrule=2\nnoborder=true\nnoborderrule=2\n"
    )
    script = session.work / "file-manager.sh"
    destination = "/usr/share/icons" if look == "aero" else "/"
    script.write_text(
        '#!/bin/sh\nset -eu\n'
        'capture_toolbar() {\n'
        '  for attempt in 1 2 3 4 5 6; do\n'
        '    spectacle -b -n -f -o "$WORK/file-manager.png"\n'
        "    python3 -c 'from PIL import Image; import sys; "
        'toolbar = Image.open("file-manager.png").convert("RGB").crop((0, 0, 170, 24)); '
        'sys.exit(toolbar.getbbox() != (0, 0, *toolbar.size) or toolbar.getcolors(8) is not None)\' && return\n'
        '    sleep 0.5\n'
        '  done\n'
        '  rm -f "$WORK/file-manager.png"\n'
        '  return 1\n'
        '}\n'
        f'thunar {destination} >"$WORK/thunar.log" 2>&1 &\n'
        'gdbus wait --session --timeout 15 org.xfce.Thunar\n'
        'capture_toolbar\n'
    )
    if look == "aero":
        # The Explorer reference has Back enabled. Visit a parent breadcrumb to build that history.
        with script.open("a") as stream:
            stream.write(
                'python3 "$WORK/eis_pointer.py" move:211,15 click:left move:980,670 wait:0.6\n'
                'capture_toolbar\n'
            )
    environment = {
        **session.environment,
        "GDK_BACKEND": "wayland",
        "GTK_THEME": settings["Settings"]["gtk-theme-name"],
        "GTK_A11Y": "none",
        "GIO_USE_VFS": "local",
        "GIO_USE_VOLUME_MONITOR": "unix",
    }
    frame = session.work / "file-manager.png"
    frame.unlink(missing_ok=True)
    run_session(session.work, script, environment, session.screen, scale=scale)
    output = visual_output / theme / "file-manager" / "gtk3" / "navigation"
    output.mkdir(parents=True, exist_ok=True)
    for log in session.work.glob("*file-manager*.log"):
        shutil.copyfile(log, output / log.name)
    thunar_log = session.work / "thunar.log"
    if thunar_log.is_file():
        shutil.copyfile(thunar_log, output / thunar_log.name)
    with Image.open(folder / "file-manager/navigation.png") as reference:
        expected = reference.convert("RGB")
    assert frame.is_file(), f"Missing Thunar capture. See {output}"
    with Image.open(frame) as screen:
        screen.save(output / "screen.png")
        actual = screen.crop((0, 0, *expected.size)).convert("RGB")
    assert actual.getbbox(), f"Thunar did not render at the capture origin. See {output}"
    if look == "aero":
        for left, right, enabled in ((3, 30, True), (34, 62, False)):
            icon = np.asarray(actual.crop((left, 0, right, 28)))
            # Enabled arrows have a white core. The disabled native lens still
            # reaches 245, so its highlight alone cannot identify the state.
            assert (icon.min(axis=2).max() > 248) == enabled, f"Unexpected Thunar history state. See {output}"
    if look in ("2000", "2001", "luna"):
        actual = rgb565(actual)
    exact(expected, actual, output)


@pytest.fixture(scope="module")
def gtk4_file_manager(installed, visual_output):
    @cache
    def capture(theme):
        assert shutil.which("nautilus"), "The GTK 4 file manager comparison requires GNOME Files"
        _, metadata = THEMES[theme]
        scale = metadata["file_manager_scale"]
        aero = metadata["look"] == "aero"
        session = installed(metadata["look"], scale, components=("explorer",))
        destination = session.work / "home" / "Local Disk" / "Windows"
        destination.mkdir(parents=True)
        (destination / "System").mkdir()
        script = session.work / "gtk4-file-manager.sh"
        start = '"$HOME/Local Disk"' if aero else '"$HOME/Local Disk/Windows"'
        script.write_text(
            "#!/bin/sh\nset -eu\n"
            "gsettings set org.gnome.desktop.interface enable-animations false\n"
            "gsettings set org.gnome.nautilus.window-state maximized true\n"
            "gsettings set org.gnome.nautilus.preferences always-use-location-entry false\n"
            "gsettings set org.gnome.nautilus.preferences default-folder-viewer icon-view\n"
            "gsettings set org.gnome.nautilus.preferences click-policy single\n"
            f'nautilus {start} >"$WORK/nautilus.log" 2>&1 &\n'
            "gdbus wait --session --timeout 15 org.gnome.Nautilus\n"
            'for attempt in 1 2 3 4 5 6; do\n'
            '    sleep 1\n'
            '    spectacle -b -n -f -o "$WORK/gtk4-file-manager.png"\n'
            "    python3 -c 'from PIL import Image; import sys; "
            'image = Image.open("gtk4-file-manager.png").convert("RGB"); '
            'sys.exit(image.getbbox() != (0, 0, *image.size) or image.getcolors(20) is not None)\' && break\n'
            'done\n'
        )
        if aero:
            # Open the only folder in the grid so Back works and Forward is disabled.
            with script.open("a") as stream:
                stream.write(
                    'python3 "$WORK/eis_pointer.py" move:296,101 click:left move:800,300 wait:1 '
                    'snapshot:gtk4-file-manager move:226,20 wait:0.4 snapshot:history-hover '
                    'move:224,20 click:left move:800,300 wait:1 snapshot:history-after-back\n'
                )
        environment = {
            **session.environment,
            "GDK_BACKEND": "wayland",
            "GSK_RENDERER": "cairo",
            "GTK_A11Y": "none",
            "GIO_USE_VFS": "local",
            "GIO_USE_VOLUME_MONITOR": "unix",
        }
        frame = session.work / "gtk4-file-manager.png"
        run_session(session.work, script, environment, session.screen, scale=scale)
        output = visual_output / theme / "file-manager" / "gtk4" / "navigation"
        output.mkdir(parents=True, exist_ok=True)
        for log in (*session.work.glob("*gtk4-file-manager.log"), session.work / "nautilus.log"):
            if log.is_file():
                shutil.copyfile(log, output / log.name)
        assert frame.is_file(), f"Missing GNOME Files capture. See {output}"
        with Image.open(frame) as image:
            screen = image.convert("RGB")
        assert screen.getbbox() == (0, 0, *screen.size) and screen.getcolors(20) is None, (
            f"GNOME Files did not finish opening at the maximized size. See {output}"
        )
        screen.save(output / "screen.png")
        if aero:
            for state in ("history-hover", "history-after-back"):
                frame = session.work / f"{state}.png"
                assert frame.is_file(), f"Missing GNOME Files {state} capture. See {output}"
                shutil.copyfile(frame, output / frame.name)
        return screen, output

    return capture


@pytest.mark.parametrize("theme", [name for name, (_, meta) in THEMES.items() if "file_manager_scale" in meta])
def test_file_manager_navigation_gtk4(theme, gtk4_file_manager):
    folder, metadata = THEMES[theme]
    screen, output = gtk4_file_manager(theme)
    with Image.open(folder / "file-manager/navigation.png") as reference:
        expected = reference.convert("RGB")
    # Classic GTK's 18px client-side title strip has its own comparison.
    top = round(18 * metadata["file_manager_scale"]) if metadata["look"] in ("1995", "1998", "2000", "2001") else 0
    actual = screen.crop((0, top, expected.width, top + expected.height))
    if metadata["look"] in ("2000", "2001", "luna"):
        actual = rgb565(actual)
    exact(expected, actual, output)


def test_win7_gtk4_file_manager_address_surface(gtk4_file_manager):
    screen, output = gtk4_file_manager("win7")
    with Image.open(THEMES["win7"][0] / "file-manager/navigation.png") as reference:
        expected = reference.convert("RGB").crop((460, 4, 476, 26))
    # The GTK shell centres its 22px address field below the client-side title controls.
    actual = screen.crop((700, 8, 716, 30))
    error = np.abs(np.asarray(actual, dtype=int) - np.asarray(expected, dtype=int)).mean()
    assert error < 8, (error, output)


def test_win7_gtk4_file_manager_toolbar_leading_edge(gtk4_file_manager, visual_output):
    screen, _output = gtk4_file_manager("win7")
    bounds = (0, 0, 6, 1)
    with Image.open(THEMES["win7"][0] / "file-manager/navigation.png") as reference:
        expected = reference.convert("RGB").crop(bounds)
    exact(expected, screen.crop(bounds), visual_output / "win7/file-manager/gtk4/toolbar-leading-edge")


def test_win7_gtk4_file_manager_navigation_orbs(gtk4_file_manager):
    screen, output = gtk4_file_manager("win7")
    back = (210, 8, 241, 34)
    forward = (244, 8, 275, 34)
    active = np.asarray(screen.crop(back), dtype=int)
    disabled = np.asarray(screen.crop(forward), dtype=int)
    with Image.open(THEMES["win7"][0] / "file-manager/navigation.png") as reference:
        expected = np.asarray(reference.convert("RGB").crop((0, 1, 31, 27)), dtype=int)

    def blue_core(image):
        r, g, b = image.transpose(2, 0, 1)
        return (r < 90) & (g < 175) & (b > r + 45)

    core = blue_core(active)
    native_area = blue_core(expected).sum()
    assert 0.7 * native_area <= core.sum() <= 1.3 * native_area, output
    rest = active[core].mean()
    assert disabled[core].mean() > rest + 20, output
    with Image.open(output / "history-hover.png") as frame:
        hover = np.asarray(frame.convert("RGB").crop(back), dtype=int)
    assert hover[core].mean() > rest + 6, output
    with Image.open(output / "history-after-back.png") as frame:
        after = frame.convert("RGB")
    inactive_back = np.asarray(after.crop(back), dtype=int)
    active_forward = np.asarray(after.crop(forward), dtype=int)
    assert inactive_back[core].mean() > rest + 20, output
    assert blue_core(active_forward).sum() >= 0.7 * native_area, output


def test_winxp_gtk4_file_manager_address_fill(gtk4_file_manager, visual_output):
    screen, _output = gtk4_file_manager("winxp")
    with Image.open(THEMES["winxp"][0] / "file-manager/navigation.png") as reference:
        expected = reference.convert("RGB").crop((450, 66, 474, 90))
    # Compare the white Address field between labels and the rightmost controls.
    actual = rgb565(screen.crop((700, 21, 724, 45)))
    exact(expected, actual, visual_output / "winxp/file-manager/gtk4/address-fill")


@pytest.mark.parametrize("theme", ("win95", "win98", "win2k", "winxp-classic"))
def test_classic_gtk4_file_manager_caption_has_no_divider(theme, gtk4_file_manager, visual_output):
    screen, _output = gtk4_file_manager(theme)
    folder, _metadata = THEMES[theme]
    with Image.open(folder / "file-manager/caption-seam.png") as reference:
        expected = reference.convert("RGB")
    # The separate sidebar and file pane meet at x=255 on the 1280 px test output.
    actual = screen.crop((250, 2, 258, 10))
    output = visual_output / theme / "file-manager/gtk4/caption-seam"
    if theme in ("win95", "win98"):
        exact(expected, actual, output)
    else:
        # Windows 2000 and XP Classic use a dithered gradient in the native title.
        # Its colour changes across columns set the bound for a visible seam.
        native_step = np.abs(np.diff(np.asarray(expected, dtype=int), axis=1)).max()
        actual_step = np.abs(np.diff(np.asarray(actual, dtype=int), axis=1)).max()
        assert actual_step <= native_step, (actual_step, native_step)


@pytest.mark.parametrize(
    ("theme", "component", "state"),
    [
        pytest.param(theme, component, state, id=f"{theme}-{component}-{state}")
        for theme, (_, metadata) in THEMES.items()
        for component, captures in metadata.get("session_screens", {}).items()
        for state in captures
    ],
)
def test_session_screen(theme, component, state, tmp_path, visual_output):
    expected, actual, capture = session_screen_images(theme, component, state, tmp_path)
    # Exclude the personal account picture or the guest's software cursor.
    mask = None
    if "exclude" in capture:
        mask = np.ones((expected.height, expected.width), dtype=bool)
        left, top, right, bottom = capture["exclude"]
        mask[top:bottom, left:right] = False
    exact(expected, actual, visual_output / theme / component / "qt" / state, mask)


def session_screen_images(theme, component, state, tmp_path):
    folder, metadata = THEMES[theme]
    capture = metadata["session_screens"][component][state]
    with Image.open(folder / capture["frame"]) as frame:
        expected = frame.convert("RGB")
    output = tmp_path / "session.png"
    subprocess.run(
        [sys.executable, str(REPO / "tests/visual/render_session_screen.py"),
         str(folder / "manifest.json"), component, state, str(output)],
        check=True, timeout=120,
    )
    with Image.open(output) as frame:
        actual = rgb565(frame) if metadata["look"] in ("2000", "2001", "luna") else frame.convert("RGB")
    return expected, actual, capture


def test_win2k_unlock_window_bounds(tmp_path):
    expected, actual, _ = session_screen_images("win2k", "lock-screen", "1280x1024", tmp_path)

    def window_bounds(image):
        # Keep the guest's pointer near the top-left outside the measurement.
        client = image.crop((0, 100, image.width, image.height))
        background = Image.new("RGB", client.size, client.getpixel((0, 0)))
        return ImageChops.difference(client, background).getbbox()

    assert window_bounds(actual) == pytest.approx(window_bounds(expected), abs=1)


@pytest.mark.parametrize("component", ("sign-in", "lock-screen"))
def test_winxp_welcome_band_placement(component, tmp_path):
    expected, actual, _ = session_screen_images("winxp", component, "1280x1024", tmp_path)

    def edges(image):
        # The centre of each band is outside the account, logo, and footer text.
        pixels = np.asarray(image)
        header = pixels[:220, 1080:1160]
        footer = pixels[850:, 440:520]
        header_accent = np.flatnonzero(np.any(header != header[25], axis=(1, 2)))[0]
        header_end = header_accent + np.flatnonzero(
            np.all(header[header_accent:] == header[-1], axis=(1, 2))
        )[0]
        return (
            header_accent,
            header_end,
            850 + np.flatnonzero(np.any(footer != footer[0], axis=(1, 2)))[0],
        )

    assert edges(actual) == edges(expected)


def test_winxp_classic_rejected_unlock_window_bounds(tmp_path):
    expected, actual, _ = session_screen_images("winxp-classic", "lock-screen", "rejected", tmp_path)

    def window_bounds(image):
        pixels = np.asarray(image)
        foreground = np.any(pixels != pixels[100, 0], axis=2)
        # At this resolution only the modal message spans over half the screen.
        rows = np.flatnonzero(foreground.sum(axis=1) > image.width / 2)
        columns = np.flatnonzero(foreground[rows].any(axis=0))
        return columns[0], rows[0], columns[-1] + 1, rows[-1] + 1

    assert window_bounds(actual) == window_bounds(expected)


def test_win2k_post_login_window_bounds(tmp_path):
    expected, actual, capture = session_screen_images("win2k", "post-login", "1280x1024", tmp_path)

    def dialog_bounds(image):
        neutral = Image.new("RGB", image.size, image.getpixel((0, 0)))
        diff = ImageChops.difference(image, neutral)
        diff.paste(0, capture["exclude"])
        return diff.getbbox()

    assert dialog_bounds(actual) == pytest.approx(dialog_bounds(expected), abs=1)


def test_win2k_post_login_body_fill(tmp_path, visual_output):
    expected, actual, _capture = session_screen_images("win2k", "post-login", "1280x1024", tmp_path)
    bounds = (650, 398, 900, 439)
    exact(expected.crop(bounds), actual.crop(bounds), visual_output / "win2k/post-login/qt/body-fill")


def test_win2k_post_login_strip_travel_matches_windows(qt_app, visual_output):
    from time import monotonic

    from PySide6.QtCore import QObject
    from PySide6.QtTest import QTest
    from test_boot_visual_states import rendered

    folder, metadata = THEMES["win2k"]
    capture = metadata["post_login_strip"]
    with Image.open(folder / capture["frame"]) as image:
        native = image.convert("RGB")

    def highlight_x(frame):
        row = np.asarray(frame)[frame.height // 2]
        bright = np.flatnonzero(row[:, 1] > 173)
        assert bright.size > 30
        return bright.mean() / frame.width

    midpoint = native.height // 2
    native_start, native_end = (native.crop((0, y, native.width, y + midpoint)) for y in (0, midpoint))
    native_distance = highlight_x(native_end) - highlight_x(native_start)
    milliseconds = capture["sample_interval_ms"]
    with rendered(qt_app, "StartupStatus.qml", (443, 127), {"stripPhase": 0, "banner": ""}) as view:
        root = view.rootObject()
        strip = root.findChild(QObject, "sessionStatusStrip")
        bounds = (round(strip.x()), round(strip.y()), round(strip.x() + strip.width()), round(strip.y() + strip.height()))
        before = qimage_to_pil(view.grabWindow()).convert("RGB").crop(bounds)
        start = monotonic()
        root.setProperty("stripPhase", -1)
        QTest.qWait(milliseconds)
        actual_ms = (monotonic() - start) * 1000
        after = qimage_to_pil(view.grabWindow()).convert("RGB").crop(bounds)

    output = visual_output / "win2k/post-login/qt/strip-travel"
    output.mkdir(parents=True, exist_ok=True)
    before.save(output / "start.png")
    after.save(output / "end.png")
    actual_distance = highlight_x(after) - highlight_x(before)
    measurements = {
        "native": {"distance_in_strip_widths": native_distance, "elapsed_ms": milliseconds},
        "qt": {"distance_in_strip_widths": actual_distance, "elapsed_ms": actual_ms},
    }
    (output / "timing.json").write_text(json.dumps(measurements, indent=2) + "\n")
    assert actual_distance / actual_ms == pytest.approx(native_distance / milliseconds, rel=0.15)


def test_win7_sign_in_power_menu_frame(tmp_path, visual_output):
    expected, actual, _ = session_screen_images("win7", "sign-in", "power-menu-open", tmp_path)
    mask = np.ones((expected.height, expected.width), dtype=bool)
    # The menu lettering occupies these three boxes. Keep the frame and separators in the comparison.
    for top, bottom in ((7, 21), (37, 51), (59, 73)):
        mask[top:bottom, 34:100] = False
    exact(expected, actual, visual_output / "win7/sign-in/qt/power-menu-frame", mask)


def test_win7_sign_in_password_field_geometry(tmp_path, visual_output):
    expected, actual, _ = session_screen_images("win7", "sign-in", "password-selected", tmp_path)

    def borders(image):
        pixels = np.asarray(image.crop((80, 8, 200, 33)))
        return Image.fromarray(np.all(pixels == (102, 102, 102), axis=2)).convert("RGB")

    exact(borders(expected), borders(actual), visual_output / "win7/sign-in/qt/password-field-borders")
    selection = [bounding_box(image.crop((12, 10, 68, 31)), lambda rgb: rgb == (51, 153, 255))
                 for image in (expected, actual)]
    assert all(selection)
    assert all(abs(native - rendered) <= 2 for native, rendered in zip(*selection, strict=True)), selection


@pytest.fixture(scope="module")
def boot_frames(qt_app, tmp_path_factory):
    @cache
    def capture(theme):
        folder, metadata = THEMES[theme]
        look = metadata["look"]
        with Image.open(folder / "boot.png") as reference:
            expected = reference.convert("RGB")
        if look in ("1995", "1998", "2000"):
            from test_loading_screen_reference import SPLASH, render_splash

            if look == "2000":
                actual = render_splash(
                    qt_app, tmp_path_factory.mktemp("win2k-boot"),
                    stage=metadata["boot_step"], strip_step=metadata["boot_strip_step"],
                    brandText="Windows 2000", company="Microsoft",
                    tagline="Built on NT Technology",
                )
            else:
                # QEMU exposes the DOS boot bitmap before the VGA display stretches it to 4:3.
                expected = expected.resize((640, 480), Image.Resampling.NEAREST)
                name = "background.png" if look == "1995" else "windows98.png"
                actual = render_splash(
                    qt_app, tmp_path_factory.mktemp(f"{theme}-boot"), style="classic",
                    picture=str(SPLASH / "images" / name), strip_step=metadata.get("boot_step", -1),
                )
        elif look == "aero":
            from test_post_xp_boot import boot_view, image_at

            with boot_view(size=expected.size) as (view, root):
                actual = image_at(view, root, (metadata["boot_step"] + 0.5) * 1000 / 15)
        else:
            from luna.luna_qml import render_luna_splash

            phase = (metadata["boot_step"] + 0.5) / 18
            actual = render_luna_splash(qt_app, size=expected.size, properties={"phase": phase})
        return expected, actual.convert("RGB")

    return capture


@pytest.mark.parametrize("theme", THEMES)
def test_boot_frame(theme, boot_frames, visual_output):
    expected, actual = boot_frames(theme)
    exact(expected, actual, visual_output / theme / "boot" / "qt" / "frame")


@pytest.mark.parametrize(
    ("region", "box"), [("edition-area", (210, 272, 430, 310)), ("loading-bar", (255, 351, 381, 366))]
)
@pytest.mark.parametrize("theme", [theme for theme, (_, data) in THEMES.items() if data["look"] in ("2001", "luna")])
def test_boot_xp_regions(theme, boot_frames, region, box, visual_output):
    expected, actual = boot_frames(theme)
    assert expected.size == actual.size
    exact(expected.crop(box), actual.crop(box), visual_output / theme / "boot" / "qt" / region)


def test_boot_win98_static_art(boot_frames, visual_output):
    expected, actual = boot_frames("win98")
    assert expected.size == actual.size
    box = (0, 0, 640, 472)
    exact(expected.crop(box), actual.crop(box), visual_output / "win98" / "boot" / "qt" / "static-art")


BOOT_STRIP_CAPTURES = {
    "win98": (tuple(range(20)), 7, (0, 472, 640, 480)),
    "win2k": ((1, 2, 3, 8, 79, 159), 10, (0, 416, 640, 426)),
}


@pytest.fixture(scope="module")
def boot_strip_frames(qt_app, tmp_path_factory):
    from PySide6.QtTest import QTest
    from test_loading_screen_reference import splash_view

    @cache
    def render(theme):
        phases, _native_height, box = BOOT_STRIP_CAPTURES[theme]
        settings = {"style": "classic", "picture": "images/windows98.png"} if theme == "win98" else {
            "style": "2000", "brandText": "Windows 2000", "company": "Microsoft",
        }
        frames = {}
        with splash_view(qt_app, tmp_path_factory.mktemp(theme), strip_step=0, **settings) as view:
            for phase in phases:
                view.rootObject().setProperty("bootStripStep", phase)
                QTest.qWait(30)
                frames[phase] = qimage_to_pil(view.grabWindow()).crop(box)
        return frames

    return render


@pytest.fixture(scope="module")
def plymouth_boot_strip_frames(tmp_path_factory):
    from test_loading_screen_reference import SPLASH

    @cache
    def render(theme):
        work = tmp_path_factory.mktemp(f"{theme}-plymouth-strip")
        output = work / "theme"
        if theme in ("win95", "win98"):
            source = CHICAGO95_SRC / "Plymouth/Chicago95"
            assert (source / "Chicago95.script").is_file(), f"Missing Setup's Plymouth source in {source}"
            artwork = "windows95-boot.gif" if theme == "win95" else "windows98.png"
            command = [
                str(REPO / "setup/make_9x_boot.py"),
                str(source),
                str(SPLASH / "images" / artwork),
                str(output),
                "--look", theme[-2:],
            ]
        else:
            shutil.copytree(SPLASH, work / "splash")
            (work / "splash/settings.js").write_text(
                '.pragma library\nvar style = "2000"\nvar brandText = "Windows 2000"\n'
                'var company = "Microsoft"\nvar loadingText = "Starting up..."\n'
                'var footer = "Copyright © 1985-1999 Microsoft Corporation"\n'
            )
            shutil.copytree(REPO / "plymouth/Chicago95-2000", output)
            script = output / "Chicago95-2000.script"
            command = [
                str(REPO / "bin/chicago95-splash-image"),
                "--splash", str(work / "splash"),
                "--size", "640x480",
                "--out", str(output / "screen.png"),
                "--progress-strip", str(script),
            ]
        subprocess.run([sys.executable, *command], check=True, timeout=30)
        if theme == "win2k":
            assert "animate_strip = 1;" in script.read_text()
            assert len(list(output.glob("strip-*.png"))) == 160
        return output

    return render


@pytest.mark.parametrize("renderer", ("qt", "plymouth"))
@pytest.mark.parametrize(
    ("theme", "index", "phase"),
    [
        pytest.param(theme, index, phase, id=f"{theme}-{phase:03}")
        for theme, (phases, _height, _box) in BOOT_STRIP_CAPTURES.items()
        for index, phase in enumerate(phases)
    ],
)
def test_boot_strip_phase(theme, index, phase, renderer, boot_strip_frames, plymouth_boot_strip_frames, visual_output):
    folder, _metadata = THEMES[theme]
    _phases, height, box = BOOT_STRIP_CAPTURES[theme]
    with Image.open(folder / "boot" / "strip-phases.png") as sheet:
        expected = sheet.crop((0, height * index, 640, height * (index + 1)))
    if theme == "win98":
        # VGA stretches the complete 400-line framebuffer to 480 lines.
        # The repeated source row depends on the strip's position in that frame.
        frame = Image.new("RGB", (640, 400))
        frame.paste(expected, (0, 400 - height))
        expected = frame.resize((640, 480), Image.Resampling.NEAREST).crop(box)
    if renderer == "qt":
        actual = boot_strip_frames(theme)[phase]
    else:
        output = plymouth_boot_strip_frames(theme)
        filename = f"win95_boot_{phase}.png" if theme == "win98" else f"strip-{phase}.png"
        with Image.open(output / filename) as frame:
            actual = frame.crop(box) if theme == "win98" else frame.copy()
    exact(expected, actual, visual_output / theme / "boot" / renderer / f"strip-{phase:03}")


def test_boot_win2k_strip_playback_cadence(qt_app, tmp_path):
    from time import monotonic

    from PySide6.QtCore import QObject
    from PySide6.QtTest import QTest
    from test_loading_screen_reference import splash_view

    folder, _metadata = THEMES["win2k"]
    native = np.loadtxt(folder / "boot" / "strip-timestamps.txt")[:, 1]
    with splash_view(qt_app, tmp_path, strip_step=0, brandText="Windows 2000", company="Microsoft") as view:
        root = view.rootObject()
        strip = root.findChild(QObject, "win2000BootStrip")
        start = monotonic()
        root.setProperty("bootStripStep", -1)
        observed = [0.0]
        while len(observed) < 7 and monotonic() - start < 1.25:
            QTest.qWait(8)
            if strip.property("step") >= len(observed):
                observed.append(monotonic() - start)

    assert len(observed) == 7
    assert observed[1] == pytest.approx(native[1], abs=0.050)
    assert np.median(np.diff(observed[1:])) == pytest.approx(np.median(np.diff(native[1:])), abs=0.016)


@pytest.fixture(scope="module")
def win95_boot_phase_frames(qt_app, tmp_path_factory):
    from PySide6.QtTest import QTest
    from test_loading_screen_reference import splash_view

    output = tmp_path_factory.mktemp("win95-boot-phases")
    phases = {}
    with splash_view(qt_app, output, style="classic", picture="images/background.png", strip_step=0) as view:
        for capture in sorted((THEMES["win95"][0] / "boot").glob("phase-*.png")):
            phase = int(capture.stem.removeprefix("phase-"))
            view.rootObject().setProperty("bootStripStep", phase)
            QTest.qWait(25)
            phases[phase] = qimage_to_pil(view.grabWindow())
    return phases


@pytest.mark.parametrize("capture", sorted((THEMES["win95"][0] / "boot").glob("phase-*.png")), ids=lambda p: p.stem)
@pytest.mark.parametrize("renderer", ("qt", "plymouth"))
def test_boot_win95_palette_phase(capture, renderer, request, plymouth_boot_strip_frames, visual_output):
    phase = int(capture.stem.removeprefix("phase-"))
    with Image.open(capture) as image:
        expected = image.convert("RGB").resize((640, 480), Image.Resampling.NEAREST)
    if renderer == "qt":
        actual = request.getfixturevalue("win95_boot_phase_frames")[phase]
    else:
        output = plymouth_boot_strip_frames("win95")
        with Image.open(output / f"win95_boot_{phase}.png") as frame:
            actual = frame.convert("RGB")
    exact(expected, actual, visual_output / "win95" / "boot" / renderer / capture.stem)


@pytest.mark.parametrize("theme", ("win95", "win98"))
def test_boot_9x_plymouth_full_frame(theme, plymouth_boot_strip_frames, visual_output):
    folder, metadata = THEMES[theme]
    output = plymouth_boot_strip_frames(theme)
    with Image.open(folder / "boot.png") as reference:
        expected = reference.convert("RGB").resize((640, 480), Image.Resampling.NEAREST)
    with Image.open(output / f"win95_boot_{metadata.get('boot_step', 0)}.png") as frame:
        actual = frame.convert("RGB")
    exact(expected, actual, visual_output / theme / "boot" / "plymouth" / "frame")


@pytest.fixture(scope="module")
def shutdown_9x_plymouth_frames(plymouth_boot_strip_frames):
    @cache
    def capture(theme):
        folder, _ = THEMES[theme]
        output = plymouth_boot_strip_frames(theme)
        # The upstream script uses this filename in Plymouth's shutdown mode for both looks.
        with Image.open(output / "win95_shutdown-01.png") as asset:
            actual = asset.convert("RGB")
        with Image.open(folder / "shutdown/transition-wait.png") as reference:
            expected = reference.convert("RGB")
        # Windows 98's generated asset uses the display aspect ratio instead of the VGA framebuffer ratio.
        if theme == "win98":
            expected = expected.resize((640, 480), Image.Resampling.NEAREST)
        return expected, actual

    return capture


@pytest.mark.parametrize("theme", ("win95", "win98"))
def test_shutdown_9x_plymouth_full_frame(theme, shutdown_9x_plymouth_frames, visual_output):
    expected, actual = shutdown_9x_plymouth_frames(theme)
    exact(expected, actual, visual_output / theme / "shutdown/plymouth/frame")


def test_shutdown_win98_plymouth_background(shutdown_9x_plymouth_frames, visual_output):
    expected, actual = shutdown_9x_plymouth_frames("win98")
    # Keep the photographic asset comparison independent of the caption's lettering.
    for name, bounds in (
        ("main", (0, 0, 640, 445)),
        ("left-of-caption", (0, 445, 218, 464)),
        ("right-of-caption", (436, 445, 640, 464)),
        ("lower-sky", (0, 464, 640, 480)),
    ):
        exact(expected.crop(bounds), actual.crop(bounds), visual_output / "win98/shutdown/plymouth" / name)


def test_shutdown_win7_plymouth_status(qt_app, tmp_path, visual_output, monkeypatch):
    from test_post_xp_boot import SPLASH

    folder, _ = THEMES["win7"]
    session = tmp_path / "data/chicago95/session"
    session.mkdir(parents=True)
    art = REPO / "sddm/Chicago95Plasma"
    shutil.copyfile(art / "AeroBackground4x3.jpg", session / "background-4x3.jpg")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    source, output = tmp_path / "splash", tmp_path / "theme"
    shutil.copytree(SPLASH, source)
    panel = load_script("chicago95-control-panel")
    (source / "settings.js").write_text(panel.LoadingPreview.settings_js({
        "BOOT_STYLE": "7", "BOOT_FRAMES": "1", "BANNER_TEXT": "Windows 7",
        "EDITION": "Professional", "LOGIN_LOGO": "aero-flag",
    }))
    load_script("chicago95-post-xp-boot").build(
        source, output, (800, 600), REPO / "setup/post_xp_boot.script.in",
    )
    with Image.open(folder / "shutdown/status-800x600.png") as native, Image.open(output / "shutdown.png") as frame:
        expected, actual = native.convert("RGB"), frame.convert("RGB")
    # The single native frame captures an arbitrary point in the spinner cycle.
    mask = np.ones((expected.height, expected.width), dtype=bool)
    mask[237:263, 288:326] = False
    exact(expected, actual, visual_output / "win7/shutdown/plymouth/status-800x600", mask)


def test_boot_win2k_plymouth_full_frame(plymouth_boot_strip_frames, visual_output):
    folder, metadata = THEMES["win2k"]
    output = plymouth_boot_strip_frames("win2k")
    with Image.open(folder / "boot.png") as reference, Image.open(output / "screen.png") as background:
        expected, actual = reference.convert("RGB"), background.convert("RGB")
    with Image.open(output / f"strip-{metadata['boot_strip_step']}.png") as strip:
        actual.paste(strip, (0, 416))
    with Image.open(output / "block.png") as block:
        tile = block.resize((8, 8)).convert("RGB")
    # The guest reference has six of the eighteen blocks filled.
    for index in range(6):
        actual.paste(tile, (274 + index * 9, 437))
    exact(expected, actual, visual_output / "win2k" / "boot" / "plymouth" / "frame")


@pytest.fixture(scope="module")
def xp_plymouth_assets(tmp_path_factory):
    from conftest import run_bash_with_steps

    home = tmp_path_factory.mktemp("xp-plymouth")
    run_bash_with_steps(home, 'SETUP_BANNER_TEXT=""; stage_luna_plymouth "$HOME/theme"')
    return home / "theme"


@pytest.mark.parametrize("theme", ("winxp-classic", "winxp"))
def test_boot_xp_plymouth_full_frame(theme, xp_plymouth_assets, visual_output):
    folder, metadata = THEMES[theme]
    with Image.open(folder / "boot.png") as reference:
        expected = reference.convert("RGB")
    script = (xp_plymouth_assets / "Chicago95-XP.script").read_text()
    assert 'native_background = "boot-stock-640.png";' in script
    with Image.open(xp_plymouth_assets / "boot-stock-640.png") as background:
        actual = background.convert("RGB")
    with Image.open(xp_plymouth_assets / "trough.png") as trough:
        actual.paste(trough, (255, 351), trough)
    step = metadata["boot_step"]
    with Image.open(xp_plymouth_assets / "block.png") as blocks:
        for index in range(3):
            slot = step - 3 + index
            if 0 <= slot < 15:
                tile = blocks.crop((index * 8, 0, index * 8 + 6, 9))
                actual.paste(tile, (259 + slot * 8, 354), tile)
    exact(expected, actual, visual_output / theme / "boot" / "plymouth" / "frame")


@pytest.mark.parametrize(
    ("region", "box"), [("paper", (0, 370, 640, 416)), ("footer-background", (0, 426, 180, 480))]
)
def test_boot_win2k_solid_regions(boot_frames, region, box, visual_output):
    expected, actual = boot_frames("win2k")
    assert expected.size == actual.size
    exact(expected.crop(box), actual.crop(box), visual_output / "win2k" / "boot" / "qt" / region)


def test_boot_win2k_initial_frame(qt_app, tmp_path, visual_output):
    from test_loading_screen_reference import render_splash

    with Image.open(THEMES["win2k"][0] / "boot" / "phase-00.png") as image:
        expected = image.convert("RGB")
    actual = render_splash(
        qt_app, tmp_path / "win2k-boot", stage=0, strip_step=0,
        brandText="Windows 2000", company="Microsoft", tagline="Built on NT Technology",
    )
    exact(expected, actual, visual_output / "win2k" / "boot" / "qt" / "phase-00")


@pytest.mark.parametrize(("top", "bottom"), [(490, 570), (630, 767)])
def test_boot_win7_caption_positions_at_four_by_three(boot_frames, top, bottom):
    expected, actual = boot_frames("win7")

    def bounds(image):
        return bounding_box(image, lambda rgb: max(rgb) > 35, y_range=(top, bottom))

    native, rendered = bounds(expected), bounds(actual)
    assert native is not None and rendered is not None
    assert all(abs(a - b) <= 1 for a, b in zip(native, rendered, strict=True)), (native, rendered)


@pytest.fixture(scope="module")
def win7_boot_animation_frames(qt_app):
    from test_post_xp_boot import boot_view, image_at

    folder, _metadata = THEMES["win7"]
    phases = np.loadtxt(folder / "boot" / "animation-timestamps.txt", usecols=0, dtype=int).tolist()
    with boot_view(size=(1024, 768)) as (view, root):
        return {
            phase: image_at(view, root, (phase + 0.5) * 1000 / 15).crop((412, 284, 612, 484))
            for phase in phases
        }


@pytest.fixture(scope="module")
def win7_plymouth_animation_frames(qt_app, tmp_path_factory):
    from test_post_xp_boot import SPLASH

    root = tmp_path_factory.mktemp("win7-plymouth")
    source, output = root / "splash", root / "theme"
    shutil.copytree(SPLASH, source)
    panel = load_script("chicago95-control-panel")
    (source / "settings.js").write_text(panel.LoadingPreview.settings_js({"BOOT_STYLE": "7"}))
    load_script("chicago95-post-xp-boot").build(
        source, output, (1024, 768), REPO / "setup/post_xp_boot.script.in",
    )
    metadata = json.loads((output / "animation.json").read_text())
    assert (metadata["AX"], metadata["AY"]) == (412, 284)
    assert (metadata["WIDTH"], metadata["HEIGHT"]) == (1024, 768)
    return output


def test_boot_win7_plymouth_full_frame(win7_plymouth_animation_frames, visual_output):
    folder, metadata = THEMES["win7"]
    output = win7_plymouth_animation_frames
    animation = json.loads((output / "animation.json").read_text())
    with Image.open(folder / "boot.png") as reference, Image.open(output / "background.png") as background:
        expected, actual = reference.convert("RGB"), background.convert("RGB")
    with Image.open(output / f"frame-{metadata['boot_step']}.png") as frame:
        actual.paste(frame, (animation["AX"], animation["AY"]))
    exact(expected, actual, visual_output / "win7" / "boot" / "plymouth" / "frame")


@pytest.mark.parametrize("renderer", ("qt", "plymouth"))
@pytest.mark.parametrize("phase", range(3, 48))
def test_boot_win7_native_animation_phase(phase, renderer, request, visual_output):
    folder, _metadata = THEMES["win7"]
    index = phase - 3
    x, y = (index % 8) * 200, (index // 8) * 200
    with Image.open(folder / "boot" / "animation-frames.png") as capture:
        expected = capture.crop((x, y, x + 200, y + 200))
    if renderer == "qt":
        actual = request.getfixturevalue("win7_boot_animation_frames")[phase]
    else:
        output = request.getfixturevalue("win7_plymouth_animation_frames")
        with Image.open(output / f"frame-{phase}.png") as frame:
            actual = frame.convert("RGB").crop((0, 0, 200, 200))
    exact(expected, actual, visual_output / "win7" / "boot" / renderer / f"animation-{phase:03}")


AERO_MOTION_THEMES = [theme for theme, (_, metadata) in THEMES.items() if "caption" in metadata.get("motion", {})]
TITLE_STRIP_REFERENCES = {
    theme: json.loads((folder / spec).read_text())
    for theme, (folder, metadata) in THEMES.items()
    if (spec := metadata.get("motion", {}).get("title_strip"))
}


@pytest.mark.parametrize(
    ("theme", "action", "width"),
    [
        (theme, action, width)
        for theme in AERO_MOTION_THEMES
        for action, width in THEMES[theme][1]["motion"]["caption"].items()
    ],
)
def test_caption_motion(theme, action, width, qt_app, visual_output):
    from motion import caption_times, check_timing, compare_caption_motion

    stem = THEMES[theme][0] / "motion" / f"caption-{action}"
    measured = compare_caption_motion(action, width, caption_times(stem))
    check_timing(measured, visual_output / theme / "motion/qt-quick" / f"caption-{action}.json")


@pytest.mark.parametrize("theme", AERO_MOTION_THEMES)
def test_high_dpi_caption_motion(theme, visual_output):
    from motion import check_timing, compare_high_dpi_caption

    folder, metadata = THEMES[theme]
    measured = compare_high_dpi_caption(folder / "motion/caption-close-144dpi", metadata["motion"]["close_scale"])
    check_timing(measured, visual_output / theme / "motion/qt-quick/caption-close-144dpi.json")


@pytest.mark.parametrize("theme", AERO_MOTION_THEMES)
def test_window_motion(theme, desktops, visual_output):
    from motion import TOOLS, check_timing, compare_window_motion

    missing = [*missing_programs(), *(tool for tool in TOOLS if not shutil.which(tool))]
    assert not missing, f"Missing live motion dependencies: {', '.join(missing)}"
    folder, metadata = THEMES[theme]
    output = visual_output / theme / "motion/kwin"
    output.mkdir(parents=True, exist_ok=True)
    stems = [folder / "motion" / f"window-{action}" for action in metadata["motion"]["window"]]
    measured = compare_window_motion(desktops, output / "window-motion.webm", metadata["look"], stems)
    check_timing(measured, output / "window-motion.json")


@pytest.mark.parametrize(
    ("theme", "scale"),
    [(theme, scale) for theme, spec in TITLE_STRIP_REFERENCES.items() for scale in spec["render_scales"]],
)
def test_title_strip_motion(theme, scale, desktops, visual_output):
    from legacy_motion import check_title_strip_speed, measure_title_strip, native_luna_title_strip
    from motion import TOOLS

    missing = [*missing_programs(), *(tool for tool in TOOLS if not shutil.which(tool))]
    assert not missing, f"Missing live motion dependencies: {', '.join(missing)}"
    folder, metadata = THEMES[theme]
    spec = TITLE_STRIP_REFERENCES[theme]
    output = visual_output / theme / "motion/kwin" / f"scale-{scale:g}"
    output.mkdir(parents=True, exist_ok=True)
    native_frames = spec.get("native_title_strip_recording", ())
    if native_frames:
        native_folder = (folder / metadata["motion"]["title_strip"]).parent
        assert all((native_folder / name).is_file() for name in native_frames)
        native_measurements = native_luna_title_strip(native_folder)
    else:
        native_measurements = {"speed_px_ms": spec["native_speed_px_ms"]}
    measured = measure_title_strip(
        desktops, output / "title-strip.webm", metadata["look"], scale, spec["minimize_button"], classic=not native_frames
    )
    measurements = {"native": native_measurements, "rendered": measured}
    (output / "title-strip.json").write_text(json.dumps(measurements, indent=2) + "\n")
    check_title_strip_speed(measured, spec)


@pytest.mark.parametrize("theme", [theme for theme, spec in TITLE_STRIP_REFERENCES.items() if "maximize_buttons" in spec])
def test_legacy_maximize_motion(theme, desktops, visual_output):
    from legacy_motion import check_maximize_and_restore
    from motion import TOOLS

    missing = [*missing_programs(), *(tool for tool in TOOLS if not shutil.which(tool))]
    assert not missing, f"Missing live motion dependencies: {', '.join(missing)}"
    look = THEMES[theme][1]["look"]
    buttons = TITLE_STRIP_REFERENCES[theme]["maximize_buttons"]
    output = visual_output / theme / "motion/kwin"
    output.mkdir(parents=True, exist_ok=True)
    measured = check_maximize_and_restore(
        desktops, output / "maximize-restore.webm", look, buttons["normal"], buttons["maximized"]
    )
    (output / "maximize-restore.json").write_text(json.dumps(measured, indent=2) + "\n")


@pytest.mark.parametrize(("theme", "scale"), (("win95", 1), ("win95", 1.25), ("win2k", 1)))
def test_zoom_maximize_keeps_the_full_client_painted(theme, scale, desktops, visual_output):
    from legacy_motion import maximize_client_coverage, maximize_trace
    from motion import TOOLS

    missing = [*missing_programs(), *(tool for tool in TOOLS if not shutil.which(tool))]
    assert not missing, f"Missing live motion dependencies: {', '.join(missing)}"
    output = visual_output / theme / "motion" / "kwin" / f"maximize-{scale:g}x"
    output.mkdir(parents=True, exist_ok=True)
    frames, timestamps, states = maximize_trace(desktops, output / "maximize.webm", THEMES[theme][1]["look"], scale)
    coverage = maximize_client_coverage(frames)
    before, after = (next(record for record in states if record["phase"] == phase) for phase in ("before", "after"))
    onset = np.flatnonzero(np.max(abs(coverage - coverage[0]), axis=1) > .08)
    (output / "trace.json").write_text(json.dumps({
        "windows": states,
        "sample_ms": timestamps.tolist(),
        "client_quarter_coverage": coverage.tolist(),
    }, indent=2) + "\n")
    assert before["bounds"] == pytest.approx([160, 150, 760, 490], abs=1 / scale)
    assert after["bounds"][:3] == [0, 0, 1024] and after["bounds"][3] > 700
    assert onset.size, "the recording never shows the maximize action"
    settled = coverage[timestamps >= timestamps[onset[0]] + 500]
    assert len(settled) >= 3, "the recording must include multiple frames after maximize settles"
    assert settled.min() > .98, f"part of the maximized client failed to repaint. See {output}"


@pytest.mark.parametrize("theme", THEMES)
def test_coverage(theme):
    folder, metadata = THEMES[theme]
    assert (folder / "caption-states.png").is_file()
    gaps = [
        f"{component}: reference and renderer not registered"
        for component in COMPONENTS
        if component
        not in {
            "caption",
            "desktop",
            "run",
            "taskbar",
            "start-menu",
            "device-manager",
            "control-panel",
            "display-properties",
            "file-manager",
            "widget-controls",
            "boot",
            "sign-in",
            "post-login",
            "lock-screen",
            "shutdown",
            "motion",
        }
    ]
    if "motion" not in metadata:
        gaps.append("motion: native recordings and matching live scenarios")
    gaps.append("motion: remaining animation and output-scale variants, plus frame-by-frame comparison")
    if not (folder / "boot.png").is_file():
        gaps.append("boot: full-frame native reference and renderer")
    gaps.append("boot: complete graphical and text transitions and live Plymouth playback")
    if theme not in RUN_HISTORY_THEMES:
        gaps.append("run: native history popup")
    gaps.append("run: Browse, remaining pointer and button states and output scales")
    session_screens = metadata.get("session_screens", {})
    if not session_screens.get("post-login"):
        gaps.append("post-login: native frame and renderer for the strict comparison")
    for component in ("sign-in", "lock-screen"):
        if not session_screens.get(component):
            gaps.append(f"{component}: native frame and renderer for the strict comparison")
    gaps.append("sign-in: account chooser, alternate inputs and focus states")
    if not any(state.get("entry") for state in session_screens.get("sign-in", {}).values()):
        gaps.append("sign-in: password entry, selection and clearing")
    if not any(state.get("failed") for state in session_screens.get("sign-in", {}).values()):
        gaps.append("sign-in: rejected authentication state")
    lock_states = session_screens.get("lock-screen", {}).values()
    if not any(state.get("entry") for state in lock_states):
        gaps.append("lock-screen: password entry")
    if not any(state.get("failed") for state in lock_states):
        gaps.append("lock-screen: rejected authentication state")
    gaps.append("lock-screen: remaining output scales, selection, clearing and focus states")
    if "file_manager_scale" not in metadata:
        gaps.append("file-manager / GTK 3 and GTK 4: navigation reference")
    gaps.append("file-manager: contents, action states, and other supported file managers")
    if "radio_scale" not in metadata:
        gaps.append("widget-controls / GTK: native radio reference")
    gaps.append("widget-controls: other control types, action states and toolkit variants")
    if not (folder / "taskbar-band.png").is_file():
        gaps.append("taskbar / Plasma: empty-band reference")
    if "start_button" not in metadata:
        gaps.append("taskbar / Plasma: native Start button press and release captures")
    gaps.append("desktop / Plasma: icon selection, full hovered rows, submenus and drop targets")
    gaps.append("taskbar / Plasma: remaining populated variants and interactive states")
    for component in ("start-menu", "device-manager", "control-panel", "display-properties", "shutdown"):
        if not (folder / f"{component}.png").is_file():
            gaps.append(f"{component} / Qt: native reference")
    interaction = folder / "start-menu"
    if any(not (interaction / f"programs-{state}.png").is_file() for state in ("selection", "popup")):
        gaps.append("start-menu / Qt: Programs selection and cascade or expanded pane")
    if theme == "winxp" and any(
        not (interaction / f"recent-{state}.png").is_file() for state in ("selection", "popup")
    ):
        gaps.append("start-menu / Qt: Luna Recent Documents highlight and cascade")
    gaps.extend(
        (
            "start-menu / Qt: remaining hover targets, cascade contents and opening motion",
            "device-manager / Qt: remaining chrome, tree and device properties",
            "control-panel / Qt: navigation and category or icon-view variants",
            "display-properties / Qt: additional control states" if "display_pages" in metadata
            else "display-properties / Qt: remaining tabs and control states",
            "shutdown / Qt: additional choices",
            "shutdown: desktop transition and session-ending sequence",
        )
    )
    if "shutdown_button_crops" in metadata:
        if theme == "winxp":
            remaining = "keyboard activation, disabled states and tooltips"
        elif "shutdown_combo_states" in metadata:
            remaining = "dropdown item hover, button focus, Help window and tooltips"
            if "shutdown_hover_sample" in metadata:
                remaining += ", plus press and default-button animation timing"
        elif "shutdown_radio_states" in metadata:
            remaining = "optional radio choice, radio hover and press, other focus states and tooltips"
        else:
            remaining = "radio indicators, focus and tooltips"
        gaps.append(f"shutdown / Qt: {remaining}")
    else:
        gaps.append("shutdown / Qt: hover and pressed states")
        if "shutdown_combo_states" in metadata:
            gaps.append("shutdown / Qt: dropdown item hover, button focus and Help window")
    if theme == "win7":
        gaps.append("start-menu / Qt: glass pane and search results")
        gaps.append("control-panel / Qt: remaining category and action states")
        gaps.append("shutdown / KWin: Aero window frame")
    else:
        gaps.append("control-panel / Qt: hover and selection captures")
    if not (folder / "run.png").is_file():
        gaps.append("run / Qt: native reference")
    assert not gaps, f"{theme} parity coverage incomplete:\n" + "\n".join(gaps)
