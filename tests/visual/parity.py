"""Exact Windows comparisons. Run explicitly with pytest tests/visual/parity.py."""

import configparser
import json
import math
import shutil
import subprocess
import sys
from functools import cache
from shlex import quote

import numpy as np
import pytest
from aurorae_model import Window
from conftest import REPO, load_script
from original_pixels import compare
from PIL import Image, ImageColor, ImageFilter
from plasma_session import HOME_AFTER_SETUP, install, missing_programs, run_session, show, work_folder
from reference import REFERENCES, qimage_to_pil, render_start_menu, rgb565, theme_references
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

THEMES = {folder.name: (folder, metadata) for folder, metadata in theme_references(REFERENCES)}
EXPECTED_THEMES = {"win95", "win98", "win2k", "winxp-classic", "winxp", "win7"}
CAPTION_STATES = STATES[:-1]
GTK_STATES = dict(zip(CAPTION_STATES, ("normal", "hovered", "pressed", "disabled", "restore"), strict=True))
CAPTION_RENDERERS = {
    "svg": STATES,
    "kwin": CAPTION_STATES,
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
    "lock-screen",
    "shutdown",
    "motion",
)
WINDOW = (160, 150, 559, 449)
PRESS_WINDOWS = (WINDOW, (160, 470, 559, 699), (610, 470, 1009, 699))
DISABLED_WINDOW = (610, 150, 1009, 449)
DISABLED_TITLE = "Caption parity disabled"
DISABLED_APP = "org.chicago95.test.caption-disabled"


class AeroCaptionWindow(Window):
    RC_NAME = "Chicago95Aerorc"


@pytest.fixture(scope="module")
def installed():
    folders = []

    @cache
    def prepare(look, setup_scale=1):
        missing = missing_programs()
        assert not missing, f"Missing live-render dependencies: {', '.join(missing)}"
        folder = work_folder(f"parity-{look}")
        folders.append(folder)
        background = (
            {"settings": [("BACKGROUND_MODE", "color"), ("BACKGROUND_COLOR", "#4395D1")], "components": ["background"]}
            if look == "aero"
            else {}
        )
        return install(look, folder, screen=(1024, 768), launchers=0, setup_scale=setup_scale, **background)

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
                    f"move:{x + 45},{y + 12}",
                    "release:left",
                    "wait:0.3",
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
                ("Caption parity", "qt", WINDOW),
                ("Caption parity maximize press", "qt", PRESS_WINDOWS[1]),
                ("Caption parity close press", "qt", PRESS_WINDOWS[2]),
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
        disabled = next((record for record in records if record["title"] == DISABLED_TITLE), None)
        assert disabled is not None, f"KWin did not report the fixed-size caption fixture: {records}"
        assert disabled["closeable"] is False and disabled["maximizable"] is False, disabled
        assert tuple(disabled["bounds"][:2]) == DISABLED_WINDOW[:2], disabled
        output = visual_output / theme / "caption" / "kwin" / "disabled"
        output.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(session.work / "caption-disabled.png", output / "screen.png")
        return session.work, disabled["bounds"]

    return capture


@pytest.fixture(scope="module")
def live_gtk(installed):
    @cache
    def capture(look, scale):
        session = installed(look, scale) if look == "luna" else installed(look)
        home = session.work / "home"
        script = session.work / "caption-gtk.sh"
        commands = ["#!/bin/sh", "set -eu"]
        for version in ("3.0", "4.0"):
            settings = configparser.ConfigParser()
            settings.read(home / ".config" / f"gtk-{version}" / "settings.ini")
            theme = settings["Settings"]["gtk-theme-name"]
            directory = session.work / f"caption-gtk-{version}"
            command = (
                f"{quote(sys.executable)} {quote(str(REPO / 'tests/gtk_showcase.py'))} "
                f"{version} {quote(theme)} {quote(str(directory))} --consistency --only caption --caption-crops"
            )
            if look == "luna" and version == "3.0":
                command += " --compositor-captions"
            commands.append(command)
        script.write_text("\n".join(commands) + "\n")
        env = {
            **session.environment,
            "GDK_BACKEND": "wayland",
            "GTK_A11Y": "none",
            "CHICAGO95_CAPTION_SCALE": str(scale),
        }
        run_session(session.work, script, env, session.screen, scale=scale)
        for version in ("3.0", "4.0"):
            assert (session.work / f"caption-gtk-{version}" / "caption-crops.json").is_file(), (
                f"GTK {version} capture incomplete. See {session.work}/kwin-*.log"
            )
        return session.work

    return capture


