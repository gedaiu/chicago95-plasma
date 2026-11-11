"""Plasma's own list rows (the network list, the clipboard, notifications) keep their text the window text
colour under the pointer: a navy fill under black text is unreadable, so a hovered or focused row gets an
outline, as the originals mark a focused row without a selection. A selected desktop icon's label turns the
highlighted text colour (white), so the selected states are filled with the selection colour, as the
originals highlight a selected icon's label."""

import re
import subprocess
import sys

import pytest
from conftest import REPO

OUTLINED = ("hover-", "focus-")
FILLED = ("selected-", "selected+hover-")


def generated_viewitem(folder, *arguments):
    subprocess.run(
        [sys.executable, str(REPO / "plasma-style/make_chicago95_plasmastyle.py"), "--out", str(folder), *arguments],
        check=True,
        capture_output=True,
    )
    return (folder / "widgets/viewitem.svg").read_text()


@pytest.fixture(scope="module")
def viewitem(tmp_path_factory):
    return generated_viewitem(tmp_path_factory.mktemp("plasma-style"))


def state_colours(svg, prefix):
    groups = re.findall(rf'<g id="{re.escape(prefix)}[a-z]+">(.*?)</g>', svg, re.S)
    return {colour.lower() for group in groups for colour in re.findall(r'fill="(#[0-9a-fA-F]{6})"', group)}


@pytest.mark.parametrize("prefix", OUTLINED)
def test_hovered_or_focused_list_row_is_outlined_in_black_and_never_filled(viewitem, prefix):
    assert state_colours(viewitem, prefix) == {"#000000"}


@pytest.mark.parametrize("prefix", FILLED)
def test_selected_item_is_filled_with_the_selection_colour_navy_by_default(viewitem, prefix):
    assert state_colours(viewitem, prefix) == {"#000080"}


def test_selected_item_takes_the_looks_selection_colour(tmp_path):
    svg = generated_viewitem(tmp_path, "--selection", "#0A246A")
    assert {state_colours(svg, prefix) == {"#0a246a"} for prefix in FILLED} == {True}
