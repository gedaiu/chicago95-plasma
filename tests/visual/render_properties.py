"""Render production Qt dialogs in an isolated process at the reference DPI."""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aurorae_model import build_theme  # noqa: E402
from conftest import REPO, load_script  # noqa: E402
from PIL import Image  # noqa: E402
from PySide6.QtCore import QElapsedTimer, QPoint, QRect, QSize, Qt  # noqa: E402
from PySide6.QtGui import QIcon  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QFrame, QPushButton, QTabWidget, QToolButton  # noqa: E402
from reference import installed_look, qimage_to_pil  # noqa: E402
from showcase import themed  # noqa: E402


def aero_style(app):
    config = Path(os.environ["XDG_CONFIG_HOME"]) / "Kvantum"
    theme = config / "Windows7Aero"
    theme.mkdir(parents=True)
    cache = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "chicago95" / "kvantum-f51ca15"
    for source, target in (
        ("Windows7Aero-paths.svg", "Windows7Aero.svg"),
        ("Windows7Aero.kvconfig", "Windows7Aero.kvconfig"),
    ):
        if not (cache / source).is_file():
            raise FileNotFoundError(f"Control Panel parity needs the Aero artwork installed by Setup: {cache / source}")
        (theme / target).symlink_to(cache / source)
    (config / "kvantum.kvconfig").write_text("[General]\ntheme=Windows7Aero\n")
    colours = (REPO / "aero/Chicago95Aero.colors").read_text()
    return installed_look(app, "[StartMenu]\nstyle=aero\n[Look]\nwidgetStyle=aero\n", colours)


def capture_hover(window, output):
    window.show()
    card = window.category_view.findChild(QFrame, "categoryCard")
    heading = card.findChild(QPushButton)
    # The Aero opening sample aligns with rows 28–35 of the Basic card's steady fill.
    region = QRect(card.mapTo(window, QPoint(card.width() - 36, 28)), QSize(8, 8))
    strip = Image.new("RGB", (40, 8))

    QTest.mouseMove(window.toolbar, window.toolbar.rect().center())
    idle = qimage_to_pil(window.grab(region).toImage())
    strip.paste(idle, (0, 0))
    QTest.mouseMove(heading, QPoint(12, 6))
    for index in range(1, 5):
        strip.paste(qimage_to_pil(window.grab(region).toImage()), (index * 8, 0))
        QTest.qWait(17)
    strip.save(Path(output).with_name("hover-opening.png"))
    assert window.grab(QRect(card.mapTo(window, QPoint()), card.size())).save(output)
    QTest.mouseMove(window.toolbar, window.toolbar.rect().center())
    assert qimage_to_pil(window.grab(region).toImage()).tobytes() == idle.tobytes()


def capture_hover_exit(window, output, scale):
    window.show()
    card = window.category_view.findChild(QFrame, "categoryCard")
    heading = card.findChild(QPushButton)
    # Sample 36 physical pixels before the right edge and 30 below the top.
    region = QRect(
        card.mapTo(window, QPoint(card.width() - round(36 / scale), round(30 / scale))),
        QSize(round(12 / scale), round(12 / scale)),
    )
    strip = Image.new("RGB", (60, 36))
    idle_position = window.toolbar.rect().center()
    QTest.mouseMove(window.toolbar, idle_position)
    for trial in range(3):
        QTest.mouseMove(heading, QPoint(12, 6))
        QTest.qWait(50)
        strip.paste(qimage_to_pil(window.grab(region).toImage()), (0, trial * 12))
        QTest.mouseMove(window.toolbar, idle_position)
        for frame in range(1, 5):
            sample = qimage_to_pil(window.grab(region).toImage())
            assert sample.size == (12, 12)
            strip.paste(sample, (frame * 12, trial * 12))
            QTest.qWait(17)
    strip.save(output)


