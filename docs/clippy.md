# Clippy artwork and the 3D prototype

HD Clippy artwork is in `data/clippy/hd-animations`: 496×372 transparent frames
at four times the original logical resolution, with 22 playable sequences.
The set includes four gaze directions, four pointing directions, eyebrow raise,
wave, greeting/goodbye, thinking, head scratch, celebration, writing, reading,
sleep/wake, snoozing, blink and rest. Gaze and blink composite eye layers onto
one fixed master to prevent body/paper movement.

Open an independent preview and right-click **HD animations** to select a clip:

```sh
python3 bin/chicago95-clippy --artwork hd --preview --mute
```

The original complete atlas remains the default. HD is a new keyframe set, not
an exact redraw of all 43 original clips. Each gesture group has four drawn poses;
greeting/goodbye share wave artwork, and wake reverses the sleep poses. The
manifest explicitly lists reused clips for assistant events such as Hide and Alert.
The installer includes the pack; `--artwork hd` also works after installation.
It copies only playback assets, excluding Blender files, generated source sheets
and review videos from the installed assistant directory.
Generated source sheets and the exact built-in image-generation prompts are
recorded in `data/clippy/hd-sources/provenance.json`.

```sh
python3 -m pytest tests/test_clippy_hd.py tests/test_clippy_hd_pack.py
python3 tests/render_clippy_hd_pack.py --output /tmp/clippy-hd-review
python3 tests/audit_clippy_hd_edges.py --output /tmp/clippy-hd-edges
```

The renderer saves a combined `all-animations.mp4`, individual clips, a contact
sheet, every keyframe, and timing metadata. Recordings show both large and normal
sizes. The output directory must be new. Add `--build` to rebuild the checked-in
pack from its source sheets. The pack includes the blink study; the redundant
standalone blink export and renderer have been removed.

The edge audit renders every frame on white, dark and magenta backgrounds and
fails if alpha above 8/255 remains more than two physical pixels outside the
solid silhouette, or if fully transparent pixels retain RGB residue. The build
uses deterministic alpha cleanup, preserving visible RGB colors and contour
antialiasing. This catches background haze that a teal-only preview hides;
it does not certify pose consistency or smooth motion. Corrected pointing poses
and their generation prompt are in `data/clippy/hd-sources/corrected-poses`.

The separate **3D calibration prototype** uses Fog's downloaded Clippy model,
retained with attribution in `data/clippy/3d-prototype/provenance.json`. It adjusts
the paper and metal materials, repairs the paper texture, replaces the missing
environment with controlled lights, and exercises the model's existing eyelid
and wire rig. `tests/clippy_3d_fit.py` fits the paper outline, body lean, and eye
centers to explicit original 124 × 93 landmarks. The turn keeps the eyes separated
and extends the pointing end outward while checking wire clearance. The approved
material settings and camera are preserved; source.blend remains untouched. It does not replace the running assistant or certify an original
animation match.

```sh
blender -b --factory-startup --disable-autoexec --python-exit-code 1 \
  --python tests/render_clippy_3d.py -- --output /tmp/clippy-3d-review --animate
python3 tests/review_clippy_3d.py /tmp/clippy-3d-review
```

Use a new output directory. The renderer saves a self-contained `calibrated.blend`,
transparent frames and timings. The review produces `materials-comparison.png`,
`prototype-comparison.mp4`, and numeric color/silhouette comparisons at 124×93.
It verifies that the rig returns to the identical rest render. Video durations
are normalized for comparison; original ACS branching is not simulated. Paper
geometry, eye shapes, and exact motion remain prototype limitations. The leftward gesture turns the body before extending the free end outward,
so the wire does not cross itself. The blink uses a horizontal hinge instead
of the rig's tilted local axes.

Run the motion regression check with Blender:

```sh
blender -b --factory-startup --disable-autoexec --python-exit-code 1 \
  --python tests/check_clippy_3d_motion.py -- --output /tmp/clippy-motion-checks.json
```

It checks wire clearance at 122 pointing poses, rejects the former intersecting
pose, and verifies the intended body turn, viewer-facing eyes, fixed camera
and paper, and 31 blink poses. Clearance uses the smoothed wire centerline
and Skin radius; this checks the prototype motions, not arbitrary future poses.

