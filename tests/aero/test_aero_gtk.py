"""Exercise Setup's GTK migration and the resulting client-side caption in both toolkits."""

import json
import shutil
from shlex import quote

import numpy as np
import pytest
from conftest import REPO, run_bash_with_steps
from PIL import Image
from plasma_session import run_session


@pytest.fixture(scope="module")
def gtk_captures(tmp_path_factory):
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
    script = tmp_path / "render"
    script.write_text(
        "#!/bin/sh\nset -e\n"
        + "\n".join(
            f"python3 {quote(str(REPO / 'tests/gtk_showcase.py'))} {version} Chicago95Aero "
            f"{version} --consistency --only {controls}"
            for version, controls in [
                ("3.0", "caption"),
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
    # Require a crisp light-to-dark outline on each glyph at the actual output scale.
    close_x = round((x.min() + x.max()) / 2) + round(930 * scale)
    cy = round((y.min() + y.max()) / 2)
    radius = round(5 * scale)
    for offset in (0, 38.5):  # centres of Close and Restore
        cx = round(close_x - offset * scale)
        glyph = header[cy - radius : cy + radius + 1, cx - radius : cx + radius + 1].mean(axis=2)
        edges = np.maximum(abs(np.diff(glyph, axis=0)[:, :-1]), abs(np.diff(glyph, axis=1)[:-1]))
        assert np.percentile(edges, 90) > 80
    # The minimize glyph is a horizontal bar. Measure its upper/lower edge across
    # its centre rather than counting the surrounding flat glass as glyph pixels.
    cx = close_x - round(67 * scale)
    inset = round(3 * scale)
    bar = header[cy - radius : cy + radius + 1, cx - inset : cx + inset + 1].mean(axis=2)
    assert np.median(np.abs(np.diff(bar, axis=0)).max(axis=0)) > 90
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


@pytest.fixture(scope="module")
def gtk4_pixels(gtk_captures):
    directory = gtk_captures / "4.0"
    result = {}
    for _, label, filename in json.loads((directory / "manifest.json").read_text()):
        shot = Image.open(directory / filename).convert("RGBA")
        canvas = Image.new("RGBA", shot.size, "#f0f0f0")
        canvas.alpha_composite(shot)
        result[label] = np.asarray(canvas.convert("RGB"), dtype=int)
    return result


@pytest.mark.parametrize("kind", ["checkbox", "radio"])
def test_indicator_size_glyph_and_interaction_states(gtk4_pixels, kind):
    def shot(state):
        return gtk4_pixels[f"{kind} {state}"]

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
def test_progress_track_fill_and_direction(gtk4_pixels, direction):
    def filled(state):
        shot = gtk4_pixels[f"progress {state}-{direction}"]
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


@pytest.mark.parametrize("direction", ["horizontal", "vertical"])
def test_scroll_thumb_geometry_position_and_feedback(gtk4_pixels, direction):
    def shot(state):
        image = gtk4_pixels[f"scrollbar {state}-{direction}"]
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
def test_notebook_paints_the_selected_tab_and_hover_face(gtk4_pixels, side):
    first, second, hover = [gtk4_pixels[f"tabs {state}-{side}"] for state in ("first", "second", "hovered")]

    def white(pixels):
        return pixels.min(axis=2) > 250

    assert (white(first) & ~white(second)).sum() > 250
    assert (white(second) & ~white(first)).sum() > 250
    assert (hover[:, :, 2] > hover[:, :, 0] + 25).sum() > 200


@pytest.mark.parametrize("kind", ["entry", "button"])
def test_disabled_form_face_is_distinct(gtk4_pixels, kind):
    normal, disabled = [gtk4_pixels[f"palette {prefix}{kind}"] for prefix in ("", "disabled-")]
    assert np.abs(normal - disabled).mean() > 5
    assert np.all(disabled[5:-5, 5:-5] == 244)


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
    assert error < (23 if kind == "checkbox" else 49), (kind, state, error)


@pytest.mark.skipif(
    not all(shutil.which(p) for p in ("kwin_wayland", "nautilus", "spectacle")), reason="needs GNOME Files and KWin"
)
@pytest.mark.parametrize("scale", [1, 1.5])
def test_restored_files_caption_uses_tinted_toolbar_bevel(gtk_captures, tmp_path, scale):
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
gdbus wait --session --timeout 10 org.gnome.Nautilus
sleep 1.5
spectacle -b -n -f -o "$PWD/normal.png"
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
    pixels = np.asarray(shot)
    right = np.flatnonzero(pixels[shot.height // 2].max(axis=1) > 50)[-1] + 1
    top = np.flatnonzero(pixels[:, shot.width // 2].max(axis=1) > 50)[0]
    group_x = right - round(111 * scale)
    # Locate the actual top outline on the native grid before resampling. The
    # large buttons' inset highlight displaces the first coloured row downwards.
    sample_x = group_x + round(8 * scale)
    start = top + round(8 * scale)
    profile = pixels[start : top + round(15 * scale), sample_x].mean(axis=1)
    y = start + int(profile.argmin())
    group = shot.crop((group_x, y, group_x + round(105 * scale), y + round(20 * scale)))
    group.save(tmp_path / "caption-buttons.png")
    actual = np.asarray(group.resize((105, 20), Image.Resampling.LANCZOS), dtype=int)
    # Sample clear of the glyphs. All faces follow the toolbar bevel at 0/49/50/100%,
    # with matching blue faces for Minimize and Maximize and a red Close face.
    for x, tint in ((6, (50, 24, 0)), (34, (50, 24, 0)), (70, (0, 70, 78))):
        column = actual[[3, 7, 12, 16], x] + tint
        expected_levels = np.array([242, 236, 217, 211])[:, None]
        assert np.abs(column - expected_levels).max() < 7

    for join in (29, 55):
        band = actual[5, join - 4 : join + 5].mean(axis=1)
        # A single narrow divider, with no second pale rim on either side.
        assert 1 <= (band < 150).sum() <= 2
        assert band.max() <= max(band[0], band[-1]) + 8
    # The top of the centered group must have a visible edge of its own.
    for x in (8, 34, 70):
        assert actual[0, x].mean() + 24 < actual[3, x].mean()
    # The rounded perimeter supplies the sole bottom line. A second sprite shadow
    # here used to make the edge darker than the top rim across all three buttons.
    for x in (8, 34, 70):
        assert actual[-2:, x].mean(axis=1).min() > actual[0, x].mean() + 10
        # Inspect native output pixels, including the toolbar immediately below.
        # A smooth ramp from rim to toolbar would pass the lightness check above.
        column = pixels[y + round(17 * scale) : y + round(22 * scale), group_x + round(x * scale)].mean(axis=1)
        assert np.diff(column).max() > 75
