"""lib/chicago95update.py: is a newer Chicago95 for Plasma published? The installed commit (COMMIT= in
setup.conf, written by Setup) is compared with the tip of the repository's branch, asked from the origin with
one `git ls-remote`; the answer is cached for a day so Clippy and the Control Panel share it."""
import json
import stat
from datetime import datetime, timedelta, timezone

import pytest

import chicago95update

NOON = datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc)
OLD, NEW = "a" * 40, "b" * 40


def fake_git(tmp_path, body):
    script = tmp_path / "git"
    script.write_text(f"#!/bin/sh\n{body}\n")
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    return str(script)


def test_latest_commit_is_the_sha_before_the_branch_ref_in_ls_remote_output():
    assert chicago95update.latest_commit(f"{NEW}\trefs/heads/main\n") == NEW


def test_latest_commit_is_empty_when_ls_remote_printed_nothing():
    assert chicago95update.latest_commit("") == ""


@pytest.mark.parametrize(
    "installed, latest, error, available",
    [(OLD, NEW, "", True), (NEW, NEW, "", False), ("", NEW, "", False), (OLD, "", "no network", False)],
)
def test_check_result_says_an_update_is_available_only_when_both_commits_are_known_and_differ(installed, latest, error, available):
    result = chicago95update.check_result(installed, latest, NOON, error)

    assert result == {"installed": installed, "latest": latest, "checked": NOON.isoformat(), "available": available, "error": error}


def test_a_check_is_due_without_a_cache_and_again_a_day_after_the_last_one():
    fresh = chicago95update.check_result(OLD, NEW, NOON)

    assert (
        chicago95update.is_due({}, NOON),
        chicago95update.is_due(fresh, NOON + timedelta(hours=23)),
        chicago95update.is_due(fresh, NOON + timedelta(days=1)),
    ) == (True, False, True)


def test_the_cache_round_trips_through_its_json_file(tmp_path):
    path = tmp_path / "cache/update-check.json"
    result = chicago95update.check_result(OLD, NEW, NOON)
    chicago95update.write_cache(path, result)

    assert (chicago95update.read_cache(path), chicago95update.read_cache(tmp_path / "missing.json")) == (result, {})


def test_the_origin_comes_from_the_repository_and_falls_back_to_the_project_url(tmp_path):
    git = fake_git(tmp_path, 'echo "https://example.org/fork.git"')
    (tmp_path / "none").mkdir()
    silent = fake_git(tmp_path / "none", "exit 1")

    assert (chicago95update.origin_of("/repo", git=git), chicago95update.origin_of("/repo", git=silent)) == (
        "https://example.org/fork.git",
        chicago95update.PROJECT_ORIGIN,
    )


def test_update_check_asks_the_origin_for_the_branch_tip_and_caches_the_answer(tmp_path, qt_app):
    git = fake_git(tmp_path, f'[ "$1" = ls-remote ] && printf "%s\\trefs/heads/main\\n" {NEW}')
    cache = tmp_path / "update-check.json"
    settings = {"REPO": str(tmp_path), "COMMIT": OLD}
    results = []
    check = chicago95update.UpdateCheck(settings, cache, git=git, now=lambda: NOON)
    check.finished.connect(results.append)
    check.start()
    while not results:
        qt_app.processEvents()

    assert (results, json.loads(cache.read_text())["latest"]) == (
        [{"installed": OLD, "latest": NEW, "checked": NOON.isoformat(), "available": True, "error": ""}],
        NEW,
    )


def test_update_check_reports_the_error_when_git_fails(tmp_path, qt_app):
    git = fake_git(tmp_path, 'echo "fatal: unable to access" >&2; exit 128')
    results = []
    check = chicago95update.UpdateCheck({"REPO": str(tmp_path), "COMMIT": OLD}, tmp_path / "c.json", git=git, now=lambda: NOON)
    check.finished.connect(results.append)
    check.start()
    while not results:
        qt_app.processEvents()

    assert (results[0]["available"], results[0]["error"]) == (False, "fatal: unable to access")


def test_short_version_is_the_first_seven_characters_or_unknown():
    assert (chicago95update.short_version(NEW), chicago95update.short_version("")) == ("bbbbbbb", "unknown")


def test_read_settings_takes_key_value_lines_and_ignores_comments(tmp_path):
    conf = tmp_path / "setup.conf"
    conf.write_text("# saved by Setup\nREPO=/repo\nCOMMIT=abc\nbroken line\n")

    assert (chicago95update.read_settings(conf), chicago95update.read_settings(tmp_path / "none")) == ({"REPO": "/repo", "COMMIT": "abc"}, {})


def test_update_message_names_both_versions_and_the_control_panel_page():
    assert chicago95update.update_message(chicago95update.check_result(OLD, NEW, NOON)) == (
        "A newer Chicago95 for Plasma is available (bbbbbbb; you have aaaaaaa).\n\nOpen Control Panel, Updates to install it."
    )


def test_the_daily_schedule_checks_when_due_and_reports_an_available_update(tmp_path, qt_app):
    git = fake_git(tmp_path, f'[ "$1" = ls-remote ] && printf "%s\\trefs/heads/main\\n" {NEW}')
    conf = tmp_path / "setup.conf"
    conf.write_text(f"REPO={tmp_path}\nCOMMIT={OLD}\n")
    announced = []
    schedule = chicago95update.DailySchedule(conf, announced.append, cache_path=tmp_path / "c.json", git=git, now=lambda: NOON)
    schedule.tick()
    while not announced:
        qt_app.processEvents()
    schedule.tick()  # cached now: no second check today
    qt_app.processEvents()

    assert (len(announced), announced[0]["available"], schedule.check is None) == (1, True, True)


def test_the_daily_schedule_leaves_a_fresh_cache_alone(tmp_path, qt_app):
    conf = tmp_path / "setup.conf"
    conf.write_text(f"REPO={tmp_path}\nCOMMIT={OLD}\n")
    cache = tmp_path / "c.json"
    chicago95update.write_cache(cache, chicago95update.check_result(OLD, NEW, NOON))
    announced = []
    schedule = chicago95update.DailySchedule(conf, announced.append, cache_path=cache, git="/nonexistent/git", now=lambda: NOON + timedelta(hours=1))
    schedule.tick()
    qt_app.processEvents()

    assert (announced, schedule.check) == ([], None)
