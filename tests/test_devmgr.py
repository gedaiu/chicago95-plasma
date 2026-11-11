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
                            "claimed": True,
                            "configuration": {"driver": "nvme"},
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
        [("Provider:", "Linux kernel"), ("Driver:", "r8169"), ("Device:", "enp5s0")],
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
    ) == (["General", "Driver", "Resources"], "Mystery Chip Properties", True, 1)


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
