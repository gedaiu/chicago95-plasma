# Testing

```
pip install --user -r requirements-dev.txt
python3 -m pytest tests
```

Control Panel → Passwords → Log On → **Test Luna startup flow…** rehearses boot,
user selection, wrong passwords, loading, desktop fade, switching users and logoff.
Use dummy passwords. **Hold loading screen** tests delayed readiness; **Continue**
releases it. **Run scenario** records a failed attempt followed by successful logins,
two user switches, logoff, another login and shutdown. **Shut down** and **Reboot**
rehearse the status-screen sequence without requesting a real power action. Choose an output folder for timestamped PNG frames,
`events.json`, and `flow.mp4` (requires ffmpeg). The desktop is a Spectacle snapshot;
the UI test uses the actual QML screens with simulated authentication and a preview fade.

For native startup integration and an automated recording, run:

```sh
python3 tests/record_login_flow.py --output /tmp/luna-flow-run
```

The destination must be new. The runner installs Luna in a disposable home and runs
an isolated KWin/Plasma session. It checks first-frame ordering, failed/successful
mock authentication, real KSplash startup, Plasma desktop/panel readiness, and the
actual KWin login fade, including an intermediate frame. Plasma supplies KSplash's
final desktop stage. Results are in `integration.json`, screenshots/logs, and
`recording/flow.mp4`; recording timestamps preserve capture delays. It does not change
the current desktop, authenticate accounts, or reboot. Dependencies are those of the
native desktop tests below, plus `ksplashqml` and ffmpeg.

**Booting Screen → Test boot sequence…** rehearses an optional text loader before
the graphical boot screen. The text-loader preview fills over 2.5 seconds by default;
this timing is adjustable in the QML and is not a measured boot duration. It does not
emulate firmware, run DOS, or alter the installed Plymouth sequence.

With the Windows 2000 login style, the installed post-login splash displays a
“Please wait” dialog. Its text follows actual KSplash session stages; it stays up
until the session completes instead of playing timed network/service messages.
Individual systemd unit reporting is not connected yet. The current banner variant
differs from the supplied video's; visual tests explicitly exclude that artwork.

For 1995, 1998, 2000 and 2001, **Distro Setup → Names and Logos → Shut Down**
has **Test shutdown…** and **Test logoff…** buttons. They use the unapplied preview
settings and always pass `--dry-run`: no session or power command runs. The classic dry run prints the requested command and exits. Action options and confirmation
buttons provide tooltips; combo-box help follows the selected action.

```sh
python3 tests/record_classic_power_flows.py --output /tmp/classic-power-review
```

This runs all supported action/cancellation paths with backend commands intercepted,
checks tooltip display and saves per-theme PNG captures and MP4 review reels. Reels
hold each capture for one second; they are not recordings of native animation timing.
The session app never announces that power is safe to cut: it cannot observe completion
after its own session ends. Real shutdown is handed to the system. Passing these
behavior tests does not establish original-OS shutdown-screen fidelity.

Video-reference visual regressions run with:

```sh
python3 -m pytest tests/luna/test_luna_video_flow.py tests/test_login_flow.py
python3 -m pytest tests/test_boot_visual_states.py tests/test_text_boot.py tests/test_loading_screen_reference.py
```

Boot checks cover empty/quarter/half/full loader bars at three resolutions, black
side margins, removal of the text overlay, uncompressed banner artwork and visible
status updates. Each comparison retains actual, expected and difference PNGs.

These compare welcome, logoff and shutdown renders against frames from the reference
video, check logo placement locally, and test fixed control dimensions at three
resolutions. Failed image comparisons retain actual, masked-reference and difference
PNGs in pytest's temporary directory. Text and account photos are explicitly masked
in full-frame comparisons because installed fonts and user pictures vary; separate
assertions check captions, alignment, avatar size and loading-state styling. Passing
these checks does not establish pixel-perfect font rendering or animation timing.

This is not a firmware/Plymouth/PAM integration test or proof of XP animation timing.
The native session uses the test account; account switching is simulated separately.
If these checks pass but installed startup still fails, reproduce it in a disposable
VM with a real boot and SDDM login before changing transition timings.

`tests/test_startmenu_reference.py` renders the Start menu at 1x and compares it with a
screenshot of the 1995 original:
size, bevel, separator, highlight, arrows and text positions must match; outside the icons and
the letter shapes, not a pixel may differ. The screenshots are in `tests/references` (sources in `SOURCES.md` there).

`tests/test_plasma_taskbar_reference.py`, `tests/test_plasma_window_reference.py` and `tests/test_plasma_desktop_reference.py` run the real
desktop: Setup installs into a throwaway home, then KWin and plasmashell run headless at 640x480 (800x600 for 2001 and Luna) with
each original's windows (Qt, GTK 3, GTK 4 and X11), Quick Launch entries and tray icons, and the
screenshot is compared with the original's taskbar and windows. They need KWin, plasmashell, spectacle,
Xwayland, xmessage and the MS W98 UI font, and are skipped without them; each look takes about 25 seconds.

`tests/luna/` tests the Luna components against the `xp*.png` references: the palette, the decoration, the
Plasma style and taskbar QML, the widget style, the Start menu, the Turn Off dialog, the log-on, splash and
Plymouth screens, and `test_flat_looks_unchanged.py`, which pins the flat looks' files byte for byte.

`python3 tests/render_report.py docs/compare [LOOK ...]` writes two images per look
(1995, 1998, 2000, 2001, luna):

