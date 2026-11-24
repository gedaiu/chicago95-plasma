"""Time real KWin window transitions against the Windows 7 SP1 frames."""

import shutil

import pytest
from motion import TOOLS, check_timing, compare_window_motion
from plasma_session import missing_programs
from reference import REFERENCES, theme_references

FOLDER, METADATA = dict((folder.name, (folder, metadata)) for folder, metadata in theme_references(REFERENCES))["win7"]


@pytest.mark.skipif(
    bool(missing_programs()) or any(not shutil.which(t) for t in TOOLS),
    reason="requires nested KWin, Spectacle, PipeWire and FFmpeg",
)
def test_aero_window_transitions_match_sp1(desktops, tmp_path):
    stems = [FOLDER / "motion" / f"window-{action}" for action in METADATA["motion"]["window"]]
    check_timing(compare_window_motion(desktops, tmp_path / "window-motion.webm", METADATA["look"], stems))
