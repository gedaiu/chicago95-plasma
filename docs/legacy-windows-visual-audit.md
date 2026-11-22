# Windows 95, 98, 2000 and XP visual audit

The four reference guests booted from the owner's installation media. Windows 95 OSR2 and English XP Professional SP3 reached their desktops. Windows 98 Second Edition and Windows 2000 Professional reached graphical Setup and require their respective product keys to finish. The 95 guest uses an emulated Pentium with instruction-count timing. Its wall-clock measurements describe that VM.

[View original and rendered controls side by side](compare/legacy-vm-details.png). Each pair uses the same display scale. The tests compare the native-size pixels.

| Theme | What the fresh reference verifies | Remaining difference or limit |
| --- | --- | --- |
| Windows 95 OSR2 | Device Manager action buttons measure 84, 84, 84 and 83 pixels across, with six-pixel gaps. The classic layout now keeps the row aligned with the tree when widened. The 12×12 selected and unselected Display Properties radio buttons match after mapping the render to the guest's four neutral VGA colours. | The native Device Manager is a System Properties tab. The Linux tool opens separately and disables unavailable hardware actions. The OSR2 boot screen adds a Microsoft Internet Explorer line under the Windows 95 wordmark. The theme shows the earlier wordmark. The captured single-user shutdown dialog also has fewer choices than the project's multi-user dialog. |
| Windows 98 SE | The installed Windows shutdown artwork, LOGOW.SYS, shows Windows 98 over clouds with a blue caption. Plymouth previously inherited the Windows 95 shutdown image. The replacement uses the 98 boot artwork and a scalable caption. A 160×120 composition test checks the full image and the caption location. | The cloud reconstruction and caption lettering are approximate. A recording of an installed desktop signing out and shutting down still requires the 98 key. |
| Windows 2000 Professional | The 640×480 boot recording shows a 165×10 bar at (273, 436). At half fill its 8×8 navy blocks, grey gaps and bevel now match all 1,650 pixels. | Desktop layout, interactive transitions and shutdown remain unmeasured on this guest. The captured graphical boot occurred during an installation restart. |
| Windows XP Professional SP3 | The 126×15 loading bar has 15 slots and 18 animation states. It advances eight pixels per step and repeats in about 1.69 seconds. The Qt preview matches every native bar frame and has a timed playback test. Plymouth uses the same SVG artwork and step sequence. Native Device Manager has five toolbar commands and a status bar. The Luna layout now follows that structure and uses SVGs for the five toolbar icons. | The toolbar glyph positions are tested within two pixels. Icon antialiasing and background gradients still differ. The unbranded theme depicts an earlier XP boot with an edition line. The SP3 capture omits it. Plymouth's on-screen cadence still needs an independent display recording. |

## Desktop motion and power

In the XP SP3 Device Manager minimize recording, the system menu dismissed at 0.181 seconds, the first captured travelling title bar appeared at 0.211 seconds, and the destination settled by 0.447 seconds. The original window body stayed visible under the travelling title bar. The shared KWin effect scales the window itself. Matching its duration alone would leave that visual difference.

The Windows 95 and XP guests both completed a real shutdown. XP displayed “Saving your settings…” during sign-out. The project's Luna shutdown preview switches from “Logging off…” to “Windows is shutting down…”. Recording the VM captures native text and transitions. It does not establish a portable duration for saving a user's session.

## Regression coverage

- The native-size XP boot animation, Device Manager command bands and Windows 2000 boot bar have captured reference fixtures. Windows 95 has explicit button-spacing and radio-indicator comparisons. Windows 98 uses its own shutdown bitmap as the reference for the reduced-size composition test.
- GTK 3 and GTK 4 render real controls in isolated KWin sessions. The classic palette tests exercise Windows 95, 98, 2000 and XP Classic separately, including the white interior of enabled text fields. Luna has separate cross-toolkit control and state tests. These comparisons cover specific controls and do not certify every application's layout.
- The Luna menu, window and taskbar tests can read the owner's XP CD directly through the fixture extractor. The SP3 and Russian SP2 fixtures both passed the 148-test selection. [Instructions for reproducing the XP comparisons](../luna/README.md#the-lunamsstyles-sprites).
- Production XP loading-bar artwork and the new Windows 98 caption are SVGs. Plymouth PNGs are generated runtime assets. PNG reference crops retain the original pixels. [Capture provenance](../tests/references/SOURCES.md).
