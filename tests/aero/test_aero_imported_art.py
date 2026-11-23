"""Render the SVG conversions against the pinned source artwork, including alpha and animation frames."""

import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from conftest import REPO
from PIL import Image, ImageChops, ImageStat
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

sys.path.insert(0, str(REPO / "aero"))
import vector_art  # noqa: E402

CACHE = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "chicago95"


def render(data, size, element=None):
    renderer = QSvgRenderer(data)
    assert renderer.isValid()
    image = QImage(*size, QImage.Format_ARGB32_Premultiplied)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    if element:
        assert renderer.elementExists(element)
        renderer.render(painter, element)
    else:
        renderer.render(painter)
    painter.end()
    rgba = image.convertToFormat(QImage.Format_RGBA8888)
    return Image.frombytes("RGBA", size, bytes(rgba.constBits()))


def compare(actual, expected, output, name, budget):
    # Both mattes expose lost transparency, white highlights and black outlines.
    def flatten(image, matte):
        result = Image.new("RGBA", image.size, matte)
        result.alpha_composite(image)
        return result.convert("RGB")

    for matte in ("white", "#25415e"):
        ours, original = flatten(actual, matte), flatten(expected, matte)
        diff = ImageChops.difference(ours, original)
        # Exclude exterior padding that could conceal a missing small glyph.
        bounds = ImageChops.lighter(actual.getchannel("A"), expected.getchannel("A")).getbbox()
        if bounds:
            diff = diff.crop(bounds)
        error = max(ImageStat.Stat(diff).mean)
        if error > budget:
            ours.save(output / f"{name}-actual.png")
            original.save(output / f"{name}-reference.png")
            pytest.fail(f"{name} over {matte}: channel error {error:.1f} exceeds {budget}; images in {output}")


def test_login_controls_match_their_source_artwork(qt_app, tmp_path):
    directory = CACHE / "sddm-f51ca15"
    if not (directory / "go.png").exists():
        pytest.skip("requires the pinned login artwork from aero/fetch-login-art.sh")
    names = [
        "12223",
        "go",
        "gohover",
        "gopressed",
        "input",
        "input-focus",
        "switch-user-button",
        "switch-user-button-hover",
        "switch-user-button-active",
        "power",
        "power-hover",
        "power-active",
        "power-glyph",
        "power-glyph-arrow",
        "12298",
        "12299",
        "12300",
        "12301",
        "12302",
        "access-button",
        "access-button-hover",
        "12213",
    ]
    for name in names:
        original = Image.open(directory / (name + ".png")).convert("RGBA")
        svg = vector_art.bitmap_svg(original)
        for scale in (1, 1.5):
            size = tuple(round(v * scale) for v in original.size)
            compare(render(svg, size), original.resize(size, Image.Resampling.LANCZOS), tmp_path, name, 20)


def test_each_session_spinner_frame_is_visible_and_distinct(qt_app, tmp_path):
    source = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "chicago95/session/spinner.png"
    if not source.exists():
        pytest.skip("requires Windows 7 session artwork from Setup")
    strip = Image.open(source).convert("RGBA")
    svg = vector_art.bitmap_svg(strip)
    for scale in (1, 1.5):
        side = round(20 * scale)
        sheet = render(svg, (18 * side, side))
        frames = []
        for frame in range(18):
            actual = sheet.crop((frame * side, 0, (frame + 1) * side, side))
            expected = strip.crop((frame * 20, 0, (frame + 1) * 20, 20)).resize((side, side), Image.Resampling.LANCZOS)
            compare(actual, expected, tmp_path, f"spinner-{frame}", 20)
            frames.append(actual.tobytes())
        assert len(set(frames)) == 18


