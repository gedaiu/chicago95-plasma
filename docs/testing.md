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
## Folder-driven pixel parity

Run the exact Windows comparisons explicitly.

```sh
python3 -m pytest tests/visual/parity.py -q
python3 -m pytest tests/visual/parity.py -q -k "win95 and caption and gtk4"
python3 -m pytest tests/visual/parity.py -q -k "device_manager or start_menu"
python3 -m pytest tests/visual/parity.py -q -k properties
python3 -m pytest tests/visual/parity.py -q -k control_panel_hover
```

The suite discovers each theme's manifest under [tests/references/themes](../tests/references/themes).
The folder names are `win95`, `win98`, `win2k`, `winxp-classic`, `winxp`, and `win7`.
Every folder uses `caption-states.png`, `run.png`, `desktop.png`, `taskbar-band.png`, `device-manager.png`,
`start-menu.png`, `control-panel.png`, and `display-properties.png`.
The existing reference helpers resolve the old names for any captures moved into these folders.

| Component | Renders regenerated by the suite | Current scope |
| --- | --- | --- |
| Caption | Qt SVG, KWin, GTK 3, GTK 4 | Rest, hover, held press, disabled Maximize and Close, and Restore. |
| Run | Qt | One dialog per theme, plus empty and typed Windows 98 frames at 120 DPI. The history popup and its second selected row are compared on Windows 95, 98, 2000 and both XP looks. Separate checks cover the high-DPI Windows 98 default button bevel and the Aero dropdown arrow. |
| Desktop | Plasma | Idle desktop, open context menu and a hover band on every theme. The Windows 7 idle crop is the unobstructed top of the archived desktop. |
| Taskbar | Plasma | Unoccupied and populated bands on all six themes. Live height checks use the native DPI, and a single active button width is measured for the five older themes. |
| Device Manager | Qt | Four-button action row on Windows 95 and 98. Console command chrome on Windows 2000, XP, and Windows 7. |
| Start menu | Qt | Root menus, the Programs selection band and cascade edge on the classic looks, the selection bands and popup edges for All Programs and My Recent Documents in Luna, and the opaque search area, selected Back face and expanded Programs pane in Aero. |
| Boot | Qt, generated Plymouth artwork | Full sampled frames on all six looks. Both compare 11 Windows 95 phases, 20 Windows 98 strip phases, six Windows 2000 strip phases and 45 Windows 7 animation phases. Windows 2000 also has a Qt playback cadence check. |
| Radio controls | GTK 3, GTK 4, Qt SVG | Idle and selected indicators on all six looks at their captured DPI. Windows 98, Windows 2000 and XP Classic also compare the installed SVG source at its native size. |
| File manager | Thunar (GTK 3), GNOME Files (GTK 4) | The installed themes' navigation bands against Explorer on all six looks. The GTK 4 captures also check the Classic title strip across the sidebar boundary, the Luna Address field fill, and Aero's address and Back/Forward states. |
| Control Panel | Qt | Icon view from Windows 95 through XP and the category view on Windows 7. The rendered window requests the guest client size at the captured DPI. Windows 7 also compares the steady hover and opening at 96 DPI and three hover exits at 144 DPI. |
| Display Properties | Qt | Appearance on 95, 98, and 2000. Settings on both XP looks. Windows 7 Screen Resolution provides the native counterpart to the theme's Settings page. The renderer checks that the selected tab is visible and its page fits without scrollbars. |

The SVG renderer draws the actual artwork at the fixture dimensions. The KWin adapter opens a real window in a
nested session, drives the pointer and records the frame while the press is held. A second, fixed-size Qt window
uses an isolated KWin rule to disable Close. The suite checks that KWin reports both actions disabled, then uses the
settled frame bounds to compare the two expected button positions. The full disabled-state screenshot is saved as
`visual/<theme>/caption/kwin/disabled/screen.png` for inspecting missing buttons.
For caption results, use the test name to see what passed.

- `test_caption_matches_windows_pixels` compares a rendered face with the Windows capture. It requires the same dimensions and RGB values within the sampled region.
- `test_luna_svg_close_glyph_core_matches_windows_pixels` compares the solid interior of the Luna Close glyph in four states against the 24-bit XP capture.
- `test_kwin_disabled_caption_interior_matches_its_own_idle_state` compares two KWin renders. It checks that the disabled glyph and interior stay the same during hover, press, and click. Its images are saved under `visual/<theme>/caption/kwin/pointer-invariance/`.
- `test_caption_svg_stays_within_windows_rgb_budget` is a separate SVG regression test. By default, it permits a per-state mean RGB error. Run it with `--exact-originals` to also require zero RGB differences.

