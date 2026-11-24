# Windows 7 Aero pixel audit

November 22, 2026. The theme differs visibly from Windows 7 in the Start menu, window captions, Control Panel and file-manager navigation. The empty superbar comes much closer. **117 of 118 audited RGB crops or sprite states differ by at least one pixel.** The unit of that count is a tested region or state. A one-level rounding difference and a redesigned toolbar each count once. Four additional tests compare layout proportions or control counts from published screenshots. [Recorded measurements for all 118 RGB comparisons](compare/report-aero-originals.csv)

![Initial audit before corrections, with original Windows 7 crops, theme renders and amplified pixel differences](compare/report-aero-originals.png)

The revised caption art uses a single neutral grey stroke around the close button’s lower-left corner and along its bottom edge in all eight states. Windows 7’s composited rim picks up the glass colour. The requested uniform rim therefore differs from the native pixels. With the active face composited over RGB (109, 146, 181), mean absolute RGB differences on the complete button are 14.52/255 at 96 DPI and 18.23/255 at 144 DPI. [Guest and SVG at both sizes](compare/win7-close-rim.png)

The installer’s Windows 7 icon pack contains 3,597 names for 1,410 distinct original images in this checkout. The import test renders the SVGs at 32 and 48 pixels and compares them with the source pack. The importer recognizes rounded rectangles and triangular cuts across a box. At 8× enlargement, tests compare the rendered outlines with their geometric boundaries. Separate tests cover the 117 embedded Kvantum control images, login controls, cursor frames and all 18 session-spinner poses. These comparisons use upstream artwork. The table and CSV below identify the comparisons with Windows itself. [Imported artwork tests](../tests/aero/test_aero_imported_art.py)

The five blue Find and Zoom icons previously showed small detached spots around the lens at large sizes. They now share a circular glass lens, an enamel rim and a single handle path. The Zoom variants add one glyph path. Tests render each icon at 8× and check both the continuous rim and the transparent area outside it. [Source, previous conversion and revised SVGs](compare/aero-search-zoom.png) · [Scalable lens artwork](../aero/icons/gtk-zoom-fit.svg)

The installed pack uses two 45 × 45 images for 15 Back and Forward aliases. The revised SVG draws the blue face, bevel and shadow with continuous gradients and mirrors the arrow for Forward. At 8×, a visual test samples the shadow along 48 radii and checks that it fades without detached specks. At the original size on a light grey background the previous trace averages 5.89/255 mean absolute RGB error in both directions. The smoother redraw averages 7.91 for Back and 7.89 for Forward. This reference is the installed Aero icon pack. [Source and both SVG renders](compare/aero-toolbar-arrows.png) · [Scalable Back artwork](../aero/icons/back.svg)

Flip Horizontal and Flip Vertical use two triangles, two gradients and a soft shadow. The source pack transposes the horizontal artwork and adds a transparent bottom row for the vertical variant. Tests check the native colours on two backgrounds and the straight diagonal at 8×. [Source and both SVG renders](compare/aero-flip-actions.png)

Rotate Left, Rotate Right and Rotate 180° now use triangular faces and a curved arrow. The 180° icon reuses the arrow for its second turn. On light grey at the native 50×48 size, revised mean RGB errors are 2.72, 2.21 and 2.74 out of 255 versus 2.08, 2.49 and 2.65 for the previous traces. Tests compare each arrow crop independently and check the blue diagonal at 8×. [Pack reference, previous SVG and revised rotation icons](compare/aero-rotation-actions.png)

## Window caption buttons

At 96 DPI, the minimize, maximize and close buttons occupy 20 painted rows. The last two rows are a dark outline and a bright highlight. The earlier theme compressed the face and glyph together into 18 rows. The revised decoration keeps the glyph at its native pixel size. The comparison uses the same regions and reference captures for both revisions.

| Region | Earlier mean RGB error (0–255) | Revised |
| --- | ---: | ---: |
| Active caption buttons | 31.32 | 17.16 |
| Inactive caption buttons | 19.52 | 14.79 |
| Active top-right corner | 34.68 | 23.65 |
| Inactive top-right corner | 18.12 | 15.75 |

The original audit crop ends above the bottom outline. An additional test samples all three buttons through the outline and highlight and checks their row positions in both focus states. The active glass around the buttons is still darker than the reference. [Windows 7, previous theme and revised theme at 2×](compare/aero-caption-buttons.png)

