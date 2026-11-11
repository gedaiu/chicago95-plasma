import re
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def sysprops():
    from conftest import load_script

    return load_script("chicago95-sysprops")


def test_product_key_keeps_its_shape_for_a_machine_id_with_leading_zeros(sysprops, tmp_path, monkeypatch):
    machine_id_file = tmp_path / "machine-id"
    machine_id_file.write_text("0" * 31 + "1\n")
    real_path = Path
    monkeypatch.setattr(
        sysprops, "Path", lambda path: real_path(machine_id_file if path == "/etc/machine-id" else path)
    )

    assert re.fullmatch(r"\d{5}-OEM-\d{7}-\d{5}", sysprops.read_product_key())
