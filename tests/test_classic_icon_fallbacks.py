import os
import subprocess
from pathlib import Path


def test_missing_optional_icon_parents_and_case(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    icons = tmp_path / ".local/share/icons"
    theme = icons / "ClassicOS-2000"
    theme.mkdir(parents=True)
    index = theme / "index.theme"
    index.write_text("[Icon Theme]\nInherits=SE98,retrosmart-icon-theme,tango,adwaita,hicolor\n[actions]\nSize=16\n")
    for parent in ("tango", "Adwaita"):
        folder = tmp_path / "system/icons" / parent
        folder.mkdir(parents=True)
        (folder / "index.theme").touch()
    env = dict(os.environ, HOME=str(tmp_path), XDG_DATA_HOME=str(icons.parent), XDG_DATA_DIRS=str(tmp_path / "system"))
    cmd = ["python3", str(repo / "setup/classic_icon_fallbacks.py"), str(index)]
    subprocess.run(cmd, env=env, check=True)
    assert index.read_text() == "[Icon Theme]\nInherits=SE98,tango,Adwaita,hicolor\n[actions]\nSize=16\n"
    modified = index.stat().st_mtime_ns
    subprocess.run(cmd, env=env, check=True)
    assert index.stat().st_mtime_ns == modified
