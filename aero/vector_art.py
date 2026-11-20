"""Build scalable paths for bitmap artwork in the imported Aero themes."""

import argparse
import base64
import hashlib
import io
import json
import os
import struct
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image

SVG = "http://www.w3.org/2000/svg"
XLINK = "{http://www.w3.org/1999/xlink}href"
ET.register_namespace("", SVG)
ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")


def tag(name):
    return f"{{{SVG}}}{name}"


def shaded_layers(palette):
    """Paint broad opaque colour regions underneath their finer shades, like a layered illustration."""
    values = palette.getpalette("RGBA")
    colours = {i: tuple(values[4 * i : 4 * i + 4]) for _, i in palette.getcolors()}
    counts = {i: count for count, i in palette.getcolors()}

    def layer(indices, colour):
        mask = palette.point([0 if i in indices else 255 for i in range(256)], "L")
        return colour, mask

    def tones(indices, inherited=None):
        dominant = max(indices, key=counts.get)
        if dominant != inherited:
            yield layer(indices, (*colours[dominant][:3], 255))
        if len(indices) > 1:
            ranges = [max(colours[i][c] for i in indices) - min(colours[i][c] for i in indices) for c in range(3)]
            channel = ranges.index(max(ranges))
            ordered = sorted(indices, key=lambda i: colours[i][channel])
            middle = len(ordered) // 2
            yield from tones(set(ordered[:middle]), dominant)
            yield from tones(set(ordered[middle:]), dominant)

    opaque = {i for i, c in colours.items() if c[3] >= 225}
    if opaque:
        yield from tones(opaque)
    for i, c in colours.items():
        if 8 <= c[3] < 225:
            yield layer({i}, c)


def trace(image, crisp=False, shaded=False):
    """Fit Bezier contours to the colour regions, retaining transparent regions."""
    small_icon = shaded and min(image.size) <= 16
    if small_icon:
        # Toolbar minis use single-pixel glyphs with deliberately square corners.
        crisp, shaded = True, False
    rgba = image.convert("RGBA")
    # Preserve antialiased glyph detail when the artwork is displayed between native sizes.
    sample = 2 if (small_icon or not (crisp or shaded)) and image.width == image.height and 9 < image.width <= 64 else 1
    if sample > 1:
        rgba = rgba.resize((image.width * sample, image.height * sample), Image.Resampling.LANCZOS)
    palette = rgba.quantize(colors=160)
    colours = palette.getpalette("RGBA")
    if shaded:
        layers = shaded_layers(palette)
    else:
        layers = []
        backed = False
        for _, index in sorted(palette.getcolors(), reverse=True):
            r, g, b, a = colours[4 * index : 4 * index + 4]
            if a < 8:
                continue
            if a >= 245 and not backed:
                backed = True
                # Back the opaque shapes with their silhouette so the viewer's own
                # antialiasing cannot open transparent seams between adjoining colours.
                layers.insert(0, ((r, g, b, 255), rgba.getchannel("A").point(lambda v: 0 if v >= 245 else 255)))
            mask = palette.point([0 if i == index else 255 for i in range(256)], "L")
            layers.append(((r, g, b, a), mask))

    # Small controls have single-pixel strokes. Trace their interpolated contours
    # on a finer grid so Potrace cannot collapse a long thin highlight into an oval.
    tiny = crisp or min(image.size) <= 9
    factor = 4 if min(image.size) <= 64 else 1
    unit = 0.1 / (sample * factor)
    group = ET.Element(tag("g"), transform=f"translate(0 {image.height}) scale({unit} {-unit})")
    for (r, g, b, a), mask in layers:
        stream = io.BytesIO()
        scaled_mask = mask
        if factor > 1:
            scaled_mask = mask.resize(
                (rgba.width * factor, rgba.height * factor),
                Image.Resampling.NEAREST if tiny else Image.Resampling.BILINEAR,
            )
        scaled_mask.convert("1", dither=Image.Dither.NONE).save(stream, "PPM")
        result = subprocess.run(
            ["potrace", "-s", "--flat", "-t", "0", "-a", "0" if tiny else "1", "-O", "0.15", "-o", "-", "-"],
            input=stream.getvalue(),
            stdout=subprocess.PIPE,
            check=True,
        )
        shape = ET.fromstring(result.stdout).find(".//" + tag("path"))
        if shape is None:
            continue
        colour = f"#{r:02x}{g:02x}{b:02x}"
        shape.set("fill", colour)
        if not tiny:
            shape.set("stroke", colour)
        # Small overlap prevents hairline gaps between adjacent antialiased contours.
        shape.set("stroke-width", str((8 if sample > 1 else 3) * factor))
        shape.set("stroke-linejoin", "round")
        if a < 255:
            shape.set("opacity", f"{a / 255:.3f}")
        group.append(shape)
    return group