At 96 DPI, the opaque Minimize, Maximize and Restore glyphs now match the VM in both resting and hovered states. The comparisons check 56, 108 and 126 pixels per state, including the dark outlines. The test accounts for the one-pixel overlap of the restored caption cells. With the same matte as the earlier SVG test, whole-face mean RGB error fell from 13.36 to 13.06 for Minimize, from 22.00 to 17.91 for Maximize, and from 14.35 to 8.91 for Restore. Close remains at 11.86. After maximizing a KWin window at 100%, moving the Restore face one pixel right brings its bright glyph overlap with the VM from 52% to 100%. The adjacent Minimize and Close glyph masks also match. [Native glyph and whole-face comparisons](../tests/aero/test_aero_buttons.py) · [Live caption tests](../tests/aero/test_aero_caption.py)

The earlier theme used a `#69747f` outer rim and dividers, a `#8d564e` divider at the left of Close, and a 36% white inner stroke. Its shared dividers belonged to the buttons on their right. With these colours, the older active and inactive caption crops differ from their references by 25.44 and 22.04 RGB levels on average. [Current KWin and GTK captures](compare/aero-installed-caption-150.png)

The VM-based SVGs use the style atlas colours and alpha for the bevel. The painted top highlight is bright, and a dark line sits directly above the translucent lower highlight. The 144 DPI artwork keeps the lower rim one physical pixel wide. On the same blue test backdrop the whole-button mean RGB error out of 255 fell from 25.20 to 14.62 for Minimize, 29.05 to 14.95 for Maximize, 25.55 to 13.50 for Close, and 23.58 to 8.40 for Restore. The first row of Restore is clipped in the guest capture. The strict RGB comparison still reports differences on all eight crops at 96 and 144 DPI. [Full button faces at 144 DPI](compare/aero-full-caption-faces-144.png)

In live renders at 150%, the entire three-button crop averages 14.30 RGB levels of error in KWin and 35.24 in GTK 4 Files. The GTK 3 Boxes Close crop alone averages 20.84 at 100%. These comparisons include the glass and the app header behind the buttons. Run `python3 -m pytest tests/aero/test_aero_buttons.py -k complete_caption_face --exact-originals` to produce per-pixel difference images. [Live KWin and GTK 4 captures](compare/aero-installed-caption-150.png)

### Controlled backdrop captures at 144 DPI

The Windows 7 SP1 Aero VM held an active Notepad window in the same position over dark, light and blue backgrounds. The SVG gradients now use colour and opacity measured against the glass immediately beside the buttons. KWin and both GTK caption generators share those gradients for their high-density resting artwork.

| Button | Dark backdrop | Light backdrop | Blue backdrop |
|---|---:|---:|---:|
| Minimize | 19.29 → 11.62 | 12.53 → 8.31 | 16.80 → 10.32 |
| Maximize | 25.70 → 6.81 | 10.92 → 3.79 | 20.07 → 5.58 |
| Close | 18.34 → 7.13 | 10.69 → 6.46 | 15.43 → 6.89 |

The table reports mean absolute RGB error out of 255 over the whole button. In all nine comparisons, the reference and SVG use the same adjacent glass colour for each row. The dark edge of Minimize and the translucent highlights on either side of Maximize now average 1.57–3.53 levels of error across the three backdrops. The three columns at the right edge of Close now average 9.25–15.80 levels, down from 45.29–50.23 before the inset bevel and highlights. Strict comparison still fails on all nine faces. Visible differences remain in the outer rim, lower corners and side shading. [Native, previous and revised renders](compare/win7-caption-controlled-glass.png) · [Visual test](../tests/aero/test_aero_buttons.py)

The next revision separates the Minimize bevel into three nested curves and brightens the glass towards the shared seam. Maximize's square ring now lands on the 40-pixel cell's grid. Its four-pixel-wide bright stems match the guest RGB samples exactly. Close has a thinner glyph outline and a brighter lower reflection along its neutral rim. All nine whole-face comparisons still differ at zero tolerance. [Visual tests](../tests/aero/test_aero_buttons.py)

| Button | Dark backdrop | Light backdrop | Blue backdrop |
|---|---:|---:|---:|
| Minimize | 11.62 → 3.40 | 8.31 → 2.26 | 10.32 → 2.86 |
| Maximize | 6.81 → 5.24 | 3.79 → 1.66 | 5.58 → 3.89 |
| Close | 7.13 → 5.62 | 6.46 → 5.40 | 6.89 → 5.56 |

At framebuffer coordinate (780, 189), increasing the solid backdrop from RGB (24, 24, 24) to (232, 232, 232) changes the native glass from (27, 35, 43) to (168, 200, 232). A constant tint with a single SVG opacity would change all three channels by the same amount. Reproducing that response across backgrounds requires a change in how the backdrop is composited.

The live 144-DPI KWin test uses those same desktop colours. The Aero blur effect now supplies the tint for active, restored windows. Setup fits its colorization parameters to the three VM mattes and turns off the effect's added corner glow. With the built-in blur, the fallback SVG supplies the tint. [Exact live comparisons and regression limits](../tests/visual/parity.py)

