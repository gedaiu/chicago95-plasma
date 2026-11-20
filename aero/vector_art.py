"""Build scalable paths for bitmap artwork in the imported Aero themes."""
import argparse
import base64
import hashlib
import io
import os
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


def trace(image):
    """Fit Bezier contours to the colour regions, retaining transparent regions."""
    palette = image.convert("RGBA").quantize(colors=96)
    group = ET.Element(tag("g"), transform=f"translate(0 {image.height}) scale(.1 -.1)")
    for _, index in sorted(palette.getcolors(), reverse=True):
        r, g, b, a = palette.getpalette("RGBA")[4 * index : 4 * index + 4]
        if a < 8:
            continue
        mask = palette.copy()
        mask.putpalette([255 if i != index else 0 for i in range(256) for _ in range(3)])
        stream = io.BytesIO()
        mask.convert("1", dither=Image.Dither.NONE).save(stream, "PPM")
        result = subprocess.run(
            ["potrace", "-s", "--flat", "-t", "0", "-O", "0.15", "-o", "-", "-"],
            input=stream.getvalue(), stdout=subprocess.PIPE, check=True,
        )
        shape = ET.fromstring(result.stdout).find(".//" + tag("path"))
        if shape is None:
            continue
        colour = f"#{r:02x}{g:02x}{b:02x}"
        shape.attrib.update(fill=colour, stroke=colour)
        # Small overlap prevents hairline gaps between adjacent antialiased contours.
        shape.set("stroke-width", "3")
        shape.set("stroke-linejoin", "round")
        if a < 255:
            shape.set("opacity", f"{a / 255:.3f}")
        group.append(shape)
    return group


def svg_bytes(source):
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
            ET.SubElement(image, tag("rect"), x=str(x), y=str(y), width=str(width),
                          height=str(height), fill="none")
            sx, sy = width / pixels.width, height / pixels.height
            if image.attrib.pop("preserveAspectRatio", None) != "none":
                sx = sy = min(sx, sy)
                x += (width - pixels.width * sx) / 2
                y += (height - pixels.height * sy) / 2
            positioned = ET.SubElement(image, tag("g"), transform=f"translate({x} {y}) scale({sx} {sy})")
            positioned.append(trace(pixels))
    return ET.tostring(root)


def bitmap_svg(image):
    root = ET.Element(tag("svg"), width=str(image.width), height=str(image.height),
                      viewBox=f"0 0 {image.width} {image.height}")
    root.append(trace(image))
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
        digest = hashlib.sha256(icon.read_bytes()).hexdigest()
        by_digest.setdefault((digest, icon.suffix), []).append((target, icon))

    def convert(entry):
        (digest, ext), aliases = entry
        cached = dest / ".paths" / (digest + ".svg")
        if not cached.exists():
            icon = aliases[0][1]
            if ext == ".svg":
                data = svg_bytes(icon.read_bytes())
            else:
                with Image.open(icon) as image:
                    data = bitmap_svg(image)
            write(cached, data)
        for target, _ in aliases:
            target.parent.mkdir(parents=True, exist_ok=True)
            link = os.path.relpath(cached, target.parent)
            if not target.is_symlink() or os.readlink(target) != link:
                temp = target.with_suffix(".tmp")
                temp.unlink(missing_ok=True)
                temp.symlink_to(link)
                temp.replace(target)

    with ThreadPoolExecutor(max_workers=4) as pool:
        for _ in pool.map(convert, by_digest.items()):
            pass
    write(dest / "index.theme", (source / "index.theme").read_bytes().replace(b"Name=Windows-7", b"Name=Windows 7 (SVG)"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=("icons", "controls", "orb"))
    parser.add_argument("source", type=Path)
    parser.add_argument("dest", type=Path)
    args = parser.parse_args()
    if args.kind == "icons":
        icon_theme(args.source, args.dest)
    elif args.kind == "controls":
        write(args.dest, svg_bytes(args.source.read_bytes()))
    else:
        with Image.open(args.source) as strip:
            write(args.dest, bitmap_svg(strip))
