"""bin/chicago95-devmgr: lshw's inventory sorted into the classic Device Manager's classes, shown by type or by
connection, with a read-only property sheet per device (General, Driver, Resources from sysfs)."""

import pytest
from conftest import REPO, load_script

INVENTORY = {
    "id": "box",
    "class": "system",
    "product": "Workstation",
    "children": [
        {
            "id": "core",
            "class": "bus",
            "description": "Motherboard",
            "claimed": True,
            "children": [
                {"id": "memory", "class": "memory", "description": "System memory"},
                {"id": "cpu", "class": "processor", "product": "Ryzen 9", "vendor": "AMD", "version": "2"},
                {
                    "id": "pci",
                    "class": "bridge",
                    "product": "Root Complex",
                    "vendor": "AMD",
                    "claimed": True,
                    "children": [
                        {
                            "id": "display",
                            "class": "display",
                            "product": "Arc B580",
                            "vendor": "Intel",
                            "version": "01",
                            "businfo": "pci@0000:03:00.0",
                            "claimed": True,
                            "configuration": {"driver": "xe"},
                        },
                        {
                            "id": "network",
                            "class": "network",
                            "product": "RTL8125 2.5GbE Controller",
                            "vendor": "Realtek",
                            "businfo": "pci@0000:05:00.0",
                            "logicalname": "enp5s0",
                            "claimed": True,
                            "configuration": {"driver": "r8169"},
                        },
                        {
                            "id": "nvme",
                            "class": "storage",
                            "product": "SSD 980 PRO",
                            "vendor": "Samsung",
                            "businfo": "pci@0000:07:00.0",
                            "serial": "S5GXNG0N",
                            "size": 1000204886016,
                            "clock": 33000000,
                            "claimed": True,
                            "configuration": {"driver": "nvme", "state": "live"},
                            "capabilities": {"nvme": True, "bus_master": "bus mastering"},
                            "children": [
                                {
                                    "id": "namespace:0",
                                    "class": "disk",
                                    "description": "NVMe disk",
                                    "logicalname": "/dev/nvme0n1",
                                    "claimed": True,
                                }
                            ],
                        },
                        {
                            "id": "cdrom",
                            "class": "disk",
                            "product": "DVD-RW DRU-880S",
                            "vendor": "Sony",
                            "claimed": True,
                        },
                        {"id": "generic", "class": "generic", "product": "Mystery Chip", "vendor": "Acme"},
                        {"id": "generic:1", "class": "generic", "product": "Granite Ridge IOMMU", "vendor": "AMD"},
                        {
                            "id": "multimedia",
                            "class": "multimedia",
                            "product": "HDA Controller",
                            "claimed": True,
                            "configuration": {"driver": "snd_hda_intel"},
                        },
                        {
                            "id": "usb",
                            "class": "bus",
                            "product": "USB 3.2 Controller",
                            "claimed": True,
                            "configuration": {"driver": "xhci_hcd"},
                        },
                    ],
                },
            ],
        },
        {
            "id": "input:0",
            "class": "input",
            "product": "Razer Orochi V2",
            "logicalname": ["input/event2", "input/mouse0"],
            "claimed": True,
        },
        {"id": "input:1", "class": "input", "product": "8BitDo Retro Keyboard", "claimed": True},
        {"id": "input:2", "class": "input", "product": "Power Button", "claimed": True},
        {"id": "input:3", "class": "input", "product": "HDA Intel PCH HDMI/DP,pcm=3", "claimed": True},
        {"id": "input:4", "class": "input", "product": "MSI MYSTIC LIGHT", "claimed": True},
    ],
}


@pytest.fixture(scope="session")
def devmgr():
    return load_script("chicago95-devmgr")


@pytest.fixture
def snapshot(devmgr):
    return devmgr.snapshot_from(INVENTORY)


def names(devices):
    return [device.name for device in devices]