- `showcase-<look>.jpg`: boot, login, a populated desktop preview, and seven taskbar variants, including overflow and chevron states.
- `showcase-controls-<look>.jpg`: controls grouped by type and labelled by toolkit and state.
  Each type has its own section with Qt, GTK3 and GTK4 examples together; scrollbars,
  sliders and progress bars have separate sections.
  Coverage includes buttons, checkboxes, radios, text and numeric fields, date/time editors,
  sliders, scrollbars, progress bars, tabs, lists, trees, tables, menus, toolbars, splitters,
  labels, window decorations and taskbars. Every look uses the same Qt catalogue in
  `controls_gallery.py`; GTK3 and GTK4 use `tests/gtk_showcase.py` in separate processes.

Scenes and controls render independently of reference screenshots. Missing reference files are
omitted. GTK rendering needs PyGObject, the corresponding GTK runtimes, KWin and D-Bus;
it runs in a disposable home and compositor session. Missing optional runtimes/assets are
reported on stdout, while rendering failures stop generation. Classic boot previews need the
upstream Chicago95 Plymouth assets (`CHICAGO95_SRC`, default `~/src/Chicago95`).
Qt Quick rendering requires the KDE KSvg and Kirigami QML modules.

Visual consistency checks:

- `python3 -m pytest tests/test_control_consistency.py -q` compares equivalent native,
  gallery and Control Panel controls for every OS look: buttons, checkboxes, radios,
  inputs, combos, spin boxes, sliders, and both scrollbar orientations. It checks
  normal, disabled, selected/mixed, hover, pressed and keyboard-focus states where
  applicable, including separate arrow and thumb states. Failures save expected,
  actual and difference PNGs in the test output directory.
- `python3 -m pytest tests/luna/test_luna_gtk_visual_consistency.py -q` renders GTK3/GTK4
  in isolated KWin sessions. It compares Luna checkbox pixels, radio interiors and
  dimensions, state changes, and Qt/GTK check marks. Checkbox comparisons are exact;
  radio interiors allow 2/255 channel rounding for antialiased hover glows. This is
  targeted cross-toolkit coverage, not a claim that every Qt/GTK widget is pixel-identical.
  It also compares classic and Luna tab borders with the first/second page selected
  and with disabled tabs, on all four sides. Fixed label boxes isolate borders from
  font rasterisation. Classic allows narrowly bounded bitmap-corner antialiasing,
  but rejects a border through the selected tab; Luna allows 2/255 corner antialiasing. The classic GTK4 override reuses
  the installed GTK3 notebook assets and is removed from the imports when switching to Luna.
  Qt and GTK previews use the same 11px interface font. GTK receives Qt's resolved font
  family so missing-font fallbacks also match; native font metadata verifies this.
  Progress bars are compared at 0%, 1%, 55% and 100%, disabled, reversed and RTL,
  horizontally and vertically. Checks require visible, increasing fill as well as
  matching pixels. Both classic GTK versions share the installed progress CSS;
  Luna explicitly sizes and segments the fill in both orientations.
  Group boxes compare a single border, fixed label space and child alignment in
  labelled, disabled and unlabelled cases. The showcase shows real labels and keeps
  group boxes in their own section, separate from switches.
  Dropdowns and spin boxes compare geometry, borders, arrow artwork and text placement
  in normal, disabled, hovered and pressed states. Smooth-font glyph antialiasing is
  excluded from the pixel comparison; glyph bounds and surrounding pixels are checked.
  Qt's Luna spin buttons also check for an uninterrupted surface between the arrows.
  Luna progress bars compare Qt/GTK3/GTK4 thickness, white inset and chunk pixels
  across fill levels, disabled, reversed and RTL states. Qt widget checks also
  require readable black labels and consistent sizing with or without text.
  Classic GTK controls and bitmap assets follow the active window/selection scheme;
  native palette checks cover Windows 2000 and XP Classic, including disabled inputs.
  Luna top-tab artwork is compared directly with Qt, including all three orange
  accent rows, inactive/hover gradients and the open selected-tab seam. GTK tab
  comparisons cover all four positions and selection, disabled and hover states.
  Luna GTK switches compare both positions across normal, disabled, hover, pressed
  and keyboard-focus states, including marks, thumb placement and visible feedback.
  Luna sliders use green-capped rectangular thumbs without marks and pointed
  thumbs facing a single row of tick marks, as in the XP screen-resolution control.
  Tests also require visible ticks, the pointed silhouette and a single grey track
  without a white highlight.
  Luna sliders compare Qt/GTK3/GTK4 thumb pixels in both orientations, including
  hover, pressed, disabled and endpoint states. They require a smooth gradient and
  compare GTK track geometry and thumb placement.
  Scrollbars compare bar/thumb geometry and end-arrow artwork, including disabled,
  hover and pressed thumbs. Luna grip checks independently require four dark ridges
  and four highlights, centred in horizontal and vertical thumbs, so two missing
  textures cannot pass just by matching each other. **GTK4 removed native stepper buttons:** its end arrows
  are decorative CSS artwork, not clickable controls, and cannot individually disable
  at the adjustment limits. GTK3 retains working steppers. The showcase labels this
  distinction; restoring functional GTK4 steppers requires application/toolkit changes.
- `tests/test_showcase.py` checks asset loading and taskbar geometry, including the
  narrower tray without a chevron and the 2001 login banner and boot logo.

Add `--details` to also generate `report-<look>-<part>.png` and `.txt` historical pixel
comparisons. Those diagnostic reports still require their reference screenshots and use the
original test scenes, masks and pixel differences.
