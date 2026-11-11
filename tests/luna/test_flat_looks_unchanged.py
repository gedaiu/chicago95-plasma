"""Pins the flat 1995, 1998 and 2000 decoration and Plasma style: the Luna work must not change a byte of them.

The generators are run into a temporary folder with the arguments bin/chicago95-sync-colors builds for each
look (colours as setup/steps.sh apply_look writes them, bevel as chicago95ui.bevel_colors derives it).
To record new hashes after an intended flat change, run this file as a script (PYTHONPATH=tests).
"""

import hashlib
import subprocess
import sys

import pytest
from conftest import REPO

AURORAE = REPO / "aurorae/make_chicago95_aurorae.py"
PLASMA_STYLE = REPO / "plasma-style/make_chicago95_plasmastyle.py"

# face, light, shadow, dark, title colours, inactive text, selection, gradient margins
LOOKS = {
    "1995": dict(
        active="#000080",
        inactive="#808080",
        inactive_text="#C0C0C0",
        face="#C0C0C0",
        light="#DFDFDF",
        shadow="#808080",
        dark="#000000",
        selection="#000080",
        margins="0,0",
    ),
    "1998": dict(
        active="#000080,#1084D0",
        inactive="#808080,#C0C0C0",
        inactive_text="#C0C0C0",
        face="#C0C0C0",
        light="#DFDFDF",
        shadow="#808080",
        dark="#000000",
        selection="#000080",
        margins="0,0",
    ),
    "2000": dict(
        active="#0A246A,#A6CAF0",
        inactive="#808080,#C0C0C0",
        inactive_text="#D4D0C8",
        face="#D4D0C8",
        light="#D4D0C8",
        shadow="#808080",
        dark="#404040",
        selection="#0A246A",
        margins="18,52",
    ),
}