def test_devices_are_sorted_into_the_classic_classes_in_their_order(devmgr, snapshot):
    grouped = devmgr.by_type(snapshot.devices)

    assert {category: names(members) for category, members in grouped.items()} == {
        "CDROM": ["DVD-RW DRU-880S"],
        "Disk drives": ["NVMe disk"],
        "Display adapters": ["Arc B580"],
        "Hard disk controllers": ["SSD 980 PRO"],
        "Human Interface Devices": ["MSI MYSTIC LIGHT"],
        "Keyboard": ["8BitDo Retro Keyboard"],
        "Mouse": ["Razer Orochi V2"],
        "Network adapters": ["RTL8125 2.5GbE Controller"],
        "Other devices": ["Mystery Chip"],
        "Sound, video and game controllers": ["HDA Controller"],
        "System devices": ["Granite Ridge IOMMU", "Motherboard", "Power Button", "Root Complex", "Ryzen 9"],
        "Universal Serial Bus controllers": ["USB 3.2 Controller"],
    }
    assert list(grouped) == [category for category in devmgr.CATEGORIES if category in grouped]


def test_memory_and_audio_jacks_are_left_out_as_the_original_never_listed_them(devmgr, snapshot):
    assert [name for name in names(snapshot.devices) if "memory" in name.lower() or "pcm" in name] == []


def test_a_device_without_a_driver_reports_code_28_and_the_others_work_properly(devmgr, snapshot):
    by_name = {device.name: device for device in snapshot.devices}

    assert (by_name["Mystery Chip"].status, by_name["Arc B580"].status, by_name["Mystery Chip"].working) == (
        devmgr.NO_DRIVER,
        devmgr.WORKING,
        False,
    )


def test_by_connection_keeps_lshws_nesting_under_the_computer(devmgr, snapshot):
    motherboard = snapshot.computer.children[0]
    root_complex = motherboard.children[1]

    assert (
        snapshot.computer.name,
        names(motherboard.children),
        names(root_complex.children)[:3],
        names(root_complex.children[2].children),
    ) == (
        "Workstation",
        ["Ryzen 9", "Root Complex"],
        ["Arc B580", "RTL8125 2.5GbE Controller", "SSD 980 PRO"],
        ["NVMe disk"],
    )


def test_general_and_driver_fields_name_the_class_maker_version_and_kernel_driver(devmgr, snapshot):
    network = next(device for device in snapshot.devices if device.kind == "network")

    assert (devmgr.general_fields(network), devmgr.driver_fields(network)) == (
        [("Device type:", "Network adapters"), ("Manufacturer:", "Realtek"), ("Hardware version:", "Not available")],
        [
            ("Provider:", "Linux kernel"),
            ("Driver:", "r8169"),
            ("Device:", "enp5s0"),
            ("Serial number:", "Not available"),
        ],
    )


def test_pci_resources_come_from_sysfs_as_interrupt_memory_and_io_ranges(devmgr, tmp_path):
    device = tmp_path / "0000:07:00.0"
    device.mkdir()
    (device / "irq").write_text("24\n")
    (device / "resource").write_text(
        "0x00000000f2000000 0x00000000f2003fff 0x0000000000140204\n"
        "0x0000000000000000 0x0000000000000000 0x0000000000000000\n"
        "0x000000000000e000 0x000000000000e0ff 0x0000000000040101\n"
    )

    assert devmgr.pci_resources(device) == [
        ("Interrupt Request", "24"),
        ("Memory Range", "F2000000 - F2003FFF"),
        ("Input/Output Range", "E000 - E0FF"),
    ]


def test_resources_of_a_device_that_is_not_on_pci_are_none(devmgr, snapshot, tmp_path):
    keyboard = next(device for device in snapshot.devices if device.category == "Keyboard")

    assert (devmgr.pci_address("pci@0000:07:00.0"), devmgr.resources_of(keyboard, tmp_path)) == ("0000:07:00.0", [])


