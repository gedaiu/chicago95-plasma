"""Reference-independent scenes and a grouped, native-widget inspection catalogue."""

import json
import shutil
from contextlib import contextmanager
from pathlib import Path

from PIL import Image
from reference import installed_look, qimage_to_pil

REPO = Path(__file__).resolve().parent.parent
SIZE = (800, 600)


@contextmanager
def themed(app, look):
    import chicago95ui
    from render_report import KDEGLOBALS

    settings = f"[StartMenu]\nstyle={look}\n[Look]\nwidgetStyle={look if look == 'luna' else 'classic'}\n"
    with installed_look(app, settings, KDEGLOBALS.get(look, "")):
        chicago95ui.apply_style(app)
        yield
    chicago95ui.apply_style(app)


def qml_image(app, path, size, context=None, properties=None):
    from PySide6.QtCore import QEventLoop, QTimer, QUrl
    from PySide6.QtQuick import QQuickView

    view = QQuickView()
    for name, value in (context or {}).items():
        view.rootContext().setContextProperty(name, value)
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    view.resize(*size)
    view.setSource(QUrl.fromLocalFile(str(path)))
    if view.errors():
        raise RuntimeError("\n".join(error.toString() for error in view.errors()))
    for name, value in (properties or {}).items():
        view.rootObject().setProperty(name, value)
    view.show()
    loop = QEventLoop()
    QTimer.singleShot(350, loop.quit)
    loop.exec()
    image = qimage_to_pil(view.grabWindow())
    view.close()
    return image


def boot(app, look, scratch):
    """A fixed boot phase, using the shipped assets/layout (no historical screenshot)."""
    from plasma_session import CHICAGO95_SRC

    if look in ("1995", "1998"):
        asset = CHICAGO95_SRC / "Plymouth/Chicago95/win95_boot_10.png"
        if not asset.exists():
            return None
        return Image.open(asset).convert("RGB").resize(SIZE, Image.Resampling.NEAREST)
    if look == "luna":
        from luna_qml import render_luna_splash

        return render_luna_splash(app, size=SIZE)
    folder = scratch / "boot"
    shutil.copytree(REPO / "splash/chicago95.splashscreen/contents/splash", folder)
    settings = (folder / "settings.js").read_text().replace('var style = "classic"', 'var style = "2000"')
    (folder / "settings.js").write_text(settings)
    return qml_image(app, folder / "Splash.qml", SIZE, properties={"stage": 3})


def login(app, look, scratch):
    from login_theme import render_login

    if look == "luna":
        from luna_qml import render_luna_login

        return render_luna_login(app, size=SIZE, user="Alex", users=("Alex",))
    return render_login(
        app,
        scratch / "login",
        size=SIZE,
        user="Alex",
        users=("Alex",),
        host_name="CHICAGO95",
        loginStyle="2000" if look in ("2000", "2001") else "classic",
        titleActive={"1995": "#000080", "1998": "#000080,#1084d0"}.get(look, "#0a246a,#a6caf0"),
    )


