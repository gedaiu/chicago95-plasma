"""Shared helpers for the tests that compare our renders with screenshots of the originals.

The screenshots live in tests/references (see SOURCES.md there); several are 256-colour, so colours
are compared with a tolerance.
"""
import io
from pathlib import Path

from PIL import Image

REFERENCES = Path(__file__).parent / "references"
TOLERANCE = 12
MASK_COLOUR = (255, 0, 255)


def screenshot(name):
    """The reference screenshot <name>.png as RGB."""
    return Image.open(REFERENCES / f"{name}.png").convert("RGB")


def close(a, b, tolerance=TOLERANCE):
    return all(abs(x - y) <= tolerance for x, y in zip(a, b))


def bounding_box(image, keep, x_range=None, y_range=None):
    """(left, top, right, bottom) of the pixels for which keep(colour) is true, or None."""
    xs, ys = [], []
    for x in range(*(x_range or (0, image.width))):
        for y in range(*(y_range or (0, image.height))):
            if keep(image.getpixel((x, y))):
                xs.append(x)
                ys.append(y)
    return (min(xs), min(ys), max(xs), max(ys)) if xs else None


def qimage_to_pil(qimage):
    from PySide6.QtCore import QBuffer, QIODevice
    buffer = QBuffer()
    buffer.open(QIODevice.WriteOnly)
    qimage.save(buffer, "PNG")
    return Image.open(io.BytesIO(bytes(buffer.data()))).convert("RGB")


def differing_pixels(reference, ours, masks, diff_path, threshold=0.1):
    """pixelmatch count of differing pixels outside the masked boxes; the diff image is saved for failures."""
    from pixelmatch.contrib.PIL import pixelmatch
    masked_reference, masked_ours = reference.copy(), ours.copy()
    for image in (masked_reference, masked_ours):
        for box in masks:
            image.paste(MASK_COLOUR, box)
    diff = Image.new("RGBA", reference.size)
    count = pixelmatch(masked_reference.convert("RGBA"), masked_ours.convert("RGBA"), diff, threshold=threshold, includeAA=True)
    diff.save(diff_path)
    side_by_side = Image.new("RGB", (reference.width * 3, reference.height), "white")
    side_by_side.paste(reference, (0, 0))
    side_by_side.paste(ours, (reference.width, 0))
    side_by_side.paste(diff.convert("RGB"), (reference.width * 2, 0))
    side_by_side.save(Path(diff_path).with_suffix(".side-by-side.png"))
    return count


def render_start_menu(startmenu, app, settings_dir, chicago95rc, kdeglobals="", without=("&Log Off...",), active=None, extra_top=()):
    """Our root Start menu at 1x with the given settings files, as a PIL image.

    extra_top adds plain items above the rest, then a separator: the originals' Office and Windows
    Update entries, so the menu reaches the same height."""
    import chicago95ui
    (settings_dir / "chicago95rc").write_text(chicago95rc)
    (settings_dir / "kdeglobals").write_text(kdeglobals)
    startmenu.SETTINGS_FILE = settings_dir / "chicago95rc"
    chicago95ui.KDEGLOBALS = str(settings_dir / "kdeglobals")
    startmenu.apply_retro_look(app)
    menu = startmenu.build_root_menu()
    menu.banner = startmenu.banner_settings()
    for action in menu.actions():
        if action.text() in without:
            menu.removeAction(action)
    if extra_top:
        first = menu.actions()[0]
        for text in extra_top:
            menu.insertAction(first, startmenu.QAction(startmenu.themed_icon("text-x-generic"), text, menu))
        menu.insertSeparator(first)
    menu.adjustSize()
    if active is not None:
        menu.setActiveAction(menu.actions()[active])
    return qimage_to_pil(menu.grab().toImage())