def test_the_window_lists_the_classes_under_the_computer_and_enables_properties_for_a_device(devmgr, snapshot, qt_app):
    window = devmgr.DeviceManagerWindow(load=lambda: snapshot)
    window.refresh()
    before = window.properties_button.isEnabled()
    display = window.tree.topLevelItem(0).child(2)
    window.tree.setCurrentItem(display)
    on_class = window.properties_button.isEnabled()
    window.tree.setCurrentItem(display.child(0))

    assert (
        window.item_texts()[:4],
        before,
        on_class,
        window.properties_button.isEnabled(),
        window.status_label.text(),
    ) == (
        ["Workstation", "  CDROM", "    DVD-RW DRU-880S", "  Disk drives"],
        False,
        False,
        True,
        "16 devices, 1 without a driver",
    )


def test_the_class_with_a_broken_device_starts_expanded(devmgr, snapshot, qt_app):
    window = devmgr.DeviceManagerWindow(load=lambda: snapshot)
    window.refresh()
    root = window.tree.topLevelItem(0)
    expanded = {root.child(index).text(0): root.child(index).isExpanded() for index in range(root.childCount())}

    assert (expanded["Other devices"], expanded["Display adapters"]) == (True, False)


def test_by_connection_view_nests_the_devices_as_lshw_found_them(devmgr, snapshot, qt_app):
    window = devmgr.DeviceManagerWindow(load=lambda: snapshot)
    window.refresh()
    window.by_connection_radio.setChecked(True)

    assert window.item_texts()[:5] == [
        "Workstation",
        "  Motherboard",
        "    Ryzen 9",
        "    Root Complex",
        "      Arc B580",
    ]


def test_the_property_sheet_has_the_originals_three_pages_and_shows_the_status(devmgr, snapshot, qt_app, tmp_path):
    device = next(device for device in snapshot.devices if device.name == "Mystery Chip")
    dialog = devmgr.PropertiesDialog(device, devmgr.themed_icon("dialog-question"), sysfs_root=tmp_path)
    from PySide6.QtWidgets import QLabel

    texts = [label.text() for label in dialog.findChildren(QLabel)]

    assert (
        [dialog.tabs.tabText(index) for index in range(dialog.tabs.count())],
        dialog.windowTitle(),
        devmgr.NO_DRIVER in texts,
        dialog.resources.topLevelItemCount(),
    ) == (["General", "Driver", "Resources", "Details"], "Mystery Chip Properties", True, 1)


def test_a_failing_lshw_leaves_an_empty_computer_with_the_reason(devmgr):
    def failing(*_arguments, **_options):
        raise OSError("not found")

    snapshot = devmgr.load_snapshot(run=failing)

    assert (snapshot.devices, snapshot.computer.name, "lshw" in snapshot.error) == ([], "Computer", True)


def test_the_kubernetes_viewer_is_the_old_tool_under_its_own_name():
    source = (REPO / "bin/chicago95-k8sview").read_text()
    steps = (REPO / "setup/steps.sh").read_text()

    assert (
        'setWindowTitle("Kubernetes Viewer")' in source,
        "KubernetesViewerWindow" in source,
        "devmgr k8sview" in steps,
    ) == (
        True,
        True,
        True,
    )


def test_the_details_page_lists_every_fact_lshw_gave_with_readable_sizes(devmgr, snapshot, qt_app, tmp_path):
    controller = next(device for device in snapshot.devices if device.name == "SSD 980 PRO")
    dialog = devmgr.PropertiesDialog(controller, devmgr.themed_icon("drive-harddisk"), sysfs_root=tmp_path)
    rows = {
        dialog.details.topLevelItem(index).text(0): dialog.details.topLevelItem(index).text(1)
        for index in range(dialog.details.topLevelItemCount())
    }

    assert (
        [dialog.tabs.tabText(index) for index in range(dialog.tabs.count())],
        rows["Serial number"],
        rows["Size"],
        rows["Clock"],
        rows["Configuration: state"],
        rows["Capability: bus_master"],
        rows["Capability: nvme"],
        rows["Driver"],
    ) == (
        ["General", "Driver", "Resources", "Details"],
        "S5GXNG0N",
        "932 GB",
        "33 MHz",
        "live",
        "bus mastering",
        "nvme",
        "nvme",
    )