For low-resolution visual inspection, compare every original frame with the
nearest available prototype pose at **124 × 93**:

```sh
python3 tests/overlay_clippy_3d.py /tmp/clippy-3d-review \
  --output /tmp/clippy-low-resolution-review
python3 -m pytest -q tests/test_clippy_3d_overlay.py
```

Use a new output directory. Every frame gets lossless original/new PNGs, a
50/50 overlay, amplified color difference, alpha difference, and alternating GIF.
Contact sheets and video enlarge those low-resolution pixels with nearest-neighbor
filtering. Downsampling uses premultiplied alpha; no per-frame alignment, cropping,
or fitting is applied. `pose-overlay.mp4` uses explicit nearest-pose mappings and
original durations; `timeline-overlay.mp4` compares actual elapsed time without
retiming and holds ended sequences on their final frame. `report.json` records
input hashes, mappings, missing expressions, and difference metrics. These are
inspection artifacts, not a visual-fidelity pass or exact reconstruction.

Export a rendered sequence to transparent WebM and a teal-background MP4 preview:

```sh
python3 tests/export_clippy_video.py /tmp/clippy-3d-review \
  --output /tmp/clippy-video-export
```

The exporter preserves manifest durations, decodes every WebM frame with libvpx,
and checks that its alpha channel exactly matches the input PNG. It also fully
decodes the MP4 and verifies its frame count. Playback transparency requires a
WebM-alpha-capable player; MP4 is the opaque preview. Export checks do not certify
artwork fidelity.

The source-indexed renderer now emits one pose for every original frame in the
selected rest/blink/pointing sequences, using the original durations. The gesture
progress curves each contain one extension, one hold, and one retraction. These
are authored approximations of the poses, not reconstructed original animation
curves. Run the overlay with `--require-acceptance` to fail if **any** frame misses
98% silhouette IoU or 98% foreground premultiplied-RGB similarity. Empty background
pixels do not contribute to the color score. Pose correctness still needs visual
review even if both numeric scores pass.

Editable Blender Actions can be baked and checked against the procedural poses:

```sh
blender -b --factory-startup --disable-autoexec --python-exit-code 1 \
  --python tests/bake_clippy_3d_actions.py -- \
  --source /tmp/clippy-3d-review/calibrated.blend \
  --output /tmp/clippy-3d-review/animated.blend
```

Each Action has source-frame markers and constant interpolation to retain the
original frame holds at 100 fps. Baking verifies all 39 keyed poses against their
source rig matrices. The `.blend` opens on `Clippy_GestureRight`; other Actions
are available in Blender's Action Editor.

Use the stricter independent fidelity validator for acceptance, rather than the
whole-image overlay score:

```sh
python3 tests/validate_clippy_fidelity.py /tmp/clippy-3d-review \
  --video /tmp/clippy-video-export/clippy-transparent.webm \
  --output /tmp/clippy-fidelity-validation
python3 -m pytest -q tests/test_clippy_fidelity.py tests/test_clippy_3d_overlay.py
```

It exits nonzero on failure and writes an HTML failure browser, annotated frames,
and detailed JSON. Nine fixed inspection windows cover eyes, wire, tips and paper
edges; they are not exact semantic masks. Each window must have at least 98% of
foreground pixels within 5/255 in every premultiplied RGB and alpha channel.
Every frame must also reach 98% alpha silhouette IoU, with symmetric boundary
p95 distance at most one native pixel and maximum distance at most two pixels.
Signed pixel changes validate motion between actual frames, independently of the
renderer progress curves. Frame count and durations must match the original.

The optional WebM audit decodes every video frame (including intermediate holds)
and compares it at its actual presentation timestamp against the source atlas.
The validator records input hashes and never realigns the images. Mutation tests
cover hidden local eye errors, paper-edge damage, shifted frames, wrong tips,
frozen/reversed motion, a doubled gesture, incorrect durations and lost alpha.
Passing these checks would still require visual review of expression/depth and
the separate Blender collision checks. The current reconstruction fails fidelity
validation; timing and file-export correctness alone do not make it acceptable.

For actionable geometry measurements, use the reference-landmark audit:

