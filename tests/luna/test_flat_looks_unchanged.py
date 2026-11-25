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

EXPECTED_HASHES = {
    "1995": {
        "aurorae/Chicago95rc": "9e5125699277099cc0bf4a988f054d45b1a1f7332ca51d71a2c56234650cd4f8",
        "aurorae/alldesktops.svg": "065f75da21313fadca4faed4a343180c199a947325e6d5aae6c77b81c6543b93",
        "aurorae/close-120.svg": "cc7040bfda1399beee2808879bc685edccf5668ad798bae94dfb9cb233852aba",
        "aurorae/close.svg": "40df89ee3b4ad21cf75fc4503d16319db394e82aaaf36538c1ac1062c81c487d",
        "aurorae/decoration.svg": "63210f5d927001bade6861dd9445820f2ad014309f43b64cc995de69de21b1ec",
        "aurorae/help.svg": "0a5e30dc7508c4d1dbe0a95b90afa66fcc228e123acdfaf76839fd080a825720",
        "aurorae/keepabove.svg": "75c3b158f3733f2af3318769ff6e3a4baa97f06b3f6dfe6eb77c9b7e5afcf4b7",
        "aurorae/keepbelow.svg": "d8161171e481c65f00cd17b7d0a9787697141127f86a3a2db492888a4ba588c4",
        "aurorae/maximize-120.svg": "672f5ae5c07897ef61d67e9a9a3f67b8bff1eca7cf3a0b8b204a1130dabf4654",
        "aurorae/maximize.svg": "75af77f3e50009677b00f97fc8c46e118b71d0e799e704fd3362f2e478268256",
        "aurorae/metadata.json": "ad9bb70001cf4ef5e0fde2248904f2c38c0b6d47f5324b1b87b1d8b210227eb1",
        "aurorae/minimize-120.svg": "3b9197e1e0f9a5b91b4508d67365b4184e8d681fb96d169535bdaa29a3ecf0e4",
        "aurorae/minimize.svg": "6f47f7a82f86bee05189837c9875894e20b195f14c0a616b1635fb7480bb0665",
        "aurorae/restore-120.svg": "558f5d9fed8b98405e397687cd3712c089c02f044a355eb20903cc8a91ce96bf",
        "aurorae/restore.svg": "e16c358639d183bd244adf585e70d6f7cfedc4af782019d0f0bc32e8a7c74fb4",
        "aurorae/shade.svg": "63d4d4f61f6b62551a45fc2e9e20d628bd3029b1899fbf5676590bbbdfa5e276",
        "plasma-style/dialogs/background.svg": "652d1bdc39a5ffd3e4bc9210e3408b734deb43e323179edc84dd4d2345779617",
        "plasma-style/solid/dialogs/background.svg": "652d1bdc39a5ffd3e4bc9210e3408b734deb43e323179edc84dd4d2345779617",
        "plasma-style/solid/widgets/background.svg": "2d4f7afcc295bd511e44cf41b17276908618a8c21f4a9c9eb4bce53cf56e9645",
        "plasma-style/solid/widgets/tooltip.svg": "36a0a7019c7653e489de3adc21edf11db0c520c2f54c6a1d76bd69ccfa1575ad",
        "plasma-style/widgets/background.svg": "2d4f7afcc295bd511e44cf41b17276908618a8c21f4a9c9eb4bce53cf56e9645",
        "plasma-style/widgets/button.svg": "d60873e17999bdbdd5cf5431869c6d735a5d4604299507ddc097f257e94f0a78",
        "plasma-style/widgets/line.svg": "acf4a83394c4b18f4991b8196c143ccef3c0be3bf01c4df5a1e58f7802937e10",
        "plasma-style/widgets/lineedit.svg": "064f54b6152432a1eb6885eedf675c99c0bde30d91f99e11fe579c7a6fb0a2a8",
        "plasma-style/widgets/panel-background.svg": "06bb0175649edaf741fb4eac4c536e901f6a62f72084713744f39bb77b734238",
        "plasma-style/widgets/plasmoidheading.svg": "86bb926aac8cc465c275d30cb0272e72fbc2722a61a20febdf9c5719ec40b1e6",
        "plasma-style/widgets/scrollbar.svg": "77d33d780fabf73f5ffd3c780f09d3d9d193d5d0db9da1a21502eab5cf096deb",
        "plasma-style/widgets/tasks.svg": "47375e91ed530f981132e0642fcfc562b7dab5aa72072d1274568915b3bc7529",
        "plasma-style/widgets/tooltip.svg": "36a0a7019c7653e489de3adc21edf11db0c520c2f54c6a1d76bd69ccfa1575ad",
        "plasma-style/widgets/viewitem.svg": "425deae1f0d1198d7112f054601f16b262f7cdaf8b6f59cd9f8161963f74e580",
    },
    "1998": {
        "aurorae/Chicago95rc": "9e5125699277099cc0bf4a988f054d45b1a1f7332ca51d71a2c56234650cd4f8",
        "aurorae/alldesktops.svg": "065f75da21313fadca4faed4a343180c199a947325e6d5aae6c77b81c6543b93",
        "aurorae/close-120.svg": "cc7040bfda1399beee2808879bc685edccf5668ad798bae94dfb9cb233852aba",
        "aurorae/close.svg": "40df89ee3b4ad21cf75fc4503d16319db394e82aaaf36538c1ac1062c81c487d",
        "aurorae/decoration.svg": "320785ddcab917059a47753b222ddbfc7f33e9cfabfe0239a561947b6332acc9",
        "aurorae/help.svg": "0a5e30dc7508c4d1dbe0a95b90afa66fcc228e123acdfaf76839fd080a825720",
        "aurorae/keepabove.svg": "75c3b158f3733f2af3318769ff6e3a4baa97f06b3f6dfe6eb77c9b7e5afcf4b7",
        "aurorae/keepbelow.svg": "d8161171e481c65f00cd17b7d0a9787697141127f86a3a2db492888a4ba588c4",
        "aurorae/maximize-120.svg": "672f5ae5c07897ef61d67e9a9a3f67b8bff1eca7cf3a0b8b204a1130dabf4654",
        "aurorae/maximize.svg": "75af77f3e50009677b00f97fc8c46e118b71d0e799e704fd3362f2e478268256",
        "aurorae/metadata.json": "ad9bb70001cf4ef5e0fde2248904f2c38c0b6d47f5324b1b87b1d8b210227eb1",
        "aurorae/minimize-120.svg": "3b9197e1e0f9a5b91b4508d67365b4184e8d681fb96d169535bdaa29a3ecf0e4",
        "aurorae/minimize.svg": "6f47f7a82f86bee05189837c9875894e20b195f14c0a616b1635fb7480bb0665",
        "aurorae/restore-120.svg": "558f5d9fed8b98405e397687cd3712c089c02f044a355eb20903cc8a91ce96bf",
        "aurorae/restore.svg": "e16c358639d183bd244adf585e70d6f7cfedc4af782019d0f0bc32e8a7c74fb4",
        "aurorae/shade.svg": "63d4d4f61f6b62551a45fc2e9e20d628bd3029b1899fbf5676590bbbdfa5e276",
        "plasma-style/dialogs/background.svg": "652d1bdc39a5ffd3e4bc9210e3408b734deb43e323179edc84dd4d2345779617",
        "plasma-style/solid/dialogs/background.svg": "652d1bdc39a5ffd3e4bc9210e3408b734deb43e323179edc84dd4d2345779617",
        "plasma-style/solid/widgets/background.svg": "2d4f7afcc295bd511e44cf41b17276908618a8c21f4a9c9eb4bce53cf56e9645",
        "plasma-style/solid/widgets/tooltip.svg": "36a0a7019c7653e489de3adc21edf11db0c520c2f54c6a1d76bd69ccfa1575ad",
        "plasma-style/widgets/background.svg": "2d4f7afcc295bd511e44cf41b17276908618a8c21f4a9c9eb4bce53cf56e9645",
        "plasma-style/widgets/button.svg": "d60873e17999bdbdd5cf5431869c6d735a5d4604299507ddc097f257e94f0a78",
        "plasma-style/widgets/line.svg": "acf4a83394c4b18f4991b8196c143ccef3c0be3bf01c4df5a1e58f7802937e10",
        "plasma-style/widgets/lineedit.svg": "064f54b6152432a1eb6885eedf675c99c0bde30d91f99e11fe579c7a6fb0a2a8",
        "plasma-style/widgets/panel-background.svg": "06bb0175649edaf741fb4eac4c536e901f6a62f72084713744f39bb77b734238",
        "plasma-style/widgets/plasmoidheading.svg": "86bb926aac8cc465c275d30cb0272e72fbc2722a61a20febdf9c5719ec40b1e6",
        "plasma-style/widgets/scrollbar.svg": "77d33d780fabf73f5ffd3c780f09d3d9d193d5d0db9da1a21502eab5cf096deb",
        "plasma-style/widgets/tasks.svg": "47375e91ed530f981132e0642fcfc562b7dab5aa72072d1274568915b3bc7529",
        "plasma-style/widgets/tooltip.svg": "36a0a7019c7653e489de3adc21edf11db0c520c2f54c6a1d76bd69ccfa1575ad",
        "plasma-style/widgets/viewitem.svg": "425deae1f0d1198d7112f054601f16b262f7cdaf8b6f59cd9f8161963f74e580",
    },
    "2000": {
        "aurorae/Chicago95rc": "0ea6471c77d038df90dd371f247e3b05dbec0c7340e4b197aefb1e2a4e588f2f",
        "aurorae/alldesktops.svg": "7faa0c89856d8827c9cd7863a6ee781191db1dae905f0a8fd01107ff76af691f",
        "aurorae/close-120.svg": "f2ece94a41c713f3d1a7ff4e5a0ddec9394dd1766c47454fe2e2ba29c2a11cec",
        "aurorae/close.svg": "59fb813c90fb682f90a3a469ccab3018a22817ecd5924f6124bfe510ff8f2a30",
        "aurorae/decoration.svg": "131dad9d8c0556a8d98b204c0e68df0234ed35fdc27a2149abcb3bc05e115646",
        "aurorae/help.svg": "2d047e98257fe5b19e06f817a83ef733585004a1fd90a9e3de0c4c7944659e52",
        "aurorae/keepabove.svg": "eeb5e954a5e71d9322bf75e61aade5cc9c3c5003a4e23c2455a6c6b9d10fa8f9",
        "aurorae/keepbelow.svg": "31a6a20d55607332a4f2d70accd8885f78bfd7c38b6d9a595715f05f51975e17",
        "aurorae/maximize-120.svg": "ef76f61a15455a58dcf2123d0b945e921ee0f6e67e2ca8029ef79c38e955fa0a",
        "aurorae/maximize.svg": "5542154620f0d73cfecb2f132b9e0f27a41641c68d1f202957f3a89f01e3c100",
        "aurorae/metadata.json": "ad9bb70001cf4ef5e0fde2248904f2c38c0b6d47f5324b1b87b1d8b210227eb1",
        "aurorae/minimize-120.svg": "26a949edb3978779da00dddee6fb468d56e1298684e47bfa28ef2cbd3cac9c6e",
        "aurorae/minimize.svg": "40e7259968865c3e8c280f31e603b90de0e7fe394e01bfe1a032476c6e3fd73f",
        "aurorae/restore-120.svg": "f8cdf0235425ea6d82d71b3b94b1f34339b8a159553a25dcabab6897d539c120",
        "aurorae/restore.svg": "e4b98dc77513c6c6962b63c756082a3529a89118f01670a17f58237378782d79",
        "aurorae/shade.svg": "2463a0b5dbfa94618653758b3bbb8c0f843f21cd526bb953af8116dfa1d8d403",
        "plasma-style/dialogs/background.svg": "454ac24237f7b41a3047a87a5d5524757e03dbba6749e5a1f47d9466de1e9930",
        "plasma-style/solid/dialogs/background.svg": "454ac24237f7b41a3047a87a5d5524757e03dbba6749e5a1f47d9466de1e9930",
        "plasma-style/solid/widgets/background.svg": "31c8d460456f417fa878da6551b156dd72dcb1af2313ff589b6cd00a7999e800",
        "plasma-style/solid/widgets/tooltip.svg": "d0551afece75764806fcca55b99269a5e8588a803002c3372c802ea2dcda0e99",
        "plasma-style/widgets/background.svg": "31c8d460456f417fa878da6551b156dd72dcb1af2313ff589b6cd00a7999e800",
        "plasma-style/widgets/button.svg": "0a8bcf8729955b9fa7095afba554a4af24f2256f6383756f2706139c5701be9b",
        "plasma-style/widgets/line.svg": "acf4a83394c4b18f4991b8196c143ccef3c0be3bf01c4df5a1e58f7802937e10",
        "plasma-style/widgets/lineedit.svg": "f6238a2e26e8a890d45bfce5b7b7e633423e4413dd3c7a8dcdb341b52b2cc10f",
        "plasma-style/widgets/panel-background.svg": "a606c5934f789e8dcb4ffba47b922980cd076d638a6a5f0d63b4b43e9040c63d",
        "plasma-style/widgets/plasmoidheading.svg": "86bb926aac8cc465c275d30cb0272e72fbc2722a61a20febdf9c5719ec40b1e6",
        "plasma-style/widgets/scrollbar.svg": "7a39b2b1d8e4c3c515bd6e3ce5356bb6dc246b28590e299f006a859ac1dc7842",
        "plasma-style/widgets/tasks.svg": "685b1e9b3a7a415bc70f787413b5e94e949b93553dca5be500948cc18624b161",
        "plasma-style/widgets/tooltip.svg": "d0551afece75764806fcca55b99269a5e8588a803002c3372c802ea2dcda0e99",
        "plasma-style/widgets/viewitem.svg": "9f37b3895d91d0112a661b46edf20bb8be7921149b5e3e8cfa1c55afa0e1ac1c",
    },
}


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
        [
            sys.executable,
            str(PLASMA_STYLE),
            "--out",
            str(plasma_style),
            *bevel_arguments(look),
            "--selection",
            look["selection"],
        ],
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
