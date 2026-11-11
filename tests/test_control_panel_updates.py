"""The Control Panel's Updates applet: the installed and the published version of Chicago95 for Plasma
(lib/chicago95update.py), a Check now button, and Install update, which pulls the repository and reruns Setup."""
import stat
from datetime import datetime, timezone

import pytest
from conftest import load_script

import chicago95update

OLD, NEW = "a" * 40, "b" * 40
NOON = datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc)


@pytest.fixture(scope="session")
def control_panel():
    return load_script("chicago95-control-panel")


@pytest.fixture
def cache(tmp_path, monkeypatch):
    path = tmp_path / "update-check.json"
    monkeypatch.setattr(chicago95update, "CACHE_FILE", path)
    return path


def updates_tab(control_panel, settings=None, **actions):
    return control_panel.build_tab("Updates", "Updates", settings or {"REPO": "/repo", "COMMIT": OLD}, control_panel.Actions(**actions))


def shown(tab):
    return (tab.installed_label.text(), tab.latest_label.text(), tab.status_label.text(), tab.install_button.isEnabled())


def test_updates_is_an_applet_with_one_page_reachable_as_the_updates_slug(control_panel):
    assert (
        control_panel.APPLET_BY_NAME["Updates"].description,
        control_panel.PAGE_TABS["Updates"],
        control_panel.PAGE_SLUGS["updates"],
    ) == ("Checks for a newer Chicago95 for Plasma and installs it.", ("Updates",), "Updates")


def test_the_page_shows_the_cached_check_and_offers_the_install_when_a_newer_version_is_published(control_panel, cache, qt_app):
    chicago95update.write_cache(cache, chicago95update.check_result(OLD, NEW, NOON))

    assert shown(updates_tab(control_panel)) == ("aaaaaaa", "bbbbbbb", "A newer version is available.", True)


def test_the_page_says_so_when_nothing_was_checked_yet(control_panel, cache, qt_app):
    assert shown(updates_tab(control_panel)) == ("aaaaaaa", "unknown", "Not checked yet.", False)


def test_the_page_says_the_installed_version_is_the_latest_and_shows_a_failed_check(control_panel, cache, qt_app):
    chicago95update.write_cache(cache, chicago95update.check_result(NEW, NEW, NOON))
    current = shown(updates_tab(control_panel, {"REPO": "/repo", "COMMIT": NEW}))
    chicago95update.write_cache(cache, chicago95update.check_result(OLD, "", NOON, "fatal: no network"))
    failed = shown(updates_tab(control_panel))

    assert (current, failed) == (
        ("bbbbbbb", "bbbbbbb", "You have the latest version.", False),
        ("aaaaaaa", "unknown", "Could not check: fatal: no network", False),
    )


def test_check_now_asks_the_origin_and_shows_the_answer(control_panel, cache, tmp_path, monkeypatch, qt_app):
    git = tmp_path / "git"
    git.write_text(f'#!/bin/sh\n[ "$1" = ls-remote ] && printf "%s\\trefs/heads/main\\n" {NEW}\n')
    git.chmod(git.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setattr(chicago95update, "GIT", str(git))
    tab = updates_tab(control_panel)
    tab.check_button.click()
    checking = tab.status_label.text()
    while tab.check is not None:
        qt_app.processEvents()

    assert (checking, shown(tab), cache.exists()) == ("Checking...", ("aaaaaaa", "bbbbbbb", "A newer version is available.", True), True)


def test_install_update_pulls_the_repository_and_reruns_setup_for_the_saved_settings(control_panel, cache, monkeypatch, qt_app, tmp_path):
    chicago95update.write_cache(cache, chicago95update.check_result(OLD, NEW, NOON))
    monkeypatch.setattr(control_panel, "SETTINGS_FILE", tmp_path / "setup.conf")
    runs = []
    tab = updates_tab(control_panel, {"REPO": "/repo", "COMMIT": OLD, "LOOK": "2000", "SAVER": "maze"}, run_setup=lambda parent, command: runs.append(command))
    tab.install_button.click()

    assert runs == [
        control_panel.OWN_SCOPE
        + [
            "sh",
            "-c",
            'git -C "$1" pull --ff-only && "$1/install.sh" --plain --yes "--settings=$2" "$3"',
            "chicago95-update",
            "/repo",
            str(tmp_path / "setup.conf"),
            "--components=look,taskbar,startmenu,screensaver",
        ]
    ]
