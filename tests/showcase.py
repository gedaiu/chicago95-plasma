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
    from PySide6.QtGui import QIcon
    from render_report import KDEGLOBALS

    previous_icons = QIcon.themeName()

    settings = f"[StartMenu]\nstyle={look}\n[Look]\nwidgetStyle={look if look == 'luna' else 'classic'}\n"
    with installed_look(app, settings, KDEGLOBALS.get(look, "")):
        chicago95ui.apply_style(app)
        QIcon.setThemeName({"1995": "Chicago95", "1998": "SE98", "2000": "ClassicOS-2000",
                            "2001": "Windows-XP", "luna": "Windows-XP"}[look])
        try:
            yield
        finally:
            QIcon.setThemeName(previous_icons)
    chicago95ui.apply_style(app)


def qml_image(app, path, size, context=None, properties=None, metadata=()):
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
    image.info["geometry"] = {}
    for name in metadata:
        value = view.rootObject().property(name)
        image.info["geometry"][name] = value.toVariant() if hasattr(value, "toVariant") else value
    view.close()
    return image


def boot(app, look, scratch):
    """A fixed boot phase, using the shipped assets/layout (no historical screenshot)."""
    from plasma_session import CHICAGO95_SRC

    if look in ("1995", "1998"):
        asset = (REPO / "splash/chicago95.splashscreen/contents/splash/images/windows98.png"
                 if look == "1998" else CHICAGO95_SRC / "Plymouth/Chicago95/win95_boot_10.png")
        if not asset.exists():
            return None
        return Image.open(asset).convert("RGB").resize(SIZE, Image.Resampling.NEAREST)
    if look in ("2001", "luna"):
        from luna_qml import render_luna_splash

        return render_luna_splash(app, size=SIZE)
    folder = scratch / "boot"
    shutil.copytree(REPO / "splash/chicago95.splashscreen/contents/splash", folder)
    from render_report import DEFAULT_LOGO, WAVING_FLAG

    settings = (folder / "settings.js").read_text().replace('var style = "classic"', 'var style = "2000"')
    logo = WAVING_FLAG if WAVING_FLAG.exists() else DEFAULT_LOGO
    settings = settings.replace('var brandLogo = ""', f"var brandLogo = {json.dumps(str(logo))}")
    settings = settings.replace('var company = ""', 'var company = "Microsoft"')
    settings = settings.replace('var tagline = "Built on Linux Technology"', 'var tagline = "Built on NT Technology"')
    settings = settings.replace('var footer = "Chicago95 for KDE Plasma"',
                                'var footer = "Copyright © 1985-1999 Microsoft Corporation"')
    settings = settings.replace(
        'var brandText = "Chicago95"', f'var brandText = "Windows {"XP" if look == "2001" else "2000"}"'
    )
    (folder / "settings.js").write_text(settings)
    return qml_image(app, folder / "Splash.qml", SIZE, properties={"stage": 3, "booting": True})


def login(app, look, scratch):
    from login_theme import render_login

    if look == "luna":
        from luna_qml import render_luna_login

        return render_luna_login(app, size=SIZE, user="Alex", users=("Alex",))
    banner = None
    if look in ("2000", "2001"):
        from conftest import load_script
        from render_report import DEFAULT_LOGO, WAVING_FLAG

        banner = scratch / "login-banner.png"
        load_script("chicago95-shutdown").render_login_banner(
            {
                "style": look,
                "osName": "Windows XP" if look == "2001" else "Windows 2000",
                "bannerText": "Windows XP" if look == "2001" else "Windows 2000",
                "osCompany": "Microsoft",
                "edition": "Professional",
                "osLogo": str(WAVING_FLAG if WAVING_FLAG.exists() else DEFAULT_LOGO),
                "companyLogo": "",
                "tagline": "Built on NT Technology",
            },
            banner,
        )
    return render_login(
        app,
        scratch / "login",
        size=SIZE,
        user="Alex",
        users=("Alex",),
        host_name="WINDOWS",
        loginTitle="Log On to Windows" if look in ("2000", "2001") else "Welcome to Windows",
        loginMessage="Type a user name and password to log on to Windows.",
        banner=banner,
        loginStyle="2000" if look in ("2000", "2001") else "classic",
        titleActive={"1995": "#000080", "1998": "#000080,#1084d0"}.get(look, "#0a246a,#a6caf0"),
    )


