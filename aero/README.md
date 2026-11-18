# Aero

The Windows 7 "Aero" component set. So far it holds the glass window decoration and the superbar, each chosen as
"Windows 7" in Setup and the Control Panel (`install.sh --decoration=aero --taskbar-style=aero`). The widgets,
Start menu and screens are still to come.

Nothing here is shared with the flat 1995, 1998 and 2000 components or with Luna.

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
- **Streaks and afterglow.** Windows 7's screen-anchored streaks, and its afterglow that follows the background's
  brightness, need a compositor shader; a decoration or a stretched panel cannot draw them. On the bar they are
  whole columns a few levels lighter or darker than its plain rows.
- **Title glow.** KWin 6's Aurorae draws no halo behind the title.
- **Superbar grouping.** A pinned program that is running shows twice, pinned and as a task, where Windows 7 merges
  them; jump lists and thumbnails are Plasma's own.
- **Orb glow while the menu is open.** The Start menu is its own program and does not yet tell the orb it is open,
  so the glow follows the pointer only.
- **Blur strength.** It is set low to match the references' roughly 12-pixel softening, but has not yet been measured
  in KWin against them.
