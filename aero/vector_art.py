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
            stops, _, rank, _ = np.linalg.lstsq(basis, channels, rcond=None)
            if rank != count:
                continue
            stops[:, 3] = np.clip(stops[:, 3], 0, 255)
            stops[:, :3] = np.clip(stops[:, :3], 0, stops[:, 3:])
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
    if min(width, height) >= 4 and 0.4 <= region.mean() <= 0.6:
        # A diagonal cut across a rectangle has just three vertices, even
        # when the source grid samples its sloping edge as a staircase.
        dx = (xx + 0.5) * height
        dy = (yy + 0.5) * width
        for pixels, vertices in (
            (dx <= dy, ((left, top), (right, bottom), (left, bottom))),
            (dx >= dy, ((left, top), (right, top), (right, bottom))),
            (dx + dy <= width * height, ((left, top), (right, top), (left, bottom))),
            (dx + dy >= width * height, ((right, top), (right, bottom), (left, bottom))),
        ):
            if np.array_equal(region, pixels):
                return ET.Element(tag("polygon"), points=" ".join(f"{x},{y}" for x, y in vertices))
    # A rounded box has straight sides tangent to four equal quarter circles.
    # Verify every pixel centre before replacing the sampled outline.
    if min(width, height) >= 5 and region[height // 2].all() and region[:, width // 2].all():
        for radius in range(2, min(width, height) // 2 + 1):
            dx = np.maximum(abs(xx + 0.5 - width / 2) - (width / 2 - radius), 0)
            dy = np.maximum(abs(yy + 0.5 - height / 2) - (height / 2 - radius), 0)
            if np.array_equal(region, dx**2 + dy**2 <= radius**2):
                return ET.Element(
                    tag("rect"), x=str(left), y=str(top), width=str(width), height=str(height), rx=str(radius)
                )
    if min(width, height) >= 4 and region.sum() < 0.35 * width * height:
        # Fit a straight strip by its axis and thickness. Only accept it when
        # sampling that quadrilateral recovers every original pixel centre.
        y, x = np.nonzero(region)
        points = np.column_stack((x + 0.5, y + 0.5))
        axis = np.linalg.eigh(np.cov(points.T))[1][:, -1]
        normal = np.array([-axis[1], axis[0]])
        along, across = points @ axis, points @ normal
        length, thickness = np.ptp(along), region.sum() / (np.ptp(along) + 1)
        if length >= 5 * thickness:
            start, end = along.min() - 0.5, along.max() + 0.5
            near, far = across.mean() - thickness / 2, across.mean() + thickness / 2
            u = (xx + 0.5) * axis[0] + (yy + 0.5) * axis[1]
            v = (xx + 0.5) * normal[0] + (yy + 0.5) * normal[1]
            if np.array_equal(region, (start <= u) & (u <= end) & (near <= v) & (v <= far)):
                corners = [
                    axis * u + normal * v + (left, top)
                    for u, v in ((start, near), (end, near), (end, far), (start, far))
                ]
                return ET.Element(tag("polygon"), points=" ".join(f"{x:.3f},{y:.3f}" for x, y in corners))
    return None


def contour(mask, crisp):
    shape = primitive(mask)
    if shape is not None:
        return shape
    # Fit curves to the silhouette, preserving holes and disjoint islands.
    buffer = io.BytesIO()
    scale = 4 if max(mask.size) <= 96 else 1
    if scale != 1:
        # Interpolate coverage before tracing a curved outline. Replicating
        # samples into square blocks turns their corners into path vertices.
        # A one-pixel stroke has no interior from which to interpolate.
        # Keep its full coverage, including isolated highlights and tips.
        solid = np.asarray(mask) > 0
        interior = solid[1:-1, 1:-1] & solid[1:-1, :-2] & solid[1:-1, 2:] & solid[:-2, 1:-1] & solid[2:, 1:-1]
        broad = interior.sum() >= max(8, solid.sum() * 0.45)
        sampling = Image.Resampling.BILINEAR if broad and not crisp else Image.Resampling.NEAREST
        mask = mask.resize((mask.width * scale, mask.height * scale), sampling)
    mask.point(lambda v: 0 if v >= 128 else 255).convert("1").save(buffer, "PPM")
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
    colours = np.asarray(rgba)
    visible = colours[:, :, 3] >= 8
    group = ET.Element(tag("g"))
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
    digest = hashlib.blake2s(struct.pack("<II?", *rgba.size, crisp), digest_size=8)
    digest.update(rgba.tobytes())
    name = "paint" + digest.hexdigest()
    defs = ET.SubElement(group, tag("defs"))

    # Back contiguous opaque paint before overlaying neighbouring gradients.
    # Otherwise antialiased contour edges expose the background between fills.
    opaque = colours[:, :, 3] >= 245
    base = None
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
            if (
                not crisp
                and shape.tag == tag("rect")
                and len(points) == len(coords)
                and min(int(shape.get("width")), int(shape.get("height"))) <= 2
                and np.any(values[:, 3] < 255)
            ):
                # Preserve the faint antialiased edge on thin, single-colour icon strokes.
                shape.attrib.update(
                    {"stroke": colour, "stroke-opacity": str(round(opacity * 0.15, 3)), "stroke-width": ".2"}
                )
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
    if base is not None and len(group) == 3:
        group.remove(base)
    if not len(defs):
        group.remove(defs)
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


def paint_session_spinner(root, image):
    """Fit the 18 glossy ring poses using six circular sectors with radial colour ramps."""
    side = image.height
    centre = side / 2
    y, x = np.mgrid[:side, :side] + 0.5
    radii = np.hypot(x - centre, y - centre).ravel()
    angles = np.arctan2(y - centre, x - centre).ravel()
    # Radial sections of the hole, inner bevel, coloured face, specular rim and outer edge.
    knots = np.array([4.9, 5.65, 6.3, 7.5, 8.55, 9.15, 9.8, 10.65])
    basis = np.array([np.interp(radii, knots, row) for row in np.eye(len(knots))]).T
    sections = 6
    defs = ET.SubElement(root, tag("defs"))
    for frame, left in enumerate(range(0, image.width, side)):
        pixels = np.asarray(image.crop((left, 0, left + side, side))).reshape(-1, 4)
        colours = colour_channels(pixels)
        group = ET.SubElement(root, tag("g"), transform=f"translate({left} 0)")
        for i in range(sections):
            middle = (i + 0.5) * 2 * np.pi / sections
            delta = np.angle(np.exp(1j * (angles - middle)))
            weights = np.exp(-((delta / (2.5 / sections)) ** 2))[:, None]
            stops = np.linalg.lstsq(basis * weights, colours * weights, rcond=1e-5)[0]
            stops[0] = stops[-1] = 0
            name = f"ring{frame}_{i}"
            gradient = ET.SubElement(
                defs, tag("radialGradient"), id=name, gradientUnits="userSpaceOnUse", cx="10", cy="10", r=str(knots[-1])
            )
            for radius, stop in zip(knots, stops, strict=True):
                colour, opacity = svg_colour(stop)
                ET.SubElement(
                    gradient,
                    tag("stop"),
                    offset=f"{radius / knots[-1]:.4f}",
                    attrib={"stop-color": colour, "stop-opacity": str(opacity)},
                )
            # A slight overlap keeps antialiasing from opening seams around the rim.
            start, end = np.array([i, i + 1]) * 2 * np.pi / sections + [-0.021, 0.021]
            sx, sy = centre + 11 * np.array([np.cos(start), np.sin(start)])
            ex, ey = centre + 11 * np.array([np.cos(end), np.sin(end)])
            ET.SubElement(
                group, tag("path"), fill=f"url(#{name})", d=f"M10 10L{sx:.3f} {sy:.3f}A11 11 0 0 1 {ex:.3f} {ey:.3f}Z"
            )


# The pinned 48px blue search and zoom icons share a lens and handle. Match
# their RGBA content so renamed copies receive the same authored geometry.
MAGNIFIERS = {
    "79a7a09c72e7cdc2": "search",
    "e398c740cb142274": "fit",
    "990ab1365564a217": "in",
    "53f9a14711210711": "out",
    "1305c59381dc6f6d": "actual",
}


def magnifier_svg(kind):
    root = ET.parse(Path(__file__).with_name("icons") / "gtk-zoom-fit.svg").getroot()
    if kind == "search":
        root.find(".//*[@id='lens']").set("fill-opacity", ".282")
    glyphs = {
        "in": "M25 14.5h4.4v4.2h4.6v4.4h-4.6v4.2H25v-4.2h-4.4v-4.4H25z",
        "out": "M20.6 18.7H34v4.4H20.6z",
        "actual": "M23 14h6v10.5h3v2.4h-9v-2.4h3V16h-3z",
    }
    if kind in glyphs:
        ET.SubElement(root, tag("path"), d=glyphs[kind], fill="url(#enamel)")
    return ET.tostring(root)


def bitmap_svg(image, shaded=False):
    root = ET.Element(
        tag("svg"), width=str(image.width), height=str(image.height), viewBox=f"0 0 {image.width} {image.height}"
    )
    rgba = image.convert("RGBA")
    if rgba.size == (48, 48):
        kind = MAGNIFIERS.get(hashlib.sha256(rgba.tobytes()).hexdigest()[:16])
        if kind:
            return magnifier_svg(kind)
    # Recognize the native session strip by its layout, apertures and opaque upper rims.
    if rgba.size == (360, 20) and all(
        rgba.getpixel((left + 10, 10))[3] == 0 and rgba.getpixel((left + 10, 2))[3] == 255 for left in range(0, 360, 20)
    ):
        paint_session_spinner(root, rgba)
    else:
        root.append(trace(image, shaded=shaded))
    return ET.tostring(root)


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as out:
        out.write(data)
    os.chmod(out.name, 0o644)
    os.replace(out.name, path)


# The pinned icon pack uses the same PNGs under several toolbar action names.
TOOLBAR_PNG = {
    "f9c996ce6e618fac3d27adb8982861c8e2c4696e2935c1d73d8266c63f7e98de": "object-rotate-180",
    "4fcaa0f4c17b292c2841e40d706316d44fb949adfbd2566d4d7e18c8a5420d6e": "object-rotate-left",
    "5c9524fdd85e894452d06cfc99b3ca09806040a2a25315602606379a98c3f246": "object-rotate-right",
    "c044cb2422c8c7a6c88bdded481c84d17cc84a34b13e1399d54fdedc696c4099": "flip-horizontal",
    "af13def5f8ff2bb082a527ac44db5c28f1a0df379f4a13d0397f68896bc2539c": "flip-vertical",
    "910f99a937e2cf2a5268061f82ba2b28efdc84a06de3226b391852ee7615e10f": "back",
    "1c3776813f53073d1f2546198337a82c7b8df7880cab973c4ee29eb845f0db37": "forward",
}


def toolbar_icons(directory):
    back = (directory / "back.svg").read_bytes()
    forward = ET.fromstring(back)
    forward.find(".//*[@id='glyph']").set("transform", "translate(45 0) scale(-1 1)")
    horizontal = (directory / "object-flip-horizontal.svg").read_bytes()
    vertical = ET.fromstring(horizontal)
    # The pack transposes both triangles and leaves one extra row of padding.
    vertical.set("height", "49")
    vertical.set("viewBox", "0 0 48 49")
    vertical.find(".//*[@id='triangles']").set("transform", "matrix(0 1 1 0 0 0)")
    return {
        **{
            name: (directory / f"{name}.svg").read_bytes()
            for name in ("object-rotate-180", "object-rotate-left", "object-rotate-right")
        },
        "back": back,
        "forward": ET.tostring(forward),
        "flip-horizontal": horizontal,
        "flip-vertical": ET.tostring(vertical),
    }


def icon_theme(source, dest):
    polished = Path(__file__).with_name("icons")
    toolbar = toolbar_icons(polished)
    assets = {}
    for icon in source.rglob("*"):
        if icon.suffix.lower() in (".png", ".svg") and icon.is_file():
            target = dest / icon.relative_to(source).with_suffix(".svg")
            if target not in assets or icon.suffix == ".svg":
                assets[target] = icon
    by_digest = {}
    for target, icon in assets.items():
        version = b"vector-icon-svg-v8" if icon.suffix == ".svg" else b"vector-theme-v8"
        original = icon.read_bytes()
        variant = TOOLBAR_PNG.get(hashlib.sha256(original).hexdigest()) if icon.suffix == ".png" else None
        artwork = toolbar[variant] if variant else original
        digest = hashlib.sha256(version + artwork).hexdigest()
        by_digest.setdefault((digest, icon.suffix, variant), []).append((target, icon))

    def convert(entry):
        (digest, ext, variant), aliases = entry
        cached = dest / ".paths" / (digest + ".svg")
        if not cached.exists():
            icon = aliases[0][1]
            if variant:
                data = toolbar[variant]
            elif ext == ".svg":
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
    write(art / "forward.svg", toolbar["forward"])
    write(art / "object-flip-vertical.svg", toolbar["flip-vertical"])
    for name in ("system-file-manager", "org.kde.dolphin", "org.xfce.thunar"):
        write(art / f"{name}.svg", (polished / "file-manager.svg").read_bytes())
    # GTK 3 at 150% requests scale 2. Without a matching directory it can
    # select a 48px, scale-1 fixed icon and display it at 48 logical pixels.
    for scale in (1, 2):
        alias = art.with_name(f"aero@{scale}")
        if not alias.exists():
            alias.symlink_to("aero", target_is_directory=True)
    index = (source / "index.theme").read_text().replace("Name=Windows-7", "Name=Windows 7 (SVG)")
    # KIconLoader skips directories with unrecognised contexts, even when the
    # theme and the SVG exist. Translate the source pack's category names.
    contexts = {
        "Filesystems": "Places",
        "Apps": "Applications",
        "Stock": "Actions",
        "Battery": "Status",
        "Wireless": "Status",
        "IndicatorApplet": "Status",
        "Volume": "Status",
        "Volume-Network": "Status",
        "Notifications": "Status",
    }
    lines = index.splitlines()
    for position, line in enumerate(lines):
        key, _, value = line.partition("=")
        if key == "Context" and value in contexts:
            lines[position] = "Context=" + contexts[value]
    # KDE picks the first matching scalable directory and GTK picks the last.
    # Both entries point at the same hand-drawn SVGs.
    for position, line in enumerate(lines):
        if line.startswith("Directories="):
            lines[position] = "Directories=scalable/aero@1," + line[12:].strip(",") + ",scalable/aero,scalable/aero@2"
            break
    index = "\n".join(lines) + "\n"
    for folder, scale in (("aero@1", 1), ("aero", 1), ("aero@2", 2)):
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
