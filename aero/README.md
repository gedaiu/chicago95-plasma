# Aero

The Windows 7 preset selects the Aero window frames, superbar, two-column Start menu, application controls,
Windows 7 icons, SDDM sign-in and boot screen. The launcher searches installed applications and opens the selected
entry on Enter. The default icon set comes from [B00merang Artwork](https://github.com/B00merang-Artwork/Windows-7).
Qt 6 applications use [AeroThemePlasma's Kvantum theme](https://github.com/aeroshell-desktop/aerothemeplasma/tree/Plasma/6.8/misc/kvantum/Windows7Aero)
when Kvantum is installed. Setup uses Fusion otherwise.

## Native frames on Plasma 6.8 Wayland

The [SMOD decoration](https://github.com/aeroshell-desktop/smod) supplies the caption halo and the
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
a KWin ABI update. Setup selects the native backend when all three files are present. Otherwise it installs the
bundled Aurorae frame. The following measurements describe the bundled art.

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
  on KWin's blur at a light strength.
- **The lines** are drawn over the glass with the atlas' alphas.
- **The caption buttons** are vector faces: a centre-column gradient, two-row bands of side shading, and gradient
  edge columns. Each face is within 6 levels of its sprite, and each glyph within 12. They stay sharp at any scale.

## The superbar

`plasma-style/make_aero_plasmastyle.py` writes the Chicago95Aero Plasma style (`plasma-style/theme`, pinned to the
generator by `tests/aero/test_aero_taskbar.py`):

- **The bar** is the references' 40 rows. Plasma draws `translucent/widgets/panel-background.svg` over KWin's blur
  when compositing, solved row by row so it shows win7dragedge.png's bar, without DWM's streaks, over its desktop.
  KWin's blur saturates what it blurs above 100%, which DWM's did not, so Setup sets its saturation to 100.
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
- **The Start orb** (`widgets/startbutton.svg`) is a vector sphere centred at x 27 in a slot from the screen's edge,
  in a one-pixel rim of white glass at 30% that the bar shows through. Outside its logo the glass is half-pixel rings
  of arcs fitted to win7dragedge.png (`orb.py`, by `tests/aero/fit_aero_orb.py`), within five levels. The logo is the one Setup's branding chose, never drawn here.
  Under the pointer it glows in the logo's own colours (`LogoGlow.qml`), as light only, so a dark outline adds
  nothing (win7allprograms.png); at rest there is no glow.
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
- **Aurorae title glow.** KWin 6's Aurorae draws no halo behind the title.
- **Superbar menus.** Jump lists and thumbnails use Plasma’s menus and previews.
- **Paging arrow size.** No reference shows the superbar's arrows, so they are 17 wide (Windows' scroll bar width)
  and half the bar tall each, placed one gap after the page's last button.
- **Unlocked taskbar.** No lossless reference shows one. Windows 7's documentation places the grip left of the
  pinned programs; that the band moves by the gripper's own width is assumed.
- **Tray icon count.** The darkening's shift with the hidden-icons button is measured; how it moves with the
  number of icons is not, as both references hold three.
- **The hidden-icons popup** is still Plasma's own, unstyled.
- **Blur strength.** It is set low to match the references' roughly 12-pixel softening, but has not yet been measured
  in KWin against them.
