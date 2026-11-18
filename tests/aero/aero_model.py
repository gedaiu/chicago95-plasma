"""The Chicago95Aero decoration laid out as KWin's Aurorae lays it out (tests/aurorae_model.py)."""

from aurorae_model import Window
from conftest import REPO

AERO_THEME = REPO / "aero/aurorae/theme"
REFERENCE_DESKTOP = "#4395D1"


class AeroWindow(Window):
    RC_NAME = "Chicago95Aerorc"

    def __init__(self, width, height, active=True, caption="", left="M", right="IAX", pressed=()):
        super().__init__(AERO_THEME, width, height, active, caption, left, right, pressed)
