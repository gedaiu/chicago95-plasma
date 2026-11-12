"""Apply the active classic colour scheme to GTK CSS and baked bitmap faces.

Always read a pristine theme: changing schemes must not accumulate recolouring.
Text, white fields, glyphs and transparency retain their separate colour roles.
"""

import re
from pathlib import Path

from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtGui import QImage


def scheme_colours(scheme, bevel):
    from chicago95ui import bevel_colors

    return {
        **{key: scheme[key].name() for key in ("face", "selection", "selection_text")},
        **{key: value.name() for key, value in bevel_colors(scheme["face"], bevel).items()},
    }


def palette_css(text, colours):
    replacements = {"#c0c0c0": colours["face"], "#dfdfdf": colours["light"], "#000080": colours["selection"]}
    text = re.sub(r"#[0-9a-fA-F]{6}\b", lambda m: replacements.get(m[0].lower(), m[0]), text)
    roles = {
        "bg_color": "face",
        "border_color": "face",
        "border_light": "light",
        "border_dark": "dark",
        "border_shade": "shadow",
        "selected_bg_color": "selection",
        "selected_fg_color": "selection_text",
    }
    for name, role in roles.items():
        text = re.sub(rf"(@define-color\s+{name}\s+)[^;]+;", rf"\g<1>{colours[role]};", text)
    tokens = {
        "face": "face",
        "border-face": "face",
        "border-light": "light",
        "border-dark": "dark",
        "border-shade": "shadow",
        "selected-bg": "selection",
        "selected-fg": "selection_text",
    }
    for name, role in tokens.items():
        text = re.sub(rf"(--c95-{name}\s*:\s*)[^;]+;", rf"\g<1>{colours[role]};", text)
    return text


def prepare_theme(source, output, colours):
    source, output = Path(source), Path(output)
    if source.resolve() == output.resolve():
        raise ValueError("GTK palette generation requires a separate pristine source")
    mapping = {
        tuple(bytes.fromhex(old)): tuple(bytes.fromhex(colours[role].lstrip("#")))
        for old, role in (("c0c0c0", "face"), ("dfdfdf", "light"), ("000080", "selection"))
    }
    for path in source.rglob("*"):
        if not path.is_file():
            continue
        target = output / path.relative_to(source)
        data = path.read_bytes()
        if path.suffix == ".css":
            data = palette_css(data.decode(), colours).encode()
        elif path.suffix == ".png":
            image = QImage(str(path)).convertToFormat(QImage.Format_RGBA8888)
            if image.isNull():
                raise ValueError(f"Cannot load GTK asset: {path}")
            pixels = bytearray(image.constBits())
            for offset in range(0, len(pixels), 4):
                replacement = mapping.get(tuple(pixels[offset : offset + 3]))
                if replacement is not None:
                    pixels[offset : offset + 3] = bytes(replacement)
            image = QImage(bytes(pixels), image.width(), image.height(), QImage.Format_RGBA8888).copy()
            buffer = QBuffer()
            buffer.open(QIODevice.WriteOnly)
            if not image.save(buffer, "PNG"):
                raise ValueError(f"Cannot encode GTK asset: {path}")
            data = bytes(buffer.data())
        elif path.suffix == ".svg":
            data = palette_css(data.decode(), colours).encode()
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() or target.read_bytes() != data:
            target.write_bytes(data)


def sync_installed(scheme, bevel, home=None):
    home = Path.home() if home is None else Path(home)
    source = home / ".local/share/chicago95/gtk-original"
    installed = home / ".themes/Chicago95"
    if not source.exists() and installed.is_dir():
        import shutil

        shutil.copytree(installed, source)
    if source.is_dir():
        if installed.is_symlink():
            installed.unlink()
        prepare_theme(source, installed, scheme_colours(scheme, bevel))


if __name__ == "__main__":
    import chicago95ui

    sync_installed(chicago95ui.read_scheme(), chicago95ui.look_settings()["bevel"])