GTK 3 and GTK 4 render header-bar widgets with Setup's CSS and the specified state at the reference DPI.
The tests capture the painted caption faces and record the widget allocations separately.
Setup uses standalone SVG files for the classic, Luna and Aero caption faces. The GTK 4 fixtures take the buttons
from GTK's own `Gtk.WindowControls` after the compositor configures the window, check their state flags, and
include the native frame in the snapshot at its original size using the window's renderer.
For Luna in GTK 3 and the Classic looks in GTK 4 at 120 DPI, the strict comparisons use the
compositor's screenshot. This includes display scaling after GTK submits its buffer. A solid marker
in the test window ties the on-screen frame to the GTK widget coordinates used to crop each button.
At 120 DPI, Setup can render the Classic GTK 4 SVGs into 20×18 PNGs when
`rsvg-convert` is available. The source SVGs remain alongside the generated files.
For Luna at 120 DPI, Setup selects the larger SVG glyphs for both GTK and Aurorae. The live comparisons
pass the reference scale to Setup so the comparison uses the artwork that would be installed at that DPI.
The larger faces preserve the five-pixel edge regions from Luna's sizing margins, with shared vector paths
and gradients filling the corners, edges, and centre.
The SVG generator regression tests also cover the standard 96 DPI vectors.
At fractional KWin scales, the Luna decoration snaps the SVG face to the physical pixel grid.
The capture accounts for KWin rounding the window origin separately from the face's position in the title bar.
An additional Aero Close check compares the normal and disabled GTK geometry and the available title pixels above
and below the painted face. Only the Windows reference test checks that the resulting pixel dimensions match
Windows, including partially painted edge pixels.
The Windows reference checks compare every unmasked RGB pixel and fail when the dimensions differ.
The known software-cursor mask is applied only to affected reference crops.

The desktop suite opens its menu in a nested Plasma session and takes a separate screenshot while hovering over
a command. It measures the right-hand gutter of the highlight independently of the command label. The full
menu comparison includes the menu's geometry and commands. The panel and button dimension checks sample
the painted geometry and allow for rounding at fractional output scales.

To check disabled KWin buttons against Windows specifically, run
`python3 -m pytest tests/visual/parity.py -q -k 'test_caption_matches_windows_pixels and kwin and disabled'`.
The Windows 7 disabled Close SVG also has three strict tests over measured dark, light and blue glass. Each uses the VM pixels at the button location with the controls hidden as its background.

Pytest stores the results under `visual/<theme>/<component>/<renderer>/` in its temporary output directory.
Pass `--basetemp <directory>` to choose that location.
The comparison image shows the original, regenerated image and amplified difference. If dimensions differ, the
test fails and saves both images at their original sizes, plus a top-left overlap diff for inspection.
The tests name the theme, renderer, state and control. KWin,
Plasma, Spectacle, the GTK GI runtimes and the normal Setup assets are required for live comparisons.

The coverage checks fail for references, components and renderers still missing from this suite. The existing
regression suites continue to cover more surfaces, including their motion and full application layouts. As new
components move into the common layout, add their references to each theme folder and register their rendering
scenarios once in the suite. A file alone cannot specify how to put a widget, desktop or session in the captured state.

The Device Manager renderer uses a fixed device inventory and draws at the captured guest DPI. The Start menu
references keep their original rows. A missing menu entry can produce a dimension mismatch even when the common
rows line up. For example, the Windows 95 capture contains Suspend and the Windows 98 capture contains Windows
Update and Favorites.

For larger Windows 7 reference scenes, Guest Additions 7.2.4 delivered a 1920×1440 native framebuffer when
VBoxSDL used a 1920×1440 virtual host display with fullscreen resizing. The Run client still measured
568×291 at 144 DPI on both the 1280×960 and 1920×1440 desktops. Use separate fixtures for captures at a
different guest DPI. [VirtualBox video mode hints](https://docs.oracle.com/en/virtualization/virtualbox/7.2/user/vboxmanage.html)
