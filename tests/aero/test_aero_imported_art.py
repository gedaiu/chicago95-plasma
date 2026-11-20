"""Render the SVG conversions against the pinned source artwork, including alpha and animation frames."""

import hashlib
import json
import os
import struct
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
        "user",
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