def kwin_window(theme, look, width, height):
    if look == "luna":
        from luna.luna_model import LunaWindow

        return LunaWindow(width, height)
    window = AeroCaptionWindow if look == "aero" else Window
    return window(theme, width, height)


def kwin_maximized_window(theme, look, width, height):
    model = kwin_window(theme, look, width, height)
    for key in ("TitleEdgeTop", "TitleEdgeLeft", "TitleEdgeRight"):
        model.layout[key] = model.layout[key + "Maximized"]
    model.layout["ButtonMarginTop"] = model.layout.get("ButtonMarginTopMaximized", 0)
    return model


def kwin_face(capture, theme, look, scale, state, index):
    directory, disabled = capture
    suffix = f"-{index}" if state in ("hover", "pressed") or state.startswith("disabled-") else ""
    path = directory / f"caption-{state}{suffix}.png"
    assert path.is_file(), f"Missing nested KWin capture {path.name}"
    with Image.open(path) as frame:
        screen = frame.convert("RGB")
    if state == "restore":
        left, top = 0, 0
        model = kwin_maximized_window(theme, look, round(screen.width / scale), round(screen.height / scale))
    elif state.startswith("disabled"):
        left, top, right, bottom = disabled
        model = kwin_window(theme, look, round(right - left), round(bottom - top))
    else:
        left, top, right, bottom = PRESS_WINDOWS[index] if state == "pressed" else WINDOW
        model = kwin_window(theme, look, right - left + 1, bottom - top + 1)
    rect = model.button_rects()["IAX"[index]]
    if (look in CLASSIC and scale == 1.25) or (look == "luna" and scale % 1):
        config = configparser.ConfigParser()
        config.read(directory / "home/.config/kwinrc")
        wrapper = "classic" if look in CLASSIC else "luna"
        if config.get("org.kde.kdecoration2", "theme", fallback="") == f"org.chicago95.{wrapper}":
            # The caption wrapper snaps the paint layer's origin, independently
            # of the window's own origin and Aurorae's hit rectangle.
            def pixel(position):
                return math.floor(position * scale + 0.5)

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
            round(edge * scale)
            for edge in (
                left + rect.left(),
                top + rect.top(),
                left + rect.right(),
                top + rect.bottom(),
            )
        )
    )


def marker_bounds(image, colour):
    rows, columns = np.where(np.all(np.asarray(image) == ImageColor.getrgb(colour), axis=-1))
    assert len(rows) > 0, "GTK compositor capture is missing the geometry marker"
    return columns.min(), rows.min(), columns.max() + 1, rows.max() + 1


def gtk_face(directory, state, index):
    records = json.loads((directory / "caption-crops.json").read_text())
    suffix = f"-{BUTTONS[index]}" if state in ("hover", "pressed") else ""
    record = records[f"caption {GTK_STATES[state]}{suffix}"]
    box = record["faces"][BUTTONS[index]]
    with Image.open(directory / record["frame"]) as frame:
        if "compositor" not in record:
            return frame.crop(box).convert("RGB")
        marker = marker_bounds(frame.convert("RGB"), record["marker"])
    with Image.open(directory / record["compositor"]) as captured:
        screen = captured.convert("RGB")
    placed = marker_bounds(screen, record["marker"])
    for dimension in (0, 1):
        assert abs((placed[dimension + 2] - placed[dimension]) - (marker[dimension + 2] - marker[dimension])) <= 1
    dx, dy = placed[0] - marker[0], placed[1] - marker[1]
    x0, y0, x1, y1 = box
    return screen.crop((x0 + dx, y0 + dy, x1 + dx, y1 + dy))


@pytest.fixture(scope="module")
def visual_output(tmp_path_factory):
    return tmp_path_factory.getbasetemp() / "visual"