def test_the_driver_page_shows_the_serial_number_when_lshw_knows_it(devmgr, snapshot):
    controller = next(device for device in snapshot.devices if device.name == "SSD 980 PRO")

    assert devmgr.driver_fields(controller)[-1] == ("Serial number:", "S5GXNG0N")


@pytest.mark.parametrize("width", [420, 740])
def test_aero_commands_stay_above_tree_when_resized(devmgr, snapshot, qt_app, monkeypatch, width):
    from PySide6.QtCore import QPoint
    from PySide6.QtWidgets import QPushButton, QToolBar

    monkeypatch.setattr(devmgr.chicago95ui, "widget_style", lambda: "aero")
    window = devmgr.DeviceManagerWindow(load=lambda: snapshot)
    try:
        window.resize(width, 480)
        window.show()
        window.refresh()
        toolbar = window.findChild(QToolBar)
        props, scan = window.properties_button, window.scan_action
        commands = [a for a in toolbar.actions() if not a.isSeparator()]
        assert not window.findChildren(QPushButton)
        assert [action.text() for action in commands] == [
            "Back",
            "Forward",
            "Console tree",
            "Device Manager Help",
            "Action pane",
            "Scan for hardware changes",
        ]
        centres = [toolbar.actionGeometry(a).center().x() for a in commands]
        assert centres == pytest.approx([12, 35, 67, 98, 121, 151], abs=4)
        assert toolbar.geometry().bottom() < window.tree.mapTo(window, QPoint()).y()
        assert window.height() - window.tree.mapTo(window, window.tree.rect().bottomRight()).y() < 32
        # Selecting a device enables Back in place, as well as its Properties command.
        area = toolbar.actionGeometry(window.back)
        before = toolbar.grab(area).toImage()
        device = window.tree.topLevelItem(0).child(0).child(0)
        window.tree.setCurrentItem(device)
        qt_app.processEvents()
        assert props.isEnabled() and toolbar.grab(area).toImage() != before
        window.back.trigger()
        assert window.tree.currentItem() is window.tree.topLevelItem(0)
        window.forward.trigger()
        assert window.tree.currentItem() is device
        window.scope_action.trigger()
        assert window.scope_tree.isVisible()
        window.pane_action.trigger()
        assert window.pane_action.isChecked()
        window.by_connection_radio.trigger()
        assert window.item_texts()[1] == "  Motherboard"
        scan.trigger()
        assert window.snapshot is snapshot
    finally:
        window.close()


@pytest.mark.parametrize(("style", "art"), [("aero", "aero"), ("luna", "luna"), ("2001", "2000"), ("2000", "2000")])
@pytest.mark.parametrize("scale", [1.5, 2.0])
def test_disabled_console_arrows_render_at_display_resolution(devmgr, snapshot, qt_app, style, art, scale):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QIcon, QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer
    from PySide6.QtWidgets import QToolBar
    from reference import installed_look

    widgets = "classic" if style in ("2000", "2001") else style
    with installed_look(qt_app, f"[StartMenu]\nstyle={style}\n[Look]\nwidgetStyle={widgets}\n", ""):
        window = devmgr.DeviceManagerWindow(load=lambda: snapshot)
        try:
            window.refresh()
            size = window.findChild(QToolBar).iconSize()
            for direction in ("back", "forward"):
                action = getattr(window, direction)
                assert not action.isEnabled()
                physical = action.icon().pixmap(size, scale, QIcon.Disabled)
                assert physical.size() == size * scale
                actual = physical.toImage().convertToFormat(QImage.Format_ARGB32_Premultiplied)
                expected = QImage(actual.size(), actual.format())
                expected.fill(Qt.transparent)
                painter = QPainter(expected)
                QSvgRenderer(str(REPO / f"data/device-manager/{art}-{direction}-disabled.svg")).render(painter)
                painter.end()
                assert bytes(actual.constBits()) == bytes(expected.constBits())
        finally:
            window.close()