def taskbars(app, look, scratch):
    """The production Qt Quick components, with identical tasks and real icons for every look."""
    from aurorae_model import LOOKS
    from render_report import DEFAULT_LOGO

    scratch.mkdir(parents=True, exist_ok=True)
    luna = look == "luna"
    themes = scratch / "themes"
    name = "Chicago95Luna" if luna else "Chicago95"
    target = themes / name
    shutil.copytree(REPO / ("luna/plasma-style/theme" if luna else "plasma-style/theme"), target)
    if not luna:
        import subprocess
        import sys

        subprocess.run(
            [
                sys.executable,
                str(REPO / "plasma-style/make_chicago95_plasmastyle.py"),
                "--out",
                str(target),
                *[f"--{key}={LOOKS[look][key]}" for key in ("face", "light", "shadow", "dark")],
            ],
            check=True,
            capture_output=True,
        )
    imports = []
    for component, alias in (("start", "Start"), ("tasks", "Tasks"), ("trayframe", "Tray")):
        source = REPO / f"plasmoids/org.chicago95.{component}/contents/ui"
        if luna:
            merged = scratch / component / "ui"
            shutil.copytree(source, merged)
            shutil.copytree(REPO / f"luna/plasmoids/org.chicago95.{component}/contents/ui", merged, dirs_exist_ok=True)
            shutil.copy(REPO / "luna/plasmoids/family.js", merged / "luna/family.js")
            source = merged / "luna"
        imports.append(f'import "{source.as_uri()}" as {alias}')
    variants = [
        ("Idle", []),
        ("Open windows", ["Documents", "Display Properties", "Notes"]),
        (
            "Crowded / long titles",
            [
                "Documents — Project archive",
                "Display Properties",
                "Notes — Meeting agenda",
                "Downloads",
                "Pictures",
                "Terminal",
            ],
        ),
    ]
    rows = []
    for index, (label, titles) in enumerate(variants):
        start_width = 98 if luna else 64
        tasks_left, tray_left = start_width + 100, 688
        width = min(165, (tray_left - tasks_left - 4) // max(1, len(titles)) - 2)
        items = []
        task_settings = "" if luna else f'look: "{look}"; bevel: "{"2000" if look in ("2000", "2001") else "1995"}";'
        for number, title in enumerate(titles):
            items.append(
                f"Tasks.TaskButton {{ x: {tasks_left + number * (width + 2)}; y: 1; "
                f'width: {width}; height: 28; text: {json.dumps(title)}; icon: "folder"; '
                f"{task_settings} pressed: {str(number == 1).lower()} }}"
            )
        if luna:
            from palette import PALETTE

            background = (
                "Column { Repeater { model: "
                + json.dumps(PALETTE["taskbar"])
                + "; Rectangle { required property string modelData; width: 800; height: 1; color: modelData } } }"
            )
            start = f'Start.StartButton {{ width: {start_width}; height: 30; text: "start" }}'
        else:
            background = f'color: "{LOOKS[look]["face"]}"'
            start = (
                f'Start.StartButton {{ x: 2; y: 2; width: {start_width}; height: 26; text: "Start"; '
                f'logoSource: "{DEFAULT_LOGO.as_uri()}"; look: "{look}"; '
                f'bevel: "{"2000" if look in ("2000", "2001") else "1995"}"; face: "{LOOKS[look]["face"]}" }}'
            )
        text = "\n".join(
            [
                "import QtQuick",
                "import org.kde.ksvg as KSvg",
                "import org.kde.kirigami as Kirigami",
                *imports,
                "Rectangle { width: 800; height: 30",
                f'Component.onCompleted: {{ KSvg.ImageSet.basePath = "{themes}"; '
                f'KSvg.ImageSet.imageSetName = "{name}" }}',
                background,
                start,
                f"Tasks.Separator {{ x: {start_width + 3}; y: 2; height: 26 }}",
                *[
                    f"Tasks.QuickLaunchButton {{ x: {start_width + 16 + number * 23}; y: 2; "
                    f'width: 23; height: 26; icon: "{icon}" }}'
                    for number, icon in enumerate(("folder", "internet-web-browser", "utilities-terminal"))
                ],
                f"Tasks.Separator {{ x: {start_width + 86}; y: 2; height: 26 }}",
                *items,
                "Tray.TrayBox { x: 688; width: 112; height: 30 }",
                *[
                    f"Kirigami.Icon {{ x: {700 + number * 22}; y: 9; width: 16; height: 16; "
                    f'source: "{icon}"; roundToIconSize: false }}'
                    for number, icon in enumerate(("audio-volume-high", "network-wired"))
                ],
                'Text { x: 750; y: 8; text: "10:30"; color: "'
                + ("white" if luna else "black")
                + '"; font.pixelSize: 11 }',
                "}",
            ]
        )
        path = scratch / f"taskbar-{index}.qml"
        path.write_text(text)
        rows.append((f"Taskbar · {label}", None, qml_image(app, path, (800, 30))))
    return rows


def frame(look, scratch, width, height, active=True, caption="Display Properties", **kwargs):
    from aurorae_model import Window, build_theme

    if look == "luna":
        from luna_model import LunaWindow

        return LunaWindow(width, height, active=active, caption=caption, **kwargs).render()
    folder = scratch / "decoration"
    if not folder.exists():
        build_theme(folder, look)
    return Window(folder, width, height, active=active, caption=caption, **kwargs).render()


def desktop(app, look, scratch, bar):
    """A deterministic composed preview: real widgets in the theme's decoration, no empty test windows."""
    from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

    import controls_gallery as gallery

    scene = Image.new("RGB", SIZE, "#008080" if look in ("1995", "1998") else "#3a6ea5")
    for active, position, title in ((False, (45, 55), "Documents"), (True, (285, 190), "Display Properties")):
        content = QWidget()
        content.setAutoFillBackground(True)
        layout = QVBoxLayout(content)
        layout.addWidget(QLabel("Project documents" if not active else "Choose your display settings"))
        layout.addWidget(gallery.list_box() if not active else gallery.tab_widget())
        layout.addWidget(gallery.text_fields() if not active else gallery.check_boxes())
        layout.addWidget(gallery.push_buttons())
        content.adjustSize()
        content.show()
        app.processEvents()
        body = qimage_to_pil(content.grab().toImage())
        content.close()
        border, top = (4, 30) if look == "luna" else (4, 22)
        window = frame(look, scratch, body.width + border * 2, body.height + top + border, active, title)
        window.paste(body, (border, top))
        scene.paste(window, position, window if window.mode == "RGBA" else None)
    scene.paste(bar, (0, SIZE[1] - bar.height))
    return scene


def scenes(app, look, scratch):
    bars = taskbars(app, look, scratch)
    panels = []
    picture = boot(app, look, scratch)
    if picture is not None:
        panels.append(("Boot · fixed progress phase", None, picture))
    else:
        print(f"{look}: boot omitted — Chicago95 Plymouth assets unavailable")
    panels.append(("Login · Alex", None, login(app, look, scratch)))
    panels.append(("Desktop · composed native-widget preview", None, desktop(app, look, scratch, bars[1][2])))
    return panels + bars


def controls(app, look, scratch):
    import controls_gallery as gallery

    rows = [
        (f"{group(name)} · Qt Widgets · {name}", original, ours) for name, original, ours in gallery.controls(app, look)
    ]
    for active in (True, False):
        for label, options in (
            ("normal", {}),
            ("close pressed", {"pressed": "X"}),
            ("dialog: help / close", {"right": "HX"}),
        ):
            image = frame(look, scratch, 340, 80, active, "Window decoration", **options)
            rows.append((f"Windows · Aurorae · {'active' if active else 'inactive'} · {label}", None, image))
    rows.extend(
        ("Shell · Qt Quick · " + name, ref, image) for name, ref, image in taskbars(app, look, scratch / "shell")
    )
    from reference import screenshot
    from test_window_reference import WINDOWS

    for active in (True, False):
        counterpart = None
        if look != "luna":
            match = next((value for value in WINDOWS.values() if value[0] == look and value[3] == active), None)
            if match:
                _, filename, (_, top, right, _), _, _, _ = match
                try:
                    counterpart = screenshot(filename).crop((right - 69, top, right + 1, top + 26))
                except FileNotFoundError:
                    pass
        elif active:
            try:
                original = screenshot("xpnotepad")
                counterpart = original.crop((original.width - 80, 0, original.width, 32))
            except FileNotFoundError:
                pass
        ours = frame(look, scratch, 340, 80, active)
        rows.append(
            (
                f"Windows · Aurorae · {'active' if active else 'inactive'} caption buttons",
                counterpart,
                ours.crop((260 if look == "luna" else 270, 0, 340, 32 if look == "luna" else 26)),
            )
        )
    rows.extend(gtk_controls(look, scratch))
    return sorted(rows, key=lambda row: row[0].split(" · ")[0])


def group(name):
    name = name.lower()
    for group_name, words in (
        ("Navigation", ("tab", "menu", "tool", "status")),
        ("Buttons", ("button", "check", "radio")),
        ("Inputs", ("field", "drop-down", "spin", "date", "text edit")),
        ("Ranges", ("slider", "scroll", "progress", "dial")),
        ("Views", ("list", "tree", "table", "header")),
    ):
        if any(word in name for word in words):
            return group_name
    return "Containers and text"


def gtk_controls(look, scratch):
    """Run both GTK versions in one isolated compositor; absent runtimes are recorded, never faked."""
    import os
    import subprocess
    import sys
    import tempfile
    from shlex import quote

    from plasma_session import CHICAGO95_SRC, link_user_assets, run_session

    rows = []
    if not shutil.which("kwin_wayland"):
        print("GTK controls omitted: kwin_wayland unavailable")
        return rows
    with tempfile.TemporaryDirectory(prefix="c95-gtk-", dir="/tmp") as folder:
        work = Path(folder)
        home, runtime = work / "home", work / "run"
        home.mkdir()
        runtime.mkdir(mode=0o700)
        link_user_assets(home)
        theme = "Chicago95Luna" if look == "luna" else "Chicago95"
        if look == "luna":
            (home / ".themes/Chicago95Luna").symlink_to(REPO / "luna/gtk/Chicago95Luna")
        elif not (CHICAGO95_SRC / "Theme/Chicago95").exists():
            print(f"{look}: GTK controls omitted: Chicago95 GTK theme unavailable")
            return rows
        commands = []
        for version in ("3.0", "4.0"):
            probe = subprocess.run(
                [sys.executable, "-c", f'import gi; gi.require_version("Gtk", "{version}")'],
                capture_output=True,
                check=False,
            )
            if probe.returncode:
                print(f"GTK {version} omitted: runtime unavailable")
                continue
            output = scratch / f"gtk-{version}"
            commands.append(
                f"timeout 30 {quote(sys.executable)} {quote(str(REPO / 'tests/gtk_showcase.py'))} "
                f"{version} {theme} {quote(str(output))} > {quote(str(work / (version + '.log')))} 2>&1"
            )
        script = work / "gtk.sh"
        script.write_text("#!/bin/sh\n" + "\n".join(commands) + "\n")
        environment = {
            **os.environ,
            "HOME": str(home),
            "XDG_CONFIG_HOME": str(home / ".config"),
            "XDG_RUNTIME_DIR": str(runtime),
            "GDK_BACKEND": "wayland",
            "GSK_RENDERER": "cairo",
        }
        environment.pop("QT_QPA_PLATFORM", None)
        environment.pop("QT_QPA_PLATFORMTHEME", None)
        environment.pop("DISPLAY", None)
        environment.pop("WAYLAND_DISPLAY", None)
        run_session(work, script, environment, SIZE)
        if commands and not any((work / f"{v}.log").exists() for v in ("3.0", "4.0")):
            raise RuntimeError((work / "kwin-gtk.log").read_text())
        for version in ("3.0", "4.0"):
            output = scratch / f"gtk-{version}"
            manifest = output / "manifest.json"
            if not manifest.exists():
                log = work / f"{version}.log"
                if log.exists():
                    raise RuntimeError(f"GTK {version} renderer failed:\n{log.read_text()}")
                continue
            for category, label, filename in json.loads(manifest.read_text()):
                image = Image.open(output / filename).convert("RGBA")
                background = Image.new("RGBA", image.size, "#ece9d8" if look == "luna" else "#c0c0c0")
                background.alpha_composite(image)
                from controls_gallery import original_control

                reference_name = {
                    "Push buttons": "Push buttons (default, plain, disabled, pressed)",
                    "Check boxes": "Check boxes",
                    "Radio buttons": "Radio buttons",
                    "Text fields": "Text fields",
                    "Progress bar": "Progress bar",
                    "Sliders": "Sliders (plain, disabled, vertical)",
                    "Tabs": "Tabs (Qt's own tab widget)",
                }.get(label.split(":")[0])
                counterpart = original_control(look, reference_name)
                rows.append((f"{category} · GTK {version} · {label}", counterpart, background.convert("RGB")))
    return rows