def test_kvantum_embedded_controls_keep_their_artwork(qt_app, tmp_path):
    source = CACHE / "kvantum-f51ca15/Windows7Aero.svg"
    if not source.exists():
        pytest.skip("requires the pinned Windows7Aero Kvantum source from Setup")
    original = source.read_bytes()
    converted = vector_art.svg_bytes(original)
    images = list(ET.fromstring(original).iter(vector_art.tag("image")))
    assert len(images) == 117
    for element in images:
        name = element.attrib["id"]
        size = tuple(max(1, round(float(element.attrib[key]) * 1.5)) for key in ("width", "height"))
        compare(render(converted, size, name), render(original, size, name), tmp_path, name, 28)


def test_aero_cursor_shapes_and_all_busy_frames_match_xcursor(qt_app, tmp_path):
    root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "icons/Windows-7-Aero-Cursors_Default"
    if not (root / "cursors/watch").exists():
        pytest.skip("requires the pinned Aero cursor pack from Setup")
    dest = tmp_path / "cursors_scalable"
    vector_art.cursor_theme(root / "cursors", dest)
    tested = set()
    for cursor in (root / "cursors").iterdir():
        folder = (dest / cursor.name).resolve()
        data = cursor.read_bytes()
        pair = (folder, hashlib.sha256(data).digest())
        if pair in tested:
            continue
        tested.add(pair)
        header, _, count = struct.unpack_from("<3I", data, 4)
        chunks = list(struct.iter_unpack("<3I", data[header : header + 12 * count]))
        nominal = max(size for kind, size, _ in chunks if kind == 0xFFFD0002)
        frames = [offset for kind, size, offset in chunks if kind == 0xFFFD0002 and size == nominal]
        records = json.loads((folder / "metadata.json").read_text())
        for record, offset in zip(records, frames, strict=True):
            length, _, _, _, w, h, x, y, delay = struct.unpack_from("<9I", data, offset)
            assert (record["nominal_size"], record["hotspot_x"], record["hotspot_y"], record["delay"]) == (
                nominal,
                x,
                y,
                delay,
            )
            pixels = data[offset + length : offset + length + 4 * w * h]
            expected = Image.frombytes("RGBA", (w, h), pixels, "raw", "BGRa")
            size = (round(1.5 * w), round(1.5 * h))
            compare(
                render((folder / record["filename"]).read_bytes(), size),
                expected.resize(size, Image.Resampling.LANCZOS),
                tmp_path,
                cursor.name,
                22,
            )
    assert len(json.loads((dest / "watch/metadata.json").read_text())) == 18


@pytest.mark.skipif(not shutil.which("kiconfinder6"), reason="requires KDE's icon loader")
def test_kde_loads_aero_places_and_applications_from_the_selected_theme(tmp_path, qt_app):
    source = tmp_path / "source"
    index = "[Icon Theme]\nName=Windows-7\nDirectories=filesystems,apps\nInherits=hicolor\n"
    icons = (("filesystems", "folder", "Filesystems", "gold"), ("apps", "konsole", "Apps", "navy"))
    for folder, name, context, colour in icons:
        (source / folder).mkdir(parents=True)
        Image.new("RGBA", (32, 32), colour).save(source / folder / (name + ".png"))
        index += f"\n[{folder}]\nSize=32\nType=Fixed\nContext={context}\n"
    Image.new("RGBA", (32, 32), "gold").save(source / "apps/org.xfce.thunar.png")
    (source / "index.theme").write_text(index)
    dest = tmp_path / "icons/Windows-7-SVG"
    vector_art.icon_theme(source, dest)
    (tmp_path / "kdeglobals").write_text("[Icons]\nTheme=Windows-7-SVG\n")
    env = dict(os.environ, XDG_DATA_HOME=str(tmp_path), XDG_CONFIG_HOME=str(tmp_path), XDG_CACHE_HOME=str(tmp_path))
    for folder, name, _, colour in icons:
        path = Path(subprocess.check_output(["kiconfinder6", name], env=env, text=True).strip())
        assert path == dest / folder / (name + ".svg")
        assert render(path.read_bytes(), (32, 32)).tobytes() == Image.new("RGBA", (32, 32), colour).tobytes()

    explorer = Path(subprocess.check_output(["kiconfinder6", "org.xfce.thunar"], env=env, text=True).strip())
    assert explorer.read_bytes() == (REPO / "aero/icons/file-manager.svg").read_bytes()