@pytest.mark.parametrize(
    ("scale", "limits"),
    [(1.0, (9, 10, 2, 11, 2, 14)), (1.5, (11, 12, 14, 16, 14, 17)), (2.0, (11, 11, 9, 14, 9, 16))],
)
def test_enabled_mmc_commands_match_guest_resources(devmgr, snapshot, qt_app, monkeypatch, scale, limits):
    import numpy as np
    from PIL import Image
    from PySide6.QtGui import QImage
    from PySide6.QtWidgets import QToolBar

    monkeypatch.setattr(devmgr.chicago95ui, "widget_style", lambda: "aero")
    window = devmgr.DeviceManagerWindow(load=lambda: snapshot)
    try:
        toolbar = window.findChild(QToolBar)
        actions = [action for action in toolbar.actions() if not action.isSeparator()]
        with Image.open(REPO / "tests/references/win7-sp1-mmc-commands.png") as strip:
            for index, (action, limit) in enumerate(zip(actions, limits, strict=True)):
                glyph = (
                    action.icon().pixmap(toolbar.iconSize(), scale).toImage().convertToFormat(QImage.Format_RGBA8888)
                )
                assert glyph.width() == glyph.height() == round(16 * scale)
                actual = Image.frombytes("RGBA", (glyph.width(), glyph.height()), bytes(glyph.constBits()))
                native = strip.crop((index * 16, 0, (index + 1) * 16, 16))
                for colour in ("#d3daed", "#25364a"):
                    # Two backgrounds expose missing transparency at the silhouette as well as errors inside it.
                    pixels = Image.alpha_composite(Image.new("RGBA", actual.size, colour), actual)
                    pixels = pixels.convert("RGB").resize(native.size, Image.Resampling.LANCZOS)
                    expected = Image.alpha_composite(Image.new("RGBA", native.size, colour), native).convert("RGB")
                    delta = np.abs(np.asarray(pixels, dtype=int) - np.asarray(expected, dtype=int))
                    assert delta.mean() < limit, (action.text(), colour)
    finally:
        window.close()


@pytest.mark.parametrize(("style", "client"), [("basic", (14, 30)), ("aero", (80, 72))])
def test_aero_console_bands_match_win7_sp1(
    devmgr, snapshot, qt_app, monkeypatch, tmp_path, style, client, exact_original
):
    import numpy as np
    from PIL import Image

    monkeypatch.setattr(devmgr.chicago95ui, "widget_style", lambda: "aero")
    window = devmgr.DeviceManagerWindow(load=lambda: snapshot)
    try:
        window.resize(782, 521)
        window.show()
        window.refresh()
        qt_app.processEvents()
        capture = tmp_path / "device-manager.png"
        assert window.grab().save(str(capture))
        reference = REPO / f"tests/references/win7-sp1-{style}-device-manager.png"
        with Image.open(capture) as surface, Image.open(reference) as original:
            # Sample both complete command bands clear of the commands.
            x, y = client
            actual = np.asarray(surface.convert("RGB").crop((300, 0, 350, 46)), dtype=int)
            expected = np.asarray(original.convert("RGB").crop((x + 300, y, x + 350, y + 46)), dtype=int)
            assert np.abs(actual - expected).mean() < 3
            # A continuous white tree extends to the status bar, including across the former buttons.
            for picture, left, top in [(surface, 0, 0), (original, x, y)]:
                band = picture.convert("RGB").crop((left + 80, top + 460, left + 700, top + 490))
                assert band.getextrema() == ((255, 255),) * 3
            expected_icons = original.convert("RGB").crop((x, y + 23, x + 170, y + 46))
            icons = surface.convert("RGB").crop((0, 23, 170, 46))
            difference = np.abs(np.asarray(icons, dtype=int) - np.asarray(expected_icons, dtype=int))
            assert difference.mean() < (4.5 if style == "aero" else 7)
            # These guest positions include the antialiased command edges and surrounding face.
            commands = [(2, 22, 7), (25, 45, 7.5), (56, 76, 1.5), (88, 105, 10), (110, 130, 1.5)]
            if style == "aero":
                commands.append((141, 161, 10))  # Scan is visible in the Aero reference.
            for left, right, limit in commands:
                assert difference[2:21, left:right].mean() < limit, (left, right)
            exact_original(expected_icons, icons)
    finally:
        window.close()


