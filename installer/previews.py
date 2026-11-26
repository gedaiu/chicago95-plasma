"""Render the selected option using project artwork or a live sample."""

import os
import platform
import socket
from pathlib import Path

from model import DATA, DESKTOP_CAPTURES, FIELDS, REF, ROOT, validate
from PySide6.QtCore import QPoint, QRect, Qt, QUrl
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPixmap, QPolygon

LOGOS = "plasmoids/org.chicago95.start/contents/images/"
SDDM = "sddm/Chicago95Plasma/"
IMAGES = {
    "flag": LOGOS + "logo-flag.png",
    "xp": LOGOS + "logo-xp-16.png",
    "penguin": LOGOS + "logo-penguin.svg",
    "keys": SDDM + "key-9x.png",
    "padlock": SDDM + "padlock.svg",
    "win2k-flag": SDDM + "Windows2000Flag.svg",
    "aero-flag": SDDM + "AeroBrandFlag.svg",
    "classic": "splash/chicago95.splashscreen/contents/splash/images/background.png",
}
BOOT = {"classic": "win95bootsm.png", "2000": "w2kboot.png", "luna": "xpsplash.png"}
LOGIN = {"classic": "xpclassiclogin.png", "2000": "w2klogon.png", "luna": "xplogin.png", "aero": "win7-login-guide.png"}


def sound_sample(value):
    checkout = Path(os.getenv("CHICAGO95_SRC", Path.home() / "src/Chicago95"))
    for directory in (
        ROOT / "data/sound-themes",
        Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local/share")) / "sounds",
        checkout / "sounds",
        Path("/usr/share/sounds"),
    ):
        for ext in ("ogg", "wav", "oga"):
            sample = directory / value / "stereo" / f"desktop-login.{ext}"
            if sample.is_file():
                return sample
    return None


def sound_url(value):
    sample = sound_sample(value)
    if sample:
        return QUrl.fromLocalFile(str(sample))
    upstream = {
        "Chicago95": "grassmunk/Chicago95/master/sounds/Chicago95/stereo/desktop-login.wav",
        "Windows7": "Pendrag00n/Windows7Sounds/0c0c85f2d0a8205f85582cb94a9f6520dfb9b8ae/sounds/Windows Logon Sound.wav",
    }
    return QUrl("https://raw.githubusercontent.com/" + upstream[value]) if value in upstream else QUrl()


def artwork(key, v, state):
    if key == "look" and v != "custom":
        return DESKTOP_CAPTURES[v]
    if key in ("decoration", "widget-style", "taskbar-style", "control-panel-style", "start-menu-style"):
        look = state.get("look", "1995") if v in ("auto", "classic") else v
        if look not in ("1995", "1998", "2000", "2001", "luna", "aero") or (
            v == "classic" and look in ("luna", "aero")
        ):
            look = "1995"
        guest = {
            "1995": "win95",
            "1998": "win98",
            "2000": "win2k",
            "2001": "winxp-classic",
            "luna": "winxp",
            "aero": "win7",
        }[look]
        capture = {
            "decoration": "run.png",
            "widget-style": "display-properties.png",
            "taskbar-style": "taskbar/populated.png",
            "control-panel-style": "control-panel.png",
            "start-menu-style": "start-menu.png",
        }[key]
        return f"{REF}themes/{guest}/{capture}"
    if key == "login-style":
        return REF + LOGIN[v]
    if key == "boot-style":
        return REF + BOOT.get(v, f"boot-{v}-video.png")
    if key == "saver":
        return f"data/screensaver-previews/{v}.png"
    if key == "explorer" and v == "thunar":
        return "docs/compare/aero-thunar-breadcrumbs.png"
    if FIELDS[key].kind == "image":
        if v == "start":
            v = state.get("start-logo", "flag")
        if v == "waving-flag":
            cached = Path.home() / ".local/share/chicago95/waving-flag.png"
            return cached if cached.is_file() else REF + "w2klogon.png"
        if v != "text":
            return IMAGES.get(v, v)
    return None


