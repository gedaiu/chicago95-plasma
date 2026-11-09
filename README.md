# chicago95-plasma

Windows 95 on KDE Plasma 6, pixel for pixel, on Wayland.

![Screenshot](screenshot.png)

This repository holds everything Plasma-specific that sits on top of
[Chicago95](https://github.com/grassmunk/Chicago95): a generated Aurorae
window decoration, a generated Plasma style, three taskbar plasmoids, a
cascading Start menu, a Win95 notification daemon, Clippy, the Shut Down
dialog, a screensaver runner, and the configuration that ties it together.

The long-form write-up of how and why each piece works is the tutorial that
accompanies this repository. The README is the map; the tutorial is the
territory.

Built and tested on Fedora 44, Plasma 6.8.2 (Wayland), 3840x2160 at 1.5x.

## Layout

| Folder | Contents |
| --- | --- |
| `aurorae/` | `make_chicago95_aurorae.py`, `bevel.py`, Start button images, and the generated theme under `theme/` |
| `plasma-style/` | `make_chicago95_plasmastyle.py` and the generated style under `theme/` |
| `plasmoids/` | `org.chicago95.start`, `org.chicago95.grip`, `org.chicago95.trayframe` |
| `bin/` | `chicago95-startmenu`, `chicago95-notifyd`, `chicago95-clippy`, `chicago95-shutdown`, `chicago95-screensaver`, `chicago95-sysprops`, `chicago95-devmgr`, `chicago95-dialup`, `chicago95-deezer` |
| `lib/` | `win95ui.py`, the shared PySide6 look module |
| `data/` | Menu stylesheet for plasmashell, tray arrow, Clippy sprites and sounds, KRunner QML override, fastfetch preset |
| `config/` | Colour scheme, KWin rules, systemd drop-in and unit, environment.d, autostart entries, Thunar, xsettingsd, GTK CSS, Dolphin toolbar, Firefox `user.js` |
| `kwin-effects/` | `chicago95notifications`, the slide-in effect |
| `lockscreen/` | The `contents/lockscreen` override for the Plasma desktop shell |
| `splash/` | `chicago95.splashscreen` KSplash package |
| `install.sh` | Copies everything into place under `~/.local` and `~/.config` |

## Requirements

Fedora package names; adjust for your distribution.

```
sudo dnf install python3-pyside6 python3-pyxdg python3-dbus python3-gobject \
    python3-pillow ImageMagick icoutils thunar xsettingsd tumbler \
    qmmp qmmp-plugin-pack xscreensaver-extras xscreensaver-gl-extras
git clone https://github.com/grassmunk/Chicago95 ~/src/Chicago95
```

Fonts: MS W98 UI (OTF) and More Perfect DOS VGA, dropped into
`~/.local/share/fonts`.

## Install

```
./install.sh
```

The script copies files, substitutes your home directory into the entries
that need an absolute path, symlinks the Chicago95 icon theme where KDE can
find it, adds `Inherits=hicolor,breeze` to it, applies the colour scheme,
widget style, decoration and Plasma style, installs the systemd drop-in
and unit, and restarts plasmashell. It does not touch Plymouth or SDDM;
those need root and are two commands in the tutorial.

Afterwards, build the panel once with the Plasma script in
`plasmoids/panel-layout.js` (System Settings > Plasma scripting console,
or `evaluateScript` over D-Bus).

## Resolution

Three KWin rules in `config/kwin/kwinrulesrc` position windows that
Wayland does not let clients position themselves: the Start menu, Clippy,
and the notification host. Their `position=` values are for a 2560x1440
logical screen with a 28 px panel. On another resolution, recompute:

| Rule | Formula (logical px) |
| --- | --- |
| `chicago95-startmenu` | `0, height - 28 - 189` |
| `chicago95-clippy` | `width - 124 - 24, height - 28 - 93 - 24` |
| `chicago95-notifyd` | `width - 340, height - 28 - 1100` |

Edit that file as plain text. Running `kwriteconfig6` against it drops
every rule group.

## Fractional scaling

At 1.5x the pixel font is crisp only at integer device sizes, which is why
the tools pin 10 px, and X11 apps need `Xft.dpi: 144` in `~/.Xresources`
and `forceFontDPI=144` in `~/.config/kcmfonts` with no `QT_SCALE_FACTOR`
anywhere. At 1x or 2x the DPI section of the tutorial can be skipped.

## Credits

Chicago95 by grassmunk and contributors (GPL-3.0) for the theme, icons,
cursors, sounds, Plymouth and SDDM themes. React Plus as the starting copy
for the Plasma style. ClippyJS for the Office Assistant sprite data.
Nullsoft's Winamp 2.91 base skin, played by qmmp. XScreenSaver by Jamie
Zawinski.

## Licence

GPL-3.0, matching Chicago95, whose artwork the generated files derive from.
See `LICENSE`.
