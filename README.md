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
| `install.sh`, `setup/` | Windows 95 style Setup: detection, component and option screens, install steps |
| `uninstall.sh` | Removes what Setup installed and restores backups |

## Requirements

KDE Plasma 6 and `git`. Setup handles the rest:

- It clones [grassmunk/Chicago95](https://github.com/grassmunk/Chicago95) to
  `~/src/Chicago95` when no checkout is found (themes, icons, cursors, sounds
  and the More Perfect DOS VGA font come from it). Point `CHICAGO95_SRC` at an
  existing checkout to reuse it.
- When Python modules are missing it shows the package command for your
  distribution and offers to run it with `sudo`. On Fedora that is:

```
sudo dnf install python3-pyside6 python3-pyxdg python3-dbus python3-gobject \
    thunar xsettingsd tumbler qmmp qmmp-plugin-pack \
    xscreensaver-extras xscreensaver-gl-extras
```

The MS W98 UI font can't be redistributed. Drop the OTF into
`~/.local/share/fonts` before running Setup, or pick another family with
`--font=`.

## Install

```
git clone https://github.com/gedaiu/chicago95-plasma ~/src/chicago95-plasma
cd ~/src/chicago95-plasma
./install.sh
```

Setup runs as a full-screen text installer in the style of Windows 95
Setup: it collects information about the computer, lets you pick
components and options, copies files with a progress bar, and reloads
Plasma.

It detects the distribution and package manager, the Plasma version, the
primary screen's logical resolution and scale, an existing Chicago95
checkout (or clones one), the XScreenSaver hack directory, the Firefox
profile in daily use, whether Thunar and qmmp are installed, and missing
Python modules, with the install command for your distribution.

Components, each optional: Chicago95 base theme, decoration and Plasma
style, taskbar plasmoids, Start menu and Shut Down dialog, notifications,
Office Assistant, extra tools, screensaver, Winamp, Explorer (Thunar or
Dolphin), lock screen, splash screen, Firefox colours.

Options are pre-filled from detection and editable on the Setup Options
screen or as flags:

| Flag | Default | Effect |
| --- | --- | --- |
| `--screen=WxH@scale` | detected | Positions of Start menu, Clippy, notifications; X11 DPI |
| `--panel=28` | 28 | Taskbar height used in the window rules |
| `--explorer=thunar` or `dolphin` | Thunar if installed | Which file manager gets the Explorer setup |
| `--saver=deepstars` | deepstars | XScreenSaver hack name |
| `--idle=5` | 5 | Minutes before the screensaver starts |
| `--cursor=48` | 48 at fractional scale, else 32 | Cursor size |
| `--clippy=yes` or `no` | yes | Start the Office Assistant at login |
| `--font="MS W98 UI"` | MS W98 UI | UI font family, applied if installed |

Other modes: `--yes` takes every default without questions,
`--components base,look,taskbar` installs only those, `--dry-run` writes
nothing and logs every action, `--plain` replaces the full-screen UI with
plain output.

Every file Setup replaces is backed up to
`~/.local/share/chicago95/backup-<date>/`, and every file it writes is
listed in `~/.local/share/chicago95/installed-files.txt`. `./uninstall.sh`
reads that list, removes the files and window rules, restores the backups
and switches Plasma back to Breeze. Window rules are merged into an
existing `~/.config/kwinrulesrc` as text, so your own rules are kept.

After Setup, build the taskbar once: remove the stock panel and run
`~/.local/share/chicago95/panel-layout.js` in the Plasma scripting
console. Plymouth and SDDM need root and are not touched:

```
sudo cp -r ~/src/Chicago95/Plymouth/Chicago95 /usr/share/plymouth/themes/
sudo plymouth-set-default-theme -R Chicago95
sudo cp -r ~/src/Chicago95/Extras/sddm/Chicago95 /usr/share/sddm/themes/
```

## Resolution

Wayland does not let clients position their own windows, so the Start
menu, Clippy and the notification column are placed by KWin rules that
Setup computes from the screen size and taskbar height. After a
resolution change, rerun
`./install.sh --components startmenu,notifications,clippy`.

## Fractional scaling

At 1.5x the pixel font is crisp only at integer device sizes, which is why
the tools pin 10 px, and X11 apps need `Xft.dpi: 144` in `~/.Xresources`
and `forceFontDPI=144` in `~/.config/kcmfonts` with no `QT_SCALE_FACTOR`
anywhere. At 1x or 2x the DPI section of the tutorial can be skipped.

## Tests

```
python3 -m pytest tests
```

## Credits

Chicago95 by grassmunk and contributors (GPL-3.0) for the theme, icons,
cursors, sounds, Plymouth and SDDM themes. React Plus as the starting copy
for the Plasma style. ClippyJS for the Office Assistant sprite data.
Nullsoft's Winamp 2.91 base skin, played by qmmp. XScreenSaver by Jamie
Zawinski.

## Licence

GPL-3.0, matching Chicago95, whose artwork the generated files derive from.
See `LICENSE`.
