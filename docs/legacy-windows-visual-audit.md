# Windows 95, 98, 2000 and XP visual audit

The four reference guests booted from the owner's installation media. Windows 95 OSR2, Windows 98 Second Edition, Windows 2000 Professional and English XP Professional SP3 reached their desktops. The 95 guest uses an emulated Pentium with instruction-count timing. Its wall-clock measurements describe that VM.

[View original and rendered controls side by side](compare/legacy-vm-details.png). Each pair uses the same display scale. The tests compare the native-size pixels.

| Theme | What the fresh reference verifies | Remaining difference or limit |
| --- | --- | --- |
| Windows 95 OSR2 | Device Manager action buttons measure 84, 84, 84 and 83 pixels across, with six-pixel gaps. The classic layout now keeps the row aligned with the tree when widened. The 12×12 selected and unselected Display Properties radio buttons match after mapping the render to the guest's four neutral VGA colours. The boot artwork includes the OSR2 Microsoft Internet Explorer line. | The native Device Manager is a System Properties tab. The Linux tool opens separately and disables unavailable hardware actions. The captured single-user shutdown dialog also has fewer choices than the project's multi-user dialog. |
| Windows 98 SE | The installed Windows shutdown artwork, LOGOW.SYS, shows Windows 98 over clouds with a blue caption. Plymouth previously inherited the Windows 95 shutdown image. The replacement uses the 98 boot artwork and a scalable caption. A 160×120 composition test checks the full image and the caption location. | The cloud reconstruction and caption lettering are approximate. The selected and unselected radio indicators in the captured shutdown dialog match the rendered black-pixel masks. |
| Windows 2000 Professional | The 640×480 boot recording shows a 165×10 bar at (273, 436). At half fill its 8×8 navy blocks, grey gaps and bevel now match all 1,650 pixels. | The installed desktop was captured at 1280×1024 with its Cirrus Logic driver. The two shutdown trials below measure the installed desktop. Other interactive transitions still need measurements. The captured graphical boot occurred during an installation restart. |
| Windows XP Professional SP3 | The 126×15 loading bar has 15 slots and 18 animation states. It advances eight pixels per step and repeats in about 1.69 seconds. The Qt preview matches every native bar frame and has a timed playback test. Plymouth uses the same SVG artwork and step sequence. Native Device Manager has five toolbar commands and a status bar. The Luna layout now follows that structure and uses SVGs for the five toolbar icons. | The Console Tree and Action Pane button faces are compared at their native positions. The Help and pane glyphs have separate RGB comparisons. Icon antialiasing and background gradients still differ. The unbranded boot screen now follows SP3 by omitting the edition line. Plymouth's on-screen cadence still needs an independent display recording. |

The XP Luna and XP Classic Device Manager captures place the command glyphs one pixel lower than the earlier Qt render. The corrected Console Tree and Action Pane SVGs use a single triangular arrow and three list lines. The tests compare the entire 14×12 face of each button at its guest position, with a limit of three levels of mean absolute RGB error out of 255. Redrawing the yellow Help mark and its paper background reduced error over the 14×15 capture from 18.38 to 9.01 in Luna and from 16.82 to 8.30 in XP Classic. The disabled Back and Forward arrows average 1.10 and 1.22 in Luna, down from 16.40 and 16.18. In XP Classic they average 2.91 and 2.96, down from 9.92 and 9.86. The unobstructed 420×23 Luna toolbar background averages 0.79 after restoring its horizontal tint and lower bevel. [VM and rendered command glyphs](compare/xp-device-manager-commands.png)

At 120 DPI, both XP Console Tree buttons return to their idle appearance while the pointer is held outside and after the release cancels the press. The tests also verify that a completed click shows the console tree and that a second click hides it. Mean RGB error across the seven Console Tree states fell from 66.47 to 38.70 in XP Classic and from 65.92 to 32.54 in Luna. Both strict comparisons still show differences in glyph alignment and the button face. The separate 420×48 empty command band in XP Classic matches at 96 DPI.

The Luna menu and toolbar now share one device-pixel boundary. The three
unobstructed bevel rows match all 1,140 tested pixels at each DPI.
Within the same 380-pixel-wide background area, mean RGB error at
96 DPI fell from 1.02/255 to 0.50/255 for the menu and from 0.80/255
to 0.51/255 for the toolbar. At 120 DPI it fell from 1.92/255 to 0.77/255
and from 3.15/255 to 0.46/255. The Luna Console Tree state test now
uses the native client width and crop origin. With the corrected
120-DPI toolbar spacing and SVG faces drawn behind the button glyph,
its mean RGB error fell from 16.37/255 to 1.25/255. The navy frame of
the icon matches at its native size and position in all seven states.
The full-state comparison still differs in 1,102 of 3,931 pixels,
including small colour differences in the rounded faces and background.

