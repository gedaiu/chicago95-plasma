import chicago95ui


def sound_theme_folder(root, theme, *file_names):
    (root / theme / "stereo").mkdir(parents=True)
    for file_name in file_names:
        (root / theme / "stereo" / file_name).touch()


def test_sound_file_is_the_chosen_themes_before_chicago95s(tmp_path):
    sound_theme_folder(tmp_path, "Chicago95", "dialog-error.wav")
    sound_theme_folder(tmp_path, "Windows98", "dialog-error.ogg")

    assert chicago95ui.sound_file("Windows98", "dialog-error", [tmp_path]) == str(tmp_path / "Windows98/stereo/dialog-error.ogg")


def test_sound_file_falls_back_to_chicago95_when_the_theme_lacks_the_event(tmp_path):
    sound_theme_folder(tmp_path, "Chicago95", "desktop-logout.wav")
    sound_theme_folder(tmp_path, "Plus98-Leonardo")

    assert chicago95ui.sound_file("Plus98-Leonardo", "desktop-logout", [tmp_path]) == str(tmp_path / "Chicago95/stereo/desktop-logout.wav")


def test_sound_file_skips_disabled_sounds_and_searches_every_root(tmp_path):
    sound_theme_folder(tmp_path / "user", "Chicago95", "bell.disabled")
    sound_theme_folder(tmp_path / "system", "Chicago95", "bell.wav")

    assert chicago95ui.sound_file("Chicago95", "bell", [tmp_path / "user", tmp_path / "system"]) == str(tmp_path / "system/Chicago95/stereo/bell.wav")


def test_sound_file_is_none_when_no_theme_has_the_event(tmp_path):
    sound_theme_folder(tmp_path, "Chicago95")

    assert chicago95ui.sound_file("Chicago95", "bell", [tmp_path]) is None
