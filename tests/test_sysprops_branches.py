import os
import platform
import pwd
import shlex
import socket
import stat
import sys
from pathlib import Path

import pytest
from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtGui import QFontMetrics
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

MEMINFO = "MemTotal: 16384000 kB\nMemFree: 1000000 kB\nMemAvailable: 4096000 kB\nSwapTotal: 8388608 kB\n"
KSCREEN_OUTPUT = "\x1b[01;32mOutput: \x1b[0m1 eDP-1\n\tGeometry: 0,0 1920x1080\n\tScale: 1.5\n"


@pytest.fixture(scope="module")
def sysprops():
    from conftest import load_script

    return load_script("chicago95-sysprops")


@pytest.fixture
def commands_on_path(tmp_path, monkeypatch):
    bin_directory = tmp_path / "bin"
    bin_directory.mkdir()
    monkeypatch.setenv("PATH", str(bin_directory))
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-test")  # a compositor to ask; without one nothing is run

    def install(name, output):
        script = bin_directory / name
        script.write_text(f"#!/bin/sh\nprintf '%s\\n' {shlex.quote(output)}\n")
        script.chmod(script.stat().st_mode | stat.S_IEXEC)

    return install


@pytest.fixture
def redirect_files(sysprops, tmp_path, monkeypatch):
    redirects = {}
    real_path = Path

    def redirected_path(path):
        return real_path(redirects.get(str(path), path))

    redirected_path.home = real_path.home
    monkeypatch.setattr(sysprops, "Path", redirected_path)

    def redirect(system_path, text):
        replacement = tmp_path / system_path.strip("/").replace("/", "_")
        replacement.write_text(text)
        redirects[system_path] = str(replacement)

    return redirect


def test_run_output_returns_the_command_output(sysprops):
    assert sysprops.run_output(["echo", "hello"]) == "hello\n"


def test_run_output_is_empty_when_the_command_is_not_installed(sysprops):
    assert sysprops.run_output(["chicago95-no-such-command"]) == ""


def test_run_output_is_empty_when_the_command_times_out(sysprops):
    assert sysprops.run_output(["sleep", "5"]) == ""


def test_run_output_hides_the_offscreen_platform_from_the_command(sysprops):
    assert sysprops.run_output(["sh", "-c", "echo [$QT_QPA_PLATFORM]"]) == "[]\n"


def test_strip_ansi_removes_colour_codes(sysprops):
    assert sysprops.strip_ansi("\x1b[01;32mgreen\x1b[0m text") == "green text"


def test_os_name_is_the_pretty_name_without_quotes(sysprops, redirect_files):
    redirect_files("/etc/os-release", 'NAME="Fedora Linux"\nPRETTY_NAME="Fedora Linux 44 (KDE Plasma)"\n')

    assert sysprops.read_os_name() == "Fedora Linux 44 (KDE Plasma)"


def test_os_name_is_the_system_name_when_os_release_has_no_pretty_name(sysprops, redirect_files):
    redirect_files("/etc/os-release", "NAME=Fedora\n")

    assert sysprops.read_os_name() == platform.system()


def test_kernel_is_linux_with_the_release(sysprops):
    assert sysprops.read_kernel() == "Linux " + platform.release()


def test_desktop_names_the_plasma_version_and_capitalised_session(sysprops, commands_on_path, monkeypatch):
    commands_on_path("plasmashell", "plasmashell 6.2.1")
    monkeypatch.setenv("XDG_SESSION_TYPE", "x11")

    assert sysprops.read_desktop() == "KDE Plasma 6.2 (X11)"


def test_desktop_defaults_to_plasma_6_on_wayland_when_nothing_is_known(sysprops, commands_on_path, monkeypatch):
    monkeypatch.delenv("XDG_SESSION_TYPE", raising=False)

    assert sysprops.read_desktop() == "KDE Plasma 6 (Wayland)"


def test_full_name_is_the_first_gecos_field_or_the_login(sysprops):
    entry = pwd.getpwuid(os.getuid())

    assert sysprops.read_full_name() == (entry.pw_gecos.split(",")[0].strip() or entry.pw_name)


def test_product_key_is_built_from_the_machine_id_digits(sysprops, redirect_files):
    redirect_files("/etc/machine-id", "0123456789abcdef0123456789abcdef\n")

    assert sysprops.read_product_key() == "15123-OEM-6607520-41709"


