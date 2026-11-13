from clippy_acceptance import REQUIRED_ACTION_CHECKS, completion_status
from clippy_all_catalog import catalog


def test_timing_and_video_success_cannot_certify_missing_choreography():
    actions = catalog()
    evidence = {name: {"timing_pass": True, "playback_pass": True} for name in actions}
    result = completion_status(actions, evidence)
    assert result["completed_actions"] == 0
    assert not result["complete"]
    assert "choreography_review_pass" in result["actions"]["SendMail"]["remaining_checks"]
    assert "blink_gaze_review_pass" in result["actions"]["Idle1_1"]["remaining_checks"]


def test_one_missing_action_or_failed_collision_keeps_library_unfinished():
    actions = catalog()
    evidence = {name: dict.fromkeys(REQUIRED_ACTION_CHECKS, True) for name in actions}
    assert completion_status(actions, evidence)["complete"]
    del evidence["Save"]
    assert not completion_status(actions, evidence)["complete"]
    evidence["Save"] = dict.fromkeys(REQUIRED_ACTION_CHECKS, True)
    evidence["Wave"]["intermediate_collision_pass"] = False
    assert not completion_status(actions, evidence)["complete"]