| Live KWin region | Dark backdrop | Light backdrop | Blue backdrop |
|---|---:|---:|---:|
| Glass beside buttons | 63.92 → 2.57 | 31.59 → 7.66 | 29.13 → 3.59 |
| Complete button group | 22.33 → 5.45 | 10.04 → 5.41 | 11.87 → 5.28 |

All six live crops still differ at zero tolerance. In an inactive-window check over the `#4395D1` desktop, changing the blur alone raised the sampled caption error from 7.32 to 14.89. The native-blur SVG now uses a cooler caption tint with a short gradient into the side borders. The caption error fell to 0.76, the right border fell from 22.20 to 19.66, and the bottom border fell from 20.58 to 15.46. [Inactive-window regression](../tests/aero/test_aero_caption.py)

### Caption hover and focus timing

The cross-theme caption test includes 144-DPI Aero captures while the pointer rests on each button and while the mouse button is held. It also compares disabled Maximize and Close in a native Win32 test window and Restore after maximizing Notepad. Those full-face comparisons still have RGB differences. [VM and SVG caption states](compare/caption-states-vms.png) · [Visual tests](../tests/test_caption_states_reference.py)

Three fresh 60 Hz trials per control from the Windows 7 SP1 VM show a fast hover entry and a slower fade on exit. The earlier decoration switched both instantly. The Aero caption now animates each button independently and draws the coloured halo beyond its edges. The live KWin test checks the halo's falloff against the original Close button. Custom groups containing additional KDE controls use Aurorae's standard renderer.

| Caption control | Windows hover entry | Revised entry | Windows hover exit | Revised exit |
| --- | ---: | ---: | ---: | ---: |
| Close | 16–33 ms | 33 ms | 117–150 ms | 130 ms |
| Maximize | 50–67 ms | 65 ms | 116–133 ms | 130 ms |
| Restore | 50–83 ms | 65 ms | 116–134 ms | 131 ms |
| Minimize | 50–84 ms | 65 ms | 117–133 ms | 131 ms |

Times measure the 10–90% change in displayed button RGB. The revised figures come from rendering the installed decoration's QML component with the project artwork. Both focus directions reached their final face in the first changed frame on both systems. The automated comparisons allow 25 ms for sampling hover transitions and require a visible intermediate frame. They do not measure input latency. [Native capture details and timestamps](../tests/references/SOURCES.md) · [Visual timing tests](../tests/aero/test_aero_caption_motion.py)

### Whole-window motion

Three trials followed Notepad from its original bounds to maximized or minimized and back. A clean installation of the Aero preset in nested KWin repeated those actions on a light Qt window of the same size. Both desktops were 1024 × 768. Times below measure the 10–90% RGB change across the workspace above the taskbar. A one-frame result means both thresholds crossed in the same displayed frame. [Windows 7, previous and revised filmstrips](compare/aero-window-motion.png) · [All 36 timings](compare/aero-window-motion.csv)

| Action | Windows 7 SP1 | Previous KWin Aero | Revised KWin Aero |
| --- | ---: | ---: | ---: |
| Maximize | One frame | 117–150 ms | One frame |
| Restore from maximized | One frame | 117–150 ms | One frame |
| Minimize to taskbar | 116–117 ms | 100–133 ms | 100–133 ms |
| Restore from taskbar | 33–50 ms | 100–133 ms | 33–50 ms |

The Windows window began shrinking and becoming transparent together. KWin's original Squash effect held the large, opaque window longer and accelerated at the end. The Aero minimize effect now fades and shrinks the window together and accelerates when restoring. The taskbar button's position determines the destination. Windows and Plasma had different taskbar layouts in these recordings. Display samples were about 17 ms apart on Windows and typically 17–33 ms apart during transitions on KWin. One KWin maximize-restore interval was 50 ms. The captures cannot establish sub-frame equality.

The Windows 7 theme selector and the installer's Aero animations preset apply the new motion. Explicit installer animation choices take precedence. The live test records real button clicks in nested KWin and compares the transitions with the saved SP1 frames. [Whole-window visual test](../tests/aero/test_aero_window_motion.py)

## Control Panel follow-up

The table under Initial measurements records the original audit. After the Control Panel revision, the same 220 × 34 navigation crop measured **25.75** levels of mean RGB error, down from **61.84**. The Aero shell now puts navigation, breadcrumbs and search on one row. Taskbar settings open in their own 398 × 424 client area. Visual tests compare its tabs and action buttons with the original at 100% and 150% scale. [Updated Control Panel](compare/aero-control-panel.png) · [Taskbar and Start Menu Properties](compare/aero-taskbar-properties.png)

### Category View

