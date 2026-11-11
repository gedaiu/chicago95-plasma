import importlib.util
import subprocess
from pathlib import Path

import pytest
from conftest import REPO


@pytest.fixture(scope="module")
def sound_themes():
    spec = importlib.util.spec_from_file_location("make_sound_themes", REPO / "setup/make_sound_themes.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def output(sound_themes, tmp_path, monkeypatch):
    destination = tmp_path / "themes"
    monkeypatch.setattr(sound_themes, "OUTPUT", destination)
    return destination


def write_wav(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "sine=duration=0.1", str(path)],
        check=True,
    )


def pack(archive: Path, folder: Path):
    subprocess.run(["7z", "a", str(archive), f"{folder}/*"], check=True, stdout=subprocess.DEVNULL, cwd=folder)


def ogg_names(theme: Path):
    return sorted(path.name for path in (theme / "stereo").glob("*.ogg"))


def test_event_name_keeps_the_2000_stem_without_aliasing(sound_themes):
    assert sound_themes.event_name("Recycle.wav", "Windows 2000") == "recycle"


def test_event_name_aliases_the_plus_pack_spelling(sound_themes):
    assert sound_themes.event_name("Jungle Windows Start remastered.wav", "Jungle") == "startup"


def test_event_name_keeps_unaliased_plus_pack_stem(sound_themes):
    assert sound_themes.event_name("Jungle Maximize.wav", "Jungle") == "maximize"


def test_theme_id_joins_windows_scheme_words(sound_themes):
    assert sound_themes.theme_id("Windows 2000") == "Windows2000"


def test_theme_id_prefixes_plus_scheme_and_spells_out_the_sixties(sound_themes):
    assert sound_themes.theme_id("The 60's USA") == "Plus98-The60sUSA"


def test_build_theme_writes_index_and_one_ogg_per_mapped_event(sound_themes, output, tmp_path):
    wavs = [tmp_path / "Jungle Startup.wav", tmp_path / "Jungle Exit Windows.wav", tmp_path / "Jungle Unmapped.wav"]
    for wav in wavs:
        write_wav(wav)

    sound_themes.build_theme("Jungle", wavs, sound_themes.WINDOWS_98_EVENTS)

    theme = output / "Plus98-Jungle"
    assert (
        (theme / "index.theme").read_text(),
        ogg_names(theme),
    ) == (
        "[Sound Theme]\nName=Jungle\nInherits=Chicago95\nDirectories=stereo\n\n[stereo]\nOutputProfile=stereo\n",
        ["desktop-login.ogg", "desktop-logout.ogg", "system-shutdown.ogg"],
    )


def test_build_theme_replaces_a_previous_build_of_the_same_scheme(sound_themes, output, tmp_path):
    stale = output / "Plus98-Jungle/stereo/stale.ogg"
    stale.parent.mkdir(parents=True)
    stale.write_bytes(b"")
    wav = tmp_path / "Jungle Startup.wav"
    write_wav(wav)

    sound_themes.build_theme("Jungle", [wav], sound_themes.WINDOWS_98_EVENTS)

    assert ogg_names(output / "Plus98-Jungle") == ["desktop-login.ogg"]


def test_main_builds_every_98_folder_and_the_2000_theme_from_the_archives(sound_themes, output, tmp_path):
    sources_98 = tmp_path / "sources98"
    write_wav(sources_98 / "Leonardo Da Vinci/Leonardo Da Vinci Startup.wav")
    write_wav(sources_98 / "Jungle/Jungle Windows Exit.wav")
    (sources_98 / "stray-file.txt").write_text("not a scheme folder")
    sources_2000 = tmp_path / "sources2000"
    write_wav(sources_2000 / "nested/Windows Logon.wav")
    write_wav(sources_2000 / "nested/Ding.wav")
    zip_98, archive_2000 = tmp_path / "98.zip", tmp_path / "2000.7z"
    pack(zip_98, sources_98)
    pack(archive_2000, sources_2000)

    sound_themes.main(str(zip_98), str(archive_2000))

    assert {theme.name: ogg_names(theme) for theme in sorted(output.iterdir())} == {
        "Plus98-Jungle": ["desktop-logout.ogg", "system-shutdown.ogg"],
        "Plus98-LeonardodaVinci": ["desktop-login.ogg"],
        "Windows2000": ["bell-window-system.ogg", "bell.ogg", "desktop-login.ogg"],
    }


def test_script_without_archives_exits_with_missing_arguments_error():
    result = subprocess.run(
        ["python3", str(REPO / "setup/make_sound_themes.py")], capture_output=True, text=True, check=False
    )

    assert (result.returncode, result.stderr.splitlines()[-1]) == (
        1,
        "TypeError: main() missing 2 required positional arguments: 'windows_98_zip' and 'windows_2000_7z'",
    )
