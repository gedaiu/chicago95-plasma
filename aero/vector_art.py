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

import numpy as np
from PIL import Image

SVG = "http://www.w3.org/2000/svg"
XLINK = "{http://www.w3.org/1999/xlink}href"
ET.register_namespace("", SVG)
ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")


def tag(name):
    return f"{{{SVG}}}{name}"


def colour_channels(rgba):
    """Premultiplied channels let a transparent edge contribute its actual visible colour."""
    values = np.asarray(rgba, dtype=float)
    return np.column_stack((values[:, :3] * values[:, 3:] / 255, values[:, 3]))


def svg_colour(channels):
    alpha = np.clip(channels[3], 0, 255)
    rgb = np.clip(np.rint(channels[:3] * 255 / max(1, alpha)), 0, 255).astype(int)
    return "#" + bytes(rgb.tolist()).hex(), round(alpha / 255, 3)


def fit_fill(x, y, channels):
    """Try a flat colour, directional ramps and an elliptical highlight in order of complexity."""
    mean = channels.mean(axis=0)
    flat_error = np.abs(channels - mean).mean()
    if flat_error <= 2 or len(x) < 8:
        return flat_error, mean, None
    coords = np.column_stack((x, y)).astype(float)
    centre = coords.mean(axis=0)
    delta = coords - centre
    # A colour plane's strongest direction is the axis along which the colour changes.
    slopes = np.linalg.lstsq(delta, channels - mean, rcond=None)[0]
    axis = np.linalg.eigh(slopes @ slopes.T)[1][:, -1]
    directions = [("linear", delta @ axis, axis)]
    radius = np.maximum(np.ptp(coords, axis=0) / 2, 0.5)
    midpoint = (coords.max(axis=0) + coords.min(axis=0)) / 2
    directions.append(("radial", np.linalg.norm((coords - midpoint) / radius, axis=1), radius))
    best = (flat_error, mean, None)
    for kind, distance, axis_or_radius in directions:
        low, high = distance.min(), distance.max()
        if high - low < 0.01:
            continue
        t = (distance - low) / (high - low)
        # Fit only a few colour stops. This preserves a gloss edge without turning
        # a smooth ramp into a separate contour for each shade.
        for count in (2, 4, 7):
            offsets = np.linspace(0, 1, count)
            basis = np.maximum(0, 1 - np.abs(t[:, None] - offsets) * (count - 1))
            stops = np.linalg.lstsq(basis, channels, rcond=None)[0]
            error = np.abs(basis @ stops - channels).mean()
            if error + 1 < best[0]:
                if kind == "linear":
                    geometry = (*(centre + axis_or_radius * low), *(centre + axis_or_radius * high))
                else:
                    geometry = (*midpoint, *(axis_or_radius * high))
                    offsets = (offsets * (high - low) + low) / high
                best = (error, None, (kind, geometry, offsets, stops))
            if error < 2:
                break
    return best


def primitive(mask):
    """Recognize rectangles and ellipses before fitting free-form outlines."""
    left, top, right, bottom = mask.getbbox()
    width, height = right - left, bottom - top
    region = np.asarray(mask.crop((left, top, right, bottom))) != 0
    if region.all():
        return ET.Element(tag("rect"), x=str(left), y=str(top), width=str(width), height=str(height))
    yy, xx = np.ogrid[:height, :width]
    ellipse = ((xx + 0.5 - width / 2) / (width / 2)) ** 2 + ((yy + 0.5 - height / 2) / (height / 2)) ** 2 <= 1
    if min(width, height) >= 5 and np.count_nonzero(region != ellipse) <= 0.03 * region.sum():
        return ET.Element(
            tag("ellipse"),
            cx=f"{left + width / 2:g}",
            cy=f"{top + height / 2:g}",
            rx=f"{width / 2:g}",
            ry=f"{height / 2:g}",
        )
    return None


def contour(mask, crisp):
    shape = primitive(mask)
    if shape is not None:
        return shape
    # Fit curves to the silhouette, preserving holes and disjoint islands.
    buffer = io.BytesIO()
    scale = 4 if max(mask.size) <= 96 else 1
    mask = mask.resize((mask.width * scale, mask.height * scale), Image.Resampling.NEAREST)
    mask.point(lambda v: 0 if v else 255).convert("1").save(buffer, "PPM")
    output = subprocess.run(
        ["potrace", "-s", "--flat", "-t", "0", "-a", "0" if crisp else "1", "-O", ".35", "-o", "-", "-"],
        input=buffer.getvalue(),
        stdout=subprocess.PIPE,
        check=True,
    )
    doc = ET.fromstring(output.stdout)
    path = doc.find(".//" + tag("path"))
    if path is None:
        return None
    # Keep the transform on the path; its parent paints gradients in original pixel coordinates.
    path.set("transform", f"translate(0 {mask.height / scale:g}) scale({0.1 / scale:g} {-0.1 / scale:g})")
    return path


