"""Contract checks for showcase coverage, optional references and theme isolation."""

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def test_reference_free_catalogue_and_composition(tmp_path):
    # The report owns a QApplication and temporary config; keep that out of pytest's shared Qt process.
    program = r"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "tests"))
import render_report as report
import chicago95ui
import controls_gallery
import reference
from showcase import group, themed
from PIL import Image

out = Path(sys.argv[1])
app = chicago95ui.make_app("showcase-test")
app.setQuitOnLastWindowClosed(False)
reference.REFERENCES = out / "no-references"
expected = None
styles = []
for look in report.LOOK_NAMES:
    with themed(app, look):
        rows = controls_gallery.controls(app, look)
        labels = [name for name, _, _ in rows]
        assert len(labels) >= 30
        assert expected is None or labels == expected
        expected = labels
        assert all(original is None for _, original, _ in rows)
        assert all(image.width > 0 and image.height > 0 for _, _, image in rows)
        styles.append((look, type(app.style()).__name__, app.palette().window().color().name()))
assert styles[-1][1] == "LunaStyle", styles
assert styles[0][2] != styles[-1][2], styles
assert group("Popup menu: checked, disabled") == "Menus"
assert group("Scroll bar, horizontal") == group("Scroll bars: vertical, disabled") == "Scrollbars"
assert group("Push buttons (default, plain)") == group("Push buttons: normal, hovered") == "Buttons"
assert group("Text fields") == group("Drop-down and spin box") == "Inputs"
assert group("Table view and headers") == "Tables"
assert group("Tabs (Qt's own tab widget)") == "Tabs"

# A missing original must never call the placeholder renderer or allocate a second column.
def forbidden(*args):
    raise AssertionError("placeholder was rendered")
report.no_reference = forbidden
ours = Image.new("RGB", (100, 20), "red")
report.compose_showcase("Only ours", [("Control", None, ours)], out / "ours.png")
report.compose_showcase("Pair", [("Control", Image.new("RGB", (100, 20), "blue"), ours)], out / "pair.png")
report.compose_showcase("Grouped", [("Buttons · Qt Widgets · Push buttons", None, ours)],
                        out / "grouped.png", grouped=True)