@pytest.mark.parametrize(("style", "capture"), [("luna", "xp-sp3"), ("2001", "xp-sp3-classic")])
def test_xp_console_matches_sp3_command_bands(devmgr, snapshot, qt_app, style, capture):
    import numpy as np
    from PIL import Image
    from PySide6.QtWidgets import QPushButton, QToolBar
    from reference import qimage_to_pil
    from showcase import themed

    def glyph_bounds(image, left, right, colour):
        pixels = np.asarray(image.convert("RGB").crop((left, 24, right, 45)), dtype=int)
        r, g, b = pixels.transpose(2, 0, 1)
        mask = (b > 80) & (r < 45) & (g < 45) if colour == "navy" else (r > 160) & (g > 160) & (b < 70)
        ys, xs = np.where(mask)
        assert len(xs) > 0
        return xs.min(), ys.min(), xs.max(), ys.max()

    with themed(qt_app, style):
        window = devmgr.DeviceManagerWindow(load=lambda: snapshot)
        try:
            window.show()
            window.refresh()
            qt_app.processEvents()
            assert not window.findChildren(QPushButton)
            commands = window.findChild(QToolBar).actions()
            assert [action.text() for action in commands if not action.isSeparator()] == [
                "Back",
                "Forward",
                "Console tree",
                "Device Manager Help",
                "Action pane",
            ]
            # Compare both bands including their one-pixel seam, clear of icons and labels.
            box = (280, 0, 550, 48 if style == "2001" else 46)
            rendered = qimage_to_pil(window.grab().toImage())
            with Image.open(REPO / f"tests/references/{capture}-device-manager-bands.png") as native:
                # Disabled navigation uses the guest's embossed glyph and theme-specific palette.
                top = 26 if style == "2001" else 25
                for left in (2, 25):
                    arrow = (left, top, left + 20, top + 20)
                    actual = np.asarray(rendered.convert("RGB").crop(arrow), dtype=int)
                    expected = np.asarray(native.convert("RGB").crop(arrow), dtype=int)
                    assert np.abs(actual - expected).mean() < (3.5 if style == "2001" else 2)
                band = (200, 23, 620, 46)
                actual = np.asarray(rendered.convert("RGB").crop(band), dtype=int)
                expected = np.asarray(native.convert("RGB").crop(band), dtype=int)
                assert np.abs(actual - expected).mean() < 1.2
                # Check native centres and the glyphs: navy pane borders and the yellow Help mark.
                for left, right, colour in [(56, 77, "navy"), (87, 109, "yellow"), (111, 132, "navy")]:
                    assert glyph_bounds(rendered, left, right, colour) == pytest.approx(
                        glyph_bounds(native, left, right, colour), abs=2
                    )
                for left, right in ((56, 77), (111, 132)):
                    x, y, x2, y2 = glyph_bounds(native, left, right, "navy")
                    region = (left + x, 24 + y, left + x2 + 1, 24 + y2 + 1)
                    expected = np.asarray(native.convert("RGB").crop(region), dtype=int)
                    actual = np.asarray(rendered.convert("RGB").crop(region), dtype=int)
                    assert expected.shape == (12, 14, 3)
                    assert np.abs(actual - expected).mean() < 3
                help_y = 28 if style == "2001" else 27
                help_box = (91, help_y, 105, help_y + 15)
                expected_help = np.asarray(native.convert("RGB").crop(help_box), dtype=int)
                actual_help = np.asarray(rendered.convert("RGB").crop(help_box), dtype=int)
                assert np.abs(actual_help - expected_help).mean() < (9 if style == "2001" else 9.8)
                original = np.asarray(native.convert("RGB").crop(box), dtype=int)
            actual = np.asarray(rendered.crop(box), dtype=int)
            assert np.abs(actual - original).mean() < 4
        finally:
            window.close()


