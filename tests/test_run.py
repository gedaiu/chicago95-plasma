"""The Run dialog's matching (bin/chicago95-run): programs by name, commands on the PATH, paths and URLs, with the
typed line run as it is when nothing is picked, and the history the drop-down keeps."""

import os
import stat

import pytest
from conftest import load_script

APPLICATIONS = [
    {"name": "Calculator", "icon": "accessories-calculator", "path": "/apps/kcalc.desktop"},
    {"name": "Text Editor", "icon": "accessories-text-editor", "path": "/apps/kate.desktop"},
    {"name": "KCalc", "icon": "kcalc", "path": "/apps/org.kde.kcalc.desktop"},
    {"name": "Mines", "icon": "kmines", "path": "/apps/kmines.desktop"},
]


@pytest.fixture(scope="module")
def run():
    return load_script("chicago95-run")


@pytest.fixture
def bin_dir(tmp_path):
    folder = tmp_path / "bin"
    folder.mkdir()
    for name in ("calc", "calendar", "cat"):
        (folder / name).write_text("#!/bin/sh\n")
        (folder / name).chmod(stat.S_IRWXU)
    (folder / "calc.txt").write_text("not a program")
    return folder


def test_programs_whose_name_starts_with_the_text_come_before_word_starts_and_the_rest(run):
    assert [name for name, _icon, _command in run.application_matches("cal", APPLICATIONS)] == [
        "Calculator",
        "KCalc",
    ]


def test_a_program_match_opens_its_desktop_file(run):
    assert run.application_matches("text", APPLICATIONS) == [
        ("Text Editor", "accessories-text-editor", ["gio", "launch", "/apps/kate.desktop"])
    ]


def test_commands_on_the_path_that_start_with_the_text_are_offered_sorted_and_only_the_executable_ones(run, bin_dir):
    assert run.command_matches("cal", [str(bin_dir), "/nowhere"]) == [
        ("calc", "application-x-executable", ["calc"]),
        ("calendar", "application-x-executable", ["calendar"]),
    ]


def test_a_path_lists_the_folders_entries_that_start_with_its_last_part(run, tmp_path):
    (tmp_path / "Documents").mkdir()
    (tmp_path / "Downloads").mkdir()
    (tmp_path / "Desktop").mkdir()
    (tmp_path / "Do.txt").write_text("")
    (tmp_path / ".Dotfile").write_text("")

    assert run.path_matches(f"{tmp_path}/Do") == [
        (f"{tmp_path}/Do.txt", "text-x-generic", ["xdg-open", f"{tmp_path}/Do.txt"]),
        (f"{tmp_path}/Documents", "folder", ["xdg-open", f"{tmp_path}/Documents"]),
        (f"{tmp_path}/Downloads", "folder", ["xdg-open", f"{tmp_path}/Downloads"]),
    ]


def test_matches_put_programs_before_commands_and_cap_the_list_at_eight(run, bin_dir):
    many = [{"name": f"Calc {index}", "icon": "", "path": f"/apps/{index}.desktop"} for index in range(10)]

    assert (
        [name for name, _icon, _command in run.matches("cal", APPLICATIONS, [str(bin_dir)])],
        len(run.matches("cal", many, [str(bin_dir)])),
        run.matches("   ", APPLICATIONS, [str(bin_dir)]),
    ) == (["Calculator", "KCalc", "calc", "calendar"], 8, [])


def test_a_web_address_is_offered_as_itself(run):
    assert run.matches("www.kde.org", APPLICATIONS, []) == [("www.kde.org", "text-html", ["xdg-open", "www.kde.org"])]


def test_the_typed_line_opens_when_it_is_a_place_or_address_and_runs_as_a_command_otherwise(run, tmp_path):
    assert (
        run.literal_command(f"{tmp_path} "),
        run.literal_command("https://kde.org"),
        run.literal_command('notepad "My File.txt"'),
    ) == (["xdg-open", str(tmp_path)], ["xdg-open", "https://kde.org"], ["notepad", "My File.txt"])


def test_the_history_keeps_the_latest_first_without_repeats_and_at_most_26_entries(run):
    history = [f"command {index}" for index in range(30)]

    assert (run.remember("command 3", history)[:3], len(run.remember("new", history))) == (
        ["command 3", "command 0", "command 1"],
        26,
    )


def test_the_history_round_trips_through_its_file(run, tmp_path):
    path = tmp_path / "chicago95/run-history"
    run.write_history(["calc", "notepad"], path)

    assert (run.read_history(path), run.read_history(tmp_path / "missing")) == (["calc", "notepad"], [])


def test_typing_lists_the_matches_under_the_field_and_the_dialog_grows_to_hold_them(run, qt_app):
    dialog = run.RunDialog({"style": "1995"}, APPLICATIONS, [], history=[])
    dialog.show()
    height_before = dialog.height()
    dialog.field.lineEdit().setText("cal")
    dialog.field.lineEdit().textEdited.emit("cal")
    rows = [dialog.results.item(index).text() for index in range(dialog.results.count())]
    grown = dialog.height() - height_before
    dialog.field.lineEdit().textEdited.emit("")

    assert (rows, grown, dialog.height() - height_before, dialog.buttons["OK"].isEnabled()) == (
        ["Calculator", "KCalc"],
        2 * run.MATCH_ROW_HEIGHT + 2 + 4,
        0,
        False,
    )


def test_enter_runs_the_picked_match_and_remembers_the_typed_text(run, qt_app, tmp_path, monkeypatch):
    monkeypatch.setattr(run, "HISTORY_FILE", tmp_path / "run-history")
    dialog = run.RunDialog({"style": "1995"}, APPLICATIONS, [], history=["old"])
    dialog.show()
    dialog.field.lineEdit().textEdited.emit("kcalc")
    dialog.results.setCurrentRow(0)
    dialog.accept()

    assert (dialog.command, dialog.history, run.read_history(tmp_path / "run-history")) == (
        ["gio", "launch", "/apps/org.kde.kcalc.desktop"],
        ["kcalc", "old"],
        ["kcalc", "old"],
    )


def test_the_start_menu_opens_our_run_dialog_when_installed_and_krunner_otherwise(startmenu):
    assert (startmenu.run_command(lambda _path: True), startmenu.run_command(lambda _path: False)) == (
        [os.path.expanduser("~/.local/bin/chicago95-run")],
        ["krunner"],
    )