def taskbars(app, look, scratch):
    """Production components and Quick Launch layout, including constrained bands and hidden tray items."""
    from aurorae_model import LOOKS
    from render_report import DEFAULT_LOGO

    start_logo = (REPO / "plasmoids/org.chicago95.start/contents/images/logo-xp-16.png"
                  if look == "2001" else DEFAULT_LOGO)
    scratch.mkdir(parents=True, exist_ok=True)
    luna = look == "luna"
    themes = scratch / "themes"
    bar_height = 30 if luna else 28
    applet_y, applet_height = (0, 30) if luna else (2, 24)
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
        # Install the whole contents tree: QML has relative image and shared-JavaScript imports.
        contents = scratch / component
        shutil.copytree(REPO / f"plasmoids/org.chicago95.{component}/contents", contents)
        if luna:
            shutil.copytree(REPO / f"luna/plasmoids/org.chicago95.{component}/contents", contents, dirs_exist_ok=True)
            shutil.copy(REPO / "luna/plasmoids/family.js", contents / "ui/luna/family.js")
        for qml in contents.rglob("*.qml"):
            qml.write_text(
                qml.read_text().replace(
                    "@HOME@/.local/share/chicago95/icons/tray-chevron.png",
                    (REPO / "data/icons/tray-chevron.png").as_uri(),
                )
            )
        source = contents / "ui" / "luna" if luna else contents / "ui"
        imports.append(f'import "{source.as_uri()}" as {alias}')
    imports.append(f'import "{(scratch / "tasks/ui/quickLaunchBand.js").as_uri()}" as Band')
    tasks = ["Documents", "Display Properties", "Notes"]
    variants = [
        ("Idle", [], False, "left", "normal"),
        ("Open windows", tasks, False, "left", "normal"),
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
            False,
            "left",
            "normal",
        ),
        ("Overflow · Quick Launch 2 of 6, tray 2 of 5", tasks, True, "left", "normal"),
        ("Overflow · chevrons hovered", tasks, True, "left", "hovered"),
        ("Overflow · chevrons pressed", tasks, True, "left", "held"),
        ("Overflow · Quick Launch docked right", tasks, True, "right", "normal"),
        ("Start hovered", tasks, False, "left", "start-hovered"),
        ("Start pressed", tasks, False, "left", "start-held"),
        ("Quick Launch hovered", tasks, False, "left", "launch-hovered"),
        ("Quick Launch pressed", tasks, False, "left", "launch-held"),
        ("Task button hovered", tasks, False, "left", "task-hovered"),
    ]
    launchers = [
        "folder",
        "internet-web-browser",
        "utilities-terminal",
        "text-editor",
        "system-file-manager",
        "help-browser",
    ]
    rows = []
    for index, (label, titles, overflow, dock, state) in enumerate(variants):
        start_width = 98 if luna else 64
        task_settings = "" if luna else f'look: "{look}"; bevel: "{"2000" if look in ("2000", "2001") else "1995"}";'
        if luna:
            from palette import PALETTE

            background = (
                "Column { Repeater { model: "
                + json.dumps(PALETTE["taskbar"])
                + "; Rectangle { required property string modelData; width: 800; height: 1; color: modelData } } }"
            )
            start = (f'Start.StartButton {{ id: startButton; width: {start_width}; height: 30; text: "start"; '
                     'hovered: root.variant === "start-hovered"; held: root.variant === "start-held" }')
        else:
            background = (
                f'color: "{LOOKS[look]["face"]}"\n'
                'KSvg.FrameSvgItem { anchors.fill: parent; imagePath: "widgets/panel-background"; '
                "enabledBorders: KSvg.FrameSvg.TopBorder }"
            )
            start = (
                'Start.StartButton { id: startButton; x: 2; y: 2; width: implicitWidth; height: 24; text: "Start"; '
                'hovered: root.variant === "start-hovered"; held: root.variant === "start-held"; '
                f'logoSource: "{start_logo.as_uri()}"; look: "{look}"; '
                f'bevel: "{"2000" if look in ("2000", "2001") else "1995"}"; face: "{LOOKS[look]["face"]}" }}'
            )
        band_size = "2 * metrics.cellWidth + metrics.chevronWidth" if overflow else "Band.fitAll()"
        tray_icons = ["audio-volume-high", "network-wired", "battery", "printer", "input-keyboard"]
        tray_chevron = (
            (
                "Tray.TrayChevron { x: root.trayLeft - 8; y: 7; hovered: root.hovered; held: root.held }"
                if luna
                else f"Image {{ x: root.trayLeft + root.trayPadding; y: root.iconTop; width: 16; height: 16; "
                f'source: "{(REPO / "data/icons/tray-chevron.png").as_uri()}"; smooth: false }}'
            )
            if overflow
            else ""
        )
        text = "\n".join(
            [
                "import QtQuick",
                "import org.kde.ksvg as KSvg",
                "import org.kde.kirigami as Kirigami",
                *imports,
                f"Rectangle {{ id: root; width: 800; height: {bar_height}",
                f'Component.onCompleted: {{ KSvg.ImageSet.basePath = "{themes}"; '
                f'KSvg.ImageSet.imageSetName = "{name}" }}',
                f'property string variant: "{state}"',
                f"property bool hovered: {str(state == 'hovered').lower()}",
                f"property bool held: {str(state == 'held').lower()}",
                f"property var launchers: {json.dumps(launchers if overflow else launchers[:3])}",
                f"property var titles: {json.dumps(titles)}",
                f"property var trayIcons: {json.dumps(tray_icons if overflow else tray_icons[:2])}",
                "property int shownTrayIcons: Math.min(2, trayIcons.length)",
                "property bool trayOverflow: trayIcons.length > shownTrayIcons",
                f"property int trayPadding: {11 if luna else 4 if look in ('2000', '2001') else 3}",
                f"property int clockGap: {4 if look in ('2000', '2001') else 1}",
                f"property int iconTop: {7}",
                "property int arrowWidth: trayOverflow ? 16 : 0",
                "property int firstTrayIcon: clock.x - clockGap - 16 - (shownTrayIcons - 1) * 17",
                f"property int trayLeft: firstTrayIcon - trayPadding - {'0' if luna else 'arrowWidth'}",
                f'property var metrics: Band.metrics("{look}")',
                "property var band: Band.layout(trayLeft - 4, startButton.x + startButton.width + 3, "
                "metrics.separatorLead, launchers.length, "
                f'{band_size}, "{dock}", metrics)',
                "property int taskWidth: Math.min(165, "
                "Math.floor((band.tasksEnd - band.tasksX - 6) / Math.max(1, titles.length)) - 3)",
                background,
                start,
                f"Tasks.Separator {{ x: root.band.leftSeparatorX; y: {applet_y}; height: {applet_height} }}",
                "Repeater { model: root.band.shown; Tasks.QuickLaunchButton { required property int index; "
                f"x: root.band.cellsX + index * root.metrics.cellWidth; y: {applet_y}; "
                f"width: root.metrics.cellWidth; height: {applet_height}; "
                "icon: root.launchers[root.band.firstShown + index]; "
                'hovered: index === 0 && root.variant === "launch-hovered"; '
                'held: index === 0 && root.variant === "launch-held" } }',
                f"Tasks.Chevron {{ visible: root.band.chevronX >= 0; x: root.band.chevronX; y: {applet_y}; "
                f"width: root.metrics.chevronWidth; height: {applet_height}; "
                f"pointsRight: {str(dock == 'left').lower()}; "
                "hovered: root.hovered; held: root.held }",
                f"Tasks.Separator {{ x: root.band.rightSeparatorX; y: {applet_y}; height: {applet_height} }}",
                "Repeater { model: root.titles; Tasks.TaskButton { required property string modelData; "
                "required property int index; "
                f"x: root.band.tasksX + index * (root.taskWidth + 3); y: {applet_y}; "
                f"width: root.taskWidth; height: {applet_height}; "
                'text: modelData; icon: ["folder", "preferences-desktop-display", "text-x-generic"][index % 3]; '
                + task_settings
                + ' hovered: index === 0 && root.variant === "task-hovered"; pressed: index === 1 } }',
                f"Tray.TrayBox {{ x: root.trayLeft; y: {applet_y}; "
                f"width: root.width - x - {0 if luna else 2}; height: {applet_height} }}",
                tray_chevron,
                "Repeater { model: Math.min(2, root.trayIcons.length); Kirigami.Icon { required property int index; "
                "x: root.firstTrayIcon + index * 17; y: root.iconTop; "
                "width: 16; height: 16; source: root.trayIcons[index]; "
                "roundToIconSize: false } }",
                "Text { id: clock; x: root.width - implicitWidth - 8; y: Math.round((root.height - height) / 2); "
                'text: "10:30"; color: "' + ("white" if luna else "black") + '"; font.pixelSize: 11 }',
                "}",
            ]
        )
        path = scratch / f"taskbar-{index}.qml"
        path.write_text(text)
        rows.append(
            (
                f"Taskbar · {label}",
                None,
                qml_image(
                    app,
                    path,
                    (800, bar_height),
                    metadata=("trayLeft", "firstTrayIcon", "arrowWidth", "iconTop", "band"),
                ),
            )
        )
    return rows