def test_cpu_model_is_the_lscpu_model_name(sysprops, commands_on_path):
    commands_on_path("lscpu", "Architecture: x86_64\nModel name:           AMD Ryzen 7  \nVendor ID: x")

    assert sysprops.read_cpu_model() == "AMD Ryzen 7"


def test_cpu_model_is_the_platform_processor_when_lscpu_is_missing(sysprops, commands_on_path):
    assert sysprops.read_cpu_model() == platform.processor()


def test_meminfo_maps_each_field_to_its_kib(sysprops, redirect_files):
    redirect_files("/proc/meminfo", MEMINFO)

    assert sysprops.read_meminfo() == {
        "MemTotal": 16384000,
        "MemFree": 1000000,
        "MemAvailable": 4096000,
        "SwapTotal": 8388608,
    }


def test_kib_to_gb_rounds_to_whole_gibibytes(sysprops):
    assert [sysprops.kib_to_gb(kib) for kib in (1048576, 1572864, 2097152, 1000)] == [1, 2, 2, 0]


def test_display_describes_a_scaled_screen_with_its_panel_size(sysprops, commands_on_path):
    commands_on_path("kscreen-doctor", KSCREEN_OUTPUT)

    assert sysprops.read_display() == "1920x1080 at 1.5x (2880x1620 panel)"


def test_display_omits_the_panel_when_the_scale_is_one(sysprops, commands_on_path):
    commands_on_path("kscreen-doctor", "Geometry: 0,0 1280x720\nScale: 1\n")

    assert sysprops.read_display() == "1280x720 at 1x"


def test_display_assumes_scale_one_when_none_is_reported(sysprops, commands_on_path):
    commands_on_path("kscreen-doctor", "Geometry: 0,0 1280x720\n")

    assert sysprops.read_display() == "1280x720 at 1x"


def test_display_is_unknown_without_a_compositor_and_kscreen_doctor_is_never_run(
    sysprops, commands_on_path, monkeypatch
):
    commands_on_path("kscreen-doctor", KSCREEN_OUTPUT)
    monkeypatch.delenv("WAYLAND_DISPLAY")
    monkeypatch.delenv("DISPLAY", raising=False)

    assert sysprops.read_display() == "Unknown display"


def test_display_is_unknown_when_kscreen_doctor_reports_no_geometry(sysprops, commands_on_path):
    commands_on_path("kscreen-doctor", "nothing here")

    assert sysprops.read_display() == "Unknown display"


def test_swap_description_mentions_zram_when_the_swap_table_lists_it(sysprops, redirect_files):
    redirect_files("/proc/swaps", "Filename Type Size\n/dev/zram0 partition 8388604 0 100\n")

    assert sysprops.read_swap_description(8388608) == "8 GB swap (zram)"


def test_swap_description_has_no_kind_for_a_disk_swap(sysprops, redirect_files):
    redirect_files("/proc/swaps", "Filename Type Size\n/dev/sda2 partition 4194300 0 -2\n")

    assert sysprops.read_swap_description(4194304) == "4 GB swap"


def test_root_filesystem_is_the_capitalised_type(sysprops, commands_on_path):
    commands_on_path("findmnt", "btrfs")

    assert sysprops.read_root_filesystem() == "Btrfs"


def test_root_filesystem_is_unknown_when_findmnt_prints_nothing(sysprops, commands_on_path):
    assert sysprops.read_root_filesystem() == "Unknown"


def test_system_facts_gathers_every_reading(sysprops, redirect_files, commands_on_path, monkeypatch):
    redirect_files("/etc/os-release", 'PRETTY_NAME="Test OS 1"\n')
    redirect_files("/etc/machine-id", "0123456789abcdef0123456789abcdef\n")
    redirect_files("/proc/meminfo", MEMINFO)
    redirect_files("/proc/swaps", "Filename\n")
    commands_on_path("findmnt", "xfs")
    monkeypatch.setenv("XDG_SESSION_TYPE", "x11")

    facts = sysprops.gather_system_facts()

    assert facts == sysprops.SystemFacts(
        os_name="Test OS 1",
        kernel="Linux " + platform.release(),
        desktop="KDE Plasma 6 (X11)",
        owner=sysprops.read_full_name(),
        hostname=socket.gethostname(),
        product_key="15123-OEM-6607520-41709",
        cpu_model=platform.processor(),
        logical_processors=f"{os.cpu_count()} logical processors",
        memory="16 GB RAM",
        display="Unknown display",
        resources_free="25% free",
        filesystem="Xfs",
        virtual_memory="8 GB swap",
    )