def exact(expected, actual, directory, mask=None):
    directory.mkdir(parents=True, exist_ok=True)
    actual.save(directory / "rendered.png")
    compare(expected, actual, directory / "comparison.png", mask)


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
    directory = visual_output / theme / "caption" / renderer / state / button
    exact(expected, actual, directory, visible_pixels(look, state, expected.size))


@pytest.mark.parametrize("state", ("rest", "hover", "pressed", "disabled"))
def test_luna_svg_close_glyph_core_matches_windows_pixels(state, svg_themes, visual_output):
    expected, background = face_region(caption_reference("luna"), "luna", state, BUTTONS.index("close"))
    ink = expected.getpixel((expected.width // 2, expected.height // 2))
    solid = np.all(np.asarray(expected) == ink, axis=-1)
    # One pixel of clearance isolates the solid X from its antialiasing and the face outline.
    core = np.asarray(Image.fromarray(solid.astype("uint8") * 255).filter(ImageFilter.MinFilter(3))) == 255
    actual = caption_pixels(svg_themes["luna"], "close", state, "luna", background.resize(expected.size))
    exact(expected, actual, visual_output / "winxp" / "caption" / "svg" / state / "close" / "glyph-core", core)


@pytest.mark.parametrize("matte", DISABLED_CLOSE_MATTES)
def test_win7_disabled_close_over_native_glass_matches_windows_pixels(svg_themes, matte, visual_output):
    glass, expected = disabled_close_matte(matte)
    actual = caption_pixels(svg_themes["aero"], "close", "disabled", "aero", glass)
    exact(expected, actual, visual_output / "win7" / "caption" / "svg" / "disabled" / "close" / matte)


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


@pytest.mark.parametrize("theme", THEMES)
def test_run_dialog(theme, qt_app, svg_themes, tmp_path, visual_output, monkeypatch):
    import chicago95ui

    folder, metadata = THEMES[theme]
    path = folder / "run.png"
    assert path.is_file(), f"{theme} needs a pixel-comparable Run dialog reference"
    look = metadata["look"]
    monkeypatch.setattr(chicago95ui, "DECORATION", svg_themes[look])
    directory = visual_output / theme / "run" / "qt"
    with Image.open(path) as reference:
        expected = reference.crop(metadata["run_crop"]) if "run_crop" in metadata else reference.convert("RGB")
    if look == "aero":
        subprocess.run(
            [
                sys.executable,
                str(REPO / "tests/aero/render_aero_dialogs.py"),
                str(tmp_path),
                str(metadata["run_scale"]),
                "--only-run",
            ],
            check=True,
            timeout=45,
        )
        with Image.open(tmp_path / "run.png") as actual:
            exact(expected, actual, directory)
        return
    with themed(qt_app, look):
        dialog = load_script("chicago95-run").RunDialog({"style": look}, [], [], history=[])
        try:
            dialog.show()
            qt_app.processEvents()
            actual = qimage_to_pil(dialog.grab().toImage())
        finally:
            dialog.close()
    exact(expected, actual, directory)


@pytest.mark.parametrize("theme", THEMES)
def test_taskbar_band(theme, installed, visual_output):
    folder, metadata = THEMES[theme]
    with Image.open(folder / "taskbar-band.png") as reference:
        expected = reference.convert("RGB")
    screen = show(installed(metadata["look"]), windows=[])
    x = metadata["taskbar_x"]
    actual = screen.crop((x, screen.height - expected.height, x + expected.width, screen.height))
    exact(expected, actual, visual_output / theme / "taskbar" / "plasma" / "empty-band")


@pytest.mark.parametrize("theme", THEMES)
def test_device_manager(theme, tmp_path, visual_output):
    folder, metadata = THEMES[theme]
    with Image.open(folder / "device-manager.png") as reference:
        expected = reference.convert("RGB")
    if "device_manager_crop" in metadata:
        expected = expected.crop(metadata["device_manager_crop"])
    look = metadata["look"]
    output = tmp_path / "device-manager.png"
    subprocess.run(
        [
            sys.executable,
            str(REPO / "tests/visual/render_device_manager.py"),
            look,
            str(metadata["device_manager_scale"]),
            str(output),
        ],
        check=True,
        timeout=45,
    )
    with Image.open(output) as capture:
        if look in CLASSIC[:2]:
            actual = capture.convert("RGB")
        else:
            # Both regions start at the console client origin. A short render
            # stays short so the comparator reports the geometry difference.
            actual = capture.crop((0, 0, min(expected.width, capture.width), min(expected.height, capture.height)))
    exact(expected, actual, visual_output / theme / "device-manager" / "qt")


@pytest.mark.parametrize("theme", THEMES)
def test_start_menu(theme, qt_app, tmp_path, visual_output, monkeypatch):
    from render_report import MENU_EXTRA_TOP, MENU_SETTINGS

    folder, metadata = THEMES[theme]
    look = metadata["look"]
    with Image.open(folder / "start-menu.png") as reference:
        expected = reference.convert("RGB")
    if look == "aero":
        subprocess.run(
            [sys.executable, str(REPO / "tests/aero/render_aero_dialogs.py"), str(tmp_path), "1"],
            check=True,
            timeout=45,
        )
        with Image.open(tmp_path / "start.png") as capture:
            # Search and All Programs sit in the opaque pane. Anchor the crop
            # to the menu's bottom edge as in the SP1 taskbar capture.
            actual = capture.crop((8, capture.height - 53, 260, capture.height - 7))
    elif look == "luna":
        with themed(qt_app, look):
            _label, _reference, actual = start_menus(qt_app, look, tmp_path)[0]
    else:
        settings, colours = MENU_SETTINGS[look]
        startmenu = load_script("chicago95-startmenu")
        if user := metadata.get("start_menu_user"):
            monkeypatch.setattr(startmenu.getpass, "getuser", lambda: user)
        actual = render_start_menu(
            startmenu,
            qt_app,
            tmp_path,
            settings,
            colours,
            active=metadata.get("start_menu_active"),
            extra_top=MENU_EXTRA_TOP.get(look, ()),
        )
    exact(expected, actual, visual_output / theme / "start-menu" / "qt")


def render_properties(folder, component, output, size):
    subprocess.run(
        [
            sys.executable,
            str(REPO / "tests/visual/render_properties.py"),
            str(folder / "manifest.json"),
            component,
            str(output),
            str(size[0]),
            str(size[1]),
        ],
        check=True,
        timeout=45,
    )


@pytest.mark.parametrize("theme", THEMES)
@pytest.mark.parametrize("component", ["control-panel", "display-properties"])
def test_properties(theme, component, tmp_path, visual_output):
    folder, _metadata = THEMES[theme]
    with Image.open(folder / f"{component}.png") as frame:
        expected = frame.convert("RGB")
    output = tmp_path / f"{component}.png"
    render_properties(folder, component, output, expected.size)
    with Image.open(output) as actual:
        exact(expected, actual, visual_output / theme / component / "qt")


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


def test_theme_inventory():
    assert set(THEMES) == EXPECTED_THEMES


@pytest.mark.parametrize("theme", THEMES)
def test_coverage(theme):
    folder, _metadata = THEMES[theme]
    assert (folder / "caption-states.png").is_file()
    gaps = [
        f"{component}: reference and renderer not registered"
        for component in COMPONENTS
        if component
        not in {
            "caption",
            "run",
            "taskbar",
            "start-menu",
            "device-manager",
            "control-panel",
            "display-properties",
        }
    ]
    if not (folder / "taskbar-band.png").is_file():
        gaps.append("taskbar / Plasma: empty-band reference")
    gaps.append("taskbar / Plasma: interactive and populated states")
    for component in ("start-menu", "device-manager", "control-panel", "display-properties"):
        if not (folder / f"{component}.png").is_file():
            gaps.append(f"{component} / Qt: native reference")
    gaps.extend(
        (
            "start-menu / Qt: hover and open submenus",
            "device-manager / Qt: remaining chrome, tree and device properties",
            "control-panel / Qt: navigation and category or icon-view variants",
            "display-properties / Qt: remaining tabs and control states",
        )
    )
    if theme == "win7":
        gaps.append("start-menu / Qt: glass pane and search results")
        gaps.append("control-panel / Qt: remaining category and action states")
    else:
        gaps.append("control-panel / Qt: hover and selection captures")
    if not (folder / "run.png").is_file():
        gaps.append("run / Qt: native reference")
    assert not gaps, f"{theme} parity coverage incomplete:\n" + "\n".join(gaps)