def frame(look, scratch, width, height, active=True, caption="Display Properties", **kwargs):
    from aurorae_model import Window, build_theme
    from PySide6.QtGui import QIcon, QImage
    from PySide6.QtWidgets import QApplication, QStyle

    if look == "luna":
        from luna_model import LunaWindow

        window = LunaWindow(width, height, active=active, caption=caption, **kwargs)
    else:
        folder = scratch / "decoration"
        if not folder.exists():
            build_theme(folder, look)
        window = Window(folder, width, height, active=active, caption=caption, **kwargs)
    image = window.render()
    rect = window.button_rects().get("M")
    if rect is not None:
        name = "folder" if caption == "Documents" else "preferences-desktop-display"
        fallback = QApplication.style().standardIcon(
            QStyle.SP_DirIcon if caption == "Documents" else QStyle.SP_ComputerIcon
        )
        icon = QIcon.fromTheme(name, fallback).pixmap(16, 16).toImage().convertToFormat(QImage.Format_RGBA8888)
        pixels = Image.frombytes(
            "RGBA", (icon.width(), icon.height()), bytes(icon.constBits()), "raw", "RGBA", icon.bytesPerLine()
        )
        image.paste(pixels, (round(rect.center().x() - 8), round(rect.center().y() - 8)), pixels)
    return image


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
    panels.extend(start_menus(app, look, scratch))
    return panels + bars