```sh
python3 tests/clippy_geometry_audit.py /tmp/clippy-3d-review \
  --output /tmp/clippy-geometry-audit
python3 -m pytest -q tests/test_clippy_geometry_audit.py
```

The HTML report shows pupil displacement vectors and sampled exposed paper
contours in native pixels. Upper-wire overlap is measured above the paper rather
than combined with its large area. Positive x means the candidate is too far
right; positive y means it is too low. Pupil error must be at most one pixel;
at least 98% of sampled contour positions must lie within one pixel. Missing or
ambiguous open-eye detections fail. Closed-eye pupil measurements are explicitly
not applicable; the strict image validator still checks those frames.

`tests/fixtures/clippy/reference-landmarks.json` freezes the original-only pupil
annotations, including five visually selected components where automatic detection
was ambiguous/missing. Atlas, animation-definition and per-frame hashes prevent
silent target changes. Candidate points are measured within eight pixels of the
reference search prior, without translating or registering the image. The full
fidelity validator also applies these geometry checks to PNGs and decoded WebM
frames. Synthetic displacement tests verify exact reported offsets, and all 39
original frames must pass identity comparison. These measurements are diagnostics,
not an assertion that projected contours establish the correct 3D paper surface.

The complete Blender library covers all **43 original action names and 1,233
source poses**, including wire morphs and editable paper, pencil, glasses,
headphone, telescope, scissors, mobile, and paper-plane elements. Build and review
it with Blender 4.5 LTS (the user-provided model remains unchanged):

```sh
blender -b --factory-startup --disable-autoexec --python-exit-code 1 \
  --python tests/build_clippy_3d_library.py -- \
  --output /tmp/clippy-library-raw --samples 192
blender -b --factory-startup --disable-autoexec --python-exit-code 1 \
  --python tests/repair_clippy_library.py -- \
  --blend /tmp/clippy-library-raw/all-animations.blend \
  --manifest /tmp/clippy-library-raw/manifest.json --output /tmp/clippy-wire-repaired
blender -b --factory-startup --disable-autoexec --python-exit-code 1 \
  --python tests/position_clippy_face.py -- \
  --folder /tmp/clippy-wire-repaired --output /tmp/clippy-face-placed
blender -b --factory-startup --disable-autoexec --python-exit-code 1 \
  --python tests/repair_clippy_attention.py -- \
  --folder /tmp/clippy-face-placed --output /tmp/clippy-attention-repaired
blender -b --factory-startup --disable-autoexec --python-exit-code 1 \
  --python tests/repair_clippy_attention.py -- --action Wave \
  --folder /tmp/clippy-attention-repaired --output /tmp/clippy-wave-repaired
blender -b --factory-startup --disable-autoexec --python-exit-code 1 \
  --python tests/repair_clippy_attention.py -- --action IdleSnooze \
  --folder /tmp/clippy-wave-repaired --output /tmp/clippy-library
blender -b --factory-startup --disable-autoexec --python-exit-code 1 \
  --python tests/render_clippy_library.py -- --folder /tmp/clippy-library
python3 tests/review_clippy_library.py /tmp/clippy-library
python3 tests/review_clippy_library.py /tmp/clippy-library --review-only
```

`index.html` links individual and combined MP4/WebM videos, and original/new/50%
overlays for every frame at the original 124×93 resolution. Renders are 744×558.
Both rendering and video export support disjoint `--shard N --shards M` workers;
rendering also supports `--preview` for three inspection frames per action. The
exporter can select individual actions with `--actions NAME [NAME ...]`.

`all-animations.blend` contains one editable timeline with named action markers;
its `CLIPPY_CLIP_RANGES.json` text block records each range. Baking re-evaluates
all 1,233 poses and rejects any changed transform, wire coordinate, paper vertex,
or visibility state. Sampled wire-centerline separation is checked during morph
construction; this is not a complete surface-collision proof. The zero-duration
branch-control pose is retained outside the timed playback range. Videos retain
all source frame holds in linear order; random branching is preserved as metadata
and is not a runtime behavior test.

The library audit verifies source metadata, timing, frame counts, PNG dimensions,
and decoded video transparency. It separately reports silhouette overlap and
foreground color similarity, with no background-dominated score. **The new actions
are reconstructions, not certified 98% matches.** The strict landmark tests above
cover the original four-action prototype; they do not establish fidelity for all
43 morphing actions. Run the exporter regression along with those tests:

