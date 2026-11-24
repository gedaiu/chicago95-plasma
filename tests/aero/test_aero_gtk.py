"""Exercise Setup's GTK migration and the resulting client-side caption in both toolkits."""

import json
import shutil
from pathlib import Path
from shlex import quote

import numpy as np
import pytest
from conftest import REPO, run_bash_with_steps
from PIL import Image
from plasma_session import run_session


@pytest.fixture(scope="module")
def aero_gtk_home(tmp_path_factory):
    if not shutil.which("kwin_wayland"):
        pytest.skip("requires a nested Wayland compositor")
    tmp_path = tmp_path_factory.mktemp("aero-gtk")
    theme = tmp_path / ".themes/Chicago95Aero"
    theme.parent.mkdir()
    theme.symlink_to(REPO / "aero/gtk/Chicago95Aero")
    decoration = tmp_path / ".local/share/aurorae/themes/Chicago95Aero"
    decoration.parent.mkdir(parents=True)
    decoration.symlink_to(REPO / "aero/aurorae/theme")
    for version in ("3.0", "4.0"):
        config = tmp_path / f".config/gtk-{version}"
        config.mkdir(parents=True)
        (config / "gtk.css").write_text(
            "/* personal rule */button { margin: 0; }/* >>> Chicago95 title bars BEGIN */\n"
            "/* obsolete classic header */\n/* <<< Chicago95 title bars END */\n"
        )
    run_bash_with_steps(
        tmp_path, 'SETUP_DECORATION=aero; import_gtk4_theme Chicago95Aero; write_gtk_titlebar_css "" "" ""'
    )
    return tmp_path


@pytest.fixture(scope="module")
def gtk_captures(aero_gtk_home):
    tmp_path = aero_gtk_home
    script = tmp_path / "render"
    script.write_text(
        "#!/bin/sh\nset -e\n"
        + "\n".join(
            f"python3 {quote(str(REPO / 'tests/gtk_showcase.py'))} {version} Chicago95Aero "
            f"{version} --consistency --only {controls}"
            for version, controls in [
                ("3.0", "caption,checkbox,radio,progress,scrollbar,tabs,palette"),
                ("4.0", "caption,checkbox,radio,progress,scrollbar,tabs,palette"),
            ]
        )
    )
    runtime = tmp_path / "run"
    runtime.mkdir(mode=0o700)
    run_session(
        tmp_path,
        script,
        {
            "HOME": str(tmp_path),
            "PATH": "/usr/bin:/bin",
            "XDG_RUNTIME_DIR": str(runtime),
            "GDK_BACKEND": "wayland",
            "GSK_RENDERER": "cairo",
            "GTK_A11Y": "none",
        },
        (700, 400),
    )
    return tmp_path


def test_aero_replaces_classic_caption_and_paints_gtk_window_buttons(gtk_captures):
    tmp_path = gtk_captures
    for version in ("3.0", "4.0"):
        css = (tmp_path / f".config/gtk-{version}/gtk.css").read_text()
        assert "personal rule" in css and "obsolete classic header" not in css
        assert css.count("Chicago95 title bars BEGIN") == 1
        results = tmp_path / version
        shots = {}
        for _, label, name in json.loads((results / "manifest.json").read_text()):
            shots[label] = np.asarray(Image.open(results / name).convert("RGB"), dtype=int)
        # A native GTK3 window can still be in backdrop state in its first frame.
        for state in ("hovered", "pressed"):
            pixels = shots[f"caption {state}"]
            r, g, b = pixels.transpose(2, 0, 1)
            assert ((r > 120) & (r > g + 48) & (r > b + 48)).sum() > 150
        assert not np.array_equal(shots["caption normal"], shots["caption pressed"])


