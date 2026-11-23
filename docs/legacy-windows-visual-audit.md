# Windows 95, 98, 2000 and XP visual audit

The four reference guests booted from the owner's installation media. Windows 95 OSR2, Windows 98 Second Edition, Windows 2000 Professional and English XP Professional SP3 reached their desktops. The 95 guest uses an emulated Pentium with instruction-count timing. Its wall-clock measurements describe that VM.

[View original and rendered controls side by side](compare/legacy-vm-details.png). Each pair uses the same display scale. The tests compare the native-size pixels.

| Theme | What the fresh reference verifies | Remaining difference or limit |
| --- | --- | --- |
| Windows 95 OSR2 | Device Manager action buttons measure 84, 84, 84 and 83 pixels across, with six-pixel gaps. The classic layout now keeps the row aligned with the tree when widened. The 12×12 selected and unselected Display Properties radio buttons match after mapping the render to the guest's four neutral VGA colours. | The native Device Manager is a System Properties tab. The Linux tool opens separately and disables unavailable hardware actions. The OSR2 boot screen adds a Microsoft Internet Explorer line under the Windows 95 wordmark. The theme shows the earlier wordmark. The captured single-user shutdown dialog also has fewer choices than the project's multi-user dialog. |
| Windows 98 SE | The installed Windows shutdown artwork, LOGOW.SYS, shows Windows 98 over clouds with a blue caption. Plymouth previously inherited the Windows 95 shutdown image. The replacement uses the 98 boot artwork and a scalable caption. A 160×120 composition test checks the full image and the caption location. | The cloud reconstruction and caption lettering are approximate. The selected and unselected radio indicators in the captured shutdown dialog match the rendered black-pixel masks. |
| Windows 2000 Professional | The 640×480 boot recording shows a 165×10 bar at (273, 436). At half fill its 8×8 navy blocks, grey gaps and bevel now match all 1,650 pixels. | The installed desktop was captured at 1280×1024 with its Cirrus Logic driver. The two shutdown trials below measure the installed desktop. Other interactive transitions still need measurements. The captured graphical boot occurred during an installation restart. |
| Windows XP Professional SP3 | The 126×15 loading bar has 15 slots and 18 animation states. It advances eight pixels per step and repeats in about 1.69 seconds. The Qt preview matches every native bar frame and has a timed playback test. Plymouth uses the same SVG artwork and step sequence. Native Device Manager has five toolbar commands and a status bar. The Luna layout now follows that structure and uses SVGs for the five toolbar icons. | The Console Tree and Action Pane button faces are compared at their native positions. The Help and pane glyphs have separate RGB comparisons. Icon antialiasing and background gradients still differ. The unbranded theme depicts an earlier XP boot with an edition line. The SP3 capture omits it. Plymouth's on-screen cadence still needs an independent display recording. |

The XP Luna and XP Classic Device Manager captures place the command glyphs one pixel lower than the earlier Qt render. The corrected Console Tree and Action Pane SVGs use a single triangular arrow and three list lines. The tests compare the entire 14×12 face of each button at its guest position, with a limit of three levels of mean absolute RGB error out of 255. Redrawing the yellow Help mark and its paper background reduced error over the 14×15 capture from 18.38 to 9.01 in Luna and from 16.82 to 8.30 in XP Classic. The disabled Back and Forward arrows average 1.10 and 1.22 in Luna, down from 16.40 and 16.18. In XP Classic they average 2.91 and 2.96, down from 9.92 and 9.86. The unobstructed 420×23 Luna toolbar background averages 0.79 after restoring its horizontal tint and lower bevel. [VM and rendered command glyphs](compare/xp-device-manager-commands.png)

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

On Windows 98 SE, minimizing Notepad left its white client visible as a shrinking title bar travelled toward the taskbar. The system menu was gone at 0.178 s and the desktop had settled by 0.339 s from recording start.

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

Windows 2000 Professional at 1280×1024 and 120 DPI showed “Saving your settings...” by 0.290 and 0.301 seconds after confirmation. The blue desktop had cleared by 1.808 and 1.818 seconds. Libvirt reported power off at 2.122 and 2.148 seconds, respectively. These are first observations in two trials. The native 96-DPI confirmation dialog measured 417×269 and its frame passed the RGB565 comparison.

The Windows 95, 98 SE and XP guests completed a real shutdown. On the 98 SE guest with an emulated Pentium II and instruction-count timing, the first captured shutdown wordmark appeared 0.877 seconds after confirmation and the first subsequent black frame appeared at 1.385 seconds. These timestamps describe one run. [Native shutdown dialog](../tests/references/win98-se-shutdown-dialog.png) · [Captured shutdown artwork](../tests/references/win98-se-shutdown-vm.png)

XP displayed “Saving your settings…” during sign-out. The project's Luna shutdown preview switches from “Logging off…” to “Windows is shutting down…”. Recording the VM captures native text and transitions. It does not establish a portable duration for saving a user's session.

## Regression coverage

- The native-size XP boot animation, Device Manager command bands and Windows 2000 boot bar have captured reference fixtures. Windows 95 has explicit button-spacing and radio-indicator comparisons. Windows 98 uses its own shutdown bitmap as the reference for the reduced-size composition test.
- GTK 3 and GTK 4 render real controls in isolated KWin sessions. The classic palette tests exercise Windows 95, 98, 2000 and XP Classic separately, including the white interior of enabled text fields. Luna has separate cross-toolkit control and state tests. These comparisons cover specific controls and do not certify every application's layout.
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