The Windows 7 preset now opens Control Panel in the eight-category layout. Category headings open the related installed applets. Task links open a specific applet or property tab. The Windows 7 reference shows another window covering the lower right, so the comparison below uses only the unobscured upper 780 × 300 pixels. At 100% and 150% the first heading in each column starts within five logical pixels of the original. The screen still differs in icon artwork, task-link text and row spacing. The links describe the settings available in this project. Opening a category now retains the native 199-pixel left sidebar. In Appearance and Personalization the first heading is within five logical pixels at both scales. The clear lower sidebar differs from the original by 0.90 levels of mean RGB error. [Original category page](../tests/references/win7-sp1-aero-category-detail.png) · [Current category page](compare/aero-appearance-category.png)

The address box moved six pixels left. Its dark inner border starts at x=71 and y=5 in the navigation strip, matching the SP1 VM at both tested scales after normalization. The breadcrumb arrow opens a menu of child locations. The published navigation crop still differs at 7,386 of 7,480 pixels, with mean channel error 25.75. The SP1 VM shows both navigation arrows disabled on initial launch. The project draws both with one SVG circle, a curved highlight and an arrow, mirrored for Forward. The disabled-arrow comparison with the VM at 100% improved from 47.27 to 26.26 levels of mean RGB error. The toolbar glass and text rendering still differ. [Scalable navigation artwork](../data/control-panel/aero-navigation-disabled.svg) [VM and revised navigation strip](compare/win7-control-panel-navigation.png)

[Full current Category View](compare/aero-control-panel-category.png) · [Windows 7 reference and current renders at both scales](compare/aero-category-comparison.png)

## SP1 reference VM and layout corrections

A clean English Windows 7 Professional SP1 x86 installation provided native 800 × 600, 96-DPI captures of [Device Manager](../tests/references/win7-sp1-basic-device-manager.png) and [Control Panel](../tests/references/win7-sp1-basic-category.png). Device Manager has a menu and toolbar above the tree. A status bar runs along the bottom. The toolbar commands differ with selection. The project now tests the colours and heights of both command bands and checks that the tree extends across the area previously occupied by buttons. These two VM images use the Basic graphics driver.

Hovering a category highlights the whole group on Windows 7. The project draws a rounded blue outline, inner highlight and vertical fill gradient behind the icon and links. The folder-driven suite compares the unobstructed right edge at 96 DPI and checks that leaving restores the idle fill. In the 60 Hz Aero capture, the group reached its highlight colour in the first changed frame. The suite compares the idle sample and four consecutive samples after moving the pointer onto the category. [Steady hover capture](../tests/references/themes/win7/control-panel/hover.png) · [Hover opening capture](../tests/references/themes/win7/control-panel/hover-opening.png)

At 144 DPI, the System and Security highlight disappeared in one visible frame in all three 60 Hz trials. The host pointer move preceded the first idle sample by about 50 ms, including input delivery and display presentation. The pixel test aligns each sequence at the final highlighted frame and checks the first four idle samples. [Hover exit capture](../tests/references/themes/win7/control-panel/hover-exit.png)

The Run button positions, Advanced System Properties action row and six-window Alt+Tab bottom inset pass their original-layout comparisons after correction. The figures below describe the earlier renders. The five Start-menu RGB crops still differ after the search field, power menu and glass changes.

| Start menu sample | Earlier mean RGB error | Revised mean RGB error |
| --- | ---: | ---: |
| All Programs search well | 25.37 | 9.42 |
| Initial search well | 25.65 | 9.73 |
| Right-hand glass | 9.55 | 5.88 |
| Shut down split button | 43.30 | 22.68 |
| Shut down options menu | 28.69 | 18.70 |

## What the Aero VM confirmed