def start_menus(app, look, scratch):
    """Real root menus, with installed icon artwork and a highlighted item."""
    from conftest import load_script
    from reference import render_start_menu
    from render_report import MENU_SETTINGS

    startmenu = load_script("chicago95-startmenu")
    rows = []
    if look == "luna":
        import chicago95lunamenu
        from luna_render import sample_apps

        apps = sample_apps()
        apps[0].update(icon="internet-web-browser", categories=["WebBrowser"])
        apps[1].update(icon="internet-mail", categories=["Email"])
        for entry, name, icon in zip(apps[2:], ("Documents", "Pictures", "Music", "Calculator", "Notepad", "Terminal"),
                                     ("folder-documents", "folder-pictures", "folder-music", "accessories-calculator",
                                      "text-editor", "utilities-terminal"), strict=False):
            entry.update(name=name, icon=icon)
        menu = chicago95lunamenu.LunaMenu(apps, [], lambda _: None, startmenu.luna_icon, None, None, user_name="Alex")
        menu.adjustSize()
        rows.append(("Start menu · normal", None, qimage_to_pil(menu.grab().toImage())))
        for title in ("Internet", "My Documents", "All Programs"):
            menu.hovered = next(row for row in menu.rows if row.text == title)
            menu.update()
            rows.append((f"Start menu · hovered {title}", None, qimage_to_pil(menu.grab().toImage())))
        menu.close()
    else:
        for label, active in (("normal", None), ("selected item", 0)):
            folder = scratch / f"start-menu-{label}"
            folder.mkdir()
            settings, colours = MENU_SETTINGS[look]
            image = render_start_menu(startmenu, app, folder, settings, colours, without=(), active=active)
            rows.append((f"Start menu · {label}", None, image))
    return rows


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
    return sorted(rows, key=lambda row: CONTROL_GROUPS.index(row[0].split(" · ")[0]))


CONTROL_GROUPS = (
    "Buttons", "Checkboxes", "Radio buttons", "Switches", "Inputs", "Scrollbars", "Sliders", "Progress bars",
    "Tabs", "Menus", "Toolbars", "Status bars", "Lists", "Trees", "Tables", "Headers",
    "Group boxes", "Containers and text", "Windows", "Shell",
)


def group(name):
    # Classify the control name, not state descriptions such as a menu's "checked" items.
    name = name.lower().split(":", 1)[0].split("(", 1)[0]
    for group_name, words in (
        ("Checkboxes", ("check box", "checkbox")),
        ("Radio buttons", ("radio",)),
        ("Switches", ("switch",)),
        ("Toolbars", ("tool",)),
        ("Buttons", ("button",)),
        ("Inputs", ("field", "drop-down", "spin", "date", "text edit")),
        ("Scrollbars", ("scroll",)),
        ("Sliders", ("slider", "dial")),
        ("Progress bars", ("progress",)),
        ("Tables", ("table",)),
        ("Tabs", ("tab",)),
        ("Menus", ("menu",)),
        ("Status bars", ("status",)),
        ("Lists", ("list",)),
        ("Trees", ("tree",)),
        ("Headers", ("header",)),
        ("Group boxes", ("group box",)),
    ):
        if any(word in name for word in words):
            return group_name
    return "Containers and text"