```sh
python3 -m pytest -q tests/test_clippy_library_export.py \
  tests/test_clippy_geometry_audit.py tests/test_clippy_fidelity.py \
  tests/test_clippy_3d_overlay.py
```

Generated Clippy previews, videos, reports, and baked Blender masters are local,
Git-ignored build outputs. The original and calibrated Blender inputs, runtime
artwork, and build/test scripts remain tracked. The links below refer to the local
review bundle; a fresh checkout must generate the outputs using the commands above.

The local [animation preview](../data/clippy/3d-prototype/preview-60fps/index.html)
contains all 43 individual clips, the combined video, slow playback controls, and
native-resolution comparisons. The editable master is
[`all-animations.blend`](../data/clippy/3d-prototype/preview-60fps/all-animations.blend). The preview
package retains video/export reports; raw render PNGs are reproducible with the
commands above and are not duplicated in that package.

The current acceptance target is **98% per frame**, defined centrally in
`tests/clippy_acceptance.py`. It applies independently to silhouette IoU and
foreground color similarity. Local inspection windows additionally require 98%
of active pixels within 5/255 per premultiplied channel; signed changes between
frames check motion. The all-action validator uses the actual reference frame
order and durations, without registering or shifting images:

```sh
python3 tests/validate_clippy_library_fidelity.py /tmp/clippy-library-complete \
  --output /tmp/clippy-source-98
```

This exits nonzero when any frame fails. The saved
[98% report](../data/clippy/3d-prototype/preview-60fps/validation/repaired-98/index.html)
shows that the existing library does **not** meet the target. Raising the threshold
does not improve the artwork; the report is a failure diagnostic.

Check evaluated triangle surfaces at every source keyframe with:

```sh
blender -b --factory-startup --disable-autoexec --python-exit-code 1 \
  --python tests/audit_clippy_collisions.py -- \
  --blend data/clippy/3d-prototype/preview-60fps/all-animations.blend \
  --manifest data/clippy/3d-prototype/preview-60fps/manifest.json \
  --output /tmp/clippy-collisions.json --require-no-wire-intersections
blender -b --factory-startup --disable-autoexec --python-exit-code 1 \
  --python tests/check_clippy_surface_collisions.py
python3 -m pytest -q tests/test_clippy_collision_geometry.py
```

The surface audit excludes shared vertices (including duplicated cap seams) from
self contacts, records eye/pupil construction contacts separately, and checks
all visible object pairs. The optional gate fails on any wire self-intersection;
it does not certify containment, all prop contacts, or motion between keyframes.
The independent fixtures catch crossings between sampled vertices, overlapping
bounding boxes without an actual intersection, and valid connected seams.

[The complete collision review](../data/clippy/3d-prototype/preview-60fps/collisions.html)
records zero wire or prop self-intersections across all 1,233 keyed poses.
The source eye/pupil construction intersects internally, and contacts between
separate objects remain recorded for review. This is not a blanket collision-free
or 98%-matched certification. Superseded Blender snapshots and review bundles
have been removed; the original source, calibration input and current master remain.

The newer [repaired Blender candidate](../data/clippy/3d-prototype/preview-60fps/all-animations.blend)
corrects the 319 wire-intersecting poses and smooths the metal eyelids. The
[eye-rim comparison](../data/clippy/3d-prototype/preview-60fps/eye-rims-before-after.png)
shows the overlapping-shell defect beside the corrected render. The lower metal
shell is inset by 0.5% so its surface no longer coincides with the upper shell.
Eyelids also use subdivided smooth geometry; production renders use 192 samples
and denoising. This is still
a reconstruction, not an accepted 98% source match.

`tests/check_clippy_eyelid_surfaces.py -- --folder <render-folder>` runs inside
Blender and reproduces the original defect in memory. It casts rays through both
visible rims, verifies that the corrected shells have no nearly coincident hits,
and checks that applying the correction twice leaves the geometry unchanged.