EXPECTED_HASHES = {'1995': {'aurorae/Chicago95rc': '9e5125699277099cc0bf4a988f054d45b1a1f7332ca51d71a2c56234650cd4f8',
          'aurorae/alldesktops.svg': '49c1eb3df3605fdedb7bc60876af5cd4e2ceb46b737781e0c56e62d47344e6a3',
          'aurorae/close.svg': 'a657a6c8e130edfa202c9b3398bcad80bb32be51972e3da809aea3f959f87892',
          'aurorae/decoration.svg': '63210f5d927001bade6861dd9445820f2ad014309f43b64cc995de69de21b1ec',
          'aurorae/help.svg': '492485ab155696c90b17e4c7afe2f6418a8f09ec6831f4fdc2a45b0583bfdd3a',
          'aurorae/keepabove.svg': 'eac87e2562314db8865d4383740faa050ab1b113d61747454058dbcc2c08dec8',
          'aurorae/keepbelow.svg': 'bdb1edccba39d92df5cdc02143e753b5b67302a76a490b9a95a07fd0725ebe8e',
          'aurorae/maximize.svg': 'e821c320c6783767d4c26ef9d3f73f443b12b4d536a3d8814bd6cf73aa6e9dde',
          'aurorae/metadata.json': 'ad9bb70001cf4ef5e0fde2248904f2c38c0b6d47f5324b1b87b1d8b210227eb1',
          'aurorae/minimize.svg': '373226e3773c6a07f782fc7bf59b751f32e0a8262bf18e51242a7e35429a9260',
          'aurorae/restore.svg': '29f546418f915edddf8d28728763749eb8cd53a73c5b5a87a58285231fc9d846',
          'aurorae/shade.svg': 'b04da6a54039bfc10ddc074c067ef64001d26bc74db4f1a96a17f2f674152a3a',
          'plasma-style/dialogs/background.svg': '652d1bdc39a5ffd3e4bc9210e3408b734deb43e323179edc84dd4d2345779617',
          'plasma-style/solid/dialogs/background.svg': '652d1bdc39a5ffd3e4bc9210e3408b734deb43e323179edc84dd4d2345779617',
          'plasma-style/solid/widgets/background.svg': '2d4f7afcc295bd511e44cf41b17276908618a8c21f4a9c9eb4bce53cf56e9645',
          'plasma-style/solid/widgets/tooltip.svg': '36a0a7019c7653e489de3adc21edf11db0c520c2f54c6a1d76bd69ccfa1575ad',
          'plasma-style/widgets/background.svg': '2d4f7afcc295bd511e44cf41b17276908618a8c21f4a9c9eb4bce53cf56e9645',
          'plasma-style/widgets/button.svg': 'd60873e17999bdbdd5cf5431869c6d735a5d4604299507ddc097f257e94f0a78',
          'plasma-style/widgets/line.svg': 'acf4a83394c4b18f4991b8196c143ccef3c0be3bf01c4df5a1e58f7802937e10',
          'plasma-style/widgets/lineedit.svg': '064f54b6152432a1eb6885eedf675c99c0bde30d91f99e11fe579c7a6fb0a2a8',
          'plasma-style/widgets/panel-background.svg': 'e26ed277d808af35325891bd271bd46c7225f45e041837c45e25fa36b2a3a8f1',
          'plasma-style/widgets/plasmoidheading.svg': '86bb926aac8cc465c275d30cb0272e72fbc2722a61a20febdf9c5719ec40b1e6',
          'plasma-style/widgets/scrollbar.svg': '56fb38971d8f1262f31009a264d01f427299c19a3d1c4c69d25f83443157328b',
          'plasma-style/widgets/tasks.svg': '47375e91ed530f981132e0642fcfc562b7dab5aa72072d1274568915b3bc7529',
          'plasma-style/widgets/tooltip.svg': '36a0a7019c7653e489de3adc21edf11db0c520c2f54c6a1d76bd69ccfa1575ad',
          'plasma-style/widgets/viewitem.svg': '425deae1f0d1198d7112f054601f16b262f7cdaf8b6f59cd9f8161963f74e580'},
 '1998': {'aurorae/Chicago95rc': '9e5125699277099cc0bf4a988f054d45b1a1f7332ca51d71a2c56234650cd4f8',
          'aurorae/alldesktops.svg': '49c1eb3df3605fdedb7bc60876af5cd4e2ceb46b737781e0c56e62d47344e6a3',
          'aurorae/close.svg': 'a657a6c8e130edfa202c9b3398bcad80bb32be51972e3da809aea3f959f87892',
          'aurorae/decoration.svg': '320785ddcab917059a47753b222ddbfc7f33e9cfabfe0239a561947b6332acc9',
          'aurorae/help.svg': '492485ab155696c90b17e4c7afe2f6418a8f09ec6831f4fdc2a45b0583bfdd3a',
          'aurorae/keepabove.svg': 'eac87e2562314db8865d4383740faa050ab1b113d61747454058dbcc2c08dec8',
          'aurorae/keepbelow.svg': 'bdb1edccba39d92df5cdc02143e753b5b67302a76a490b9a95a07fd0725ebe8e',
          'aurorae/maximize.svg': 'e821c320c6783767d4c26ef9d3f73f443b12b4d536a3d8814bd6cf73aa6e9dde',
          'aurorae/metadata.json': 'ad9bb70001cf4ef5e0fde2248904f2c38c0b6d47f5324b1b87b1d8b210227eb1',
          'aurorae/minimize.svg': '373226e3773c6a07f782fc7bf59b751f32e0a8262bf18e51242a7e35429a9260',
          'aurorae/restore.svg': '29f546418f915edddf8d28728763749eb8cd53a73c5b5a87a58285231fc9d846',
          'aurorae/shade.svg': 'b04da6a54039bfc10ddc074c067ef64001d26bc74db4f1a96a17f2f674152a3a',
          'plasma-style/dialogs/background.svg': '652d1bdc39a5ffd3e4bc9210e3408b734deb43e323179edc84dd4d2345779617',
          'plasma-style/solid/dialogs/background.svg': '652d1bdc39a5ffd3e4bc9210e3408b734deb43e323179edc84dd4d2345779617',
          'plasma-style/solid/widgets/background.svg': '2d4f7afcc295bd511e44cf41b17276908618a8c21f4a9c9eb4bce53cf56e9645',
          'plasma-style/solid/widgets/tooltip.svg': '36a0a7019c7653e489de3adc21edf11db0c520c2f54c6a1d76bd69ccfa1575ad',
          'plasma-style/widgets/background.svg': '2d4f7afcc295bd511e44cf41b17276908618a8c21f4a9c9eb4bce53cf56e9645',
          'plasma-style/widgets/button.svg': 'd60873e17999bdbdd5cf5431869c6d735a5d4604299507ddc097f257e94f0a78',
          'plasma-style/widgets/line.svg': 'acf4a83394c4b18f4991b8196c143ccef3c0be3bf01c4df5a1e58f7802937e10',
          'plasma-style/widgets/lineedit.svg': '064f54b6152432a1eb6885eedf675c99c0bde30d91f99e11fe579c7a6fb0a2a8',
          'plasma-style/widgets/panel-background.svg': 'e26ed277d808af35325891bd271bd46c7225f45e041837c45e25fa36b2a3a8f1',
          'plasma-style/widgets/plasmoidheading.svg': '86bb926aac8cc465c275d30cb0272e72fbc2722a61a20febdf9c5719ec40b1e6',
          'plasma-style/widgets/scrollbar.svg': '56fb38971d8f1262f31009a264d01f427299c19a3d1c4c69d25f83443157328b',
          'plasma-style/widgets/tasks.svg': '47375e91ed530f981132e0642fcfc562b7dab5aa72072d1274568915b3bc7529',
          'plasma-style/widgets/tooltip.svg': '36a0a7019c7653e489de3adc21edf11db0c520c2f54c6a1d76bd69ccfa1575ad',
          'plasma-style/widgets/viewitem.svg': '425deae1f0d1198d7112f054601f16b262f7cdaf8b6f59cd9f8161963f74e580'},
 '2000': {'aurorae/Chicago95rc': '0ea6471c77d038df90dd371f247e3b05dbec0c7340e4b197aefb1e2a4e588f2f',
          'aurorae/alldesktops.svg': '9e4f479bcc74a13a52aab9c354abc9343521a1bb744a0672f0699d2b855b0505',
          'aurorae/close.svg': '3a79961f2d6839249f182f19decc858f89ae204099edb6a8d1cc4fbd80c55cde',
          'aurorae/decoration.svg': '131dad9d8c0556a8d98b204c0e68df0234ed35fdc27a2149abcb3bc05e115646',
          'aurorae/help.svg': 'ea07cec879919dabec25e6a7abcdeae69f56c2ca91e12325f0c33d9ae6c37589',
          'aurorae/keepabove.svg': 'e09fdb9a9956f3c12c49c21efa7c06f996766c1f8452a537f4593631d434879c',
          'aurorae/keepbelow.svg': '2b1462ec9e4b8b326f4e03d9215691205ab297964a6144903e30e125adb36fe0',
          'aurorae/maximize.svg': 'da5972ca47bd7e7f05f9a2142be53983e65630dcfe169c1f3369d1d024ffe47a',
          'aurorae/metadata.json': 'ad9bb70001cf4ef5e0fde2248904f2c38c0b6d47f5324b1b87b1d8b210227eb1',
          'aurorae/minimize.svg': '4527474f5f1549dc13e81afc58cb0c2c2ef021385d7d25c0815e3709c7eccf03',
          'aurorae/restore.svg': 'd6910e83b5c6c803b911957394297c65190095c253b4b846eff4ba69b0a062f4',
          'aurorae/shade.svg': '18ba5423169a1addad00f03e965d80c8233cd57d9a48b9faf7e5ab13aa5b0a52',
          'plasma-style/dialogs/background.svg': '454ac24237f7b41a3047a87a5d5524757e03dbba6749e5a1f47d9466de1e9930',
          'plasma-style/solid/dialogs/background.svg': '454ac24237f7b41a3047a87a5d5524757e03dbba6749e5a1f47d9466de1e9930',
          'plasma-style/solid/widgets/background.svg': '31c8d460456f417fa878da6551b156dd72dcb1af2313ff589b6cd00a7999e800',
          'plasma-style/solid/widgets/tooltip.svg': 'd0551afece75764806fcca55b99269a5e8588a803002c3372c802ea2dcda0e99',
          'plasma-style/widgets/background.svg': '31c8d460456f417fa878da6551b156dd72dcb1af2313ff589b6cd00a7999e800',
          'plasma-style/widgets/button.svg': '0a8bcf8729955b9fa7095afba554a4af24f2256f6383756f2706139c5701be9b',
          'plasma-style/widgets/line.svg': 'acf4a83394c4b18f4991b8196c143ccef3c0be3bf01c4df5a1e58f7802937e10',
          'plasma-style/widgets/lineedit.svg': 'f6238a2e26e8a890d45bfce5b7b7e633423e4413dd3c7a8dcdb341b52b2cc10f',
          'plasma-style/widgets/panel-background.svg': '7104e9c3afafeb30694fef28fa5a9f09379195173a5eff1b3ab9b494e0453617',
          'plasma-style/widgets/plasmoidheading.svg': '86bb926aac8cc465c275d30cb0272e72fbc2722a61a20febdf9c5719ec40b1e6',
          'plasma-style/widgets/scrollbar.svg': '82a4776e637420a6c9e03e1cc2fe64ca7dc7a0b4163e320ae7b221fb7e15f139',
          'plasma-style/widgets/tasks.svg': '685b1e9b3a7a415bc70f787413b5e94e949b93553dca5be500948cc18624b161',
          'plasma-style/widgets/tooltip.svg': 'd0551afece75764806fcca55b99269a5e8588a803002c3372c802ea2dcda0e99',
          'plasma-style/widgets/viewitem.svg': '9f37b3895d91d0112a661b46edf20bb8be7921149b5e3e8cfa1c55afa0e1ac1c'}}