def gtk_controls(look, scratch, audit=False, audit_kinds=()):
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
    # Session services can finish flushing after KWin exits; cleanup must not discard valid renders.
    with tempfile.TemporaryDirectory(prefix="c95-gtk-", dir="/tmp", ignore_cleanup_errors=True) as folder:
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
        classic_theme = CHICAGO95_SRC / "Theme/Chicago95"
        if look in ("2000", "2001"):
            import chicago95ui
            from gtk_palette import prepare_theme, scheme_colours
            from PySide6.QtWidgets import QApplication

            app = QApplication.instance() or chicago95ui.make_app("gtk-showcase-palette")
            with themed(app, look):
                colours = scheme_colours(chicago95ui.read_scheme(), chicago95ui.look_settings()["bevel"])
            classic_theme = home / ".themes/Chicago95"
            if classic_theme.is_symlink():
                classic_theme.unlink()
            prepare_theme(CHICAGO95_SRC / "Theme/Chicago95", classic_theme, colours)
        if look != "luna":
            from gtk_inputs import input_css
            from gtk_notebooks import notebook_css
            from gtk_scrollbars import scrollbar_css
            from gtk_sliders import slider_css

            config = home / ".config/gtk-4.0"
            config.mkdir(parents=True, exist_ok=True)
            (config / "gtk.css").write_text(
                notebook_css(classic_theme) + scrollbar_css(classic_theme)
            )
            progress_css = (REPO / "config/gtk-progress-classic.css").read_text()
            progress_css += (REPO / "config/gtk-frames-classic.css").read_text()
            for version in ("3.0", "4.0"):
                config = home / f".config/gtk-{version}"
                config.mkdir(parents=True, exist_ok=True)
                with (config / "gtk.css").open("a") as stylesheet:
                    stylesheet.write(progress_css)
                    stylesheet.write(input_css(classic_theme, version))
                    stylesheet.write(slider_css(version))
        # Use Qt's resolved family, so an unavailable font falls back identically in Pango.
        import chicago95ui
        from PySide6.QtGui import QFontInfo
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = chicago95ui.make_app("gtk-showcase-fonts")
            gtk_controls._font_app = app  # retain the application for standalone GTK audits
        with themed(app, look):
            font_family = QFontInfo(app.font()).family()
        fontconfig = home / ".config/fontconfig/conf.d"
        fontconfig.mkdir(parents=True, exist_ok=True)
        font_rules = (REPO / "luna/fontconfig/61-chicago95-luna-fonts.conf" if look == "luna"
                      else REPO / "config/fontconfig/60-chicago95-pixel-font.conf")
        shutil.copy(font_rules, fontconfig / font_rules.name)
        for version in ("3.0", "4.0"):
            config = home / f".config/gtk-{version}"
            config.mkdir(parents=True, exist_ok=True)
            with (config / "gtk.css").open("a") as stylesheet:
                stylesheet.write(f'\n* {{ font-family: "{font_family}"; font-size: 11px; }}\n')
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
            (output / "manifest.json").unlink(missing_ok=True)
            commands.append(
                f"timeout 60 {quote(sys.executable)} {quote(str(REPO / 'tests/gtk_showcase.py'))} "
                f"{version} {theme} {quote(str(output))}{' --consistency' if audit else ''} "
                + (f"--only {quote(','.join(audit_kinds))} " if audit_kinds else "")
                + f"> {quote(str(work / (version + '.log')))} 2>&1"
            )
        script = work / "gtk.sh"
        script.write_text("#!/bin/sh\n" + "\n".join(commands) + "\n")
        environment = {
            **os.environ,
            "HOME": str(home),
            "XDG_CONFIG_HOME": str(home / ".config"),
            "XDG_RUNTIME_DIR": str(runtime),
            "CHICAGO95_SHOWCASE_FONT": font_family,
            "GDK_BACKEND": "wayland",
            "GSK_RENDERER": "cairo",
            "GTK_A11Y": "none",
            "NO_AT_BRIDGE": "1",
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
            if output.exists() and (work / f"{version}.log").exists():
                shutil.copy(work / f"{version}.log", output / "render.log")
            if not manifest.exists():
                log = work / f"{version}.log"
                if log.exists():
                    raise RuntimeError(f"GTK {version} renderer failed:\n{log.read_text()}")
                continue
            for _category, label, filename in json.loads(manifest.read_text()):
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
                    "Sliders": "Sliders (plain, ticks, disabled, vertical)",
                    "Tabs": "Tabs (Qt's own tab widget)",
                }.get(label.split(":")[0])
                counterpart = original_control(look, reference_name)
                rows.append((f"{group(label)} · GTK {version} · {label}", counterpart, background.convert("RGB")))
    return rows