`tests/repair_clippy_library.py` adjusts wire depth using evaluated triangle
intersections, then checks all 1,233 baked poses. `tests/position_clippy_face.py`
keeps the face in front of the repaired wire while preserving its camera
projection and scaling the face lighting consistently. The candidate retains
both verification reports. Videos exported with `--fps 60` hold those audited
poses; cumulative boundary rounding limits timing error to half an output frame
(8.34 ms) without accumulating drift. It does not add interpolated movement.
Consequently these exports are timing/pose reviews, not finished smooth 60-fps
animations. True 60-fps motion requires rendering intermediate Blender poses,
preserving intentional holds and source branch/exit behavior, and auditing the
evaluated geometry at every output frame rather than only at source keyframes.
Ten 10-ms source poses receive no frame in the individual 60-fps clips; all source
poses, including these, remain in the native-resolution comparison sheets.

Show uses the size and centre measured from each original frame, preserving the
blank start and five 10-ms holds. Its visual audit rejects bounds more than one
native pixel from the original. The preview plays this entrance once and holds
the final rest pose instead of continuously looping the 50-ms transition.
Hide uses the same source sequence in reverse, ending fully transparent. It has
the same size/position audit and plays once instead of looping the exit.

The local [GetAttention repair review](../data/clippy/3d-prototype/preview-getattention/index.html)
contains the corrected clip and all-frame before/after comparison. Its separate
candidate master also preserves the pending Hide correction. The older combined
library video has not been regenerated with these changes.
`tests/repair_clippy_attention.py` separates the enlarged eye assemblies and places
the face, original wire, and paper in disjoint depth ranges. It rejects every
remaining surface contact except internal eye assembly/pupil construction, checks
all 24 baked poses and all 159 held playback samples, and verifies the other 1,209
poses are unchanged. This does not validate future interpolated motion.

The same repair supports Wave via `--action Wave`. The local
[Wave review](../data/clippy/3d-prototype/preview-wave/index.html) contains its corrected
clip and every-frame comparison. It checks all 27 source poses, reopens the saved
master for a second contact audit, and verifies 294 held playback samples; 1,206
other keyed poses remain unchanged. This clip preserves the source holds and
does not yet add smooth intermediate motion.

The local [IdleSnooze review](../data/clippy/3d-prototype/preview-snooze/index.html)
uses the same repair with `--action IdleSnooze`. All 88 source poses are checked
again after reopening the saved master; the 816 held playback samples retain
the original 13.6-second linear sequence. The repair separates the wire from the
paper and the face, while preserving the other 1,145 keyed poses. Internal eye
construction remains recorded. This is a collision repair, not a source-fidelity
certification or a smooth-motion update; the older combined video is unchanged.

```sh
blender -b --factory-startup --disable-autoexec --python-exit-code 1 \
  --python tests/repair_clippy_attention.py -- --action Wave \
  --folder /tmp/clippy-library --output /tmp/clippy-wave
blender -b --factory-startup --disable-autoexec --python-exit-code 1 \
  --python tests/render_clippy_library.py -- --folder /tmp/clippy-wave --actions Wave
python3 tests/export_clippy_video.py /tmp/clippy-wave \
  --output /tmp/clippy-wave/videos/Wave --actions Wave --fps 60
```

The local [CheckingSomething review](../data/clippy/3d-prototype/preview-checking/index.html)
is a separate single-animation candidate with 398 individually rendered poses at
60 fps. It adds continuous entrance/return motion and checks the reopened baked
geometry at every output sample. The wire contraction and glasses introduction
are reconstructed transitions, not a certified recreation of the original morph.
Internal eye construction and glasses bridge/frame joints remain; eye/glasses,
eyebrow/glasses, wire/face and paper intersections are rejected. Size checks also
reject collapsed glasses, which collision tests alone cannot detect.

```sh
blender -b --factory-startup --disable-autoexec --python-exit-code 1 \
  --python tests/repair_clippy_checking.py -- \
  --folder /tmp/clippy-library --output /tmp/clippy-checking
blender -b --factory-startup --disable-autoexec --python-exit-code 1 \
  --python tests/render_clippy_library.py -- --folder /tmp/clippy-checking
python3 tests/review_clippy_checking.py /tmp/clippy-checking
```

This review checks matching endpoint geometry and pixels within one 8-bit level, unclipped artwork, distinct
intermediate renders, and decoded video transparency. The animation keeps the
original 6.64-second linear sequence to within one 60-fps sample; branch-driven
interactive playback and the older combined library video are not updated here.