The XP Classic 120-DPI command bands match all 19,968 tested pixels
across their outer edges and unobstructed background. Its Console Tree
test now uses the native client width and crop origin. The bevels,
checked stipple, and navy icon frame match in all seven states.
The full comparison differs in 70 of 3,931 pixels, mostly around
the antialiased arrow. Mean RGB error is 0.48/255.

XP Luna’s GTK 3 and GTK 4 checkmarks use two polygon arms. The radio dot uses a circle and a radial highlight. On both toolkits the checked marks cover the same pixels as the XP SP3 resources at 100% and 200%, measured at the green-channel threshold used in the tests. At 200%, the comparison resamples the 26-pixel GTK control to the original 25-pixel resource. The complete checked checkbox averages 1.01 RGB levels of difference out of 255 at 100% and 5.82 at 200%, down from 4.40 and 29.98 respectively. A density-specific SVG rectangle keeps the border one physical pixel wide at both scales. [XP SP3, GTK 3 and GTK 4 side by side](compare/xp-gtk-checkmarks.png)

The XP GTK control generator now ships 84 standalone SVGs in each toolkit theme. This replaces 284 PNG files across the two themes. Tabs use CSS gradients and retain their measured 21-row profile. Switches use rounded rectangles, circles and a dashed focus line. Slider pointers use two straight beveled edges. The Linux toolkit comparisons cover horizontal and vertical tracks, three pointer shapes and all six tested control states and positions. The native-size GTK slider renders stay within one RGB level of the Qt samples. [GTK 3 and GTK 4 tab, switch and slider captures](compare/xp-gtk-vector-controls.png)

An earlier scan of 331 shipped SVG files found 33 that painted all four corners opaque. These were rectangular slider thumbs, checkbox outlines, the Device Manager command band and boot-bar pieces. A separate test renders radio assets and individual sprite elements from GTK, Plasma and Kvantum on dark violet and pale green at two sizes. Each exposed corner retains the backdrop, and the disabled XP radio ring also lets the backdrop show through its centre. At 200% the complete checked GTK radio averages 5.51 RGB levels of difference from XP SP3.

At 120 DPI the Windows 2000 Device Manager command band is 25 physical pixels high. The earlier layout left its buttons only six logical pixels of height. The revised band includes both raised grips, a disabled stippled folder for Up one level and embossed navigation arrows. The comparison uses the original guest coordinates and quantizes the Qt capture to RGB565. [Guest, previous and revised command bands](compare/win2000-device-manager-commands.png)

| Windows 2000 toolbar crop | Previous mean RGB error (0–255) | Revised |
| --- | ---: | ---: |
| Back | 9.20 | 2.39 |
| Forward | 9.65 | 2.60 |
| Up one level | 26.98 | 4.20 |
| Console tree | 41.04 | 0.87 |
| Help | 52.04 | 3.72 |

Windows 7 Aero Device Manager uses the MMC toolbar. Its 778×518 client
has an unselected first row, an 18-pixel row pitch and a white viewport
extending to the bottom bevel. Inventory errors remain visible. At 96 DPI
the exposed gutter, tree surround, and empty viewport now match all
182,878 tested pixels. Mean RGB error for the idle expanded arrow is
1.48/255. The hollow SVG outline reduces the idle collapsed arrow from
2.15/255 to 0.48/255. The expanded hover, collapsed hover and held-open states
measure 1.52/255, 1.55/255 and 1.52/255 with the revised SVG outlines and
glow gradients. Pointer tests verify that moving from
the arrow to the label clears the glow and that the branch opens on
press and stays open when the button is released outside. The command
bands fell from 2.59/255 to 2.02/255 within the same 778-column client.
The exposed toolbar interior and all three separators match all 13,409
tested pixels. Six individual 16×16 icon comparisons show remaining
differences. The disabled Back and Forward icons use SVG paths for the
rounded outline, bevel, and face. The revised outlines and gradients
reduced their mean RGB errors from 4.64/255 to 2.31/255 for Back and
from 4.59/255 to 2.17/255 for Forward at 96 DPI.
The redrawn Scan icon fell from 12.03/255 to 6.67/255.
The toolbar region where Scan appears matches all 621 pixels at startup
with no selection. With the computer selected, the five Scan button
states average 4.40/255. Releasing a held click outside cancels it.
A click opens a 282×88 scan dialog while Linux collects the inventory.
Interaction tests verify that it stays open during the scan and closes
after a result or error. At 96 DPI the blank message panel and the
bottom frame match all 6,650 and 2,256 pixels respectively. The SVG's
side reflections and bevel bring the mean RGB error outside the caption
regions from 0.36/255 to 0.20/255. The full dialog averages 4.27/255
across 24,744 compared pixels. Caption rendering accounts for most
of the remaining error. Loading the VM's Segoe UI into the comparison
process changed the text rendering, with a similar overall error.
The redrawn Help icon fell
from 10.29/255 to 3.06/255. The seven Console Tree states fell from
11.38/255 to 4.27/255. Dragging a held press outside clears the highlight
and releasing there cancels the click. Device labels and icons depend
on the detected hardware.
The Windows 95 and 98 button gaps and alignment still pass the geometry
tests. The strict captures still differ in the button states and text.

