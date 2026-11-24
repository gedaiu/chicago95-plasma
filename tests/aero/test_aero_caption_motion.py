"""Compare rendered Aero caption motion with the native Windows timing samples."""

import pytest
from motion import caption_times, check_timing, compare_caption_motion, compare_high_dpi_caption
from reference import REFERENCES, theme_references

FOLDER, METADATA = dict((folder.name, (folder, metadata)) for folder, metadata in theme_references(REFERENCES))["win7"]


@pytest.mark.parametrize("action,width", METADATA["motion"]["caption"].items())
def test_caption_rgb_transition_matches_vm(qt_app, action, width):
    check_timing(compare_caption_motion(action, width, caption_times(FOLDER / "motion" / f"caption-{action}")))


def test_live_close_transition_at_144_dpi():
    check_timing(compare_high_dpi_caption(FOLDER / "motion/caption-close-144dpi", METADATA["motion"]["close_scale"]))
