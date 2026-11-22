# Aero

The Windows 7 preset selects the Aero window frames, superbar, two-column Start menu, application controls,
Windows 7 icons, SDDM sign-in and boot screen. The launcher ranks programs by use, groups All Programs into folders and searches applications and files.
Use Up and Down in the search box to select a result and Enter to open it. In All Programs, Right expands a folder or enters its first item. Left returns to the folder or collapses it.

File search checks KDE and XBEL recent-document history in the background and searches the Baloo index alongside it when available. Duplicate matches share one row. Hover over a file result to see its full path. The default icon set comes from [B00merang Artwork](https://github.com/B00merang-Artwork/Windows-7).
Qt 6 applications use [AeroThemePlasma's Kvantum theme](https://github.com/aeroshell-desktop/aerothemeplasma/tree/Plasma/6.8/misc/kvantum/Windows7Aero)
when Kvantum is installed. Setup uses Fusion otherwise.

## Native frames on Plasma 6.8 Wayland

Setup selects the bundled SVG Aurorae decoration for window frames and caption buttons. The optional
[Aero Glass Blur effect](https://github.com/aeroshell-desktop/aeroshell-kwin-components) supplies screen-relative
reflections and brightness-dependent afterglow. Build against the KWin version installed on the target machine.
The build needs CMake, Ninja, a C++ compiler, ECM, and the Qt 6, KDE Frameworks 6, KDecoration3, KWin, Wayland,
epoxy and Vulkan development packages. On Fedora install the `kvantum` package for the Qt widget theme.

```sh
./aero/build-native.sh --install
./install.sh --look=aero
```

The helper downloads two checksum-verified source archives and compiles the decoration, resource and effect.
Only installation of those three files needs administrator privileges. A build without arguments leaves them in
`build/aero-native`. Use `--install-built` to install that local build on the same KWin version. Rebuild after
a KWin ABI update. Setup uses the installed Aero Glass Blur effect for rigid frames. With Wobbly Windows enabled, Setup selects KWin’s built-in blur, which suspends backdrop painting while the frame bends and resumes it when the window settles. The native reflection and afterglow are unavailable in this combination. For blur that follows the bent frame during movement, choose **Wobble with live blur** during Setup, pass `--wobbly=blurred` to `install.sh`, or select **With live blur** under **Control Panel → Display → Effects → Wobbly windows** and click **Apply**. Setup builds and installs the effect if it is missing, using the development packages listed above and administrator access for the plugin files. This builds [Better Wobbly Windows](https://github.com/GoldenBilly/BetterWobblyWindows/tree/a6d6443a54dc731e5784cf9a0fec77f378a126f9) against your local KWin. Its embedded renderer handles motion and KWin supplies the stationary blur.

On Fedora, Setup checks the live-blur build packages against the installed KWin version, release and architecture and installs missing packages with DNF. On other distributions, install the development packages with your package manager. CMake checks the Qt, KDE Frameworks and KWin development libraries before compilation. In a running Plasma session, Setup also asks KWin whether it can load the effect.

## Where the numbers come from

There are two sources, and every value names which one it came from:

- **Microsoft's Windows 7 `aero.msstyles`.** It gives the colours and alphas of the frame's lines, the caption
  button faces in all four states for active and inactive windows, the glyphs, and their content margins. The bitmaps
  are never copied into the repository. Only fitted numbers are committed (`aero/palette.py`,
  `aero/aurorae/stops.py`).
- **`tests/references/win7*.png`**, Toasty Technology's lossless 96 DPI captures (`tests/references/SOURCES.md`).
  They give the geometry DWM draws on screen: an 8-pixel border, a 30-row title, 6/5 corner radii, and the 30/27/50
  buttons 18 rows tall, 6 pixels inside the edge. They also give the glass colour over a plain desktop.

## Reading aero.msstyles

From Vista on, a theme's part properties are a binary stream, not XP's `NORMALBLUE.ini`, and DWM's glass parts are
rectangles of one atlas image. To refresh the fits:

```sh
wrestool -x --raw -o ~/src/aero-msstyles/images aero.msstyles   # icoutils
python3 tests/aero/msstyles.py ~/src/aero-msstyles ~/src/msstyleEditor/libmsstyle
AERO_MSSTYLES_DIR=~/src/aero-msstyles python3 tests/aero/fit_aero_stops.py
python3 aero/aurorae/make_aero_aurorae.py
```

`tests/aero/msstyles.py` reads the property map. The names of parts and properties come from libmsstyle (MIT,
https://github.com/nptr/msstyleEditor). The tests that compare our art with the sprites run when `AERO_MSSTYLES_DIR`
is set, and skip otherwise.

## The decoration

`aurorae/make_aero_aurorae.py` writes `aurorae/theme`, which `tests/aero/test_aero_decoration.py` pins to the
generator.

- **The frame** is translucent glass. Its `mask-*` elements make KWin blur what lies behind the frame, and Setup turns
  on KWin's blur at strength 2 for both stationary and wobbling frames. In the 96 DPI striped-wallpaper test, the edge spans 6.9 pixels at rest and 6.7 during a drag. The reference measures 8.8 pixels. The next KWin setting measures 15.9 and 18.1 pixels respectively.
- **The lines** are drawn over the glass with the atlas' alphas.
- **The caption buttons** are vector faces: a centre-column gradient, two-row bands of side shading, and gradient
  edge columns. Each face is within 6 levels of its sprite, and each glyph within 12. They stay sharp at any scale.

## The superbar

`plasma-style/make_aero_plasmastyle.py` writes the Chicago95Aero Plasma style (`plasma-style/theme`, pinned to the
generator by `tests/aero/test_aero_taskbar.py`):

- **The bar** is the references' 40 rows. Plasma draws `translucent/widgets/panel-background.svg` over KWin's blur
  when compositing, solved row by row so it shows win7dragedge.png's bar, without DWM's streaks, over its desktop.
  Setup sets the standard KWin blur to 100% saturation. With the native Aero shader, the Plasma theme paints
  the translucent bar directly so its tint and screen-wide reflections are applied once.
- **The glass streaks** (`widgets/reflection.svg`) are aero.msstyles' DWMWindow REFLECTIONMAP, straight bands at
  29 degrees, drawn as one gradient across them (`aero/reflection.py`, by `tests/aero/fit_aero_reflection.py`) and
  stretched over the screen at 75%, as DWM does: the orb's part draws them under everything on the bar, then the
  bar's edge lines over them (`widgets/baredge.svg`).
- **The darkening behind the orb** (`widgets/startshade.svg`) is an ellipse anchored at the bar's bottom-left corner,
  fitted to the references (`palette.START_SHADE`), fading out under the first pinned program.
- **The task buttons** (`widgets/tasks.svg`) are TaskBand2's TASKITEM states the superbar draws: running, focused and
  attention, with their pointer states. Each is a vector face (a base per row, a white gloss bounded by a curve and
  fading from an elliptical highlight, and exact edge lines) fitted by drawing it (`fit_aero_stops.py`), every
  column within four levels of its sprite. A pinned program at rest is its icon alone. Those PNG resources store
  premultiplied colours, which `aero_sprites.straight` reads back to straight alpha.
- **Show desktop** (`widgets/showdesktop.svg`) comes from ShowDesktop::Button's three states.
- **The Start orb** (`widgets/startbutton.svg`) is a glass sphere centred at x 27 in a slot from the screen's edge,
  in a one-pixel rim of white glass at 30% that the bar shows through. Outside its logo the glass is half-pixel rings
  of arcs fitted to win7dragedge.png (`orb.py`, by `tests/aero/fit_aero_orb.py`), within five levels. The generator draws the rings with continuous SVG gradients at the display scale. The logo is the one Setup's branding chose, never drawn here.
  The Windows flag uses a three-state SVG with separate glass, flag and halo layers. The button displays
  its normal, hover and pressed frames at 54 × 54, centered in the 40-pixel panel. The open menu retains the pressed frame.
  For custom branding, each quarter of the logo lights the surrounding glass in its own colour. Pressing Start dims the halo and
  shades the upper glass. The menu keeps that pressed face until it closes, including when opened from the keyboard.
- **The darkening at the notification area** (`widgets/trayshade.svg`) is drawn by the orb's part too, from the
  screen's right edge, so it lies under the task buttons wherever they reach, as the bar's own shading. While the
  "show hidden icons" button shows, it starts the button's 21 pixels further left, as win7peek.png's does against
  win7screenres.png's (within half a level at that shift).
- **The "show hidden icons" button** (`widgets/trayarrow.svg`) is TrayNotifyHoriz::Button and its Open variant:
  hot and pressed glass faces fitted as the task faces are, a white triangle shaded row by row, and a soft shadow of
  two grown and lowered copies of it in black (`traybutton.py`, by `tests/aero/fit_aero_tray_button.py`), within
  two levels on average. It stands 5 pixels before the first icon, which sit 24 apart and end 15 before the clock,
  and points down while Plasma's hidden-icons popup is open (win7peek.png).
- **The paging arrows** (`widgets/scrollarrow.svg`) are TaskBand2Composited::ScrollBar's ARROWBTN in its twenty
  states: two lines at 50% (black outside, white inside, open towards the other arrow) and a white triangle placed
  to come closest to the sprite's stair. The frame matches within a level and the glyph within six on average. When
  more windows are open than fit, the superbar keeps its buttons whole and shows a page of them (`paging.js`), with
  the up and down arrows after it (`PageArrows.qml`); the older taskbars narrow their buttons instead.
- **The grip** (`widgets/grip.svg`) is TaskBar::Rebar's GRIPPER at its own 12-pixel width, its 2 by 2 dots tiled
  down the bar (`palette.GRIP_DOT`), within a level of the sprite. "Lock the taskbar" in the taskbar's menu (the
  task list's `locked` setting, on by default as in Windows 7) hides it; unlocked, it stands where the band began
  and the band starts after it.
- **The hover light** (`HoverGlow.qml`) washes a hovered button in its icon's hue at full brightness and paler,
  brightest at its foot under the pointer (win7peek.png).

The QML parts live in `plasmoids/*/contents/ui/aero/`, and `styleParts.js` picks them for the taskbar style `aero`.
Buttons sit on a 62-pixel pitch from x 59, 60 wide and 2 apart, with no Quick Launch separators, as the references'.

`tests/aero/test_aero_session.py` runs the superbar in a nested KWin and Plasma session laid out as
win7screenres.png (three pinned programs and a running task, over its plain blue desktop) and compares it with
Windows 7 pixel for pixel: the bar, the orb, the pinned slots and their pitch, and the running task's button.

## Known limits

- **Glass colour.** One plain background cannot separate the glass' opacity from its colour. The opacity keeps
  Windows 7's default 49% share for the background, and the colour is solved to give the references' median. A
  screenshot of glass over a varied wallpaper would let both be fitted.
- **Aurorae frame streaks and afterglow.** The superbar draws DWM's streaks from the screen's corner, but an Aurorae
  frame cannot know where it lies on the screen, so window frames have none; Windows 7's afterglow, which follows the
  background's brightness, needs a compositor shader.
- **Aurorae title glow.** The Aero decoration centres the window icon beside the black lettering and draws a soft white glow behind the caption. Systems without the Aurorae QML renderer or Qt graphical effects use the SVG decoration alone.
- **Superbar menus.** The window picker shows each grouped window using Plasma’s screencast stream. Jump Lists show up to ten recent local documents for the selected application, followed by its desktop-entry actions. Setup’s taskbar reads both the shared XBEL history and KDE’s RecentDocuments links, orders documents by their last use in that application and combines duplicate entries.
- **Paging arrow size.** No reference shows the superbar's arrows, so they are 17 wide (Windows' scroll bar width)
  and half the bar tall each, placed one gap after the page's last button.
- **Unlocked taskbar.** No lossless reference shows one. Windows 7's documentation places the grip left of the
  pinned programs; that the band moves by the gripper's own width is assumed.
- **Tray icon count.** The darkening's shift with the hidden-icons button is measured; how it moves with the
  number of icons is not, as both references hold three.
- **Hidden icons.** The Aero overflow arranges Plasma’s tray items in a compact grid. Individual tray applications supply their own menus.

### Fonts, icons, cursors and event sounds

Setup prefers an installed Segoe UI for Aero and supplies regular and bold Selawik as a fallback. The greeter carries its own copy so it can render account names and controls before a home directory is available. [Microsoft Selawik release](https://github.com/microsoft/Selawik/releases/tag/1.01) · [Bundled font license](../sddm/Chicago95Plasma/fonts/selawik/LICENSE.txt)

The Windows 7 preset uses the [B00merang Windows 7 icon theme](https://github.com/B00merang-Artwork/Windows-7), with KDE application IDs mapped to the corresponding icons. Setup uses Pillow and Potrace to build Windows-7-SVG from the icon pack, trace the embedded control artwork in Kvantum and supply KDE scalable cursor frames with the original hotspots and animation delays. Setup downloads the default white [Aero cursor port](https://github.com/lLexian/Windows-7-Aero-Cursors_Linux) and maps the [Windows 7 sound collection](https://github.com/Pendrag00n/Windows7Sounds) to desktop event names. The cursor port credits separate artwork for the open and closed hand. The cursor and sound archives are pinned by revision and SHA-256 and cached for reinstalls.

## Visual regression tests

Run `python3 tests/aero/run_visuals.py` from a Plasma 6 development machine. The command fails if any comparison fails or skips. It uses the local Aero Setup assets, the extracted `aero.msstyles` described above, and the nested Plasma/KWin test harness. Set `AERO_ORB_REFERENCE` to the original 54 × 162 SevenStart PNG when the old installer’s cached copy is unavailable. On other distributions, point `AERO_FEDORA_REFERENCE` at Fedora’s 256-pixel `fedora-logo-icon.png` to check the custom orb.

- The panel, Start orb, tray, clock, Show desktop strip, task buttons and window frames have comparisons against original Windows 7 captures or theme sprites.
- The dialog portraits in `tests/aero/portraits` are project regression baselines at 100% and 150% scale. They cover the Start menu, All Programs, search, power options and confirmations, System Properties, notifications, and preview cards. Fusion, a fixed font family, representative icons and a test window feed keep these renders reproducible. The Kvantum artwork is checked separately.
- The imported artwork tests build the SVGs and compare rendered pixels with their source images on two backgrounds. They include icon aliases, cursor hotspots and animation frames, the login controls, the session spinner and all embedded Kvantum controls. Login and unlock comparisons also check where controls appear in the assembled screen. Boot tests compare rendered and exported frames.
- Failed portrait comparisons save the actual image and difference in pytest’s temporary directory. To review a deliberate design change, render to a separate directory with `python3 tests/aero/render_aero_dialogs.py /tmp/aero-review 1.5` and inspect the images before replacing any baseline.

The [Windows 7 pixel audit](../docs/windows-7-pixel-audit.md) records exact RGB differences, side-by-side captures and coverage across the 22 installer components. Run `python3 tests/aero/run_visuals.py --exact-originals` to reproduce the comparisons.
