"""Programs our plasmoids start run in their own systemd scope, not in plasmashell's service: Setup
(started from the Control Panel) restarts plasmashell, and stopping its service stops every process in it."""
import re

import pytest

from conftest import REPO

PLASMOIDS = REPO / "plasmoids"


def launched_commands():
    """(plasmoid, command) for every command handed to an executable data source."""
    found = []
    for qml in sorted(PLASMOIDS.glob("org.chicago95.*/contents/ui/*.qml")):
        text = qml.read_text()
        if 'engine: "executable"' not in text:
            continue
        constants = dict(re.findall(r'property string (\w+): "([^"]*)"', text))
        for argument in re.findall(r"connectSource\(([^)]*)\)", text):
            argument = argument.strip()
            if argument.startswith('"'):
                found.append((qml.parent.parent.parent.name, argument.strip('"')))
            elif argument.startswith("root."):
                name = argument.split(".", 1)[1]
                if name in constants:
                    found.append((qml.parent.parent.parent.name, constants[name]))
    return found


def test_there_are_launches_to_check():
    assert len(launched_commands()) >= 3


@pytest.mark.parametrize("plasmoid, command", launched_commands())
def test_plasmoid_starts_programs_in_their_own_scope(plasmoid, command):
    assert command.startswith("systemd-run --user --scope --quiet --collect "), (plasmoid, command)