def test_gtk_symbolic_icon_keeps_its_transparent_padding(tmp_path):
    import base64
    import io
    import subprocess
    import sys

    from test_aero_imported_art import vector_art

    source = tmp_path / "source"
    actions = source / "actions"
    actions.mkdir(parents=True)
    (source / "index.theme").write_text("[Icon Theme]\nName=Windows-7\nDirectories=actions\n[actions]\nSize=16\n")
    image = Image.new("RGBA", (16, 16))
    image.paste("black", (6, 2, 10, 14))
    stream = io.BytesIO()
    image.save(stream, "PNG")
    data = base64.b64encode(stream.getvalue()).decode()
    (actions / "test-symbolic.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16">'
        f'<image width="16" height="16" href="data:image/png;base64,{data}"/></svg>'
    )
    vector_art.icon_theme(source, tmp_path / "icons/Aero")
    # GtkIconInfo applies GTK's symbolic recolouring before we inspect the rendered pixels.
    subprocess.run(
        [
            sys.executable,
            "-c",
            """
import gi, sys
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk
theme = Gtk.IconTheme()
theme.set_search_path([sys.argv[1]])
theme.set_custom_theme("Aero")
pixbuf, symbolic = theme.lookup_icon("test-symbolic", 16, 0).load_symbolic(Gdk.RGBA(0,0,0,1))
assert symbolic
alpha = pixbuf.get_pixels()[3::4]
assert alpha[0] == 0 and alpha[8 * 16 + 8] == 255
""",
            str(tmp_path / "icons"),
        ],
        check=True,
    )


@pytest.mark.skipif(
    not all(shutil.which(p) for p in ("kwin_wayland", "nautilus", "spectacle")), reason="needs GNOME Files and KWin"
)
@pytest.mark.parametrize(("view", "scale"), [("icon", 1), ("list", 1), ("icon", 1.5)])
def test_files_selection_in_grid_and_list_views(gtk_captures, tmp_path, view, scale):
    folder = tmp_path / "Filing cabinet"
    (folder / "Documents").mkdir(parents=True)
    (folder / "Pictures").mkdir()
    runtime = tmp_path / "run"
    runtime.mkdir(mode=0o700)
    script = tmp_path / "files"
    script.write_text(
        """#!/bin/sh
set -eu
gsettings set org.gnome.desktop.interface enable-animations false
gsettings set org.gnome.nautilus.preferences always-use-location-entry "$EDIT_LOCATION"
gsettings set org.gnome.nautilus.window-state maximized true
gsettings set org.gnome.desktop.wm.preferences button-layout ":minimize,maximize,close"
gsettings set org.gnome.nautilus.preferences default-folder-viewer "$VIEW-view"
nautilus --select "$FOLDER/Documents" >"$VIEW.log" 2>&1 &
for attempt in 1 2 3 4 5 6; do
    sleep 0.5
    spectacle -b -n -f -o "$PWD/$VIEW.png"
    python3 - "$VIEW.png" <<'PYREADY' && break
from PIL import Image
import sys
sys.exit(Image.open(sys.argv[1]).getpixel((850, 300))[:3] != (255, 255, 255))
PYREADY
done
# A maximized window may still be scaling into position during the first capture.
sleep 0.5
spectacle -b -n -f -o "$PWD/$VIEW.png"
"""
    )
    run_session(
        tmp_path,
        script,
        {
            "HOME": str(gtk_captures),
            "PATH": "/usr/bin:/bin",
            "XDG_RUNTIME_DIR": str(runtime),
            "GSETTINGS_BACKEND": "keyfile",
            "GDK_BACKEND": "wayland",
            "GSK_RENDERER": "cairo",
            "GTK_A11Y": "none",
            "FOLDER": str(folder),
            "VIEW": view,
            "EDIT_LOCATION": "true" if view == "list" else "false",
            "XDG_SESSION_TYPE": "wayland",
        },
        (1000, 700),
        scale=scale,
    )
    image = Image.open(tmp_path / f"{view}.png").convert("RGB")
    assert image.size == (1000 * scale, 700 * scale)
    header = np.asarray(image, dtype=int)
    # Both halves meet at 20% of the window width. Compare the glass and bottom rule.
    left, right = [header[: round(44 * scale), round(x * scale)] for x in (195, 204)]
    assert np.abs(left - right).mean() < 3
    # Centre the 20px painted group in the 42px toolbar, with 6px outside its
    # right edge. The red interior sits inside the glass border and its highlight.
    r, g, b = header[: round(45 * scale), round(930 * scale) :].transpose(2, 0, 1)
    y, x = np.where((r > 145) & (r > g + 50) & (r > b + 50))
    assert abs((y.min() + y.max()) / 2 - 21 * scale) <= 2 * scale
    right_gap = image.width - (round(930 * scale) + x.max() + 1)
    assert 6 * scale <= right_gap <= 10 * scale
    assert 44 * scale <= np.ptp(x) <= 50 * scale
    from caption_cluster import compare_cluster

    region = image.crop((round(850 * scale), 0, image.width, round(50 * scale)))
    scores, buttons = compare_cluster(region, scale, maximized=True)
    buttons.save(tmp_path / "maximized-caption.png")
    limits = (0.88, 0.65, 0.98) if scale == 1 else (0.60, 0.72, 0.72)
    assert all(score >= limit for score, limit in zip(scores, limits, strict=True)), scores
    # Both location modes share one rounded outline. The straight top and bottom
    # edges stop short of the left and right sides by the radius of each corner.
    field = header[: round(42 * scale), round(270 * scale) : round(790 * scale)]
    border = np.abs(field - (136, 153, 167)).max(axis=2) < 4
    edges = np.flatnonzero(border.sum(axis=1) > 300 * scale)
    assert len(edges) >= 2
    sides = np.flatnonzero(border[round(18 * scale)])
    for row in (edges[0], edges[-1]):
        top_or_bottom = np.flatnonzero(border[row])
        assert 3 * scale <= top_or_bottom[0] - sides[0] <= 8 * scale
        assert 3 * scale <= sides[-1] - top_or_bottom[-1] <= 8 * scale
    shot = np.asarray(image.resize((1000, 700), Image.Resampling.NEAREST), dtype=int)
    # The selected row spans the pane in list mode; the icon's tile is bounded in grid mode.
    pane = shot[55:350, 210:950]
    r, g, b = pane.transpose(2, 0, 1)
    assert ((r >= 200) & (r < 232) & (g > r + 12) & (b > g + 5)).sum() > 1000
    y, x = np.where(np.all(pane == (153, 201, 231), axis=2))
    assert len(x) > 200
    if view == "list":
        assert np.ptp(x) > 650 and np.ptp(y) < 70
    else:
        assert 70 < np.ptp(x) < 180 and np.ptp(y) > 70
    assert (pane.min(axis=2) == 255).sum() > 5000


