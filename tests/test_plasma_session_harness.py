"""The nested-session harness's own parts (plasma_session.py)."""

from pathlib import Path

import pytest
from plasma_session import enforce_screenshot, link_user_assets, setup_key, work_folder


def test_work_folder_is_made_in_the_memory_filesystem_under_a_short_c95_name(tmp_path):
    folder = work_folder("aero", memory=tmp_path)

    assert (folder.parent, folder.name.startswith("c95-aero-"), folder.is_dir()) == (tmp_path, True, True)


def test_work_folder_falls_back_to_tmp_without_a_memory_filesystem(tmp_path):
    folder = work_folder("aero", memory=tmp_path / "missing")
    folder.rmdir()

    assert folder.parent == Path("/tmp")


def test_session_without_its_screenshot_raises_naming_the_session_and_its_logs(tmp_path):
    with pytest.raises(RuntimeError, match=f"Setup's session took no screenshot.*{tmp_path}"):
        enforce_screenshot(tmp_path / "setup-screen.png", "Setup's")


def test_users_cloned_icon_set_is_linked_into_the_session_home_so_setup_clones_nothing(tmp_path, monkeypatch):
    user, session = tmp_path / "user", tmp_path / "session"
    (user / "src/Windows-XP").mkdir(parents=True)
    (user / "src/Windows-XP/index.theme").write_text("[Icon Theme]\n")
    (user / "src/private-work").mkdir()
    session.mkdir()
    monkeypatch.setenv("HOME", str(user))

    link_user_assets(session)

    assert sorted(path.name for path in (session / "src").iterdir()) == ["Windows-XP"]
    assert (session / "src/Windows-XP").resolve() == user / "src/Windows-XP"


AERO = {"taskbar_style": "aero", "settings": [("DECORATION", "aero")], "screen": (1024, 768)}


def test_desktops_differing_in_windows_pointer_and_tray_icons_share_one_setup():
    plain = setup_key("luna", {**AERO, "windows": [("Notes", "qt", "minimized")]})
    clicked = setup_key("luna", {**AERO, "pointer_steps": ["move:850,749", "click:left"], "tray_icons": 3})

    assert plain == clicked


@pytest.mark.parametrize(
    "option",
    [
        {"tasks_config": [("locked", "false")]},
        {"hidden_applets": ["org.kde.plasma.notifications"]},
        {"launchers": 0},
        {"components": ["background"]},
    ],
)
def test_desktop_with_another_setup_option_gets_its_own_setup(option):
    assert setup_key("luna", {**AERO, **option}) != setup_key("luna", AERO)


def test_setup_is_not_shared_between_looks():
    assert setup_key("luna", AERO) != setup_key("1998", AERO)
