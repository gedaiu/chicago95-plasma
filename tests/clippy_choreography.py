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
# Additional sequences inspected in full at their original 124×93 canvas.
STUDIES.update(
    {
        "Thinking": [
            (
                0,
                8,
                "Open into a ring",
                "The wire opens into a ring. One eye moves toward the center while the other stays on the ring.",
            ),
            (
                9,
                11,
                "Build crossing orbits",
                "Additional orbital loops form around the central eye; the second eye stays outside.",
            ),
            (
                12,
                33,
                "One central eye, one orbiting eye",
                "One eye remains near the center while the other travels along the orbital loops, "
                "changing apparent size with depth. Track their identities separately.",
            ),
            (34, 44, "Unwind", "The orbital loops become one circle, then curl back into the standing paperclip."),
        ],
        "Print": [
            (0, 8, "Lean and turn", "The clip tilts, blinks and rotates; the eyes become vertically stacked."),
            (
                9,
                27,
                "Turn the upper loop",
                "The tall loop pivots through side and front views while the low eyes alternate gaze and closure.",
            ),
            (
                28,
                35,
                "Lower into the sheet",
                "The upper wire straightens and drops; the lower end extends along the paper's lower edge.",
            ),
            (
                36,
                49,
                "Build the flat stack",
                "The extending wire makes successive horizontal turns stacked at the paper's bottom-right corner.",
            ),
            (
                50,
                58,
                "Retract and stand",
                "The stacked turns retract as the wire lifts and rotates back to the standing pose.",
            ),
        ],
        "Processing": [
            (0, 3, "Leave the sheet", "The body lifts and tilts while the paper flattens and separates into sections."),
            (
                4,
                15,
                "Circulate the paper",
                "Large curled paper sections rotate around the angled wire and pass in front of and behind it.",
            ),
            (
                16,
                35,
                "Alternate orbit phases",
                "The sections repeatedly turn edge-on and broadside at distinct positions around the wire.",
            ),
            (36, 37, "Reassemble", "The sections become the normal sheet as the clip returns to rest."),
        ],
        "Searching": [
            (0, 3, "Look down", "Eyes and lids turn toward the sheet while the body remains upright."),
            (
                4,
                13,
                "Roll the paper",
                "The sheet rolls upward from its lower edge into a tube, leaving the clip without its backing sheet.",
            ),
            (
                14,
                19,
                "Lift the tube",
                "The wire lifts and tilts the rolled paper toward an eye; the far end points right.",
            ),
            (
                20,
                37,
                "Scan with the telescope",
                "The paper tube extends and swings through front, side and opposite-side views.",
            ),
            (
                38,
                54,
                "Alternate scanning poses",
                "The telescope changes direction, aperture size and tilt; eyelids and gaze vary.",
            ),
            (55, 60, "Unroll and replace", "The tube opens back into the original sheet behind the clip."),
        ],
        "IdleRopePile": [
            (
                0,
                41,
                "Idle gaze and blinks",
                "The standing clip changes gaze through repeated blinks; collapse must not start during these poses.",
            ),
            (42, 57, "Slump and bend", "The wire softens into changing bends as the eyes lean and rotate."),
            (58, 65, "Drop into a coil", "The wire falls into a small coil on the paper while the eyes descend."),
            (66, 71, "Rest in the coil", "Low eyes alternate open and closed poses over the resting wire."),
            (72, 74, "Stand back up", "The coil extends and the eyes rise back to the neutral standing pose."),
        ],
        "IdleSnooze": [
            (
                0,
                12,
                "Become sleepy",
                "The standing eyes blink and remain closed briefly; the body has not yet collapsed.",
            ),
            (
                13,
                26,
                "Lie down",
                "The wire bends and settles as a flat clip lying on the curved sheet, with lowered eyes.",
            ),
            (
                27,
                45,
                "Sleeping poses",
                "The resting clip remains stretched along the sheet, with small lid and brow changes.",
            ),
            (
                46,
                82,
                "Alternate sleepy expressions",
                "Open, half-closed and closed eyes form repeatable resting variants; the wire remains lying down.",
            ),
            (83, 87, "Wake and rise", "The wire uncurls from the paper and the eyes rise to the original stance."),
        ],
        "CheckingSomething": [
            (
                0,
                5,
                "Turn the wire into glasses",
                "The clip rotates and contracts into spectacle frames around the eyes.",
            ),
            (
                6,
                14,
                "Inspect the upper sheet",
                "The glasses change tilt and expression while positioned over the paper.",
            ),
            (15, 24, "Move up the paper", "The glasses become smaller toward the far/top edge and blink there."),
            (
                25,
                39,
                "Track across the sheet",
                "The spectacles traverse the paper, with clear changes in position, size and gaze.",
            ),
            (
                40,
                49,
                "Move down and tilt",
                "The glasses approach the lower/near part of the sheet and rotate into alternative reading poses.",
            ),
            (50, 54, "Unfold to standing", "The spectacle frame extends and rotates back into the ordinary paperclip."),
        ],
        "Writing": [
            (
                0,
                7,
                "Prepare the grip",
                "The lower wire bends into a hand-like grip while the clip blinks over the existing sheet.",
            ),
            (
                8,
                12,
                "Lift and fold the sheet",
                "The full sheet swings upright and folds smaller; the pencil becomes visible at frame 11.",
            ),
            (
                13,
                25,
                "Write on the held sheet",
                "The clip holds the small sheet and pencil, making distinct writing strokes with blinks.",
            ),
            (
                26,
                31,
                "Pause and look",
                "The eyes look toward the viewer while the sheet and pencil remain held; frames 28 and 30 can repeat.",
            ),
            (
                32,
                41,
                "Alternative strokes",
                "The pencil and wire grip perform another writing phrase, with a held pose and blink.",
            ),
            (
                42,
                53,
                "Turn the sheet",
                "The paper twists and curls in the grip while the pencil moves; branching returns to "
                "earlier writing phrases.",
            ),
            (
                54,
                60,
                "Put the sheet back",
                "The paper opens through a curled shape and returns behind the standing clip; the pencil disappears.",
            ),
        ],
        "GetArtsy": [
            (
                0,
                2,
                "Turn edge-on",
                "The standing clip and sheet rotate to a thin side view; a large flattened eye replaces "
                "the frontal pair.",
            ),
            (
                3,
                10,
                "Open into a hanging mobile",
                "The rotated form spreads into an asymmetric mobile with a huge left eye, small right eye "
                "and hanging loops.",
            ),
            (
                11,
                17,
                "Hold and blink",
                "The mobile sways and the large eye closes and reopens; frame 17 holds for 2400 ms.",
            ),
            (
                18,
                22,
                "Turn back from edge-on",
                "The mobile narrows through the same side-on form before the ordinary paperclip and sheet return.",
            ),
        ],
        "GetAttention": [
            (
                0,
                2,
                "Rise and enlarge",
                "The eyes grow and the clip rises from rest, with the upper wire arch changing shape.",
            ),
            (
                3,
                15,
                "Wave the free end",
                "The enlarged character repeatedly bends and lifts its free wire end; the body and eyes "
                "bounce with it.",
            ),
            (
                16,
                19,
                "Blink while waving",
                "The eyes close at frame 17 and reopen while the free end finishes its gesture.",
            ),
            (20, 23, "Settle", "Eye size, wire arch and body position return to their rest values."),
        ],
        "Wave": [
            (0, 6, "Prepare and lift", "The free end curls upward as the eyes turn toward the viewer."),
            (
                7,
                14,
                "Wave and optional exit",
                "The end changes curl and height; normal branching skips 7–8 and exits from 14 to 26.",
            ),
            (
                15,
                25,
                "Head-down alternate",
                "An alternate/exit path flips the body into a long head-down pose, holds and blinks, then lifts back.",
            ),
            (26, 26, "Rest", "The initial silhouette and expression return."),
        ],
        "GestureUp": [
            (0, 3, "Turn and lower", "The clip leans and rotates into a broad, low loop on the paper."),
            (
                4,
                12,
                "Point upward",
                "A free wire end rises above the flattened loop; the eyes look up and blink while the pose holds.",
            ),
            (13, 16, "Stand again", "The flattened body rolls upright and the raised end retracts."),
        ],
        "GestureDown": [
            (
                0,
                3,
                "Turn horizontally",
                "The eyes rise as the body rotates into a horizontal loop across the upper sheet.",
            ),
            (
                4,
                14,
                "Point down",
                "The free end drops toward the paper below the horizontal body; lids and gaze change during holds.",
            ),
            (15, 18, "Return upright", "The horizontal loop rotates down into the normal clip."),
        ],
        "GestureLeft": [
            (
                0,
                3,
                "Turn toward screen right",
                "The body turns toward the gesture, with corresponding eye and brow movement.",
            ),
            (
                4,
                11,
                "Extend toward screen right",
                "The free end extends right; the eyes blink at frame 7 and hold the directed gaze.",
            ),
            (12, 15, "Retract and face front", "The free end retracts and the body turns back to rest."),
        ],
        "GestureRight": [
            (
                0,
                4,
                "Turn through edge-on",
                "The clip turns around its vertical axis before pointing toward screen left.",
            ),
            (
                5,
                12,
                "Extend toward screen left",
                "The free wire end points left while the eyes track it and blink at frame 8.",
            ),
            (13, 16, "Retract and rotate back", "The body passes through a narrow side view on its return."),
        ],
        "Alert": [
            (0, 2, "Prepare", "The wire and eyes begin reacting before the headphones are fully visible."),
            (
                3,
                15,
                "Headphones and vibration",
                "A headband and padded earcups surround the eyes; vibration marks and eye expressions alternate.",
            ),
            (16, 19, "Remove headphones", "The props withdraw and the character settles back to rest."),
        ],
        "Hearing_1": [
            (0, 2, "Prepare", "The character begins reacting before the headphones appear."),
            (
                3,
                30,
                "Listen and react",
                "The padded headphones vibrate; gaze, blinks and held expressions change while the prop "
                "remains attached.",
            ),
            (
                31,
                38,
                "Withdraw and settle",
                "Headphones and vibration marks disappear through the exit sequence; the neutral pose returns.",
            ),
        ],
        "Greeting": [
            (0, 6, "Paper arrives", "A thin sliver grows into the curved sheet; Clippy is not yet at full size."),
            (
                7,
                13,
                "Approach along the sheet",
                "A small clip appears at the far edge and tumbles toward the viewer, growing in perspective.",
            ),
            (
                14,
                22,
                "Close-up reaction",
                "Large eyes and a curled wire rest near the front edge with blinks and held expressions.",
            ),
            (23, 29, "Stand up", "The wire rolls and rises into the upright resting stance."),
            (
                30,
                38,
                "Alternative appearance",
                "A separate route grows small eyes and sheet into the normal pose; it is not appended to "
                "every greeting.",
            ),
        ],
        "GoodBye": [
            (0, 6, "Tip forward", "The upright clip rotates and curls toward a near-edge close-up."),
            (7, 20, "Close-up goodbye", "Large eyes, brows and curled wire hold and blink near the viewer."),
            (
                21,
                30,
                "Retreat along the paper",
                "The character turns away, becomes small and moves toward the far edge.",
            ),
            (31, 34, "Paper withdraws", "The sheet shrinks through a narrow sliver and disappears."),
            (
                35,
                37,
                "Alternative shrink exit",
                "Another route shrinks the standing clip and sheet together; it is not an ordinary final appendage.",
            ),
        ],
        "IdleSideToSide": [
            (
                0,
                16,
                "Blink between gaze holds",
                "Eye closures separate different sideways gaze poses while the wire and paper stay mostly still.",
            ),
            (
                17,
                24,
                "Second gaze phrase",
                "The eyes look in another direction, with partial and full lid closure between held expressions.",
            ),
            (
                25,
                25,
                "Invisible control junction",
                "This zero-duration frame is branch control, not visible animation artwork.",
            ),
            (
                26,
                36,
                "Further variants and return",
                "Additional blink/gaze variants lead back to the neutral eye pose.",
            ),
        ],
        "IdleHeadScratch": [
            (0, 4, "Look and blink", "The eyes and brows react before the scratch gesture develops."),
            (
                5,
                15,
                "Scratch beside the head",
                "The free end reaches up beside the upper loop and moves at the head, with changing eye expressions.",
            ),
            (16, 18, "Withdraw", "The scratching end returns and the eyes face forward."),
        ],
        "IdleFingerTap": [
            (
                0,
                4,
                "Tap the free end",
                "The lower free end moves through small tapping/curling poses, with matching gaze changes.",
            ),
            (
                5,
                7,
                "Blink and pause",
                "The eyes close at frame 5 then reopen while the wire completes the tapping pose.",
            ),
            (8, 10, "Settle", "The character returns to the initial wire and gaze state."),
        ],
        "Explain": [
            (0, 2, "Raise the brows", "The brows lift while the eyes stay open and the body remains still."),
            (3, 3, "Hold the expression", "The raised-brow expression holds for 900 ms."),
            (4, 6, "Relax", "The brows return to rest; this is not a full blink."),
        ],
        "IdleEyeBrowRaise": [
            (0, 2, "Raise the brows", "The eyebrows rise over open eyes."),
            (3, 3, "Hold", "The raised-brow pose holds for 900 ms."),
            (4, 6, "Relax", "The eyebrows return to the original pose."),
        ],
        "Show": [
            (0, 0, "Blank start", "The first source image is transparent."),
            (1, 4, "Grow into view", "Clip and paper grow through four poses on a 10-ms timing grid."),
        ],
        "Hide": [
            (0, 3, "Shrink away", "Clip and paper shrink through the reverse appearance poses."),
            (4, 4, "Blank end", "The final source image is transparent."),
        ],
        "RestPose": [
            (
                0,
                0,
                "Neutral reference",
                "Standing wire, open eyes, brows and curved ruled sheet define the shared rest pose.",
            )
        ],
    }
)
# These source directions were each visually inspected; Left/Right are the
# character's directions, so screen-space gaze is reversed horizontally.
for _name, _direction in {
    "LookRight": "screen left",
    "LookLeft": "screen right",
    "LookUpRight": "upper screen left",
    "LookUpLeft": "upper screen right",
    "LookDownRight": "lower screen left",
    "LookDownLeft": "lower screen right",
    "LookUp": "upward",
    "LookDown": "downward",
}.items():
    STUDIES[_name] = [
        (0, 2, "Direct the gaze", f"Eyes and lids turn {_direction}; body and sheet remain still."),
        (3, 3, "Hold gaze", "The directed eye pose holds for 1200 ms."),
        (4, 6, "Look forward", "Eyes and lids return to the neutral pose."),
    ]
# IdleAtom uses the same visible frames as Thinking, but different branch rules.
STUDIES["IdleAtom"] = STUDIES["Thinking"]

# These source actions are aliases; verify their DATA identity, not their names.
ALIASES = {"Congratulate": "GetWizardy", "GetTechy": "Thinking"}


def study(name):
    return STUDIES.get(ALIASES.get(name, name))


def validate_studies(actions):
    for alias, target in ALIASES.items():
        assert actions[alias] == actions[target], (alias, "Source alias changed; study needs review")
    assert set(STUDIES) | set(ALIASES) == set(actions), "Every action needs a source study"
    assert [f.get("images") for f in actions["IdleAtom"]["frames"]] == [
        f.get("images") for f in actions["Thinking"]["frames"]
    ]
    for name in STUDIES:
        covered = [i for start, end, _, _ in study(name) for i in range(start, end + 1)]
        assert covered == list(range(len(actions[name]["frames"]))), (name, "Missing or overlapping source beats")