def capture_category_press(window, output):
    window.show()
    card = window.category_view.findChild(QFrame, "categoryCard")
    heading = card.findChild(QPushButton)
    outside = window.toolbar.mapTo(window, window.toolbar.rect().center())
    inside = heading.mapTo(window, QPoint(12, 6))
    region = QRect(card.mapTo(window, QPoint(card.width() - 36, 28)), QSize(8, 8))
    strip = Image.new("RGB", (48, 8))

    def sample(frame, position):
        QTest.mouseMove(window.windowHandle(), position)
        strip.paste(qimage_to_pil(window.grab(region).toImage()), (frame * 8, 0))

    sample(0, outside)
    sample(1, inside)
    QTest.mousePress(window.windowHandle(), Qt.LeftButton, pos=inside)
    sample(2, inside)
    sample(3, outside)
    sample(4, inside)
    QTest.mouseMove(window.windowHandle(), outside)
    QTest.mouseRelease(window.windowHandle(), Qt.LeftButton, pos=outside)
    sample(5, outside)
    assert window.pages.currentWidget() is window.category_view
    assert heading.hasFocus()
    focus_region = QRect(card.mapTo(window, QPoint(52, 0)), QSize(165, 24))
    assert window.grab(focus_region).save(str(Path(output).with_name("category-focus.png")))

    QTest.mouseMove(window.windowHandle(), inside)
    QTest.mousePress(window.windowHandle(), Qt.LeftButton, pos=inside)
    QTest.mouseMove(window.windowHandle(), outside)
    QTest.mouseMove(window.windowHandle(), inside)
    QTest.mouseRelease(window.windowHandle(), Qt.LeftButton, pos=inside)
    assert window.address_bar.crumbs()[-1] == heading.text()
    strip.save(output)


def capture_shutdown_buttons(dialog, crops, output, hover_settle_ms):
    left, top, right, bottom = next(iter(crops.values()))
    width, height = right - left, bottom - top
    sheet = Image.new("RGB", (3 * width, len(crops) * height))
    outside = QPoint(8, 8)
    idle_focus = dialog.focusWidget()

    def sample(box, row, column):
        tile = qimage_to_pil(dialog.grab().toImage()).crop(tuple(box))
        assert tile.size == (width, height)
        sheet.paste(tile, (column * width, row * height))

    for row, (name, box) in enumerate(crops.items()):
        button = dialog.buttons[name]
        centre = button.rect().center()
        QTest.mouseMove(dialog.windowHandle(), outside)
        idle_focus.setFocus()

        assert not button.underMouse()
        sample(box, row, 0)
        QTest.mouseMove(dialog.windowHandle(), button.mapTo(dialog, centre))
        assert button.underMouse()
        if hover_settle_ms:
            QTest.qWait(hover_settle_ms)
        sample(box, row, 1)
        QTest.mousePress(button, Qt.LeftButton, pos=centre)
        assert button.isDown()
        sample(box, row, 2)
        QTest.mouseRelease(button, Qt.LeftButton, pos=QPoint(-4, -4))
        assert dialog.isVisible() and not button.isDown()
    sheet.save(output)


def capture_shutdown_button_hover(dialog, position, output):
    button = dialog.buttons["cancel"]
    patch = QRect(QPoint(*position), QSize(1, 1))

    def sample():
        return dialog.grab(patch).toImage().pixelColor(0, 0).getRgb()[:3]

    def record(point, duration):
        samples = [(0, sample())]
        clock = QElapsedTimer()
        clock.start()
        QTest.mouseMove(dialog.windowHandle(), point)
        while clock.elapsed() < duration:
            QTest.qWait(40)
            colour = sample()
            samples.append((clock.elapsed(), colour))
        return samples

    outside = QPoint(8, 8)
    QTest.mouseMove(dialog.windowHandle(), outside)
    enter = record(button.mapTo(dialog, button.rect().center()), 850)
    assert button.underMouse()
    leave = record(outside, 1850)
    assert not button.underMouse()
    Path(output).write_text(json.dumps({"enter": enter, "leave": leave}))