@pytest.mark.parametrize("width", [420, 720])
@pytest.mark.parametrize("capture", ["win95-osr2-device-actions", "win98-se-device-actions"])
def test_classic_device_action_row_matches_guest(devmgr, snapshot, qt_app, width, capture):
    from PIL import Image
    from reference import qimage_to_pil

    window = devmgr.DeviceManagerWindow(load=lambda: snapshot)
    try:
        window.resize(width, 480)
        window.show()
        qt_app.processEvents()
        first = window.properties_button.geometry()
        assert first.left() == window.layout().contentsMargins().left()
        with Image.open(REPO / f"tests/references/{capture}.png") as original:
            y = first.bottom()
            actual = qimage_to_pil(window.grab().toImage()).crop((first.x(), y, first.x() + original.width, y + 1))
            # The dark bottom bevel spans exactly the button width and leaves each gap visible.
            expected = original.crop((0, original.height - 1, original.width, original.height))
            assert (
                actual.convert("L").point(lambda v: v < 64).tobytes()
                == expected.convert("L").point(lambda v: v < 64).tobytes()
            )
    finally:
        window.close()


def test_windows_2000_console_combines_menus_and_commands(devmgr, snapshot, qt_app, tmp_path):
    import os
    import subprocess

    import numpy as np
    from PIL import Image
    from PySide6.QtWidgets import QMenuBar, QToolBar
    from reference import LOOK_2000_KDEGLOBALS, rgb565, screenshot
    from showcase import themed

    with themed(qt_app, "2000"):
        window = devmgr.DeviceManagerWindow(load=lambda: snapshot)
        window.refresh()
        menus = window.findChild(QMenuBar)
        toolbar = window.findChild(QToolBar)
        assert [a.text() for a in menus.actions()] == ["&Action", "&View"]
        assert menus.y() == toolbar.y()
        assert [a.text() for a in toolbar.actions() if not a.isSeparator()] == [
            "Back",
            "Forward",
            "Up one level",
            "Console tree",
            "Device Manager Help",
        ]
        root = window.tree.topLevelItem(0)
        window.tree.setCurrentItem(root.child(0))
        assert window.up.isEnabled()
        window.up.trigger()
        assert window.tree.currentItem() == root
        window.close()
    # Run the installed entry point at the guest's physical scale.
    (tmp_path / "chicago95rc").write_text("[StartMenu]\nstyle=2000\n[Look]\nwidgetStyle=classic\nbevel=2000\n")
    (tmp_path / "kdeglobals").write_text(LOOK_2000_KDEGLOBALS)
    capture = tmp_path / "console.png"
    subprocess.run(
        [REPO / "bin/chicago95-devmgr", "--screenshot", capture],
        check=True,
        env={**os.environ, "XDG_CONFIG_HOME": str(tmp_path), "QT_QPA_PLATFORM": "offscreen", "QT_SCALE_FACTOR": "1.25"},
    )
    original = screenshot("win2000-pro-120dpi-device-manager-band")
    with Image.open(capture) as live:
        actual = rgb565(live)
    # Compare each command at its guest position, including the surrounding face.
    for left, right, limit in ((124, 146, 3), (147, 168, 3.5), (179, 200, 5), (201, 222, 1.5), (232, 253, 4.5)):
        box = (left, 2, right, 23)
        pixels = np.asarray(actual.crop(box), dtype=int)
        native = np.asarray(original.crop(box), dtype=int)
        assert np.abs(pixels - native).mean() < limit, box
    # Match the menu text baseline despite different font antialiasing.
    for left, right in ((12, 64), (65, 108)):
        bounds = []
        for image in (original, actual):
            ink = np.asarray(image.crop((left, 1, right, 24)))[:, :, :3].max(axis=2) < 140
            y, x = np.nonzero(ink)
            bounds.append((x.min(), y.min(), y.max()))
        assert bounds[1] == pytest.approx(bounds[0], abs=1)
    # The outer bevels bound a single 25-row band. Sample clear of commands.
    band = (290, 0, 500, original.height)
    assert np.abs(np.asarray(actual.crop(band), dtype=int) - np.asarray(original.crop(band), dtype=int)).mean() < 1.7
