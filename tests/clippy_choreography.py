"""Human-reviewed source beats: observations, not a claim of authored equivalence.

Frame ranges are inclusive ORIGINAL indices, never dense render indices. A beat
must survive the chosen branch path; the source atlas remains the visual oracle.
"""

STUDIES = {
    "SendMail": [
        (0, 3, "Lift away from the sheet", "Clippy rises while the sheet settles flatter beneath him."),
        (4, 7, "Fold the sheet into a plane", "The sheet changes through folds into a pointed, winged paper plane."),
        (8, 12, "Pause beside the plane", "Clippy remains beside the folded plane; an eye closure occurs at frame 10."),
        (
            13,
            18,
            "Get aboard",
            "Clippy turns sideways and moves onto the plane; the wire and plane move relative to each other.",
        ),
        (19, 23, "Take off", "The wings tilt and Clippy rides the plane as the combined silhouette recedes."),
        (
            24,
            48,
            "Flight and turns",
            "Plane and rider follow changing positions, scales and orientations, including edge-on views.",
        ),
        (49, 53, "Puff and disappearance", "Small white puffs replace the plane, disperse, then leave a blank hold."),
        (
            54,
            62,
            "Return to the ordinary sheet",
            "The small eyes and sheet return, enlarge, and settle into the original stance.",
        ),
    ],
    "Save": [
        (0, 3, "Reshape the wire", "The wire turns and opens into a box-like frame while the eyes remain expressive."),
        (
            4,
            10,
            "Raise the sheet",
            "The paper stands upright in the open wire frame; one wire end projects to the right.",
        ),
        (
            11,
            19,
            "Fold the paper down",
            "The upper sheet bends and folds through multiple orientations into the lower frame.",
        ),
        (20, 23, "Close the frame", "The projecting wire closes around the compact paper and low-positioned eyes."),
        (24, 33, "Hold the packed shape", "The compact outline remains while eyes, brows and lids change expression."),
        (34, 39, "Open and unpack", "The eyes rise; wire and paper rotate and unfold back toward the upright stance."),
        (40, 41, "Settle at rest", "The normal paper and paperclip silhouette are restored."),
    ],
    "EmptyTrash": [
        (0, 2, "Open into a coil", "The wire bends from the standing clip into a broad horizontal coil."),
        (3, 15, "Spin into a funnel", "The coil becomes a tapering funnel; paper pieces and eyes rotate around it."),
        (
            16,
            28,
            "Pull the paper inward",
            "The paper rolls and shrinks into the spinning funnel instead of remaining rigid strips.",
        ),
        (29, 32, "Shrink and disappear", "The funnel rapidly shrinks and gives way to an empty hold."),
        (33, 41, "Return and settle", "Eyes and paper reappear small and return to the standing rest pose."),
    ],
    "GetWizardy": [
        (0, 6, "Straighten the wire", "The wire rotates and extends diagonally; eyes move down toward the paper."),
        (7, 10, "Long-handle pose", "A long narrow wire shaft points upper-right with the eyes at its lower end."),
        (
            11,
            15,
            "Hold and change expression",
            "The transformed outline is held; lids and brows change, including closure at frame 13.",
        ),
        (16, 21, "Curl back to rest", "The straight wire curls back through intermediate shapes and returns upright."),
    ],
    "Idle1_1": [
        (0, 1, "Neutral entry and gaze hold", "Frame 0 may branch to the eyebrow sequence; frame 1 can repeat."),
        (2, 4, "Close and reopen", "Frame 2 closes the lids; frame 3 reopens partway; frame 4 holds a gaze pose."),
        (
            5,
            17,
            "Blink between gaze variants",
            "Closures at 5, 8, 11 and 14 separate alternative gaze poses and repeatable holds.",
        ),
        (
            18,
            35,
            "Asymmetric eye expressions",
            "The eye apertures and gaze are not symmetric; several poses have separate looping holds.",
        ),
        (36, 36, "Neutral exit junction", "The neutral pose can exit directly to frame 42 when stopping."),
        (37, 41, "Brow movement", "The eyes remain open while the brows change; frame 39 holds for 900 ms."),
        (42, 42, "Neutral end", "The source uses the same atlas image as its initial rest pose."),
    ],
}
# These source actions are aliases; verify their DATA identity, not their names.
ALIASES = {"Congratulate": "GetWizardy"}


def study(name):
    return STUDIES.get(ALIASES.get(name, name))


def validate_studies(actions):
    for alias, target in ALIASES.items():
        assert actions[alias] == actions[target], (alias, "Source alias changed; study needs review")
    for name in STUDIES:
        covered = [i for start, end, _, _ in study(name) for i in range(start, end + 1)]
        assert covered == list(range(len(actions[name]["frames"]))), (name, "Missing or overlapping source beats")