The local [GetArtsy transition review](../data/clippy/3d-prototype/preview-artsy/index.html)
is an isolated 4.9-second candidate with 294 independently rendered 60-fps poses.
It reconstructs the idle wire before interpolation, fades the paper and reveals
the mobile continuously over 600 ms, and returns to the identical idle pose.
Every saved output pose is checked for intersections; intended mobile joints and
internal eye construction remain. This repairs continuity, not original-image
fidelity, and does not replace the installed assistant or combined library.

```sh
blender -b --factory-startup --disable-autoexec --python-exit-code 1 \
  --python tests/repair_clippy_artsy.py -- \
  --folder /tmp/clippy-library --output /tmp/clippy-artsy
blender -b --factory-startup --disable-autoexec --python-exit-code 1 \
  --python tests/render_clippy_library.py -- --folder /tmp/clippy-artsy
python3 tests/review_clippy_artsy.py /tmp/clippy-artsy
```

The local [Writing source comparison](../data/clippy/3d-prototype/preview-writing/index.html)
contains an original/previous/candidate video, every-frame overlays, and the strict
source-match report. This candidate replaces the early disappearing sheet and
blank notepad with reference-derived paper outlines, follows the source pencil
positions, and fits a smooth wire toward the original metal outline. The curl,
depth and facial acting remain reconstructed: it is **not a finished 98% match**.

```sh
python3 tests/clippy_writing_reference.py --output /tmp/clippy-writing-reference.json
blender -b --factory-startup --disable-autoexec --python-exit-code 1 \
  --python tests/repair_clippy_writing.py -- --folder /tmp/clippy-library \
  --landmarks /tmp/clippy-writing-reference.json --output /tmp/clippy-writing
blender -b --factory-startup --disable-autoexec --python-exit-code 1 \
  --python tests/render_clippy_library.py -- --folder /tmp/clippy-writing
python3 tests/review_clippy_writing.py /tmp/clippy-writing --before /tmp/clippy-library
```

The review writes its artifacts and exits nonzero if any source frame fails the
98% visual/motion gate. Geometry checks separately reopen all 61 poses and verify
surface contacts, continuous paper visibility, source pencil placement, and the
original 8.4-second timing and branch metadata. Exports hold source poses; smooth
intermediate motion, branch playback, and the old combined video are not updated.

## Source-driven playback and 60-fps timing