| Surface | Comparison with the installed theme |
| --- | --- |
| Device Manager | Windows 7 uses a toolbar above the tree and a status bar below it. The project's Aero view now puts commands there and tests their centres at two widths. The blue navigation arrows and their grey disabled states, both pane commands, the Help book and Scan use SVGs. Tests render the six enabled commands at 100%, 150% and 200% and compare them with the command resources from the installed VM on light and dark backgrounds. Mean RGB error in the 170×23 Aero crop fell from 16.82 to 3.54, with 2,262 of 3,910 pixels differing. The aligned Basic crop averages 6.00. Its guest toolbar omits Scan in the captured state. [Original Device Manager](../tests/references/win7-sp1-aero-device-manager.png) · [Toolbar comparison](compare/aero-device-manager-toolbar.png) |
| Display Properties | All five project tabs fit without either scrollbar at 100% and 150% scale. The native Windows 7 Display applet opens Screen Resolution. The multi-tab project sheet retains settings for the other desktop styles. [Native Screen Resolution](compare/win7-sp1-screen-resolution.png) · [Project Appearance tab](compare/aero-display-appearance.png) |
| Taskbar settings | The icon-only Windows 7 taskbar hides its sizing controls and button-width preview. The properties sheet has separate comparisons for tab and action positions. [Native sheet](../tests/references/win7-sp1-aero-taskbar-properties.png) |
| Start and hover | In both keyboard and mouse captures, the white program pane is fully visible in the first frame in which it appears. The default theme now reproduces that change. The original orb took about 217 ms to go from 10% to 90% of its hover colour change. A rendered animation test compares the same area and allows three frames for sampling. [Start opening samples](../tests/references/win7-sp1-start-opening.png) · [Orb hover samples](../tests/references/win7-sp1-start-orb-hover.png) |
| Lock screen | The credential field now lands within two pixels of all four original bounds at both tested resolutions. Across its top edge and the adjoining background the mean RGB error is 1.85 at 1024 × 768 and 0.79 at 800 × 600. [Original locked session](../tests/references/themes/win7/lock-screen/1024x768.png) |
| Calendar | The 336 × 247 client, analog clock span and settings footer match their geometry or colour checks. The fixed rim crop still differs at 466 of 560 pixels. [Original calendar](../tests/references/win7-sp1-aero-calendar.png) |

## Shutdown from the desktop to power-off

The original spent about half a second showing only the desktop wallpaper after its windows closed. A brief black interval followed, then the blue screen showed **Logging off...** for one or two capture intervals before changing to **Shutting down...**. In Plasma, the panel stayed visible until the black handoff, and Plymouth opened directly on **Shutting down...**. [Side-by-side shutdown recording](compare/win7-sp1-shutdown-comparison.webm)

| Measurement | Windows 7 Professional SP1 | Fedora KDE 44 with revised Plymouth theme |
| --- | ---: | ---: |
| Final click to desktop disappearing | 1.03–1.20 s | 2.40–2.44 s |
| Black handoff before the first blue status screen | 0.20–0.23 s | 0.20 s |
| Final click to first blue status screen | 1.23–1.40 s | 2.60–2.63 s |
| Final click to “Shutting down...” | 1.30–1.47 s | 2.60–2.63 s |
| Time on the blue background, including both Windows captions | 1.20–3.67 s | 1.13–2.85 s |
| Median time for one spinner revolution in each trial | 0.834 s | 0.834–0.866 s |
| Final click to hypervisor-reported power-off | 2.52–4.95 s | 3.73–5.48 s |

The original 18-pose spinner was faster than the theme's earlier 15 fps setting (a nominal 1.20 s per revolution). Plymouth at 21 fps reproduced the Windows period to within one captured frame. The shutdown caption previously began at y=376 on the 1024 × 768 export. It now begins at y=326, the original position. Tests also check the 800 × 600 layout. The configured font affects the horizontal lettering bounds. [Caption and spinner comparison at native scale](compare/win7-sp1-shutdown-position.png)

Time zero is the final click on Shut down in the Windows Start menu or in the project's confirmation dialog. Each display was sampled against a monotonic clock at 30 Hz and 1024 × 768. Windows ran in the offline WDDM reference VM. Fedora ran in a disposable QEMU/KVM guest built from Fedora KDE 44 release 1.7, with the distribution's Plasma desktop, the project's shutdown command, the exported theme and the real Plymouth power-off service. No applications had unsaved work. Power-off was detected separately from screen colour. The first Windows trial recorded the final black frame without a hypervisor power-off timestamp. Fedora displayed the blue screen through the last sample in both final trials; one also contained a single dark frame during that screen. Three Windows trials and two final Fedora trials supply these ranges. Individual transitions are resolved to roughly one frame (33 ms). Service load, open applications and hardware can change the timings. The theme adds no timer to prolong shutdown. [Per-trial measurements in seconds](compare/win7-sp1-shutdown-timing.csv)

## GTK 3 and GTK 4 controls

Both toolkits now use the Aero faces for checkboxes, radio buttons, progress bars, tabs and disabled form controls. GTK 3 paints the scrollbar grips with orientation-specific CSS and uses grey artwork for disabled indicators. GTK 4 Files keeps its header layout and uses the same SVG caption faces as GTK 3. At native scale the checked and mixed checkboxes match between the two toolkits in the visual tests. The radio buttons use separate SVG faces for normal, hover, press, checked and disabled states. The checked, hovered radio differs by 1.69 levels of mean absolute RGB error between toolkits. Against Windows artwork, the checked, pressed GTK 4 radio improved from 42.77 to 7.77 levels. Errors across all seven tested radio states range from 4.43 to 9.30. The 6×5 push-button corner now averages 3.98 levels in GTK 4 and 5.51 in GTK 3. The disabled corner averages 2.53 and 4.11 respectively. These comparisons use the rendered widgets with the showcase margins removed. [Side-by-side toolkit renders](compare/aero-gtk-toolkit-controls.png)