def test_icon_pack_renders_every_source_artwork(qt_app, tmp_path):
    source = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "icons/Windows-7"
    if not (source / "index.theme").exists():
        pytest.skip("requires the Windows 7 icon pack from Setup")
    dest = tmp_path / "icons"
    vector_art.icon_theme(source, dest)
    compared = set()
    for icon in source.rglob("*"):
        if not icon.is_file() or icon.suffix not in (".svg", ".png"):
            continue
        if icon.suffix == ".png" and icon.with_suffix(".svg").exists():
            continue
        vector = (dest / icon.relative_to(source)).with_suffix(".svg")
        assert vector.is_file(), icon
        pair = (vector.resolve(), hashlib.sha256(icon.read_bytes()).digest())
        if pair in compared:
            continue
        compared.add(pair)
        if icon.suffix == ".png":
            original = Image.open(icon).convert("RGBA")
        else:
            renderer = QSvgRenderer(str(icon))
            assert renderer.isValid(), icon
            original = render(icon.read_bytes(), renderer.defaultSize().toTuple())
        # Toolbar and taskbar use 32 logical pixels; preserve the source aspect ratio.
        for side in (32, 48):
            ratio = side / (min(original.size) if icon.parts[-2] == "animations" else max(original.size))
            size = tuple(max(1, round(v * ratio)) for v in original.size)
            image = render(vector.read_bytes(), size)
            expected = (
                render(icon.read_bytes(), size)
                if icon.suffix == ".svg"
                else original.resize(size, Image.Resampling.LANCZOS)
            )
            compare(image, expected, tmp_path, icon.stem, 30)
    assert compared


def test_fedora_orb_logo_retains_its_shape_and_colour(qt_app, tmp_path):
    source = Path(os.environ.get("AERO_FEDORA_REFERENCE", "/usr/share/icons/hicolor/256x256/apps/fedora-logo-icon.png"))
    if not source.is_file():
        pytest.skip("requires the Fedora orb logo used by Setup on Fedora")
    with Image.open(source) as image:
        original = image.convert("RGBA")
    svg = vector_art.bitmap_svg(original)
    for side in (22, 33, 44):
        size = (side, side)
        compare(render(svg, size), original.resize(size, Image.Resampling.LANCZOS), tmp_path, "fedora-orb", 10)


def test_simple_art_is_expressed_as_geometry():
    import numpy as np

    y, x = np.indices((32, 32))
    ramp = np.zeros((32, 32, 4), dtype=np.uint8)
    ramp[..., :3] = x[:, :, None] * 8
    ramp[..., 3] = 255
    svg = ET.fromstring(vector_art.bitmap_svg(Image.fromarray(ramp)))
    assert len(list(svg.iter(vector_art.tag("linearGradient")))) == 1
    assert len(list(svg.iter(vector_art.tag("stop")))) == 2
    assert len(list(svg.iter(vector_art.tag("rect")))) == 1

    for mask, shape in [
        ((x - 15.5) ** 2 + (y - 15.5) ** 2 <= 100, "ellipse"),
        (x == y, "polygon"),
        (x <= y, "polygon"),
    ]:
        ramp[..., 3] = mask * 255
        svg = ET.fromstring(vector_art.bitmap_svg(Image.fromarray(ramp)))
        assert len(list(svg.iter(vector_art.tag(shape)))) == 1
        assert not list(svg.iter(vector_art.tag("path")))

    # The long sides and four tangent arcs of a rounded control are one primitive.
    dx = np.maximum(abs(x - 15.5) - 11, 0)
    dy = np.maximum(abs(y - 15.5) - 7, 0)
    ramp[..., 3] = (dx**2 + dy**2 <= 4**2) * 255
    svg = ET.fromstring(vector_art.bitmap_svg(Image.fromarray(ramp)))
    boxes = list(svg.iter(vector_art.tag("rect")))
    assert len(boxes) == 1 and boxes[0].get("rx") == "4"
    assert not list(svg.iter(vector_art.tag("path")))

    # A circular highlight has one centre and one radial ramp irrespective of how many
    # source pixels or distinct grey levels sample it.
    radius = np.hypot(x - 15.5, y - 15.5)
    ramp[..., 3] = 255
    ramp[..., :3] = np.rint(radius[:, :, None] * 10).astype(np.uint8)
    svg = ET.fromstring(vector_art.bitmap_svg(Image.fromarray(ramp)))
    assert len(list(svg.iter(vector_art.tag("radialGradient")))) == 1
    assert len(list(svg.iter(vector_art.tag("stop")))) == 2