def icon_gallery(theme):
    desktop, panel = {
        "chicago95": ("1995", "win95"),
        "se98": ("1998", "win98"),
        "classicos2000": ("2000", "win2k"),
        "windowsxp": ("2001", "winxp"),
        "windows7": ("aero", "win7"),
    }[theme]
    desktop_dir = ROOT / "data/desktop-icons/native" / desktop
    panel_dir = ROOT / DATA / "native" / panel
    if theme == "windows7":
        samples = [
            ("Recycle Bin", desktop_dir / "recycle.png"),
            ("Network", panel_dir / "network-and-internet.png"),
            ("Programs", panel_dir / "programs.png"),
            ("Hardware", panel_dir / "hardware-and-sound.png"),
            ("User Accounts", panel_dir / "user-accounts-and-family-safety.png"),
            ("Appearance", panel_dir / "appearance-and-personalization.png"),
        ]
    else:
        personal = "Inbox" if desktop == "1995" else "Documents"
        samples = [
            ("My Computer", desktop_dir / "computer.png"),
            (personal, desktop_dir / f"{personal.lower()}.png"),
            ("Network", desktop_dir / "network.png"),
            ("Recycle Bin", desktop_dir / "recycle.png"),
            ("Display", panel_dir / "display.png"),
            ("Mouse", panel_dir / "mouse.png"),
        ]
    gallery = QPixmap(344, 212)
    gallery.fill(QColor("#008080"))
    with QPainter(gallery) as painter:
        painter.setPen(Qt.white)
        for i, (caption, path) in enumerate(samples):
            icon = QPixmap(str(path))
            if icon.isNull():
                raise ValueError(f"Preview image unavailable: {path}")
            icon = icon.scaled(
                48, 48, Qt.KeepAspectRatio, Qt.FastTransformation if desktop != "aero" else Qt.SmoothTransformation
            )
            x, y = i % 3 * 114, i // 3 * 106
            painter.drawPixmap(x + (114 - icon.width()) // 2, y + 16 + (48 - icon.height()) // 2, icon)
            painter.drawText(QRect(x, y + 66, 114, 36), Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap, caption)
    return gallery


def render(key, value, state):
    if key not in FIELDS:
        raise ValueError("Unknown preview option")
    field = FIELDS[key]
    if field.kind in ("number", "screen", "saver") or (field.kind == "menu" and (key, value) != ("look", "custom")):
        validate(key, value)
    if field.kind == "image" and value not in field.choices and value != "aero-flag":
        validate(key, value)
    if key == "icons":
        return icon_gallery(value)
    result = QPixmap(344, 212)
    result.fill(QColor("#008080"))
    with QPainter(result) as p:

        def label(x, y, text, width=310, height=30, color="black"):
            p.setPen(QColor(color))
            p.drawText(QRect(x, y, width, height), Qt.AlignVCenter | Qt.TextWordWrap, str(text))

        def box(x, y, w, h, colour):
            p.fillRect(x, y, w, h, QColor(colour))

        path = artwork(key, value, state)
        if path:
            img = QPixmap(str(ROOT / path))
            if not img.isNull():
                img = img.scaled(
                    344,
                    212,
                    Qt.KeepAspectRatio,
                    Qt.FastTransformation if img.width() < 160 else Qt.SmoothTransformation,
                )
                p.drawPixmap((344 - img.width()) // 2, (212 - img.height()) // 2, img)
                return result
            if key not in ("saver", "LOGIN_LOGO"):
                raise ValueError(f"Preview image unavailable: {path}")
            label(20, 58, f"{value}\nArtwork is supplied separately.", 305, 80, "white")
            return result
        # Small desktop samples retain legibility when editing text, sizes and colours.
        box(15, 30, 314, 149, "#c0c0c0")
        colours = state.get("TITLE_ACTIVE", "#000080").split(",")
        if key in ("TITLE_ACTIVE", "TITLE_INACTIVE"):
            colours = value.split(",")
        gradient = QLinearGradient(20, 0, 320, 0)
        for pos, col in enumerate(colours):
            gradient.setColorAt(pos / max(1, len(colours) - 1), QColor(col.split("@")[0]))
        p.fillRect(19, 34, 306, 25, gradient)
        title = state.get("LOGIN_TITLE", "Log On") if key == "LOGIN_TITLE" else field.label
        if key == "LOGIN_TITLE":
            title = value.replace("%h", socket.gethostname())
        label(24, 34, title, 295, 25, "white")
        if key in ("panel", "task-button-width", "quick-launch", "task-grouping", "start-text"):
            height = min(88, max(16, int(value))) if key == "panel" else 30
            y = 157 - height
            box(20, y, 304, height, "#999999")
            box(23, y + 2, 68, height - 4, "#dadada")
            label(27, y, value if key == "start-text" else state.get("start-text", "Start"), 63, height)
            x = 94
            quick_launch = value == "yes" or (value == "auto" and state.get("look", "1995") != "1995")
            if key == "quick-launch" and quick_launch:
                p.drawPixmap(x, y + 4, 20, 20, QPixmap(str(ROOT / "data/desktop-icons/native/1995/computer.png")))
                x += 27
            tasks = (
                ["Explorer (2)"]
                if key == "task-grouping"
                and (value == "always" or (value == "auto" and state.get("taskbar-style") == "aero"))
                else ["Documents", "Pictures"]
            )
            for caption in tasks:
                width = min(156, int(value) or 90) if key == "task-button-width" else 81
                box(x, y + 2, width, height - 4, "#e2e2e2")
                label(x + 3, y, caption, width - 4, height)
                x += width + 3
        elif field.kind == "colour" or key == "banner-text":
            background = value if key == "BANNER_BG" else state.get("BANNER_BG", "#808080")
            stops = background.split(",")
            banner = QLinearGradient(0, 77, 0, 144)
            for i, stop in enumerate(stops):
                banner.setColorAt(i / max(1, len(stops) - 1), QColor(stop.split("@")[0]))
            p.fillRect(24, 77, 296, 67, banner)
            label(
                35,
                86,
                value if key == "banner-text" else state.get("banner-text", "Chicago95"),
                270,
                42,
                value.split(",")[0] if key == "BANNER_FG" else "white",
            )
        elif key == "explorer":
            for i, (action, caption) in enumerate(
                [
                    ("go-previous", "Back"),
                    ("go-next", "Forward"),
                    ("go-up", "Up"),
                    ("edit-cut", "Cut"),
                    ("edit-copy", "Copy"),
                ]
            ):
                x = 30 + i * 59
                icon = QPixmap(str(ROOT / "data/toolbar-icons/2000" / f"{action}.png"))
                p.drawPixmap(x + 4, 73, 24, 24, icon)
                label(x, 99, caption, 57, 22)
            label(30, 134, "Home — Dolphin")
        elif key == "screen":
            dimensions, scale = value.split("@")
            w, h = map(int, dimensions.split("x"))
            ratio = min(165 / w, 70 / h)
            p.fillRect(33, 75, max(1, round(w * ratio)), max(1, round(h * ratio)), QColor("#008080"))
            label(32, 144, f"{dimensions} at {scale}×")
        elif key == "cursor":
            size = int(value)
            p.setBrush(Qt.white)
            p.drawPolygon(
                QPolygon(
                    [
                        QPoint(95 + x * size // 16, 84 + y * size // 16)
                        for x, y in [(0, 0), (0, 16), (5, 11), (9, 16), (11, 15), (7, 10), (14, 10)]
                    ]
                )
            )
        elif key in ("font", "font-scope"):
            selected = QFont(value if key == "font" else state.get("font", "Sans Serif"))
            p.setFont(selected if value != "none" else QFont())
            label(30, 77, "Active Window")
            if key == "font-scope" and value == "desktop":
                p.setFont(QFont())
            label(30, 116, "File    Edit    View     •     Aa Bb 0123")
        elif key == "wobbly":
            for i in range(3 if value != "no" else 1):
                p.setPen(QColor("#777777" if value == "blurred" else "#000080"))
                p.drawRoundedRect(
                    80 + i * 12, 72 + i * 6, 150, 70, 10 if value != "no" else 0, 10 if value != "no" else 0
                )
        elif key == "clippy":
            if value == "yes":
                p.drawPixmap(30, 69, 108, 90, QPixmap(str(ROOT / REF / "clippy-letter.png")))
            label(145, 79, "Starts at login" if value == "yes" else "Manual start", 161, 60)
        else:
            samples = {
                "branding": platform.freedesktop_os_release().get("NAME", "Linux") if value == "distro" else "Windows",
                "idle": f"Idle for {value} min → screensaver",
                "COMPANY_LOGO": state.get("COMPANY", "KDE"),
                "sounds": f"Desktop login  ♪   {value}",
                "LOGIN_MESSAGE": value,
            }
            label(31, 72, samples.get(key, value).replace("%h", socket.gethostname()), 282, 87)
    return result
