"""Animation choices applied by Setup's animations step in a real Plasma session (tests/plasma_session.py): KWin
loads the title bar zoom without a script error and drops the effects of events turned off."""

import pytest
from conftest import needs_ui_font
from plasma_session import missing_programs

pytestmark = [
    needs_ui_font,
    pytest.mark.skipif(bool(missing_programs()), reason=f"needs {', '.join(missing_programs())}"),
]

CHOSEN = (("ANIM_MINIMIZE", "zoom"), ("ANIM_MAXIMIZE", "zoom"), ("ANIM_WINDOWS", "none"), ("ANIM_SPEED", "1"))


@pytest.fixture(scope="module")
def session(desktops):
    return desktops("1998", settings=CHOSEN).info


def loaded(session):
    return {name.strip(" '\"()<>[],") for name in session["loaded_effects"].replace(",", " ").split()}


def test_kwin_loads_the_title_bar_zoom_and_drops_the_window_open_effect_turned_off(session):
    assert ("chicago95zoom" in loaded(session), "scale" in loaded(session)) == (True, False)


def test_the_title_bar_zoom_runs_without_a_script_error(session):
    assert [line for line in session["kwin_log"].splitlines() if "chicago95zoom" in line] == []
