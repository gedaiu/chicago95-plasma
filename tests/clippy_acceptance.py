"""User-requested per-frame acceptance; never averaged over actions or backgrounds."""

MATCH_THRESHOLD = 0.98
CHANNEL_TOLERANCE = 5  # At most ~2% error in an 8-bit premultiplied channel.

# Timing alone must never be reported as completion of the reconstruction.
REQUIRED_ACTION_CHECKS = (
    "source_match_pass",
    "choreography_review_pass",
    "branch_coverage_pass",
    "blink_gaze_review_pass",
    "intermediate_collision_pass",
    "playback_pass",
)


def completion_status(source_actions, evidence):
    actions = {}
    for name in source_actions:
        checks = evidence.get(name, {})
        missing = [key for key in REQUIRED_ACTION_CHECKS if checks.get(key) is not True]
        actions[name] = {"complete": not missing, "remaining_checks": missing}
    return {
        "complete": bool(actions) and all(row["complete"] for row in actions.values()),
        "completed_actions": sum(row["complete"] for row in actions.values()),
        "total_actions": len(actions),
        "actions": actions,
    }