GTK 3 and GTK 4 paint each thumb face from an SVG gradient. The grip uses three straight strokes and their highlights. The scrollbar tests compare the fixed corner and a strip across the face with the Windows 7 Aero artwork at 96 DPI. The GTK 4 corner audit previously started one pixel inside the Windows sprite. With both renders aligned, the normal horizontal corner improved from 5.20 to 3.39 and the vertical corner from 5.98 to 5.28. Across both toolkits, orientations and all three states, mean error on the face fell from 8.45–16.78 to 2.02–3.59 out of 255. The comparison shows the leading end of each thumb enlarged with nearest-neighbour sampling. [Windows 7, GTK 3 and GTK 4 scrollbar thumbs](compare/win7-scrollbar-thumbs.png)

## Initial measurements before the corrections

| Surface                    | Original versus theme                                                                                                                                                                                                                                                                                                                                                                                                                 |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Start menu                 | The original search well has a larger inset, italic placeholder and a small magnifier. The test render has a wider field, upright placeholder and a different search glyph. In All Programs, 8,459 of 11,340 search-well pixels differ. The Shut down split button differs at all 2,592 sampled pixels, with mean channel error 43.30. All 11,025 pixels in a text-free stretch of the right-hand glass differ, with mean error 9.55. |
| Frames and blur            | The modeled active caption buttons differ at 1,903 of 1,995 pixels, with mean error 31.32. The active top-right corner averages 34.68 and the inactive buttons average 19.52. In the live striped-wallpaper test, the light-to-dark transition spans 6.88 px at rest and 6.66 px during a drag. The fitted Windows 7 reference spans 8.84 px.                                                                                         |
| Superbar                   | The empty panel between x=320 and x=799 differs at 17,381 of 19,200 pixels, yet averages **0.78** levels of error. The running-button edges average 1.12, the hidden-icons arrow 2.34, Show desktop 3.62 and the Start orb ring 4.44. The orb measurement excludes the branding, and the running-button measurement excludes the application icon.                                                                                    |
| Control Panel and Explorer | Windows 7 combines circular navigation arrows and breadcrumbs on glass. The project's Control Panel has labelled actions and a separate address row. Thunar has a menu button, chevrons and a home button. The two 1× navigation crops average 61.84 and 65.39 respectively.                                                                                                                                                          |
| Alt+Tab                    | With six previews at 160 px, the space below the thumbnail image occupies 20.2% of the panel height. Microsoft's six-preview illustration measures 10.8%, with about 2.7 percentage points of measurement uncertainty.                                                                                                                                                                                                                |
| Run and System Properties  | In Run, the first action starts at 33.9% of the client width against 27.3% in the Windows 7 figure. The other two actions also start farther right. The original Advanced System Properties sheet has OK, Cancel and Apply. The rendered sheet has OK and Cancel.                                                                                                                                                                     |
| GTK and Firefox            | All 15 tested GTK checkbox and radio states differ from the original sprites. A normal checkbox averages 5.60 levels of error and a checked, pressed radio averages 7.77. The fixed corners of both push-button states, both entry states, the horizontal progress track and both scroll-thumb orientations also differ. Firefox's button is much closer. Its 10 × 21 left edge averages 2.44.                                       |
| Notification balloon       | Microsoft's Windows Update example shows a wrench beside Close. The rendered file-completion balloon has a single Close control in this corner. The 44 × 23 action crop averages 13.89 levels of error. Sender content and the balloon tail are outside the crop.                                                                                                                                                                     |

The sampled plain blue wallpaper matches exactly. Including that sample, 30 comparisons have mean absolute RGB error at or below 1/255. The simplified gradient fits introduce small rounding differences in the grouped-task stack sprites and middle caption faces that previously matched exactly. The face tests exclude the glyph. Separately, the boot test reproduces both lettering crops of the supplied 1080p video frame exactly. In the 4:3 sign-in comparison, the password field centres at 63.87% of screen height against 63.86% in the published figure.