@pytest.fixture
def metrics(qt_app):
    return QFontMetrics(QApplication.font())


def test_wrapped_keeps_a_value_on_one_line_when_it_fits(sysprops, metrics):
    assert sysprops.wrapped("aa bb", metrics, 1000) == ["aa bb"]


def test_wrapped_breaks_between_words_when_the_next_word_does_not_fit(sysprops, metrics):
    assert sysprops.wrapped("aa bb", metrics, metrics.horizontalAdvance("aa")) == ["aa", "bb"]


def test_wrapped_is_one_empty_line_for_empty_text(sysprops, metrics):
    assert sysprops.wrapped("", metrics, 100) == [""]


def test_wrapped_breaks_a_first_word_longer_than_the_line_where_it_fits(sysprops, metrics):
    assert sysprops.wrapped("aaaa", metrics, metrics.horizontalAdvance("aa")) == ["aa", "aa"]


def test_wrapped_breaks_a_long_word_after_the_line_that_precedes_it(sysprops, metrics):
    assert sysprops.wrapped("a bbbb", metrics, metrics.horizontalAdvance("bb")) == ["a", "bb", "bb"]


def test_wrapped_puts_one_letter_per_line_when_the_line_is_narrower_than_a_letter(sysprops, metrics):
    assert sysprops.wrapped("abc", metrics, 1) == ["a", "b", "c"]


def test_device_manager_launcher_starts_the_program_when_it_exists(sysprops, tmp_path, monkeypatch):
    marker = tmp_path / "started"
    launcher = tmp_path / "devmgr"
    launcher.write_text(f"#!/bin/sh\ntouch {marker}\n")
    launcher.chmod(0o755)
    monkeypatch.setattr(sysprops, "DEVICE_MANAGER_PATH", launcher)

    sysprops.launch_device_manager()

    QTest.qWait(500)
    assert marker.exists() is True


def test_device_manager_launcher_does_nothing_when_the_program_is_missing(sysprops, tmp_path, monkeypatch):
    monkeypatch.setattr(sysprops, "DEVICE_MANAGER_PATH", tmp_path / "missing")

    assert sysprops.launch_device_manager() is None


def test_clicking_a_tab_selects_its_page(sysprops, qt_app, redirect_files, commands_on_path, monkeypatch):
    redirect_files("/proc/meminfo", MEMINFO)
    redirect_files("/proc/swaps", "Filename\n")
    redirect_files("/etc/machine-id", "0123456789abcdef0123456789abcdef\n")
    window = sysprops.build_window(sysprops.gather_system_facts(), "1995")
    strip = window.tabs
    left, right = strip.boxes[1]
    window.show()

    QTest.mouseClick(
        strip,
        Qt.LeftButton,
        pos=QPoint(round((left + right) / 2 - sysprops.BODY_ORIGIN[0]), sysprops.TAB_TOP + 2 - sysprops.BODY_ORIGIN[1]),
    )

    assert strip.current == 1


def run_main(sysprops, monkeypatch, *arguments):
    monkeypatch.setattr(sys, "argv", ["chicago95-sysprops", *arguments])
    return sysprops.main()


@pytest.fixture
def machine_readings(redirect_files, commands_on_path):
    redirect_files("/proc/meminfo", MEMINFO)
    redirect_files("/proc/swaps", "Filename\n")
    redirect_files("/etc/machine-id", "0123456789abcdef0123456789abcdef\n")


def test_main_saves_the_window_for_screenshot(sysprops, qt_app, machine_readings, monkeypatch, tmp_path):
    monkeypatch.setattr(sysprops.chicago95ui, "make_app", lambda _name: qt_app)
    path = tmp_path / "sysprops.png"

    exit_code = run_main(sysprops, monkeypatch, "--screenshot", str(path))

    assert (exit_code, path.exists()) == (0, True)


def test_main_shows_the_window_and_returns_the_event_loop_result(sysprops, qt_app, machine_readings, monkeypatch):
    monkeypatch.setattr(sysprops.chicago95ui, "make_app", lambda _name: qt_app)
    QTimer.singleShot(300, lambda: qt_app.exit(7))

    assert run_main(sysprops, monkeypatch) == 7