assert Image.open(out / "grouped.png").height == Image.open(out / "ours.png").height + 50
single = Image.open(out / "ours.png")
assert single.getpixel((24, 130)) == (255, 0, 0)
assert single.getpixel((400, 130)) == report.CARD
pair = Image.open(out / "pair.png")
assert pair.getpixel((24, 130)) == (0, 0, 255)
assert pair.getpixel((350, 130)) == (255, 0, 0)
"""
    result = subprocess.run(
        [sys.executable, "-c", program, str(tmp_path)],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_taskbar_assets_overflow_states_and_window_icons(tmp_path):
    import pytest

    qml_roots = ("/usr/lib64/qt6/qml", "/usr/lib/qt6/qml", "/usr/lib/x86_64-linux-gnu/qt6/qml")
    if not any((Path(root) / "org/kde/ksvg").exists() for root in qml_roots):
        pytest.skip("taskbar rendering needs KDE KSvg")
    program = r"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "tests"))
import render_report
import chicago95ui
from showcase import taskbars, frame, themed, login, boot, start_menus

app = chicago95ui.make_app("showcase-overflow-test")
app.setQuitOnLastWindowClosed(False)
for look in ("1995", "2001", "luna"):
    with themed(app, look):
        folder = Path(sys.argv[1]) / look
        panels = taskbars(app, look, folder)
        assert len(panels) == 12
        images = [panel[2] for panel in panels]
        assert all(image.size == (800, 30 if look == "luna" else 28) for image in images)
        normal, overflow = images[0].info["geometry"], images[3].info["geometry"]
        assert normal["arrowWidth"] == 0 and overflow["arrowWidth"] == 16
        if look != "luna":
            assert normal["trayLeft"] - overflow["trayLeft"] == 16
        for image in images:
            geometry = image.info["geometry"]
            assert geometry["band"]["tasksEnd"] <= geometry["trayLeft"]
            assert geometry["firstTrayIcon"] > geometry["trayLeft"]
        if look == "2001":
            assert login(app, look, folder).size == (800, 600)
            assert (folder / "login/theme/brand-banner.png").is_file()
            assert boot(app, look, folder).size == (800, 600)
            assert boot(app, look, folder).getpixel((0, 0)) == (0, 0, 0)
        if look == "luna":
            menus = start_menus(app, look, folder)
            assert len(menus) == 4
            assert len({image.tobytes() for _, _, image in menus}) == 4
        # Hovered and held chevrons must actually change the rendered pixels.
        assert images[3].tobytes() != images[4].tobytes()
        assert images[4].tobytes() != images[5].tobytes()
        assert images[3].tobytes() != images[6].tobytes()
        # The flag contributes red pixels absent from the green/grey Start background.
        box = (10, 6, 30, 24) if look == "luna" else (4, 8, 20, 24)
        assert any(r > 140 and g < 130 and b < 130 for r, g, b in images[0].crop(box).getdata())
        window = frame(look, folder, 340, 80, caption="Documents").convert("RGB")
        # The folder icon contributes yellow ink absent from either blue title bar.
        assert any(r > 150 and g > 140 and b < 130 for r, g, b in window.crop((4, 4, 24, 24)).getdata())
"""
    result = subprocess.run(
        [sys.executable, "-c", program, str(tmp_path)],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
        timeout=40,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Cannot open" not in result.stderr and "No such file" not in result.stderr, result.stderr


def test_gtk_controls_at_scale_two_are_rendered_at_double_size(tmp_path):
    program = r"""
import sys
from pathlib import Path
sys.path[:0] = [str(Path.cwd() / "tests"), str(Path.cwd() / "lib"), str(Path.cwd() / "luna/lib")]
import conftest  # noqa: F401
import showcase

out = Path(sys.argv[1])
(out / "1").mkdir()
(out / "2").mkdir()
single = showcase.gtk_controls("luna", out / "1")
double = showcase.gtk_controls("luna", out / "2", scale=2)
assert single, "no GTK controls rendered"
print(sorted({(b.width - 2 * a.width, b.height - 2 * a.height) for (_, _, a), (_, _, b) in zip(single, double)}))
"""
    result = subprocess.run(
        [sys.executable, "-c", program, str(tmp_path)],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
        timeout=600,
    )

    assert (result.returncode, result.stdout.strip().splitlines()[-1:]) == (0, ["[(0, 0)]"]), result.stderr[-2000:]


def showcase_sizes(tmp_path, scale, part="controls"):
    program = r"""
import json
import os
import sys
from pathlib import Path
sys.path[:0] = [str(Path.cwd() / "tests"), str(Path.cwd() / "lib"), str(Path.cwd() / "luna/lib")]
import conftest  # noqa: F401
os.environ["QT_SCALE_FACTOR"] = sys.argv[2]
import chicago95ui
import showcase

scratch = Path(sys.argv[1])
app = chicago95ui.make_app("showcase-scale-test")
app.setQuitOnLastWindowClosed(False)
with showcase.themed(app, "luna"):
    rows = getattr(showcase, sys.argv[3])(app, "luna", scratch)
print(json.dumps({name: image.size for name, _, image in rows}))
"""
    scratch = tmp_path / f"{part}-{scale}"
    scratch.mkdir()
    result = subprocess.run(
        [sys.executable, "-c", program, str(scratch), str(scale), part],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
        timeout=600,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_every_luna_control_in_a_scale_two_showcase_is_double_the_scale_one_size(tmp_path):
    single, double = showcase_sizes(tmp_path, 1), showcase_sizes(tmp_path, 2)

    assert {
        name: (single[name], double.get(name))
        for name in single
        if double.get(name) != [2 * side for side in single[name]]
    } == {}


def test_every_luna_scene_in_a_scale_two_showcase_is_double_the_scale_one_size(tmp_path):
    single, double = showcase_sizes(tmp_path, 1, "scenes"), showcase_sizes(tmp_path, 2, "scenes")

    assert {
        name: (single[name], double.get(name))
        for name in single
        if double.get(name) != [2 * side for side in single[name]]
    } == {}


def test_render_report_scale_option_sets_the_qt_scale_factor_before_the_application_starts():
    program = r"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "tests"))
import render_report
render_report.main = lambda output, looks: print(os.environ["QT_SCALE_FACTOR"])
render_report.cli(["unused", "luna", "--scale", "2"])
"""
    result = subprocess.run(
        [sys.executable, "-c", program], cwd=REPO, capture_output=True, text=True, check=False, timeout=60
    )

    assert result.stdout.strip().splitlines()[-1:] == ["2"], result.stderr[-2000:]


def test_showcase_sheet_widens_to_show_a_1600_pixel_image_whole_at_one_to_one(tmp_path):
    program = r"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "tests"))
import render_report as report
from PIL import Image

wide = Image.new("RGB", (1600, 40), "blue")
wide.paste((255, 0, 0), (1599, 0, 1600, 40))
report.compose_showcase("Wide", [("Boot", None, wide)], Path(sys.argv[1]) / "wide.png")
sheet = Image.open(Path(sys.argv[1]) / "wide.png")
print(sheet.width >= 1600 + 4 * report.GAP, sheet.getpixel((2 * report.GAP + 1599, 130)))
"""
    result = subprocess.run(
        [sys.executable, "-c", program, str(tmp_path)],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )

    assert result.stdout.strip().splitlines()[-1:] == ["True (255, 0, 0)"], result.stderr[-2000:]


def test_aero_showcase_shows_frames_beside_windows_7_every_button_state_the_2x_caption_and_superbar_close_ups(
    tmp_path,
):
    program = r"""
import sys
from pathlib import Path
sys.path[:0] = [str(Path.cwd() / "tests"), str(Path.cwd() / "tests/aero"), str(Path.cwd() / "lib")]
import conftest  # noqa: F401
import chicago95ui
from showcase import aero_panels

app = chicago95ui.make_app("aero-showcase-test")
panels = aero_panels(app, desktop=None)
print(len([name for name, original, _ in panels if "frame" in name and original is not None]))
print(len([name for name, _, _ in panels if name.startswith("Caption button")]))
print(any("2x" in name for name, _, _ in panels), all(image.width and image.height for _, _, image in panels))
print(len([name for name, original, _ in panels if name.startswith("Superbar close-up") and original is not None]))
"""
    result = subprocess.run(
        [sys.executable, "-c", program], cwd=REPO, capture_output=True, text=True, check=False, timeout=120
    )

    assert result.stdout.split() == ["2", "4", "True", "True", "3"], result.stderr[-2000:]


def test_readme_shows_the_windows_7_showcase_and_the_image_exists():
    readme = (REPO / "README.md").read_text()

    assert ("](docs/compare/showcase-aero.jpg)" in readme, (REPO / "docs/compare/showcase-aero.jpg").is_file()) == (
        True,
        True,
    )
