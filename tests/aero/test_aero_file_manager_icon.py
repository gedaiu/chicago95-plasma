from conftest import run_bash_with_steps


def test_both_file_managers_use_the_explorer_art_from_the_selected_icon_pack(tmp_path):
    icons = tmp_path / ".local/share/icons/Windows-7"
    for name in ("apps/file-manager.png", "apps/32/system-file-manager.png", "filesystems/user-desktop.png"):
        path = icons / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(name.encode())
    (icons / "index.theme").write_text("[Icon Theme]\nInherits=Gnome,hicolor\n")
    run_bash_with_steps(tmp_path, "install_icon_pack() { :; }; kconf() { :; }; SETUP_ICONS=windows7 apply_icon_set")
    for app in ("org.xfce.thunar", "org.kde.dolphin"):
        assert (icons / f"apps/{app}.png").read_bytes() == b"apps/file-manager.png"
        assert (icons / f"apps/32/{app}.png").read_bytes() == b"apps/32/system-file-manager.png"