def widget_pixels(directory):
    result = {}
    for _, label, filename in json.loads((directory / "manifest.json").read_text()):
        shot = Image.open(directory / filename).convert("RGBA")
        canvas = Image.new("RGBA", shot.size, "#f0f0f0")
        canvas.alpha_composite(shot)
        if directory.name == "3.0":
            # GTK 3 captures the window with the showcase's 12px margins.
            canvas = canvas.crop((12, 12, canvas.width - 12, canvas.height - 12))
        result[label] = np.asarray(canvas.convert("RGB"), dtype=int)
    return result


@pytest.fixture(scope="module")
def gtk4_pixels(gtk_captures):
    return widget_pixels(gtk_captures / "4.0")


@pytest.fixture(scope="module")
def gtk3_pixels(gtk_captures):
    return widget_pixels(gtk_captures / "3.0")


@pytest.fixture(params=["gtk3_pixels", "gtk4_pixels"], scope="module")
def gtk_pixels(request):
    return request.getfixturevalue(request.param)


@pytest.mark.parametrize(
    "label,limit",
    [
        ("checkbox checked", 2),
        ("checkbox mixed", 2),
        ("radio checked-hovered", 3),
        ("radio disabled", 7),
        ("palette button", 2),
        ("palette entry", 2),
        ("progress half-horizontal", 2),
        ("scrollbar pressed-vertical", 2),
        ("tabs first-top", 5),
    ],
)
def test_control_face_matches_across_gtk_versions(gtk3_pixels, gtk4_pixels, label, limit):
    gtk3 = gtk3_pixels[label]
    gtk4 = gtk4_pixels[label]
    assert gtk3.shape == gtk4.shape
    assert np.abs(gtk3 - gtk4).mean() < limit


@pytest.mark.parametrize("kind", ["checkbox", "radio"])
def test_indicator_size_glyph_and_interaction_states(gtk_pixels, kind):
    def shot(state):
        return gtk_pixels[f"{kind} {state}"]

    assert shot("normal").shape[:2] == (13, 13)
    for state in ("normal", "hovered", "pressed"):
        unchecked = shot(state)
        checked = shot("checked" if state == "normal" else f"checked-{state}")
        assert (np.abs(checked - unchecked).max(axis=2) > 35).sum() >= 8
    normal, hover, press = [shot(state)[3, 4] for state in ("normal", "hovered", "pressed")]
    assert np.ptp(normal) < 25
    assert hover[2] > hover[0] + 40 and press[0] < hover[0]
    assert np.ptp(shot("disabled"), axis=2).max() < 5
    if kind == "checkbox":
        assert np.abs(shot("checked") - shot("mixed")).sum() > 1000


