from conftest import run_bash_with_steps
from PIL import Image


def test_both_file_managers_use_the_explorer_art_from_the_selected_icon_pack(tmp_path):
    icons = tmp_path / ".local/share/icons/Windows-7"
    for name in ("apps/file-manager.png", "apps/32/system-file-manager.png", "filesystems/user-desktop.png"):
        path = icons / name
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGBA", (32, 32), "gold").save(path)
    (icons / "index.theme").write_text("[Icon Theme]\nInherits=Gnome,hicolor\n")
    run_bash_with_steps(tmp_path, "install_icon_pack() { :; }; kconf() { :; }; SETUP_ICONS=windows7 apply_icon_set")
    for app in ("org.xfce.thunar", "org.kde.dolphin"):
        for size in ("apps", "apps/32"):
            vector = icons.with_name("Windows-7-SVG") / size / f"{app}.svg"
            art = vector.read_text()
            assert "<path" in art and "<image" not in art