The Windows 95 and 98 Device Manager captures at 120 DPI show a
470×28 action row. The Qt row now matches the bevels and gaps exactly
in both guests. The eight 112×28 Refresh frames also match outside
the captions and pointer rectangles, including the focus frame while
dragging a held click outside. The test verifies that releasing there
does not activate Refresh. Mean RGB error across the full row fell
from 23.91/255 to 9.17/255. The original five Refresh comparisons
fell from 15.24/255 to 7.47/255, and all eight average 7.45/255.
The strict comparisons still show differences in caption rendering
and enabled states.
The Windows 2000 command bar's unobstructed 370×25 band, pane edges,
grips, and separators match every tested RGB565 pixel. Mean RGB error
over the full band fell from 3.86/255 to 3.61/255 after redrawing the
contributing SVGs. In separate 16×16 comparisons, Back fell from
4.32/255 to 0.66/255, Forward from 4.48/255 to 0.87/255, Up one level
from 7.23/255 to 1.65/255, and Console Tree from 1.50/255 to 1.15/255.
The same 16×16 Help comparison improved from 6.41/255 to 3.86/255
in Windows 2000, from 7.58/255 to 4.96/255 in XP Luna, and from
6.80/255 to 4.28/255 in XP Classic. The Console Tree
bevels and checked pattern match in all seven captured states. The
full state strip still differs in 68 of 4,403 visible pixels, mostly
around the arrow inside the icon. Its mean RGB error is 0.38/255.

## Comparisons on the installed guests

| Surface | Result at native scale |
| --- | --- |
| Windows 95 OSR2 and 98 SE Run | Both dialogs measured 347×163. The editable field and three button bevels matched across four comparison bands after mapping the intermediate light grey to the VGA palette. |
| Windows 95 OSR2 and 98 SE Start and taskbar | Both menus used 32-pixel rows. The 98 theme previously used 36. The 28 taskbar rows match in an unoccupied band after the same palette mapping. The high-colour Help icon paints 22 rows on the theme and 24 on the SE VGA guest. |
| Windows 98 SE Device Manager and Display | The four Device Manager button widths and gaps match the shared classic row. The Appearance sample measures 355×193. The corrected preview matches the guest’s desktop silhouette and both scroll arrowheads. The monitor with its stand measures 184×169. The old drawing omitted the bottom 13 rows. The full replacement SVG passes the monitor comparison. |
| Windows 98 SE Mouse | Both handedness illustrations and the open and closed double-click test pictures match the captured RGB pixels at 1×. The SVGs preserve the native object colours and expose the window behind each silhouette. Full-crop comparisons on two contrasting backgrounds cover both mouse and box states. [View all four illustrations](compare/win98-mouse-transparency.png) |
| Windows 2000 Professional Setup | The 75×23 Back button matches the theme’s ordinary push-button size and top-to-bottom bevel sequence. The setup and desktop palettes differ. |
| Windows 2000 and XP Classic Run | Both measure 347×179, 16 pixels taller than Windows 95. The field and button bevels now match the guest samples, including the 16-bit colour quantization on Windows 2000. XP Classic also matches the empty 28-row taskbar band. |
| Windows XP SP3 Start and taskbar | The Luna menu matches the captured 380×477 dimensions. Three chrome regions compare within six mean RGB levels. The empty taskbar matches the existing per-channel tolerance in all 30 rows. |

[Compare the Windows 98 Appearance preview and monitor at native size.](compare/win98-se-display.png)

The Windows 98 cold boot advances the bottom colour band to the right by 32 pixels per observed step. Sixteen captured strips compare within three mean RGB levels after adjusting the 640×400 VGA pixel aspect ratio. The recording includes missed display updates and irregular startup pauses. A warm restart on this emulated machine stalled at the logo. Timing measurements use the successful cold boot.

The shared suite has a strict full-frame Qt boot comparison for each theme.
Mean absolute RGB errors out of 255 at the captured phases follow.

| Theme | Previous | Updated |
| --- | ---: | ---: |
| Windows 95 OSR2 | 66.99 | 0.00 |
| Windows 98 SE | 0.429 | 0.004 |
| Windows 2000 Professional | 8.22 | 0.11 |
| Windows XP SP3 Classic and Luna | 3.49 | 0.00 |
| Windows 7 SP1 | 1.13 | 0.08 |

