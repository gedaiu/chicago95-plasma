"""Contract checks for showcase coverage, optional references and theme isolation."""

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