def capture_shutdown_radio_states(dialog, box, output):
    left, top, right, bottom = box
    width, height = right - left, bottom - top
    sheet = Image.new("RGB", (width, len(dialog.radios) * height))
    for index, radio in enumerate(dialog.radios):
        assert radio.isChecked() and dialog.focusWidget() is radio
        tile = qimage_to_pil(dialog.grab().toImage()).crop(tuple(box))
        sheet.paste(tile, (0, index * height))
        if index + 1 < len(dialog.radios):
            QTest.keyClick(radio, Qt.Key_Down)
    sheet.save(output)


def capture_shutdown_combo(dialog, component, metadata, output, app):
    combo = dialog.combo
    assert dialog.focusWidget() is combo
    if component.startswith("shutdown-dropdown"):
        QTest.keyClick(combo, Qt.Key_Down, Qt.AltModifier)
        app.processEvents()
        popup = combo.view().window()
        assert popup.isVisible()
        if component != "shutdown-dropdown":
            row = metadata["highlighted_rows"].index(component.removeprefix("shutdown-dropdown-"))
            QTest.keyClick(combo.view(), Qt.Key_Home)
            for _ in range(row):
                QTest.keyClick(combo.view(), Qt.Key_Down)
            assert combo.view().currentIndex().row() == row
            app.processEvents()
        assert popup.grab().save(output)
        combo.hidePopup()
        return

    left, top, right, bottom = metadata["choice_crop"]
    width, height = right - left, bottom - top
    sheet = Image.new("RGB", (width, combo.count() * height))
    descriptions = set()
    QTest.keyClick(combo, Qt.Key_Home)
    for index in range(combo.count()):
        assert combo.currentIndex() == index
        assert dialog.description.text() not in descriptions
        descriptions.add(dialog.description.text())
        tile = qimage_to_pil(dialog.grab().toImage()).crop((left, top, right, bottom))
        sheet.paste(tile, (0, index * height))
        if index + 1 < combo.count():
            QTest.keyClick(combo, Qt.Key_Down)
    sheet.save(output)


def capture_shutdown(app, metadata, component, output, scale):
    import chicago95ui

    look = metadata["look"]
    # The classic dialogs draw their own frame. The Aero comparison is the Qt client area.
    if look in ("1995", "1998", "2000", "2001"):
        chicago95ui.DECORATION = build_theme(Path(output).with_name("aurorae"), look)
    if metadata.get("shutdown_flat_title"):
        with Path(chicago95ui.KDEGLOBALS).open("a") as scheme:
            scheme.write("\n[WM]\nactiveBlend=0,0,128\n")
    branding = metadata["shutdown_os_name"]
    combo = metadata.get("shutdown_combo_states", {})
    if "user" in combo:
        os.environ["LOGNAME"] = combo["user"]
    flag = REPO / "luna/images/windows-xp-flag.svg" if look in ("2001", "luna", "aero") else ""
    with Path(chicago95ui.CHICAGO95RC).open("a") as config:
        config.write(f"\n[Branding]\nosCompany=Microsoft\nosName={branding}\nosEdition=Professional\nosLogo={flag}\n")
    shutdown = load_script("chicago95-shutdown")
    if "sleep_actions" in combo:
        actions = {getattr(shutdown, name) for name in combo["sleep_actions"]}
        shutdown.sleep_action_available = lambda action: action in actions
    dialog = shutdown.screenshot_dialog(False, include_optional_radio=metadata.get("shutdown_optional_radio"))
    try:
        dialog.show()
        app.processEvents()
        assert dialog.devicePixelRatioF() == scale
        if component == "shutdown-button-states":
            capture_shutdown_buttons(
                dialog, metadata["shutdown_button_crops"], output, metadata.get("shutdown_button_hover_settle_ms", 0)
            )
            return
        if component == "shutdown-button-hover":
            capture_shutdown_button_hover(dialog, metadata["shutdown_hover_sample"], output)
            return
        if component == "shutdown-radio-states":
            capture_shutdown_radio_states(dialog, metadata["shutdown_radio_states"]["crop"], output)
            return
        if component.startswith("shutdown-dropdown") or component == "shutdown-choices":
            capture_shutdown_combo(dialog, component, metadata["shutdown_combo_states"], output, app)
            return
        shot = dialog.grab()
        assert shot.devicePixelRatio() == scale
        assert shot.save(output)
    finally:
        dialog.close()