Windows 95 matches all pixels in the main frame and eleven additional
captured phases. The render uses the indexed stock artwork and rotates
the same 20 palette entries as the guest. All 302,080 pixels above the Windows 98 animation strip match.
The strip advances in 20 steps in Qt and Plymouth. The captured phase still
differs in 92 dither pixels. The Windows 2000 initial frame is exact.
The active frame differs in 770 pixels in the blue strip. At 1024×768
the Windows 7 caption and copyright bounds
match within one pixel after correcting the canvas scale.
At 640×480 the XP stock boot preview matches the tested full frame in
both themes. Larger Qt previews retain the scalable wordmark.
Full playback through Plymouth still needs a display
capture. [Native boot captures](../tests/references/SOURCES.md#native-boot-frames)

The Windows 7 Run client at 150% now has the native height of 291
pixels. The render is 569 pixels wide and the guest is 568. The revised
two-tone client, SVG icon and button positions reduced mean RGB error
in the common rectangle from 25.07/255 to 9.27/255. The visual test
types a command so the default button is enabled.

The Windows 7 single-account sign-in comparison at 800×600 uses
the guest's 4:3 background and aligns the account group 16 pixels lower.
The mean RGB error outside the portrait interior fell from 9.12/255 to
2.11/255. The password field's blank interior matches exactly. Manual
sign-in remains available through the Ease of Access menu.

## Desktop motion and power

The caption-state comparison covers Windows 95 OSR2, Windows 98 SE, Windows 2000 Professional, XP Classic, XP Luna and Windows 7 Aero. It pairs native VM crops with the theme SVGs for the resting, hovered and held Minimize, Maximize and Close buttons, the disabled Maximize and Close buttons, and Restore after maximizing Notepad. The classic guests keep the face unchanged when hovered. Luna and Aero change the face on hover. All six looks change the button while held and return to the idle face after the pointer leaves and the press is cancelled. The visual comparisons sample settled states. [Side-by-side comparison](compare/caption-states-vms.png) · [Regression and exact RGB tests](../tests/test_caption_states_reference.py)

The 60 Classic SVG face comparisons pass at strict RGB tolerance at 120 DPI. The faces use device-size vector geometry for the bevel and glyph. Windows 2000 and XP Classic use the guests' RGB565 display palette for comparison. The native software cursor occupies a 6×6 mask in hover and held-press captures. The table shows the highest mean absolute RGB error out of 255 among the tested SVG faces in each state. The Luna comparison generates the same 120-DPI art that Setup installs.

| Look | Rest | Hover | Held press | Disabled | Restore after maximize | After cancel |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Windows 95 OSR2 | 0 | 0 | 0 | 0 | 0 | 0 |
| Windows 98 SE | 0 | 0 | 0 | 0 | 0 | 0 |
| Windows 2000 Professional | 0 | 0 | 0 | 0 | 0 | 0 |
| XP Classic | 0 | 0 | 0 | 0 | 0 | 0 |
| XP Luna | 3.75 | 3.57 | 2.56 | 2.83 | 2.87 | 4.17 |
| Windows 7 Aero | 9.57 | 17.91 | 22.38 | 21.56 | 16.73 | 9.57 |

Live KWin captures at 125% also pass all 48 Classic face comparisons. The wrapper requests the 120-DPI face at its
logical size, and KSVG rasterizes it once at the output scale. GTK 3 and GTK 4 share the device-size vector outlines
when Setup configures 120 DPI. The 144 GTK comparisons across the six themes still show differences. In the four
Classic themes, fractional positioning spreads the face across an extra row or column. The tested Luna faces have the
native dimensions and differ in RGB. A 27-pixel PNG export of the same Luna artwork gave mean RGB error of 20.43
in GTK 3 and 18.07 in GTK 4, within 0.02 of the earlier installed SVGs across 12 states per toolkit. A larger CSS
face spread across up to 28 pixels and softened the glyph interiors. At 120 DPI, Setup now gives GTK 3 an SVG
with a 42-pixel intrinsic size for its 2× backing buffer. It shares the 27-pixel artwork's viewBox and paths.
The live GTK 3 mean fell from 20.45 to 17.86, with the original 27×27 captured bounds in all 12 comparisons.
GTK 4 keeps the 27-pixel viewport and averages 18.06. Trials at 21, 26, 28, 42, 52, 54 and 81 pixels gave larger
errors there. All 24 strict comparisons still show RGB differences. [Live GTK 3 regression](../tests/visual/parity.py)

Luna at 125% keeps its 27-pixel face inside a 28-pixel SVG canvas, which
lets KSVG render it at its authored size. All 12 live KWin comparisons reproduce the opaque SVG interior exactly.
Mean RGB error against the XP guest fell from 7.33 to 2.74 across those 12 faces. The strict VM comparisons for
Luna and Aero still show RGB differences.
Aero Restore now clips its top device row at the screen edge when maximized, giving the same 40×29 visible face
as the 144-DPI VM. [Exact tests by renderer](../tests/visual/parity.py)

On Windows 98 SE, minimizing Notepad left its white client visible as a shrinking title bar travelled toward the taskbar. The system menu was gone at 0.178 s and the desktop had settled by 0.339 s from recording start.

Fresh Windows 98 SE captures at 1280×1024 show a 23-device-pixel strip moving at about 2.9 to 3.2 vertical pixels per
millisecond in the sampled portions of the two directions. The client stays in place on minimize and appears after
the strip returns on restore. Windows 95 OSR2 shows the same sequence at 1024×768, with a 23-device-pixel strip and
measured speeds of 4.3 to 4.6 vertical pixels per millisecond. The KWin presets use the inset Classic title band and
scale the duration with travel distance in device pixels. The live tests check the client and the speed of the
travelling strip at 125% for both looks and at 100% for Windows 98. [Live compositor regression](../tests/test_plasma_animations.py)

In the Windows 2000 Professional and XP Classic captures at 1280×1024, both 23-device-pixel strips also move
independently of the window client. The measured vertical speed was 3.10 to 3.15 pixels per millisecond for
Windows 2000 and 3.29 to 3.37 for XP Classic. Setup uses these timings for the two presets.
The 95 and 98 recordings show a solid navy strip in both directions. Windows 2000 and XP Classic
draw the active blue gradient at the full caption width and clip it as the strip narrows. KWin now
paints those fills independently of the window's focus state and preserves the title and icon from
the caption. The live tests also check for the active blue palette during restore.

A Windows 98 SE Notepad recording at 120 DPI showed the native title strip travelling over the stationary
client. The maximized client first appeared about 262 ms after the click release. KWin's Windows 98 preset
now switches directly to the new bounds to avoid the previous whole-client fold. Minimize and taskbar restore
keep the title-strip animation. At Normal speed its base duration caps at 300 ms, approximately the travelling
time observed in the native taskbar restore. The Speed setting still scales the effect.

In the XP SP3 Device Manager minimize recording, the system menu dismissed at 0.181 seconds, the first captured
travelling title bar appeared at 0.211 seconds, and the destination settled by 0.447 seconds. The original client
stayed visible under the travelling title strip. A later Notepad capture also showed the strip returning before
the client appeared on restore.

The Luna KWin effect now moves a crop of the live title bar. The client stays in place until minimize completes and
appears when restore completes. The recorded regression checks that the strip travels at least 200 logical pixels
while the client stays in place or stays hidden, respectively, at both 100% and 150% scale. In the recorded runs,
detectable movement spanned 217 to 234 ms of the configured 260 ms animation. The setup step installs the effect's
configuration schema and reloads an enabled copy so saved animation settings take effect. XP draws a dedicated
horizontal-gradient strip during both directions. KWin's strip uses the existing caption artwork, including its
inactive tint during restore. [Live KWin regression](../tests/test_plasma_animations.py)

The XP SP3 Luna maximize and restore captures show the title travelling across a stationary client in both
directions. The earlier KWin effect scaled the entire client during its fold and left flashing regions after
maximize. The two XP presets now use an immediate resize. The regression clicks the caption buttons with
the older zoom setting explicitly selected and checks the visible client and the settled bounds.
[Live regression](../tests/test_plasma_animations.py)

Windows 2000 Professional at 1280×1024 and 120 DPI showed “Saving your settings...” by 0.290 and 0.301 seconds after confirmation. The blue desktop had cleared by 1.808 and 1.818 seconds. Libvirt reported power off at 2.122 and 2.148 seconds, respectively. These are first observations in two trials. The native 96-DPI confirmation dialog measured 417×269 and its frame passed the RGB565 comparison.

The Windows 95, 98 SE and XP guests completed a real shutdown. On the 98 SE guest with an emulated Pentium II and instruction-count timing, the first captured shutdown wordmark appeared 0.877 seconds after confirmation and the first subsequent black frame appeared at 1.385 seconds. These timestamps describe one run. [Native shutdown dialog](../tests/references/win98-se-shutdown-dialog.png) · [Captured shutdown artwork](../tests/references/win98-se-shutdown-vm.png)

XP displayed “Saving your settings…” during sign-out. The project's Luna shutdown preview switches from “Logging off…” to “Windows is shutting down…”. Recording the VM captures native text and transitions. It does not establish a portable duration for saving a user's session.

## Regression coverage

- The native-size XP boot animation, Device Manager command bands and Windows 2000 boot bar have captured reference fixtures. Windows 95 has explicit button-spacing and radio-indicator comparisons. Windows 98 uses its own shutdown bitmap as the reference for the reduced-size composition test.
- The shared visual suite runs the installed-look Qt shutdown chooser against a native Alt+F4 capture for each of the six themes. All six match the dimensions of their primary reference. The additional Windows 98 capture at 120 DPI still differs by one row. All six fail strict RGB equality. Alternate selections, further control states, the Windows 7 window frame, and the desktop shutdown sequence still need coverage in the shared suite. [Strict test](../tests/visual/parity.py) · [Capture details](../tests/references/SOURCES.md#desktop-shutdown-choosers)
- Windows 95 uses the VM's three-choice layout when AccountsService reports a single desktop account. Windows 98 uses three choices if logind reports that suspend is unavailable. The expanded layouts remain available on desktops that support the extra action. The Windows 95 dialog measures 347×201 and 460×246 at 96 and 120 DPI. The Windows 98 dialog measures 323×173 at 96 DPI. At 120 DPI the guest measures 428×212 and Qt renders 428×213. [Radio chooser regressions](../tests/test_shutdown_reference.py)
- Windows 95 has 96-DPI idle, hover and held-press comparisons for Yes, No and Help. The held frames and inset outlines match the native pixels outside the labels. The full state sheet still differs, with mean RGB error reduced from 18.85/255 to 10.20/255. [Held-frame comparison](../tests/visual/parity.py)
- Windows 98 has 120-DPI idle, hover and held-press comparisons for OK, Cancel and Help. Both classic dialogs keep their idle faces on hover, as the guests do. The three Windows 98 held frames match the native pixels outside the captions. Mean RGB error across the full Windows 98 button sheet fell from 22.71/255 to 14.18/255. The arrow-key radio comparison covers all three available choices. Keeping the indicators at their native 12-pixel size and drawing a solid focus outline reduced mean RGB error there from 14.02/255 to 12.21/255. [State comparisons](../tests/visual/parity.py)
- Windows 2000 matches the 417×269 and 486×313 chooser dimensions at 96 and 120 DPI. The 120-DPI list popup matches the 303×66 reference dimensions. Its strict comparison still shows differences in the list border, selection and lettering. All three button frames match at idle and while held outside their captions. The full chooser, button and keyboard-choice comparisons still differ. The Help button explains the selected action in the Linux dialog. The guest opens a separate Windows Help window. [State captures](../tests/references/SOURCES.md#desktop-shutdown-choosers)
- XP Classic and Windows 7 now use the same dropdown and keyboard-choice comparisons as Windows 2000. The XP Classic popup matches the 303-pixel width but is one pixel taller than the 82-pixel VM capture. The XP descriptions use the guest’s wording for Stand by and Hibernate. The Windows 7 list is 317×67 and matches the VM outside its labels, including the frame and selection fill. Its five captured choices include Switch user and Hibernate. Sleep and Hibernate appear only when supported on the Linux desktop. The closed field’s focus indicator, lettering, and further action states still differ or need captures. [State comparisons](../tests/visual/parity.py)
- Windows 7’s shutdown chooser uses SVG faces for the idle, default, hover and held buttons. The 96-DPI button sheet compares OK, Cancel and Help. The full sheet still shows pixel differences in the captions, corners and inset strokes. Across three native Cancel-button trials at the sampled pixel, hover settled in 476–564 ms and leave settled in 1,608–1,755 ms. The Qt timing test compares those intervals and the final colors. Whole-button motion, the default button’s timing and the press transition still need independent comparisons. [Capture details](../tests/references/SOURCES.md#desktop-shutdown-choosers)
- XP Classic uses the guest's two layouts, 417×247 at 96 DPI and 486×285 at 120 DPI. Its banner background and CRT icon are vector artwork. The 120-DPI mean RGB error fell from 55.10/255 in the old top-left overlap to 11.47/255 at matching dimensions. The 96-DPI comparison measures 10.11/255. Lettering, the title gradient, the flag and other controls still differ. [Shutdown reference tests](../tests/test_shutdown_reference.py)
- The native 120-DPI XP Classic and Windows 2000 sheets for OK, Cancel and Help match pixel for pixel. The shared renderer matches all three XP Classic frames outside the captions in idle and held states. Hover matches idle. Mean RGB error for the full XP Classic sheet fell from 33.99/255 to 9.94/255. [State comparisons](../tests/visual/parity.py)
- XP Luna measures 314×200 at 96 DPI and 418×246 at 120 DPI. The higher-DPI panel uses an SVG background, and the power button faces use vector bevels, gradients and strokes. Mean RGB error is 6.80/255 at 96 DPI and 6.75/255 at 120 DPI. The 120-DPI button sheet compares idle, hover and held press for Stand By, Turn Off and Restart. Its mean RGB error fell from 35.05/255 to 24.00/255. Cancel, focus, disabled states and tooltips still need corresponding guest comparisons. [Luna dialog tests](../tests/luna/test_luna_dialogs.py)
- GTK 3 and GTK 4 render real controls in isolated KWin sessions. The classic palette tests exercise Windows 95, 98, 2000 and XP Classic separately, including the white interior of enabled text fields. Luna has separate cross-toolkit control and state tests. These comparisons cover specific controls and do not certify every application's layout.
- The full Control Panel and display settings comparisons still differ for all six themes. Windows 7's Display entry and Adjust screen resolution link open Screen Resolution inside Control Panel. At the native 144-DPI viewport of 1178×804, 80,477 of 947,112 pixels differ, with a mean RGB error of 4.21/255. The SVG preview resizes as the pending resolution changes. [Application comparisons](../tests/visual/parity.py)
- Windows 7 Category View has strict crops for all eight icons at 144 DPI. System and Security, Clock, Language, and Region, and Ease of Access now measure 13.15/255, 20.78/255, and 28.03/255 mean RGB error. The existing User Accounts and Family Safety artwork is closer to the VM than the SVG trial. The full panel fell from 10.66/255 to 10.31/255. The 96-DPI hover-opening and press-and-cancel samples and the 144-DPI hover-exit samples all match the VM exactly. At 96 DPI the settled hover strip fell from 0.17/255 to 0.09/255, and the complete border measures 0.05/255. The heading keeps its dotted focus outline after a cancelled click. The strict focused-heading comparison fell from 46.44/255 to 32.82/255. The Control Panel uses the checkout artwork when it runs from the repository. [Capture details](../tests/references/SOURCES.md)
- The Windows 7 resolution flyout uses a vertical slider with clickable modes and SVG artwork for its track and thumb. It matches the native 202×312 dimensions in all three 96-DPI captures. The thumb moves 19 pixels after Up and 76 pixels after clicking 1280×768 from 800×600, matching the VM. The strict comparisons still differ by 9.07–9.08/255 in mean RGB. [Capture and interaction states](../tests/references/SOURCES.md#control-panel-and-display-properties)
- Windows 98 Display Properties matches the 528×519 client at 120 DPI. All implemented tabs and Appearance editors fit without scrolling. In the common 498×519 region, mean RGB error fell from 38.05/255 to 20.51/255. The full Appearance crop differs on 59,104 of 274,032 pixels. Remaining differences include the missing Web tab, lettering, controls, and the gradient title bars in the installed preset versus the VM's solid title bars. [Application comparisons](../tests/visual/parity.py)
- Windows 95, Windows 2000, and XP Classic also match the 528×519 client at 120 DPI. Windows 95 and 2000 use the measured Appearance preview and editor positions. XP Classic Settings puts resolution on the left and color quality on the right, with an SVG monitor and color strip. In the common 498×519 region, mean RGB error fell from 40.29 to 18.03 for Windows 95, 34.74 to 17.37 for Windows 2000, and 22.11 to 11.90 for XP Classic. Both renders in each Windows 2000 and XP Classic comparison use the VM's RGB565 framebuffer format. The full crops still differ, including the tab set, typography, and the XP preview artwork. [Application comparisons](../tests/visual/parity.py)
- XP Luna now shares the XP Settings layout, including its SVG monitor and color strip. The color-quality field shows the reported display depth. Tabs and Appearance editors fit without scrolling at 100%, 125%, 150%, and 200%. At 120 DPI the 528×518 client is one row taller than the VM capture. In the common 528×517 area, mean RGB error fell from 27.00/255 to 14.32/255 using RGB565 for both renders. The tab set, typography, controls, and preview artwork still differ. [Application comparisons](../tests/visual/parity.py)
- Windows 95 Control Panel uses the VM's four menus, 18-entry icon grid, and single status pane. Seven applet SVGs use sharper contours, and their idle renders align to physical pixels at fractional scale. The File menu keeps Chicago95's additional settings accessible. At 120 DPI the initial client mean RGB error fell from 39.19/255 to 18.62/255 in the common crop. The circular clock, calendar hinge and hands reduced the Date/Time icon crop's mean error from 65.59/255 to 54.17/255. Pressing End selects System and scrolls to its row. The End comparison measures 17.20/255. Both strict tests still differ in typography, icon shapes, and scroll thumb geometry, and the Qt client is one column wider. [Capture details](../tests/references/SOURCES.md#control-panel-and-display-properties)
- Windows 95 Accessibility Options, Fonts, Internet and Keyboard now use dedicated SVGs. The compact menu is one physical pixel shorter at 120 DPI, bringing the grid closer to the captured position. The native Display artwork stays in the theme because its SVG trial had higher RGB error. All five fixed icon crops improved and still differ from the VM. [Capture details](../tests/references/SOURCES.md#control-panel-and-display-properties)
- Windows 98 Control Panel uses the 22-entry Web View, an SVG sidebar background and folder, and a compact Explorer toolbar. The View menu toggles the sidebar. Selecting Display updates the sidebar and status text, and Properties opens the applet. The sidebar links to the Chicago95 Plasma repository and issue tracker and opens the in-app theme selector. The ODBC and Printers SVGs fill more of their native 32-pixel icon boxes. At 120 DPI mean RGB error fell from 18.65/255 to 15.31/255 in the common client area. The Display-selected crop measures 14.96/255. Both strict comparisons still differ, including icon artwork, text, links, and toolbar action states. [Capture details](../tests/references/SOURCES.md#control-panel-and-display-properties)
- Windows 2000 Control Panel uses the 23-entry Web View, an SVG sidebar background, and the compact horizontal toolbar. Search filters local applets, Folders opens the home directory, and History exposes Control Panel navigation. At 120 DPI the 800×690 client matches the VM dimensions and mean RGB error fell from 17.54/255 to 14.90/255. The Display-selected crop measures 14.93/255. Icon artwork, text, toolbar actions, and sidebar details still differ. [Capture details](../tests/references/SOURCES.md#control-panel-and-display-properties)
- Windows 98 and 2000 share SVG applet artwork for the Display monitor and ruler, Internet Options globe and tools, and Power battery and plug. Windows 98 has its own Telephony icon. Windows 2000 has separate artwork for Administrative Tools, Network and Dial-up Connections, and Scheduled Tasks. With the revised grid spacing, mean RGB error across the icon crops fell from 71.56/255 to 50.19/255 in Windows 98 and from 78.31/255 to 53.92/255 in Windows 2000. Each crop still differs at strict tolerance. [Capture details](../tests/references/SOURCES.md#control-panel-and-display-properties)
- XP Classic and Luna share the 29-applet Classic View and the Category View switch. Classic View opens by default. At 120 DPI, Classic View mean RGB error in the overlapping region fell from 24.32/255 to 18.73/255 for XP Classic and from 37.20/255 to 17.11/255 for Luna. The Category View and End-key selection have their own strict VM comparisons. All six captures still differ in the icon artwork, text, and sidebar details. The Qt clients also render one physical pixel wider at 125% scaling. [Capture details](../tests/references/SOURCES.md#control-panel-and-display-properties)
- XP's Date and Time, Display, Mouse, Power Options, and Printers and Faxes applets use SVG paths and gradients. After the artwork and XP toolbar spacing updates, mean RGB error across the five icon crops fell from 47.72/255 to 21.74/255 for XP Classic and from 48.20/255 to 22.03/255 for Luna. All ten crops still show pixel differences. The tests compare identical coordinates in the VM and live Qt windows. [Capture details](../tests/references/SOURCES.md#control-panel-and-display-properties)
- The Luna menu, window and taskbar tests can read the owner's XP CD directly through the fixture extractor. The SP3 and Russian SP2 fixtures both passed the 148-test selection. [Instructions for reproducing the XP comparisons](../luna/README.md#the-lunamsstyles-sprites).
- Production XP loading-bar artwork and the new Windows 98 caption are SVGs. Plymouth PNGs are generated runtime assets. PNG reference crops retain the original pixels. [Capture provenance](../tests/references/SOURCES.md).


## High-resolution guest captures

| Guest | Framebuffer | DPI | Comparison |
| --- | --- | --- | --- |
| Windows 95 OSR2 | 1024×768, 256 colours | 120 | The 32×32 Run hourglass is identical to the 96-DPI capture. The 16-bit mode produced a crosshatch artifact, so the reference uses the clean 256-colour mode. |
| Windows 98 SE | 1280×1024, 256 colours | 120 | All 1,024 hourglass pixels match the SVG on the native dialog face. |
| Windows 2000 Professional | 1280×1024, 16-bit | 120 | The same 32×32 SVG matches the native icon after RGB565 quantization. The frame and the empty taskbar band have separate 96-DPI comparisons. Device Manager’s Action and View menus share one 25-pixel band with five toolbar commands. The live Qt window follows this layout. The five command glyphs now have individual comparisons at the guest positions. |
| Windows XP Professional SP3 | 1280×1024, 16-bit | 120 | XP uses a slanted blue window. Its SVG is rendered into the 40×40 icon area and tested against independent Luna and XP Classic captures. At 96 DPI, XP Classic Device Manager uses the five-command console and two flat 24-pixel command bands. |

All four guests used the Cirrus display adapter and the display settings in their installed copies of Windows. Windows 7 used its installed VirtualBox Guest Additions and WDDM driver. [QEMU Cirrus adapter documentation](https://www.qemu.org/docs/master/system/qemu-manpage.html)

## Scalable artwork

The shared SVG test renders every shipped asset at 100%, 150% and 200%. Separate guest comparisons check the Windows 98 monitor, handed mouse, jack-in-the-box states and classic Run icon at native size. The monitor’s bevel now uses three two-pixel stipple patterns. The classic caption generator draws each bevel as four connected edges and each glyph as a single outline. All nine caption sheets produce the same native-size pixels as their previous versions. The Luna Kvantum checkmark also retains the original rendered pixels across the complete 24×3486 widget sheet. [Cross-scale tests](../tests/test_theme_svg_art.py) · [Native mouse comparisons](../tests/test_mouse_page.py) · [Run dialog comparisons](../tests/test_run_reference.py)