The [source-timed review](../data/clippy/3d-prototype/preview-source-timed/index.html)
replaces linear frame-list playback for timing review. `agent.js` durations are
**display holds**. Its weighted branches and exit branches determine which pose
comes next; summing every listed duration is not generally an animation's length.
For example, Wave has unconditional jumps that skip frames, and Writing contains
loops. Microsoft documents [frame holds, branches and return animations](https://learn.microsoft.com/en-us/windows/win32/lwef/creating-animations).
Clippy.js [draws each frame before its duration timer](https://github.com/clippyjs/clippy.js/blob/master/src/animator.js)
and its [ordinary play method requests exit after five seconds by default](https://github.com/clippyjs/clippy.js/blob/master/src/agent.js).
That timeout is player policy, not an intrinsic animation length.

`clippy_playback_timeline.py` creates deterministic branch traces with explicit
source indices, timestamps, branch choices, sound cues and stop requests. The
review uses one reproducible path per action, requesting a graceful stop at
5000 ms. It never silently truncates a nonterminating path. Unit tests also exercise
multiple random paths and stop requests at every visited boundary. These tests
cannot prove equivalence with every historical Office/Agent host.

`retime_clippy_library.py` places source poses at their exact timestamp on a
60-fps Blender timeline, retaining fractional keyframe positions. For example,
110 ms is frame 7.6 with frame 1 at time zero. Numeric channels interpolate during
the last at most 100 ms of a display interval; longer intervals retain a still
prefix. Visibility stays discrete. This interpolation policy is reconstructed,
not encoded in the original sprite data. It deliberately avoids stretching a
short movement across a multi-second hold. Repeated self-loop poses remain still.
The last pose holds until the traced end; no invented return-to-idle is appended.

All 1,233 source poses remain in a separate reference bank, including alternatives
not visited by the chosen path and the zero-duration control frame. The saved
master is reopened to check every source anchor, every playback occurrence, and
hold interiors against the input channel values. The image review uses source
indices from the trace, never dense output indices, to select original atlas
images. A 10-ms pose may fall between 60-fps samples; its exact subframe key and
separate comparison remain available. Video lengths are rounded to the nearest
60-fps sample, at most 8.34 ms from the traced duration.

```sh
blender -b --factory-startup --disable-autoexec --python-exit-code 1 \
  --python tests/retime_clippy_library.py -- \
  --folder /tmp/clippy-library --output /tmp/clippy-source-timed
blender -b --factory-startup --disable-autoexec --python-exit-code 1 \
  --python tests/prepare_clippy_timing_review.py -- \
  --folder /tmp/clippy-source-timed --output /tmp/clippy-source-timed-review
blender -b --factory-startup --disable-autoexec --python-exit-code 1 \
  --python tests/render_clippy_library.py -- --folder /tmp/clippy-source-timed-review
python3 tests/review_clippy_timing.py /tmp/clippy-source-timed-review
```

The small review uses 248×186 renders and 16 samples. Its cache reuses only
identical complete animation-channel states, preserving genuine still holds;
other output frames are rendered at their own Blender time. The original-size
master manifest retains 744×558/64-sample settings for a full-resolution export.
Review PNGs, videos and Blender masters remain ignored authoring outputs.

Timing acceptance is separate from art acceptance. This retiming reuses the full
source-pose library; it does not merge the standalone CheckingSomething, Writing
or GetArtsy art candidates. Those earlier videos use different reconstructed
motion and must not be treated as source-playback timing references. Native-size
image comparisons still expose the unfinished 98% fidelity requirement, and
new intermediate geometry requires collision review before runtime integration.

## Choreography rebuild status

All 43 animations remain **unfinished**. The [original-source study](../data/clippy/3d-prototype/preview-choreography/index.html)
now records the observed action beats and inclusive original frame ranges for every
sequence, with complete native-size storyboards. These are source observations,
not certification of the existing 3D recipes. Important omissions include the
SendMail folds/boarding/flight/puff, Save packing and unpacking, Searching's rolled
paper telescope, GetArtsy's edge-on rotation, asymmetric idle eyelids, and alternate
head-down/appearance/exit paths. A generic shape morph or paper fade cannot replace
those actions.

`clippy_branch_coverage.py` finds legal normal/stop routes covering every reachable
source frame. Stop state is monotonic, each edge is checked against the playback
rules, and unreachable source frames are explicitly listed instead of inventing
transitions. A single seeded demonstration may omit a complete transformation;
IdleAtom's immediate exit and Wave's head-down alternative are regression cases.
All original frames, including unreachable alternatives, remain in the study.

`audit_clippy_timed.py` audits actual evaluated triangle surfaces for every 60-fps
output sample. The initial source-timed candidate has been checked at all 9,227
samples. The report retains contacts requiring classification; it does not treat
all detected contacts as unintended penetration or claim containment safety.
Cache entries are tied to the exact Blender file hash. Source indices in this
report come from playback metadata, not the dense output index.

`completion_status` in `clippy_acceptance.py` requires all six gates for **every**
source action: source image match, choreography, branch coverage, blink/gaze,
intermediate collisions, and playback. Missing evidence is failure. Timing or
video-export success alone cannot make an animation or the library complete.
The current completion ledger is 0/43; no keyframes were changed during this
source-study/audit pass.

```sh
blender -b --factory-startup --disable-autoexec --python-exit-code 1 \
  --python tests/audit_clippy_timed.py -- \
  --folder /tmp/clippy-source-timed-review --output /tmp/clippy-timed-collisions
blender -b --factory-startup --disable-autoexec --python-exit-code 1 \
  --python tests/audit_clippy_timed.py -- \
  --folder /tmp/clippy-source-timed-review --output /tmp/clippy-timed-collisions --summarize
python3 tests/review_clippy_choreography.py \
  --output data/clippy/3d-prototype/preview-choreography \
  --collisions /tmp/clippy-timed-collisions/report.json
```


## Shared rest-pose calibration (unfinished)

The isolated calibration now changes actual paper vertices, wire dimensions,
eye geometry, and material parameters. It does not replace animation keyframes or
runtime assets. `fit_clippy_rest_eyes.py` evaluates each trial as a 744×558 Blender
render through the same premultiplied-alpha Lanczos reduction used by the normal
124×93 comparison. `fit_clippy_rest_materials.py --hd-python /usr/bin/python3`
uses that same full-resolution path for material fitting. Native-resolution
proxy optimization alone is insufficient: the paper-surface experiment improved
its fitting loss but regressed the independently measured color score.

`review_clippy_rest_fit.py` records independent measurements and render/master
hashes, publishes original/candidate/overlay/difference panels, and explicitly
marks regressions. All stages remain experiments until the full acceptance gates
pass; no score is averaged across animations to hide failed frames.

```sh
python3 tests/review_clippy_rest_fit.py /tmp/clippy-rest-fit \
  data/clippy/3d-prototype/preview-rest-fit
```

The authoring Blender files and generated comparison images remain ignored.
The review reports the 98% image threshold separately from animation acceptance.

Body-light calibration uses `fit_clippy_rest_lighting.py --folder
/tmp/clippy-rest-fit --python /usr/bin/python3` under Blender. It adjusts the
body key light's position, size and energy and the body fill energy, while keeping
the separate eye lights, camera, geometry and source fixed. Trials use full-size
renders and native comparisons. The published final image is rendered after
reopening the saved Blender file, rather than copied from the fitting cache.
This rest-pose experiment does not certify lighting across other source poses.

The optional `--paper-depth` pass starts from that lighting candidate. It changes
paper distance with a camera-centred scale, preserving projected placement, and
rejects trials with evaluated paper/body triangle intersections. The selected
rest pose had no detected paper/body surface contacts; this says nothing about
other contacts, containment, or animation intermediates. Collision-rejected
trials and fitting parameters are retained in the review reports.

### Detailed rest-pose geometry fitting

`fit_clippy_rest_shape.py` fits actual paper/wire control vertices and optional
local Skin radii using rendered alpha. A one-sample emission override speeds up
shape trials; it is removed before saving, and reported scores always come from
fully shaded 64-sample renders of the reopened master. Armature deformation is
applied before fine wire fitting so camera-space displacements refer to the posed
wire. This is an isolated authoring model, not an animation-rig replacement.

`fit_clippy_rest_face_depth.py` moves the face and its linked lights toward the
camera while preserving its projection. It bakes the full affine into the mesh
because unparented object transforms otherwise discard parent-derived shear.
The audit rejects remaining face/wire surface contacts. `fit_clippy_rest_face_shape.py`
then fits eye and eyebrow outlines. Existing internal eye/pupil construction
contacts are still reported separately; these checks do not certify all animations.

`fit_clippy_rest_paper_ruling.py` searches UV frequency, phase and ruling contrast
using the existing paper texture, with no source-image projection. The review can
select a deliberate unfinished authoring stage using `--candidate after-wire-detail`;
this makes metric tradeoffs explicit and does not override any acceptance gate.

### Approved smooth-HD color comparison

The user approved a separate smoothed-reference color comparison. The fixed
policy is `alpha-normalized-gaussian-sigma-0.5-native-pixels-v1`: a 0.5-pixel
Gaussian with radius 3, applied only to reference RGB using alpha-normalized
weights. Source alpha is copied exactly. Candidate images are never blurred,
aligned, cropped, or rescaled beyond the existing full-canvas downsampling.
Raw-source color scores remain in every new rest-fit report alongside the
approved comparison. Both original-silhouette IoU and approved color similarity
must still reach 98% for each source pose; this does not waive choreography,
local-region, timing, branch, blink, or collision requirements.

The library validator exposes this policy explicitly with
`--smooth-color-reference`. Legacy raw-source validation remains available;
its results must not be relabeled as smoothed-reference results. Tests cover
hidden-RGB isolation, exact alpha preservation, and rejection of shifted frames
and incorrect timing under the new color policy.

The filter's impulse response is pinned by a regression test, preventing a
stronger blur from silently changing this agreement. Rest-pose review reports
include the pupil, paper UV, smooth procedural paper field, and separate-light
experiments. These remain isolated calibration candidates: a passing silhouette
does not mean passing color, and neither substitutes for animation validation.