Windows XP offered both Category View and Classic View. The latter exposed applets directly, including the older Display Properties. [Microsoft’s Control Panel history](https://download.microsoft.com/download/9/a/3/9a36304d-cb64-427e-a184-4ed1bb556712/win7_sbs_earlycontent_ch1.pdf) · [Microsoft’s XP applet testing guide](https://learn.microsoft.com/en-us/previous-versions/windows/desktop/dnacc/testing-assistive-technology-for-compatibility-with-microsoft-windows-xp)

## Scope across the installer

| Installer component | Visual evidence and coverage limit                                                                                                                                                                                                                                      |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Base                | GTK indicators and selected widget corners have Microsoft sprite comparisons. The icon collection, aliases and cursor frames are rendered against their imported source packs.                                                                                          |
| Look                | Active and inactive Aurorae frames, button faces and glyphs have original comparisons. The 117 embedded Kvantum controls have source-art comparisons. Font substitution and application layouts can still change the result.                                            |
| Animations          | Nested KWin captures cover stationary and moving glass. A source screenshot constrains blur width. The Start program pane, orb hover and Control Panel category highlight have frame comparisons from the Aero VM. Other transitions lack paired timing measurements.                                                                                         |
| Taskbar             | Nested Plasma covers the panel, orb, buttons, grouping, tray, clock, calendar, Peek and Jump Lists. The numeric original comparisons cover selected collapsed regions and sprites. The calendar flyout geometry and clock rim also have SP1 comparisons. Clock text, unlocked spacing and paging layout have partial coverage. |
| Start menu          | Original shell captures cover fixed chrome on the initial page, All Programs and the power menu. Search results, application identities and confirmations have project portraits and interaction tests.                                                                 |
| Notifications       | The original balloon action area, project portrait and dismissal/expiry tests cover appearance and behavior for the tested examples.                                                                                                                                    |
| Clippy              | The Office Assistant has its own original idle-frame and balloon comparisons. It is an optional Office component.                                                                                                                                                       |
| Extras              | Advanced System Properties and Run have original layout checks. The other System Properties pages have project portraits. Device Manager has native Basic and Aero client and toolbar checks. Other utilities still lack complete matched captures.                                                         |
| Control Panel       | Navigation, Category View layout, category hover and the Taskbar properties sheet have original comparisons. The Display sheet has two-scale fit checks. Project-specific settings have different content.                                                                                                                                    |
| Sounds              | The installer and sound-mapping tests cover this component. Sound playback has no pixel output.                                                                                                                                                                         |
| Background          | The plain blue reference matched exactly. Stock wallpaper selection, image scaling and custom wallpapers are separate cases.                                                                                                                                            |
| Desktop             | Desktop tests cover shortcut configuration and destinations. Icon-pack tests cover artwork. A desktop with matching shortcuts and label rasterization remains unverified.                                                                                               |
| Switcher            | A six-window render has a proportional comparison against Microsoft's Windows Flip illustration. The reduced source supports layout measurements only.                                                                                                                  |
| Screensaver         | Selection and invocation of XScreenSaver hacks have behavior tests. Animation frames lack a matching stock Windows 7 reference for the selected hack.                                                                                                                   |
| Winamp              | The optional qmmp integration has sizing and docking tests. Its application skin has no stock Windows 7 counterpart.                                                                                                                                                    |
| Explorer            | Thunar now draws the Explorer breadcrumb triangle after each directory. The live GTK 3 test compares all four separators in /usr/share/icons at 100% and 150% with the Windows glyph. [Explorer and Thunar breadcrumbs](compare/aero-thunar-breadcrumbs.png) GTK Files has separate visual tests. A complete Dolphin or Thunar window with matching folder contents remains unverified.                                                                        |
| Mouse               | Converted cursors have source-art comparisons, hotspot checks and animation-frame checks. Button mapping, acceleration and double-click timing are behavioral.                                                                                                          |
| Lock screen         | The actual lock QML is rendered with simulated authentication. Portrait, submit, failure and switch-user states have artwork or placement checks. Native full-screen lock captures at two resolutions constrain the password field. The complete backdrop and account artwork are outside the field comparison.                                                                  |
| Splash              | Welcome and the session spinner have rendered-frame and source-art checks. The session handoff lacks a synchronized Windows sequence.                                                                                                                                   |
| Plymouth            | Boot lettering has the two exact video crops. Animation tests cover frames and timing, and export tests check preview parity. VM recordings cover desktop teardown, the shutdown screen and power-off. Physical display and firmware behaviour remain unmeasured.                                                        |
| SDDM                | The sign-in field position matches the published 4:3 layout within measurement uncertainty. Login controls and failure states have separate source-art and QML checks. Full-screen RGB fidelity remains unverified.                                                     |
| Firefox             | Headless Firefox renders a fixture using the stylesheet installed by Setup. The left button edge has a native Windows control reference. Whole browser chrome is outside this comparison.                                                                               |

## Reproduce

From the repository root on a Plasma development machine with the [Aero reference assets](../aero/README.md), run both commands. The second returns a failure for each tested original-pixel mismatch or layout discrepancy. Use a fresh pytest temporary directory if retaining multiple runs.

```sh
python3 tests/aero/run_visuals.py
python3 tests/aero/run_visuals.py --exact-originals --junitxml=/tmp/windows7-pixels.xml
```

RGB comparisons use the mean absolute error across the three 8-bit channels. One unequal channel marks a changed pixel. Failed RGB tests save a triptych under the reported pytest path. The difference panel multiplies absolute channel errors by four for visibility. Inputs are unscaled 96-DPI crops and composited theme sprites. Published, reduced, or JPEG figures contribute only to the four layout tests. [Reference provenance](../tests/references/SOURCES.md) · [Audit tests](../tests/aero/audit_desktop_pixels.py)

The Start and balloon renders use the existing deterministic Fusion, DejaVu Sans and sample-icon fixture. Their glass, dimensions and placement are measurable, while different installed fonts and icon themes can change text and glyphs. The panel captures use an isolated nested Plasma session, the frames use the Aurorae layout model, and the file manager runs inside an isolated KWin session. [Portrait harness](../tests/aero/render_aero_dialogs.py) · [Frame harness](../tests/aero/test_aero_window_reference.py)

An earlier run of the normal visual runner passed **402 tests** across two runs, with zero skips. The full suite passed its 400 cases, and the applet rerun covered the two subsequently added category-detail scale cases. A separate applet, installer, theme and sound run passed **381 cases**. The tests overlap. These counts include behavior, project baselines and imported-art checks. The 118 zero-tolerance original-image comparisons are reported separately in the CSV.

### GNOME Boxes guest title bar

The GTK 3 test loads the display toolbar from the installed GNOME Boxes binary and renders it at 1× and 2×. It measures the caption buttons' widths and checks that their edges touch. It compares the rendered close glyph with the SVG rasterized at the same density and measures the close button's hover and leave transitions against Windows 7 SP1 recordings. The back, fullscreen, keyboard and menu actions belong to Boxes itself. [2× toolbar capture](compare/aero-boxes-gtk3-header.png) · [Visual comparison tests](../tests/aero/test_aero_gtk.py)


## High-DPI caption artwork

On the Windows 7 SP1 WDDM guest with VirtualBox Guest Additions 7.2.4, the 1280×960 desktop at 150% (144 DPI) draws a 16×4 bright minimize bar and an 18×14 maximize ring. The 96-DPI SVG enlarged to the same physical size drew a 14×4 bar and a 14×11 ring. The high-density SVG artwork uses a thicker ring and close cross. Four visual comparisons cover minimize, maximize, close and restore against native Notepad captures at 150%. The last uses maximized Notepad. The guest capture retains its original pixels. [Native and SVG captions at 144 DPI, enlarged 3× for inspection](compare/win7-144dpi-captions.png)

Live GTK 3 and GTK 4 captures at 2× are also compared with the 144-DPI originals on a common pixel grid. The Display control panel provided selected and unselected 19×19 radio indicators at 144 DPI. GTK 3 and GTK 4 use high-density SVGs for these two states. In the native-size artwork comparison, the unselected indicator averages 8.37 RGB levels of error and the selected indicator averages 14.64.

Three 60 Hz recordings of the same restored Notepad button at 144 DPI measured about 17 ms from 10% to 90% on pointer entry and 133–150 ms on leave. The live caption at 150% passed those intervals with a 25 ms sampling tolerance. A separate nested KWin screenshot at 150% verifies the physical size of the close glyph. [Native 60 Hz frames](../tests/references/win7-sp1-144dpi-close-motion.png)

At 100% scale KWin draws the same light glyph pixels as the SP1 Device Manager capture for Minimize, Maximize and Close. The same three glyph masks also match in the GTK 4 Files capture at 100%. At 150% scale the caption comparison registers the whole three-button group against one Windows 7 SP1 capture, then measures the overlap of the light glyph pixels. This preserves errors in the spacing between buttons. KWin now matches all three bright glyph masks at 150%, up from 81% for Minimize, 90% for Maximize and 95% for Close in the previous comparison. Aligning the group to physical pixels removed the step along the Minimize bar. Its entire 16×4 interior now matches the guest in RGB. GTK 4 Files scores 84% for Minimize, 97% for Maximize and 82% for Close. Its SVG canvases now match the width of each GTK button slot. Full-face colour also depends on the backdrop behind the glass. [Guest, previous KWin, current KWin and GTK 4 Files](compare/aero-installed-caption-150.png)

A live click on KWin’s Maximize button at 150% produces the same bright Restore glyph mask as maximized SP1 Notepad. The neighbouring Minimize and Close glyph masks also match. A separate 40-pixel SVG rasterization compares all 212 bright Restore pixels in RGB and matches every value. The surrounding face and outline still differ. Maximized GTK 4 Files uses Restore in the centre of the group. Its glyph overlaps the SP1 reference by 68% at 100% scale and 75% at 150%. The comparison aligns the native Restore capture by the bottom border because Windows clips its top row when maximized.