@pytest.mark.parametrize("rounded", [False, True], ids=["diagonal", "rounded-box"])
def test_imported_outline_at_eight_times_source_size(qt_app, rounded):
    import numpy as np

    def coverage(size):
        y, x = (np.indices((size, size)) + 0.5) * (32 / size)
        if rounded:
            dx = np.maximum(abs(x - 16) - 11, 0)
            dy = np.maximum(abs(y - 16) - 7, 0)
            return dx**2 + dy**2 <= 16
        return x <= y

    source = Image.new("RGBA", (32, 32), "white")
    source.putalpha(Image.fromarray((coverage(32) * 255).astype("uint8")))
    face = render(vector_art.bitmap_svg(source), (256, 256)).getchannel("A")
    # Integrate the analytic outline at the display scale, independently of Qt.
    expected = coverage(1024).reshape(256, 4, 256, 4).mean(axis=(1, 3)) * 255
    error = np.abs(np.asarray(face, dtype=float) - expected)
    assert error.mean() < 0.5
    assert error.max() < 64


@pytest.mark.parametrize("name", ["gtk-find", "gtk-zoom-fit", "gtk-zoom-in", "gtk-zoom-out", "gtk-zoom-100"])
def test_blue_magnifiers_have_continuous_rims(qt_app, name, tmp_path):
    import numpy as np

    source = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "icons/Windows-7/actions/48"
    if not (source / (name + ".png")).is_file():
        pytest.skip("requires the pinned Windows 7 icon pack")
    with Image.open(source / (name + ".png")) as image:
        original = image.convert("RGBA")
    data = vector_art.bitmap_svg(original)
    root = ET.fromstring(data)
    assert len(list(root.iter(vector_art.tag("circle")))) == 2
    assert len(list(root.iter(vector_art.tag("path")))) <= 2
    compare(render(data, original.size), original, tmp_path, name, 10)

    # At 8× the upper semicircle is uninterrupted blue enamel. Outside its
    # antialiased outline the background must be completely clear.
    pixels = np.asarray(render(data, (384, 384)))
    y, x = (np.indices((384, 384)) + 0.5) / 8
    radius = np.hypot(x - 27.5, y - 20.5)
    upper = y < 20.5
    assert pixels[upper & (radius > 16.5), 3].max() == 0
    assert pixels[upper & (radius >= 12.1) & (radius <= 15.8), 3].min() > 230


@pytest.fixture(scope="module")
def toolbar_pack(tmp_path_factory):
    source = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "icons/Windows-7/actions/48"
    folder = tmp_path_factory.mktemp("toolbar")
    pack = folder / "source"
    pack.mkdir()
    (pack / "index.theme").write_text("[Icon Theme]\nDirectories=actions\n")
    for name in (
        "back",
        "forward",
        "go-previous",
        "go-next",
        "object-flip-horizontal",
        "object-flip-vertical",
        "object-rotate-left",
        "object-rotate-right",
        "object-rotate-180",
    ):
        png = source / (name + ".png")
        if not png.is_file():
            pytest.skip("requires the pinned Windows 7 icon pack")
        (pack / png.name).write_bytes(png.read_bytes())
    output = folder / "installed"
    vector_art.icon_theme(pack, output)
    return pack, output


