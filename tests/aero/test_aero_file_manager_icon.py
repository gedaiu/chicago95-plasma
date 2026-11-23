from xml.etree import ElementTree as ET

from conftest import run_bash_with_steps
from PIL import Image


def test_both_file_managers_use_the_explorer_art_from_the_selected_icon_pack(tmp_path):
    icons = tmp_path / ".local/share/icons/Windows-7"
    for name in ("apps/file-manager.png", "apps/32/system-file-manager.png", "filesystems/user-desktop.png"):
        path = icons / name
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGBA", (32, 32), "gold").save(path)
    (icons / "index.theme").write_text("[Icon Theme]\nInherits=Gnome,hicolor\n")
    run_bash_with_steps(tmp_path, "kconf() { :; }; SETUP_ICONS=windows7 apply_icon_set")
    for app in ("org.xfce.thunar", "org.kde.dolphin"):
        for size in ("apps", "apps/32"):
            vector = icons.with_name("Windows-7-SVG") / size / f"{app}.svg"
            art = vector.read_text()
            nodes = ET.fromstring(art)
            ns = {"svg": "http://www.w3.org/2000/svg"}
            flat = nodes.findall(".//svg:rect", ns)
            assert len(flat) == 1
            assert (flat[0].get("width"), flat[0].get("height"), flat[0].get("fill")) == ("32", "32", "#ffd700")
            assert nodes.find(".//svg:image", ns) is None