def bevel_arguments(look):
    return ["--face", look["face"], "--light", look["light"], "--shadow", look["shadow"], "--dark", look["dark"]]


def generate(name, out):
    """Runs both generators as chicago95-sync-colors does; returns {relative path: sha256}."""
    look = LOOKS[name]
    decoration, plasma_style = out / "aurorae", out / "plasma-style"
    subprocess.run(
        [
            sys.executable,
            str(AURORAE),
            "--out",
            str(decoration),
            "--active",
            look["active"],
            "--inactive",
            look["inactive"],
            "--inactive-text",
            look["inactive_text"],
            *bevel_arguments(look),
            "--gradient-margins",
            look["margins"],
        ],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [sys.executable, str(PLASMA_STYLE), "--out", str(plasma_style), *bevel_arguments(look), "--selection", look["selection"]],
        check=True,
        capture_output=True,
    )
    return {
        str(path.relative_to(out)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(out.rglob("*"))
        if path.is_file()
    }


@pytest.mark.parametrize("name", LOOKS)
def test_decoration_and_plasma_style_hashes_are_unchanged(tmp_path, name):
    assert generate(name, tmp_path) == EXPECTED_HASHES[name]


if __name__ == "__main__":
    import pprint
    import tempfile
    from pathlib import Path

    recorded = {}
    for look_name in LOOKS:
        with tempfile.TemporaryDirectory() as folder:
            recorded[look_name] = generate(look_name, Path(folder))
    print("EXPECTED_HASHES =", end=" ")
    pprint.pprint(recorded, width=120, sort_dicts=True)
