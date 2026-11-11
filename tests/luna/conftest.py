import chicago95ui
import pytest

LUNA_CONFIG = "[StartMenu]\nstyle=luna\n[Look]\nwidgetStyle=luna\n"


@pytest.fixture
def luna_look(qt_app, tmp_path):
    config = tmp_path / "chicago95rc"
    config.write_text(LUNA_CONFIG)
    original_config = chicago95ui.CHICAGO95RC
    chicago95ui.CHICAGO95RC = str(config)
    chicago95ui.apply_style(qt_app)
    yield config
    chicago95ui.CHICAGO95RC = original_config
    chicago95ui.apply_style(qt_app)