def render(manifest, component, output, width, height, scale_override=None):
    import chicago95ui

    metadata = json.loads(Path(manifest).read_text())
    look = metadata["look"]
    hover = component == "control-panel-hover"
    hover_exit = component == "control-panel-hover-exit"
    picker = component.startswith("display-resolution-picker-")
    scale_key = "shutdown_scale" if component.startswith("shutdown") else "properties_scale"
    if hover or component == "control-panel-category-press":
        scale_key = "control_panel_hover_scale"
    scale = float(scale_override) if scale_override is not None else metadata[scale_key]
    os.environ["QT_SCALE_FACTOR"] = str(scale)
    app = chicago95ui.make_app("Control Panel")
    context = aero_style(app) if look == "aero" else themed(app, look)
    with context:
        if look == "aero":
            chicago95ui.apply_style(app)
            QIcon.setThemeName("Windows-7-SVG")
        if component.startswith("shutdown"):
            capture_shutdown(app, metadata, component, output, scale)
            return
        if component.startswith("run-history-"):
            history = json.loads((Path(manifest).parent / "run/history.json").read_text())["entries"]
            dialog = load_script("chicago95-run").RunDialog({"style": look, "osName": "Windows"}, [], [], history)
            try:
                dialog.show()
                app.processEvents()
                field = dialog.field
                QTest.keyClick(field.lineEdit(), Qt.Key_Down, Qt.AltModifier)
                app.processEvents()
                view = field.view()
                assert view.isVisible()
                if component.endswith("-down"):
                    QTest.keyClick(view, Qt.Key_Down)
                    app.processEvents()
                    assert field.lineEdit().selectedText() == history[1]
                assert view.window().grab().save(output)
                field.hidePopup()
            finally:
                dialog.close()
            return
        if component.startswith("run-"):
            chicago95ui.DECORATION = build_theme(Path(output).with_name("aurorae"), look)
            run_states = metadata["run_states"]
            if run_states.get("flat_title"):
                with Path(chicago95ui.KDEGLOBALS).open("a") as scheme:
                    scheme.write("\n[WM]\nactiveBlend=0,0,128\n")
            text = run_states["text"][component.removeprefix("run-")]
            dialog = load_script("chicago95-run").RunDialog({"style": look, "osName": "Windows"}, [], [], [])
            try:
                dialog.show()
                app.processEvents()
                if text:
                    QTest.keyClicks(dialog.field.lineEdit(), text)
                assert dialog.buttons["OK"].isEnabled() == bool(text)
                assert dialog.grab().save(output)
            finally:
                dialog.close()
            return
        panel = load_script("chicago95-control-panel")
        resolution = metadata["display_resolution"]
        sizes = list(dict.fromkeys(("640x480", "800x600", "1024x768", resolution)))
        if picker:
            resolution = metadata["display_resolution_picker"]["current"]
            sizes = metadata["display_resolution_picker"]["modes"]
        monitor = (
            "Generic Non-PnP Monitor"
            if look == "aero"
            else "Default Monitor on Cirrus Logic 5446 Compatible Graphics Adapter"
        )
        screen = panel.Screen(monitor, resolution, sizes, dict(zip(sizes, range(len(sizes)), strict=True)))
        actions = panel.Actions(
            current_screen=lambda: screen,
            list_screensavers=lambda: [],
            wallpapers=lambda: [],
            display_depth=lambda _output: 16 if metadata.get("properties_rgb565") else 32,
        )
        settings = Path(output).with_name("look.conf")
        panel.write_settings(settings, {**panel.LOOK_PRESETS[look], "LOOK": look})
        window = panel.ControlPanel(settings_path=settings, actions=actions)
        try:
            if hover:
                capture_hover(window, output)
                return
            if hover_exit:
                window.resize(round(int(width) / scale), round(int(height) / scale))
                capture_hover_exit(window, output, scale)
                return
            if component == "control-panel-category-press":
                capture_category_press(window, output)
                return
            if component in ("control-panel", "control-panel-end", "control-panel-selection", "control-panel-category"):
                window.resize(round(int(width) / scale), round(int(height) / scale))
                window.show()
                target = window
                if component == "control-panel-end":
                    window.icon_view.setFocus()
                    app.processEvents()
                    QTest.keyClick(window.icon_view, Qt.Key_End)
                    selected = metadata["control_panel_end"]
                    wanted = selected if isinstance(selected, str) else "System"
                    current = window.icon_view.currentItem()
                    actual = current.data(Qt.UserRole).name if current else None
                    assert actual == wanted, f"End selected {actual!r}, expected {wanted!r}"
                elif component == "control-panel-category":
                    app.processEvents()
                    QTest.mouseClick(window.sidebar.view_link, Qt.LeftButton)
                    assert window.xp_views.currentWidget() is window.xp_category_view
                elif component == "control-panel-selection":
                    app.processEvents()
                    selection = metadata["control_panel_selection"]
                    view = window.icon_view
                    item, = view.findItems(selection, Qt.MatchExactly)
                    QTest.mouseClick(view.viewport(), Qt.LeftButton, pos=view.visualItemRect(item).center())
                    assert item.isSelected()
            elif look == "aero":
                window.show()
                window.open_applet("Display")
                target = window.screen_resolution
                if picker:
                    app.processEvents()
                    target.resolutions.setFocus()
                    QTest.keyClick(target.resolutions, Qt.Key_Down, Qt.AltModifier)
                    app.processEvents()
                    popup = app.activePopupWidget()
                    assert popup and popup.isVisible()
                    if component.endswith("-up"):
                        QTest.keyClick(popup.focusWidget() or popup, Qt.Key_Up)
                        app.processEvents()
                    elif component.endswith("-click"):
                        mode = metadata["display_resolution_picker"]["click_mode"]
                        label = next(button for button in popup.findChildren(QToolButton) if button.text() == mode)
                        QTest.mouseClick(label, Qt.LeftButton)
                        app.processEvents()
                        assert popup.isVisible()
                    assert popup.grab().save(output)
                    popup.close()
                    return
                # The VM's Explorer window is resizable. Reproduce the captured client viewport.
                app.processEvents()
                window.resize(round(int(width) / scale), round(int(height) / scale) + window.header.height())
            else:
                window.open_applet("Display")
                target = window.applet_windows["Display"]
                tabs = target.page.tabs
                tabs.setCurrentIndex(target.page.tab_names().index(metadata["display_page"]))
            app.processEvents()
            shot = target.grab()
            assert shot.devicePixelRatio() == scale
            assert shot.save(output)
            if component == "display-properties" and look != "aero":
                selected = tabs.currentIndex()
                area = tabs.widget(selected)
                assert area.horizontalScrollBar().maximum() == area.verticalScrollBar().maximum() == 0
                if isinstance(tabs, QTabWidget):
                    bar = tabs.tabBar()
                    assert bar.rect().contains(bar.tabRect(selected))
                else:
                    assert tabs.bar.rect().contains(tabs.bar.tab_rects()[selected])
        finally:
            for sheet in window.applet_windows.values():
                sheet.close()
            window.close()


if __name__ == "__main__":
    render(*sys.argv[1:])