@pytest.mark.parametrize(("direction", "alias"), [("back", "go-previous"), ("forward", "go-next")])
def test_toolbar_arrow_aliases_render_smooth_glass(qt_app, tmp_path, toolbar_pack, direction, alias):
    import numpy as np

    pack, output = toolbar_pack
    icon = output / f"{direction}.svg"
    assert icon.resolve() == (output / f"{alias}.svg").resolve()
    data = icon.read_bytes()
    assert (output / "scalable/aero@2" / icon.name).read_bytes() == data
    with Image.open(pack / f"{direction}.png") as image:
        compare(render(data, image.size), image.convert("RGBA"), tmp_path, direction, 17)
    # The circular outer shadow fades continuously along every radius at 8×.
    alpha = np.asarray(render(data, (360, 360)), dtype=int)[:, :, 3]
    for theta in np.linspace(0, 2 * np.pi, 48, endpoint=False):
        radii = np.arange(18, 22.5, 0.125)
        x = ((22.5 + radii * np.cos(theta)) * 8).astype(int)
        y = ((22.2 + radii * np.sin(theta)) * 8).astype(int)
        assert np.diff(alpha[y, x]).max() <= 2


@pytest.mark.parametrize("direction", ["horizontal", "vertical"])
def test_flip_actions_have_straight_edges(qt_app, tmp_path, toolbar_pack, direction):
    import numpy as np

    pack, output = toolbar_pack
    name = f"object-flip-{direction}"
    data = (output / f"{name}.svg").read_bytes()
    assert (output / "scalable/aero@2" / f"{name}.svg").read_bytes() == data
    with Image.open(pack / (name + ".png")) as original:
        size = original.size
        compare(render(data, size), original.convert("RGBA"), tmp_path, name, 8)
    pixels = np.asarray(render(data, tuple(8 * n for n in size)), dtype=int)
    if direction == "vertical":
        pixels = pixels.transpose(1, 0, 2)
    # Find the sloping blue edge on each row between the tip and the base.
    red, _, blue, alpha = pixels.transpose(2, 0, 1)
    rows = np.arange(12 * 8, 37 * 8)
    edge = np.where(((blue - red > 60) & (alpha > 160))[rows], np.arange(pixels.shape[1]), -1).max(axis=1)
    assert np.abs(edge - np.polyval(np.polyfit(rows, edge, 1), rows)).max() < 1


@pytest.mark.parametrize("direction", ["left", "right", "180"])
def test_rotate_actions_match_the_pack_at_native_size_and_scale(qt_app, tmp_path, toolbar_pack, direction):
    import numpy as np

    pack, output = toolbar_pack
    name = f"object-rotate-{direction}"
    data = (output / f"{name}.svg").read_bytes()
    assert (output / "scalable/aero@2" / f"{name}.svg").read_bytes() == data
    with Image.open(pack / f"{name}.png") as source:
        original = source.convert("RGBA")
        compare(render(data, original.size), original, tmp_path, name, 7)
        high = render(data, (400, 384))
        # Compare each curved arrow separately: a missing or reversed turn is
        # easy to miss when its pixels are averaged with the larger triangles.
        boxes = {
            "left": [(22, 4, 39, 19)],
            "right": [(7, 4, 24, 19)],
            "180": [(33, 3, 48, 19), (0, 28, 16, 45)],
        }
        for i, box in enumerate(boxes[direction]):
            expected = original.crop(box)
            actual = high.crop(tuple(n * 8 for n in box)).resize(expected.size, Image.Resampling.LANCZOS)
            compare(actual, expected, tmp_path, f"{name}-arrow-{i}", 24)

    # The coloured triangle's diagonal is a single edge at 8×.
    red, _, blue, alpha = np.asarray(high, dtype=int).transpose(2, 0, 1)
    rows = np.arange(20 * 8, 37 * 8)
    ink = ((blue - red > 70) & (alpha > 180))[rows]
    columns = np.arange(400)
    if direction == "left":
        edge = np.where(ink, columns, 400).min(axis=1)
    else:
        edge = np.where(ink, columns, -1).max(axis=1)
    assert np.abs(edge - np.polyval(np.polyfit(rows, edge, 1), rows)).max() < 1