def svg_bytes(source, shaded=False, preserve_bounds=True):
    root = ET.fromstring(source)
    for image in root.iter(tag("image")):
        href = image.attrib.pop(XLINK, "") or image.attrib.pop("href", "")
        header, data = href.split(",", 1)
        if not header.startswith("data:image/") or not header.endswith(";base64"):
            raise ValueError(f"Unsupported SVG image source: {header[:50]}")
        with Image.open(io.BytesIO(base64.b64decode(data))) as pixels:
            image.tag = tag("g")
            width = float(image.attrib.pop("width", pixels.width))
            height = float(image.attrib.pop("height", pixels.height))
            x = float(image.attrib.pop("x", 0))
            y = float(image.attrib.pop("y", 0))
            # Kvantum uses element bounds as nine-slice metrics, including clear margins.
            # GTK recolours every shape in a symbolic icon, including an unpainted rectangle.
            if preserve_bounds:
                ET.SubElement(image, tag("rect"), x=str(x), y=str(y), width=str(width), height=str(height), fill="none")
            sx, sy = width / pixels.width, height / pixels.height
            if image.attrib.pop("preserveAspectRatio", None) != "none":
                sx = sy = min(sx, sy)
                x += (width - pixels.width * sx) / 2
                y += (height - pixels.height * sy) / 2
            positioned = ET.SubElement(image, tag("g"), transform=f"translate({x} {y}) scale({sx} {sy})")
            positioned.append(trace(pixels, crisp="optimizeSpeed" in image.get("style", ""), shaded=shaded))
    return ET.tostring(root)


def bitmap_svg(image, shaded=False):
    root = ET.Element(
        tag("svg"), width=str(image.width), height=str(image.height), viewBox=f"0 0 {image.width} {image.height}"
    )
    root.append(trace(image, shaded=shaded))
    return ET.tostring(root)


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as out:
        out.write(data)
    os.chmod(out.name, 0o644)
    os.replace(out.name, path)


def icon_theme(source, dest):
    assets = {}
    for icon in source.rglob("*"):
        if icon.suffix.lower() in (".png", ".svg") and icon.is_file():
            target = dest / icon.relative_to(source).with_suffix(".svg")
            if target not in assets or icon.suffix == ".svg":
                assets[target] = icon
    by_digest = {}
    for target, icon in assets.items():
        version = b"vector-icon-svg-v4" if icon.suffix == ".svg" else b"vector-theme-v3"
        digest = hashlib.sha256(version + icon.read_bytes()).hexdigest()
        by_digest.setdefault((digest, icon.suffix), []).append((target, icon))

    def convert(entry):
        (digest, ext), aliases = entry
        cached = dest / ".paths" / (digest + ".svg")
        if not cached.exists():
            icon = aliases[0][1]
            if ext == ".svg":
                data = svg_bytes(icon.read_bytes(), shaded=True, preserve_bounds=False)
            else:
                with Image.open(icon) as image:
                    data = bitmap_svg(image, shaded=True)
            write(cached, data)
        for target, _ in aliases:
            target.parent.mkdir(parents=True, exist_ok=True)
            link = os.path.relpath(cached, target.parent)
            if not target.is_symlink() or os.readlink(target) != link:
                with tempfile.TemporaryDirectory(dir=target.parent) as staging:
                    temp = Path(staging) / "link"
                    temp.symlink_to(link)
                    temp.replace(target)

    with ThreadPoolExecutor(max_workers=4) as pool:
        for _ in pool.map(convert, by_digest.items()):
            pass
    # The Explorer and power icons have drawn gradients and fine detail at toolbar sizes.
    polished = Path(__file__).with_name("icons")
    art = dest / "scalable" / "aero"
    for path in polished.glob("*.svg"):
        write(art / path.name, path.read_bytes())
    for name in ("system-file-manager", "org.kde.dolphin", "org.xfce.thunar"):
        write(art / f"{name}.svg", (polished / "file-manager.svg").read_bytes())
    index = (source / "index.theme").read_text().replace("Name=Windows-7", "Name=Windows 7 (SVG)")
    index = index.replace("Directories=", "Directories=scalable/aero,", 1)
    index += "\n[scalable/aero]\nSize=32\nMinSize=1\nMaxSize=512\nType=Scalable\n"
    write(dest / "index.theme", index.encode())


def cursor_theme(source, dest):
    """Use the largest nominal Xcursor size, including every animation frame and its hotspot."""
    shapes = {}
    for cursor in sorted(source.iterdir(), key=lambda p: (len(p.name), p.name)):
        data = cursor.read_bytes()
        digest = hashlib.sha256(data).digest()
        folder = dest / cursor.name
        if digest in shapes:
            if not folder.exists():
                folder.symlink_to(shapes[digest], target_is_directory=True)
            continue
        if data[:4] != b"Xcur":
            raise ValueError(f"Invalid Xcursor file: {cursor}")
        header, _, count = struct.unpack_from("<3I", data, 4)
        chunks = (struct.unpack_from("<3I", data, header + 12 * i) for i in range(count))
        images = [(size, offset) for kind, size, offset in chunks if kind == 0xFFFD0002]
        largest = max(size for size, _ in images)
        metadata = []
        for size, offset in images:
            if size != largest:
                continue
            length, _, _, _, w, h, x, y, delay = struct.unpack_from("<9I", data, offset)
            start = offset + length
            frame = Image.frombytes("RGBA", (w, h), data[start : start + 4 * w * h], "raw", "BGRa")
            name = f"{len(metadata)}.svg"
            write(folder / name, bitmap_svg(frame))
            metadata.append(dict(filename=name, nominal_size=size, hotspot_x=x, hotspot_y=y, delay=delay))
        write(folder / "metadata.json", json.dumps(metadata, indent=2).encode())
        shapes[digest] = cursor.name


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=("icons", "controls", "bitmap", "cursors"))
    parser.add_argument("source", type=Path)
    parser.add_argument("dest", type=Path)
    args = parser.parse_args()
    if args.kind == "icons":
        icon_theme(args.source, args.dest)
    elif args.kind == "cursors":
        cursor_theme(args.source, args.dest)
    elif args.kind == "controls":
        write(args.dest, svg_bytes(args.source.read_bytes()))
    else:
        with Image.open(args.source) as image:
            write(args.dest, bitmap_svg(image))
