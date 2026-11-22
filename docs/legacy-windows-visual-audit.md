# Windows 95, 98, 2000 and XP visual audit

The four reference guests booted from the owner's installation media. Windows 95 OSR2, Windows 98 Second Edition and English XP Professional SP3 reached their desktops. Windows 2000 Professional is at the product-key screen. The 95 guest uses an emulated Pentium with instruction-count timing. Its wall-clock measurements describe that VM.

[View original and rendered controls side by side](compare/legacy-vm-details.png). Each pair uses the same display scale. The tests compare the native-size pixels.

| Theme | What the fresh reference verifies | Remaining difference or limit |
| --- | --- | --- |
| Windows 95 OSR2 | Device Manager action buttons measure 84, 84, 84 and 83 pixels across, with six-pixel gaps. The classic layout now keeps the row aligned with the tree when widened. The 12×12 selected and unselected Display Properties radio buttons match after mapping the render to the guest's four neutral VGA colours. | The native Device Manager is a System Properties tab. The Linux tool opens separately and disables unavailable hardware actions. The OSR2 boot screen adds a Microsoft Internet Explorer line under the Windows 95 wordmark. The theme shows the earlier wordmark. The captured single-user shutdown dialog also has fewer choices than the project's multi-user dialog. |
| Windows 98 SE | The installed Windows shutdown artwork, LOGOW.SYS, shows Windows 98 over clouds with a blue caption. Plymouth previously inherited the Windows 95 shutdown image. The replacement uses the 98 boot artwork and a scalable caption. A 160×120 composition test checks the full image and the caption location. | The cloud reconstruction and caption lettering are approximate. The selected and unselected radio indicators in the captured shutdown dialog match the rendered black-pixel masks. |
| Windows 2000 Professional | The 640×480 boot recording shows a 165×10 bar at (273, 436). At half fill its 8×8 navy blocks, grey gaps and bevel now match all 1,650 pixels. | Desktop layout, interactive transitions and shutdown remain unmeasured on this guest. The captured graphical boot occurred during an installation restart. |
| Windows XP Professional SP3 | The 126×15 loading bar has 15 slots and 18 animation states. It advances eight pixels per step and repeats in about 1.69 seconds. The Qt preview matches every native bar frame and has a timed playback test. Plymouth uses the same SVG artwork and step sequence. Native Device Manager has five toolbar commands and a status bar. The Luna layout now follows that structure and uses SVGs for the five toolbar icons. | The toolbar glyph positions are tested within two pixels. Icon antialiasing and background gradients still differ. The unbranded theme depicts an earlier XP boot with an edition line. The SP3 capture omits it. Plymouth's on-screen cadence still needs an independent display recording. |

## Comparisons on the installed guests

| Surface | Result at native scale |
| --- | --- |
| Windows 95 OSR2 and 98 SE Run | Both dialogs measured 347×163. The editable field and three button bevels matched across four comparison bands after mapping the intermediate light grey to the VGA palette. |
| Windows 95 OSR2 and 98 SE Start and taskbar | Both menus used 32-pixel rows. The 98 theme previously used 36. The 28 taskbar rows match in an unoccupied band after the same palette mapping. The high-colour Help icon paints 22 rows on the theme and 24 on the SE VGA guest. |
| Windows 98 SE Device Manager and Display | The four Device Manager button widths and gaps match the shared classic row. The Appearance sample measures 355×193. The corrected preview matches the guest’s desktop silhouette and both scroll arrowheads. The monitor with its stand measures 184×169. The old drawing omitted the bottom 13 rows. The full replacement SVG passes the monitor comparison. |
| Windows 98 SE Mouse | Both handedness illustrations and the open and closed double-click test pictures match the captured RGB pixels at 1×. Production pictures are SVG. |
| Windows 2000 Professional Setup | The 75×23 Back button matches the theme’s ordinary push-button size and top-to-bottom bevel sequence. The setup and desktop palettes differ. |
| Windows XP SP3 Start and taskbar | The Luna menu matches the captured 380×477 dimensions. Three chrome regions compare within six mean RGB levels. The empty taskbar matches the existing per-channel tolerance in all 30 rows. |

[Compare the Windows 98 Appearance preview and monitor at native size.](compare/win98-se-display.png)

The Windows 98 cold boot advances the bottom colour band to the right by 32 pixels per observed step. Sixteen captured strips compare within three mean RGB levels after adjusting the 640×400 VGA pixel aspect ratio. The recording includes missed display updates and irregular startup pauses. A warm restart on this emulated machine stalled at the logo. Timing measurements use the successful cold boot.

## Desktop motion and power

On Windows 98 SE, minimizing Notepad left its white client visible as a shrinking title bar travelled toward the taskbar. The system menu was gone at 0.178 s and the desktop had settled by 0.339 s from recording start.

In the XP SP3 Device Manager minimize recording, the system menu dismissed at 0.181 seconds, the first captured travelling title bar appeared at 0.211 seconds, and the destination settled by 0.447 seconds. The original window body stayed visible under the travelling title bar. The shared KWin effect scales the window itself. Matching its duration alone would leave that visual difference.

The Windows 95, 98 SE and XP guests completed a real shutdown. On the 98 SE guest with an emulated Pentium II and instruction-count timing, the first captured shutdown wordmark appeared 0.877 seconds after confirmation and the first subsequent black frame appeared at 1.385 seconds. These timestamps describe one run. [Native shutdown dialog](../tests/references/win98-se-shutdown-dialog.png) · [Captured shutdown artwork](../tests/references/win98-se-shutdown-vm.png)

XP displayed “Saving your settings…” during sign-out. The project's Luna shutdown preview switches from “Logging off…” to “Windows is shutting down…”. Recording the VM captures native text and transitions. It does not establish a portable duration for saving a user's session.

## Regression coverage

- The native-size XP boot animation, Device Manager command bands and Windows 2000 boot bar have captured reference fixtures. Windows 95 has explicit button-spacing and radio-indicator comparisons. Windows 98 uses its own shutdown bitmap as the reference for the reduced-size composition test.
- GTK 3 and GTK 4 render real controls in isolated KWin sessions. The classic palette tests exercise Windows 95, 98, 2000 and XP Classic separately, including the white interior of enabled text fields. Luna has separate cross-toolkit control and state tests. These comparisons cover specific controls and do not certify every application's layout.
- The Luna menu, window and taskbar tests can read the owner's XP CD directly through the fixture extractor. The SP3 and Russian SP2 fixtures both passed the 148-test selection. [Instructions for reproducing the XP comparisons](../luna/README.md#the-lunamsstyles-sprites).
- Production XP loading-bar artwork and the new Windows 98 caption are SVGs. Plymouth PNGs are generated runtime assets. PNG reference crops retain the original pixels. [Capture provenance](../tests/references/SOURCES.md).
