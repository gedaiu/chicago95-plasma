import pytest
from conftest import load_script


@pytest.fixture
def control_panel():
    return load_script("chicago95-control-panel")


def test_luna_look_drops_the_windows_style_override_for_child_tools(luna_look, control_panel, monkeypatch):
    monkeypatch.setenv("QT_STYLE_OVERRIDE", "Windows")
    assert "QT_STYLE_OVERRIDE" not in control_panel.native_environment()


def test_classic_look_keeps_the_style_override_for_child_tools(control_panel, monkeypatch):
    monkeypatch.setenv("QT_STYLE_OVERRIDE", "Windows")
    assert control_panel.native_environment()["QT_STYLE_OVERRIDE"] == "Windows"


def test_child_tools_never_inherit_the_qt_platform(control_panel, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    assert "QT_QPA_PLATFORM" not in control_panel.native_environment()


def import_ui_override(tmp_path, widget_style):
    import subprocess
    import sys

    from conftest import REPO

    (tmp_path / "chicago95rc").write_text(f"[Look]\nwidgetStyle={widget_style}\n")
    environment = {"PATH": "/usr/bin:/bin", "XDG_CONFIG_HOME": str(tmp_path), "QT_QPA_PLATFORM": "offscreen"}
    code = "import chicago95ui, os; print(os.environ.get('QT_STYLE_OVERRIDE', 'unset'))"
    return subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env=environment,
        cwd=REPO / "lib",
        check=True,
        timeout=60,
    ).stdout.strip()


def test_ui_import_leaves_the_style_override_unset_under_luna(tmp_path):
    assert import_ui_override(tmp_path, "luna") == "unset"


def test_ui_import_sets_the_windows_style_override_under_classic(tmp_path):
    assert import_ui_override(tmp_path, "classic") == "Windows"