def trace(image, crisp=False, shaded=False):
    """Fit vector regions and colour ramps; retain outlines for irregular silhouettes."""
    rgba = image.convert("RGBA")
    scale = 3 if not crisp and min(image.size) <= 9 else 1
    if scale != 1:
        rgba = rgba.resize((rgba.width * scale, rgba.height * scale), Image.Resampling.BICUBIC)
    colours = np.asarray(rgba)
    visible = colours[:, :, 3] >= 8
    group = ET.Element(tag("g"))
    if scale != 1:
        group.set("transform", f"scale({1 / scale:.8f})")
    if not visible.any():
        return group
    # A short palette guides segmentation only; fit colours from the original pixels.
    indexed = rgba.quantize(colors=48)
    labels = np.asarray(indexed)
    coords = np.column_stack(np.nonzero(visible))
    ids = labels[visible]
    values = colour_channels(colours[visible])
    samples = {}
    for index in np.unique(ids):
        points = np.flatnonzero(ids == index)
        samples[int(index)] = points
    palette = {i: values[points].mean(axis=0) for i, points in samples.items()}
    # Namespace paint servers even when multiple bitmap elements share one SVG document.
    name = "paint" + hashlib.blake2s(rgba.tobytes(), digest_size=8).hexdigest()
    defs = ET.SubElement(group, tag("defs"))

    # Back contiguous opaque paint before overlaying neighbouring gradients.
    # Otherwise antialiased contour edges expose the background between fills.
    opaque = colours[:, :, 3] >= 245
    if opaque.any():
        base = contour(Image.fromarray(opaque.astype("uint8") * 255), crisp)
        if base is not None:
            base.set("fill", svg_colour(np.median(colour_channels(colours[opaque]), axis=0))[0])
            group.append(base)

    def draw(indices):
        points = np.concatenate([samples[i] for i in indices])
        # Bound fitting cost independently of output resolution.
        chosen = points if len(points) <= 768 else points[np.linspace(0, len(points) - 1, 768, dtype=int)]
        y, x = coords[chosen].T
        error, solid, ramp = fit_fill(x + 0.5, y + 0.5, values[chosen])
        if len(indices) > 1 and error > 5:
            # Separate the most distinct colours, then refit each region against
            # its spatial coordinates. Adjacent shades of a ramp stay together.
            channel = np.ptp([palette[i] for i in indices], axis=0).argmax()
            ordered = sorted(indices, key=lambda i: palette[i][channel])
            split = len(ordered) // 2
            draw(ordered[:split])
            draw(ordered[split:])
            return
        selected = np.zeros(visible.shape, dtype=np.uint8)
        selected[tuple(coords[points].T)] = 255
        shape = contour(Image.fromarray(selected), crisp)
        if shape is None:
            return
        if solid is not None:
            colour, opacity = svg_colour(solid)
            shape.set("fill", colour)
            if opacity != 1:
                shape.set("fill-opacity", str(opacity))
            group.append(shape)
            return
        kind, geom, offsets, stops = ramp
        gradient_id = name + str(len(defs))
        if kind == "linear":
            gradient = ET.SubElement(
                defs,
                tag("linearGradient"),
                {k: f"{v:.3f}" for k, v in zip(("x1", "y1", "x2", "y2"), geom, strict=True)},
            )
        else:
            cx, cy, rx, ry = geom
            gradient = ET.SubElement(
                defs,
                tag("radialGradient"),
                cx="0",
                cy="0",
                r="1",
                gradientTransform=f"translate({cx:.3f} {cy:.3f}) scale({rx:.3f} {ry:.3f})",
            )
        gradient.set("id", gradient_id)
        gradient.set("gradientUnits", "userSpaceOnUse")
        for offset, stop in zip(offsets, stops, strict=True):
            colour, opacity = svg_colour(stop)
            ET.SubElement(
                gradient, tag("stop"), offset=f"{offset:.4f}", **{"stop-color": colour, "stop-opacity": str(opacity)}
            )
        if shape.get("transform"):
            units = 40 if max(rgba.size) <= 96 else 10
            inverse = f"matrix({units} 0 0 {-units} 0 {units * rgba.height})"
            gradient.set("gradientTransform", (inverse + " " + gradient.get("gradientTransform", "")).strip())
        shape.set("fill", f"url(#{gradient_id})")
        group.append(shape)

    draw(list(samples))
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
    polished = Path(__file__).with_name("icons")
    assets = {}
    for icon in source.rglob("*"):
        if icon.suffix.lower() in (".png", ".svg") and icon.is_file():
            target = dest / icon.relative_to(source).with_suffix(".svg")
            if target not in assets or icon.suffix == ".svg":
                assets[target] = icon
    by_digest = {}
    for target, icon in assets.items():
        version = b"vector-icon-svg-v5" if icon.suffix == ".svg" else b"vector-theme-v4"
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
    art = dest / "scalable" / "aero"
    for path in polished.glob("*.svg"):
        write(art / path.name, path.read_bytes())
    for name in ("system-file-manager", "org.kde.dolphin", "org.xfce.thunar"):
        write(art / f"{name}.svg", (polished / "file-manager.svg").read_bytes())
    # GTK 3 at 150% requests scale 2. Without a matching directory it can
    # select a 48px, scale-1 fixed icon and display it at 48 logical pixels.
    hidpi = dest / "scalable" / "aero@2"
    if not hidpi.exists():
        hidpi.symlink_to("aero", target_is_directory=True)
    index = (source / "index.theme").read_text().replace("Name=Windows-7", "Name=Windows 7 (SVG)")
    # GTK prefers the last matching scalable directory at the requested size.
    lines = index.splitlines()
    for position, line in enumerate(lines):
        if line.startswith("Directories="):
            lines[position] = line.rstrip(",") + ",scalable/aero,scalable/aero@2"
            break
    index = "\n".join(lines) + "\n"
    for folder, scale in (("aero", 1), ("aero@2", 2)):
        index += f"\n[scalable/{folder}]\nSize=24\nScale={scale}\nMinSize=1\nMaxSize=512\nType=Scalable\n"
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
