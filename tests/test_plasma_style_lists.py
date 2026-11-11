"""Plasma's own list rows (the network list, the clipboard, notifications) keep their text the window text
colour when highlighted: a navy fill under black text is unreadable. Our style marks a hovered, focused or
selected row as the originals mark a focused row without a selection: an outline on the window colour."""
import re
import subprocess
import sys

import pytest

from conftest import REPO

HIGHLIGHTS = ("hover-", "focus-", "selected-", "selected+hover-")


@pytest.fixture(scope="module")
def viewitem(tmp_path_factory):
    out = tmp_path_factory.mktemp("plasma-style")
    subprocess.run([sys.executable, str(REPO / "plasma-style/make_chicago95_plasmastyle.py"), "--out", str(out)], check=True, capture_output=True)
    return (out / "widgets/viewitem.svg").read_text()


def state_colours(svg, prefix):
    groups = re.findall(rf'<g id="{re.escape(prefix)}[a-z]+">(.*?)</g>', svg, re.S)
    return {colour.lower() for group in groups for colour in re.findall(r'fill="(#[0-9a-fA-F]{6})"', group)}


@pytest.mark.parametrize("prefix", HIGHLIGHTS)
def test_highlighted_list_row_is_outlined_in_black_and_never_filled_navy(viewitem, prefix):
    assert state_colours(viewitem, prefix) == {"#000000"}
