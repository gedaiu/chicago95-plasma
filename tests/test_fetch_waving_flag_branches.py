import hashlib
import importlib.util
import json
import subprocess

import pytest
from conftest import REPO
from PySide6.QtGui import QColor, QImage

INSIDE_FRAME_POINT = (100, 100)


@pytest.fixture(scope="module")
def waving_flag():
    spec = importlib.util.spec_from_file_location("fetch_waving_flag", REPO / "setup/fetch-waving-flag.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def logo_bytes(tmp_path):
    logo = QImage(1778, 524, QImage.Format_ARGB32)
    logo.fill(QColor(248, 248, 248))
    for offset in range(4):
        logo.setPixelColor(INSIDE_FRAME_POINT[0] + offset, INSIDE_FRAME_POINT[1], QColor(0, 0, 0))
    path = tmp_path / "logo.png"
    logo.save(str(path))
    return path.read_bytes()


@pytest.fixture
def commons(waving_flag, logo_bytes, tmp_path, monkeypatch):
    """Points the Commons API and the picture it names at local files, with the picture's real SHA-1."""
    picture_path = tmp_path / "logo.png"
    info = {"query": {"pages": {"200014766": {"imageinfo": [{"url": picture_path.as_uri()}]}}}}
    (tmp_path / "api.json").write_text(json.dumps(info))
    monkeypatch.setattr(waving_flag, "COMMONS_API", (tmp_path / "api.json").as_uri())
    monkeypatch.setattr(waving_flag, "COMMONS_SHA1", hashlib.sha1(logo_bytes).hexdigest())
    return waving_flag


def test_fetch_reads_a_local_file_url(waving_flag, tmp_path):
    source = tmp_path / "payload.bin"
    source.write_bytes(b"payload")

    assert waving_flag.fetch(source.as_uri()) == b"payload"


def test_download_logo_returns_the_picture_whose_sha1_matches(commons, logo_bytes):
    assert commons.download_logo() == logo_bytes


def test_download_logo_exits_when_the_picture_sha1_differs(commons, monkeypatch):
    monkeypatch.setattr(commons, "COMMONS_SHA1", "0" * 40)

    with pytest.raises(SystemExit, match="The Commons file has changed since Setup was written; pick another logo."):
        commons.download_logo()


def test_main_saves_the_flag_cut_out_of_the_downloaded_logo(commons, tmp_path):
    flag_path = tmp_path / "flag.png"

    commons.main(str(flag_path))

    flag = QImage(str(flag_path))
    assert (flag.width(), flag.height()) == (4, 3)


def test_main_exits_when_the_output_folder_does_not_exist(commons, tmp_path):
    missing = tmp_path / "missing/flag.png"

    with pytest.raises(SystemExit, match=f"Could not write {missing}"):
        commons.main(str(missing))


def test_script_without_output_path_exits_with_index_error():
    result = subprocess.run(
        ["python3", str(REPO / "setup/fetch-waving-flag.py")], capture_output=True, text=True, check=False
    )

    assert (result.returncode, result.stderr.splitlines()[-1]) == (1, "IndexError: list index out of range")