@pytest.mark.parametrize("direction", ["horizontal", "vertical"])
def test_progress_track_fill_and_direction(gtk_pixels, direction):
    def filled(state):
        shot = gtk_pixels[f"progress {state}-{direction}"]
        if direction == "vertical":
            shot = shot.transpose(1, 0, 2)[:, ::-1]
        assert shot.shape[0] == 14
        r, g, b = shot[8].T
        return (g > r + 80) & (g > b + 80)

    assert not filled("empty").any()
    assert 0 < filled("low").sum() < 5
    assert 0.52 < filled("half").mean() < 0.58
    assert filled("full").mean() > 0.97
    assert filled("half")[5] and filled("inverted")[-6]
    assert filled("rtl")[-6 if direction == "horizontal" else 5]


def scroll_thumb_image(capture, direction):
    """Crop the thumb including the native sprite's one-pixel exterior."""
    horizontal = direction == "horizontal"
    image = capture if horizontal else capture.transpose(1, 0, 2)
    ink = np.flatnonzero((image[image.shape[0] // 2] != (240, 240, 240)).any(axis=1))
    start, stop = ink[0] - 1, ink[-1] + 2
    assert 0 <= start < stop <= image.shape[1]
    thumb = image[:, start:stop]
    return thumb if horizontal else thumb.transpose(1, 0, 2)


@pytest.mark.parametrize(("state", "index"), [("normal", 0), ("hovered", 1), ("pressed", 2)])
@pytest.mark.parametrize("direction", ["horizontal", "vertical"])
def test_scroll_thumb_against_windows_art(gtk_pixels, direction, state, index):
    from aero_sprites import control_state, part, sprites_available

    if not sprites_available():
        pytest.skip("requires the extracted Windows 7 control artwork")
    horizontal = direction == "horizontal"
    name = "THUMBBTNHORZ" if horizontal else "THUMBBTNVERT"
    original = np.asarray(control_state("SCROLLBAR", name, index), dtype=int)
    actual = scroll_thumb_image(gtk_pixels[f"scrollbar {state}-{direction}"], direction)
    margins = part("SCROLLBAR", name).margins
    corner = np.s_[:margins.top, :margins.left]
    assert np.abs(actual[corner] - original[corner]).mean() < (6 if horizontal else 8.5)

    # Windows stretches the centre strip between the fixed caps. Sample the
    # painted face before the separately drawn grip, including both rims.
    if not horizontal:
        original = original.transpose(1, 0, 2)
        actual = actual.transpose(1, 0, 2)
    cap = margins.left if horizontal else margins.top
    assert np.abs(actual[:, cap + 1:cap + 4] - original[:, cap:cap + 1]).mean() < 4


@pytest.mark.parametrize("direction", ["horizontal", "vertical"])
def test_scroll_thumb_geometry_position_and_feedback(gtk_pixels, direction):
    def shot(state):
        image = gtk_pixels[f"scrollbar {state}-{direction}"]
        return image if direction == "horizontal" else image.transpose(1, 0, 2)

    normal = shot("normal")
    assert normal.shape[0] == 17
    # Three dark grip ridges cross the centre of each thumb.
    assert (normal[8].max(axis=1) < 135).sum() >= 3
    for state, endpoint in (("start", 3), ("end", -4)):
        assert (shot(state)[1, endpoint] < 200).all()
    y, x = np.where(shot("hovered")[:, :, 2] > shot("hovered")[:, :, 0] + 25)
    assert np.ptp(y) >= 8 and np.ptp(x) >= 25
    assert np.mean(shot("pressed")[y, x, 0]) < np.mean(shot("hovered")[y, x, 0]) - 10
    assert np.abs(normal - shot("disabled")).sum() > 1200


@pytest.mark.parametrize("side", ["top", "bottom", "left", "right"])
def test_notebook_paints_the_selected_tab_and_hover_face(gtk_pixels, side):
    first, second, hover = [gtk_pixels[f"tabs {state}-{side}"] for state in ("first", "second", "hovered")]

    def white(pixels):
        return pixels.min(axis=2) > 250

    assert (white(first) & ~white(second)).sum() > 250
    assert (white(second) & ~white(first)).sum() > 250
    assert (hover[:, :, 2] > hover[:, :, 0] + 25).sum() > 200


@pytest.mark.parametrize("kind", ["entry", "button"])
def test_disabled_form_face_is_distinct(gtk_pixels, kind):
    normal, disabled = [gtk_pixels[f"palette {prefix}{kind}"] for prefix in ("", "disabled-")]
    assert np.abs(normal - disabled).mean() > 5
    assert np.all(disabled[5:-5, 5:-5] == 244)


@pytest.mark.parametrize(("label", "state"), [("button", 0), ("disabled-button", 3)])
def test_push_button_corner_against_windows_art(gtk_pixels, label, state):
    from aero_sprites import fixed_corner, sprites_available

    if not sprites_available():
        pytest.skip("requires the extracted Windows 7 control artwork")
    corner = np.asarray(fixed_corner("BUTTON", "PUSHBUTTON", state), dtype=int)
    height, width = corner.shape[:2]
    assert np.abs(gtk_pixels["palette " + label][:height, :width] - corner).mean() < 6


INDICATOR_STATES = {
    "normal": 0,
    "hovered": 1,
    "pressed": 2,
    "checked": 4,
    "checked-hovered": 5,
    "checked-pressed": 6,
    "disabled": 7,
}


@pytest.mark.parametrize(
    ("kind", "state", "index"),
    [(kind, state, index) for kind in ("checkbox", "radio") for state, index in INDICATOR_STATES.items()]
    + [("checkbox", "mixed", 8)],
)
def test_gtk4_indicator_faces_against_original_windows_art(gtk4_pixels, kind, state, index, exact_original):
    from aero_sprites import part_table, sprite_dir, sprites_available, straight

    if not sprites_available():
        pytest.skip("requires the extracted Windows 7 control artwork")
    part_name = "CHECKBOX" if kind == "checkbox" else "RADIOBUTTON"
    part = part_table()["BUTTON"][part_name]["0"]
    strip = straight(Image.open(sprite_dir() / part["IMAGEFILE1"]).convert("RGBA"))
    size = strip.width
    reference = Image.new("RGBA", (size, size), "#f0f0f0")
    reference.alpha_composite(strip.crop((0, size * index, size, size * (index + 1))))
    captured = gtk4_pixels[f"{kind} {state}"]
    exact_original(reference, Image.fromarray(captured.astype("uint8")))
    error = np.abs(captured - np.asarray(reference.convert("RGB"))).mean()
    assert error < (23 if kind == "checkbox" else 11), (kind, state, error)


@pytest.mark.skipif(
    not all(shutil.which(p) for p in ("kwin_wayland", "nautilus", "spectacle")), reason="needs GNOME Files and KWin"
)
@pytest.mark.parametrize("scale", [1, 1.5])
def test_restored_files_caption_matches_windows_7_glyphs(gtk_captures, tmp_path, scale, exact_original):
    runtime = tmp_path / "run"
    runtime.mkdir(mode=0o700)
    script = tmp_path / "caption"
    script.write_text("""#!/bin/sh
set -eu
gsettings set org.gnome.desktop.interface enable-animations false
kscreen-doctor output.Virtual-0.scale."$OUTPUT_SCALE" >/dev/null
gsettings set org.gnome.nautilus.window-state maximized false
gsettings set org.gnome.nautilus.window-state initial-size '(890, 550)'
gsettings set org.gnome.desktop.wm.preferences button-layout ':minimize,maximize,close'
nautilus "$HOME" >files.log 2>&1 &
for attempt in $(seq 12); do
    sleep 0.5
    spectacle -b -n -f -o "$PWD/normal.png"
    python3 - <<'PYREADY' && exit 0
from pathlib import Path
from PIL import Image
import numpy as np
shot = Image.open("normal.png").convert("RGB")
red, green, blue = np.asarray(shot, dtype=int).transpose(2, 0, 1)
y, x = np.where((red > 145) & (red > green + 50) & (red > blue + 50))
if x.size < 100:
    raise SystemExit(1)
# A window can appear partway through the compositor's opening animation.
# Wait for consecutive identical caption pixels at the same screen position.
region = (int(x.max()) - 180, int(y.min()) - 10, int(x.max()) + 12, int(y.min()) + 42)
sample = repr(region).encode() + shot.crop(region).tobytes()
previous = Path("previous-caption.bin")
stable = previous.exists() and previous.read_bytes() == sample
previous.write_bytes(sample)
raise SystemExit(0 if stable else 1)
PYREADY
done
exit 1
""")
    run_session(
        tmp_path,
        script,
        {
            "HOME": str(gtk_captures),
            "OUTPUT_SCALE": str(scale),
            "PATH": "/usr/bin:/bin",
            "XDG_RUNTIME_DIR": str(runtime),
            "GSETTINGS_BACKEND": "keyfile",
            "GDK_BACKEND": "wayland",
            "GSK_RENDERER": "cairo",
            "GTK_A11Y": "none",
            "XDG_SESSION_TYPE": "wayland",
        },
        (1200, 800),
        scale=scale,
    )
    shot = Image.open(tmp_path / "normal.png").convert("RGB")
    from caption_cluster import compare_cluster, native_cluster

    scores, group = compare_cluster(shot, scale)
    group.save(tmp_path / "caption-buttons.png")
    exact_original(native_cluster(scale)[0], group)
    limits = (0.95, 0.95, 0.98) if scale == 1 else (0.82, 0.93, 0.79)
    assert all(score >= limit for score, limit in zip(scores, limits, strict=True)), scores


@pytest.mark.parametrize("density", [1, 2])
def test_boxes_guest_titlebar_uses_vector_faces_and_fades(aero_gtk_home, tmp_path, density, exact_original):
    import io
    import subprocess

    if not Path("/usr/bin/gnome-boxes").exists():
        pytest.skip("requires the Boxes display toolbar template")
    script = tmp_path / "capture"
    script.write_text(
        f"#!/bin/sh\nkscreen-doctor output.Virtual-0.scale.{density} >/dev/null || exit 1\n"
        f"exec python3 {quote(str(REPO / 'tests/aero/boxes_header_capture.py'))} {tmp_path}/frames\n"
    )
    runtime = tmp_path / "run"
    runtime.mkdir(mode=0o700)
    run_session(
        tmp_path,
        script,
        {
            "HOME": str(aero_gtk_home),
            "XDG_RUNTIME_DIR": str(runtime),
            "GDK_BACKEND": "wayland",
            "GDK_SCALE": str(density),
            "GTK_A11Y": "none",
        },
        (800, 400),
        scale=density,
    )
    frames = tmp_path / "frames"
    boxes = json.loads((frames / "layout.json").read_text())
    normal = Image.open(frames / "normal.png")
    assert normal.width == 700 * density
    assert normal.height <= 40 * density
    assert boxes["back"][2] <= 32
    x, y, w, h = boxes["close"]
    assert (boxes["minimize"][2], boxes["maximize"][2], w) == (30, 27, 50)
    assert boxes["minimize"][0] + 30 == boxes["maximize"][0]
    assert boxes["maximize"][0] + 27 == x
    assert y <= 4
    crop = tuple(v * density for v in (x, y, x + w, y + h))
    if density == 1:
        from reference import screenshot

        expected = screenshot("win7-sp1-caption-close-motion").crop((0, 2, w, h + 2))
        exact_original(expected, normal.crop(crop))

    # Compare the close glyph against the SVG rasterized directly on the output grid.
    # Upscaling the 1× icon instead raises the 2× glyph's mean RGB error above 17.
    svg = (
        aero_gtk_home
        / ".local/share/chicago95/gtk4-caption/gtk3"
        / ("close-active@2x.svg" if density == 2 else "close-active.svg")
    )
    vector = Image.open(io.BytesIO(subprocess.check_output(["rsvg-convert", svg]))).convert("RGBA")
    background = normal.crop(((x - 80) * density, y * density, (x - 80) * density + 1, (y + h) * density)).resize(
        vector.size
    )
    expected = Image.alpha_composite(background, vector).convert("RGB")
    glyph = tuple(v * density for v in (w // 2 - 6, 4, w // 2 + 6, h - 4))
    original = np.asarray(expected.crop(glyph), dtype=int)
    rendered = np.asarray(normal.crop(crop).convert("RGB").crop(glyph), dtype=int)
    assert np.abs(rendered - original).mean() < 2

    def region(name):
        return np.asarray(Image.open(frames / (name + ".png")).convert("RGB").crop(crop), dtype=int)

    from test_aero_caption_motion import native_times

    assert np.abs(region("rest") - region("hover")).mean() > 8
    for label, native in zip(("hover", "rest"), native_times("close"), strict=True):
        timestamps, level = np.asarray(json.loads((frames / (label + ".json")).read_text())).T
        progress = (level - level[0]) / (level[-1] - level[0])
        assert ((progress > 0.1) & (progress < 0.9)).any()
        duration = timestamps[np.flatnonzero(progress >= 0.9)[0]] - timestamps[np.flatnonzero(progress >= 0.1)[0]]
        assert min(native) - 25 <= duration <= max(native) + 25, (duration, native)


@pytest.mark.parametrize(("subdirectory", "widths"), [("gtk3", (30, 27, 50)), ("", (29, 26, 50))])
def test_caption_svg_is_rasterized_at_the_button_size(aero_gtk_home, subdirectory, widths):
    import xml.etree.ElementTree as ET

    assets = aero_gtk_home / ".local/share/chicago95/gtk4-caption" / subdirectory
    for kind, width in zip(("minimize", "maximize", "close", "restore"), (*widths, widths[1]), strict=True):
        for density, suffix in ((1, ""), (2, "@2x")):
            svg = ET.parse(assets / f"{kind}-active{suffix}.svg").getroot()
            assert svg.get("viewBox") == f"0 0 {width} 20"
            assert int(svg.get("width")) == density * width
            assert int(svg.get("height")) == density * 20


@pytest.mark.parametrize(("art", "capture", "limit"), [("normal", "normal", 9), ("checked-normal", "checked", 15)])
def test_large_radio_svg_matches_144_dpi_display_settings(qt_app, art, capture, limit):
    from test_aero_buttons import rendered

    graphic = REPO / f"aero/gtk/Chicago95Aero/gtk-4.0/indicators/radio-{art}@2x.svg"
    face = Image.new("RGBA", (20, 20), "white")
    face.alpha_composite(rendered(graphic.read_text(), face.size))
    actual = np.asarray(face.convert("RGB").crop((0, 0, 19, 19)), dtype=int)
    with Image.open(REPO / f"tests/references/win7-sp1-144dpi-radio-{capture}.png") as native:
        expected = np.asarray(native.convert("RGB"), dtype=int)
    assert np.abs(actual - expected).mean() < limit


@pytest.mark.parametrize("version", ["3.0", "4.0"])
def test_live_high_density_radio_matches_guest(aero_gtk_home, tmp_path, version):
    runtime = tmp_path / "run"
    runtime.mkdir(mode=0o700)
    script = tmp_path / "radios"
    script.write_text(
        f"#!/bin/sh\nexec python3 {quote(str(REPO / 'tests/gtk_showcase.py'))} "
        f"{version} Chicago95Aero {version} --consistency --only radio\n"
    )
    run_session(
        tmp_path, script,
        {"HOME": str(aero_gtk_home), "PATH": "/usr/bin:/bin", "XDG_RUNTIME_DIR": str(runtime),
         "GDK_BACKEND": "wayland", "GSK_RENDERER": "cairo", "GTK_A11Y": "none"}, (350, 200), scale=2,
    )
    directory = tmp_path / version
    for _, label, file in json.loads((directory / "manifest.json").read_text()):
        if label not in ("radio normal", "radio checked"):
            continue
        with Image.open(directory / file) as shot:
            actual = shot.convert("RGBA")
        if version == "3.0":
            actual = actual.crop((24, 24, actual.width - 24, actual.height - 24))
        assert actual.size == (26, 26)
        # Compare the device-scale widget to the 150% guest on the same grid.
        face = Image.new("RGBA", actual.size, "white")
        face.alpha_composite(actual)
        native = Image.open(REPO / f"tests/references/win7-sp1-144dpi-radio-{label.split()[1]}.png")
        sampled = face.resize((20, 20), Image.Resampling.LANCZOS).crop((0, 0, 19, 19)).convert("RGB")
        error = np.abs(np.asarray(sampled, dtype=int) - np.asarray(native, dtype=int)).mean()
        assert error < 19, (label, error)
