# Luna

The Windows XP "Luna" component set: window decoration, Plasma style, taskbar QML, widget style,
Start menu and fonts. Each is a component of its own, chosen separately in the Control Panel.

Nothing here is shared with the flat 1995, 1998 and 2000 components. The one exception is that the
generators may import `svg`, `rect` and `hidden` from `aurorae/bevel.py`. A change to a flat look
must never alter a Luna file, and the other way round; `tests/luna/test_flat_looks_unchanged.py`
pins the flat generators' output so that stays true.

- `palette.py`: every colour and gradient as plain data, no Qt.
- `Luna.colors`: the KDE colour scheme (face `#ECE9D8`, selection `#316AC5`, Luna title colours).

## Reference images

Everything is measured, not eyeballed, from `tests/references/xp*.png`. `palette.py` names the image,
column and rows of each value; the images' origins are listed in `tests/references/SOURCES.md`.

## Quick Launch and tray

`tests/references/xpquicklaunch.png` (2x, every pixel doubled; halve it for 1x) gives the band: Start pill, 10px, a 6px
dotted grip (seven 2x2 dark `#082EA0` dots with a `#1590E6` shadow one pixel down and right, three rows apart, alternating
between two columns, rows 6..26), 4px, 23px cells with the 16px icon 3px in and 7px down, 6px, the second grip, 4px, the
task buttons. The Luna files are `QuickLaunchButton.qml`, `Separator.qml` and `Chevron.qml` under
`plasmoids/org.chicago95.tasks/contents/ui/luna/`, loaded through the same seams as the flat ones; the band's sizes come
from `quickLaunchBand.js`' `metrics("luna")`. The tray: the notch at x width-93 on an 800px panel, icons 16px on rows
7..22 starting 11px after it at a pitch of 17, the "show hidden icons" button a 16px round blue button centred on the notch.

## The luna.msstyles sprites

`tests/luna/test_luna_sprites.py` compares the taskbar pieces with the sprites of Microsoft's `luna.msstyles`. They are
not in the repository and are not redistributed: clone https://github.com/freitagdavid/QuickXP, run its extract script
over your own copy of `luna.msstyles`, and point `LUNA_MSSTYLES_DIR` at the folder that holds `images/BLUE_<NAME>_BMP.png`
(and `settings/NORMALBLUE.ini`, which gives each part's state count and sizing margins). Without the folder those tests
skip. What was fitted from them: the Quick Launch grip's dot colours (`TASKBARGRIPPER`), the flat blue hot and pressed
Quick Launch button (`TASKBANDBUTTONNOEDGE`), the `>>` glyph's exact pixels and colours (`TASKBARCHEVRON`), the hidden icons
button's sphere (`TRAYCHEVRONHORIZONTAL`) and the taskbar background rows (`TASKBARBACKGROUND`).

## Logo pictures

`images/windows-xp-logo.svg` is the single source of every flag and wordmark. `python3 luna/images/render_logo.py`
derives `windows-xp-flag.svg` (flag only, cropped to its measured box, no drop shadow) and
`windows-xp-logo-light.svg` (flag and wordmark with the lettering in white, for the dark login and boot
screens), then writes the flag PNGs: the 2001 Start button's `logo-xp-16.png`, the Luna Start button's
`logo-flag-xp.png` and `@2x`, and the dialogs' `lib/images/windows-xp-flag-dialog.png` and `@2x`. The Plymouth
wordmark comes from `plymouth/make_assets.py`, which uses the same renderer. QML draws the SVGs directly.

Setup installs `images/` next to `qml/` (the login and splash QML load `../images/`) and `lib/images/` beside
the dialog module.

## Widget themes (Qt and GTK)

- `kvantum/`: `make_luna_kvantum.py` writes `Chicago95Luna/Chicago95Luna.svg` and `.kvconfig`, the Kvantum theme that gives
  every Qt and KDE application the Luna widgets. Colours, gradients and sizes are the table in `kvantum/stops.py`
  (LunaStyle's measured values; the push button body is the fit in `plasma-style/stops.py`, the title bar the palette's).
  Setup installs it to `~/.config/Kvantum/Chicago95Luna` and sets `kdeglobals` `widgetStyle=kvantum` when Kvantum is
  installed, `Fusion` otherwise (the Setup log says so).
- `gtk/`: `make_luna_gtk.py` writes `Chicago95Luna/gtk-3.0/gtk.css`, `gtk-4.0/gtk.css` and `index.theme`, installed to
  `~/.themes/Chicago95Luna` and selected in `settings.ini` and `xsettingsd` (`config/xsettingsd/xsettingsd-luna.conf`,
  Tahoma 8). `--titlebar` prints the header bar block Setup writes for the Luna decoration.
- Cursors stay Chicago95's: the XP cursors are Microsoft assets and no free equivalent is fetched.

The generated files are committed; `tests/luna/test_luna_kvantum.py` and `test_luna_gtk.py` pin them to the generators.

## Icons

The XP look's icon set (`--icons=windowsxp`, the Control Panel's "Windows XP") is the B00merang Windows-XP pack
(GPL-2, https://github.com/B00merang-Artwork/Windows-XP), cloned by Setup into `~/src/Windows-XP` and installed to
`~/.local/share/icons/Windows-XP`, never bundled. When the user keeps XP icon archives (`ICON.zip`, the numbered shell
icons, and `High-Res_XP_Icons.zip`) in `~/Downloads` (or `SETUP_XP_ICON_ARCHIVES`), Setup builds
`Windows-XP-Originals` from them with `icons/xp_originals.py` and the B00merang set falls back to it before
Chicago95. The repository holds only the map from freedesktop icon names to archive numbers and file names.

## References consulted

The per-state colours of the widgets (hover, pressed, disabled, default, focus) were checked against the B00merang
"Windows XP Luna" GTK theme (GPL-3, https://github.com/B00merang-Project/Windows-XP). Only its state colours and its
list of widgets that need rules were used; its bitmaps and CSS are not copied.

## Licensing

The flag and the wordmark are the Wikipedia SVG
(https://de.wikipedia.org/wiki/Datei:Microsoft_Windows_XP_Logo_2.svg), a Microsoft trademark used here to
identify the look. No other Microsoft assets are bundled: fonts come from the user's Wine Tahoma, the Bliss
wallpaper and the fallback icons from the user's own files.
