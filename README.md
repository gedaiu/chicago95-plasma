# chicago95-plasma

A classic desktop for KDE Plasma 6, inspired by Windows 95, pixel for pixel, on Wayland.

![Screenshot](screenshot.png)

This repository holds everything Plasma-specific that sits on top of
[Chicago95](https://github.com/grassmunk/Chicago95): a generated Aurorae
window decoration, a generated Plasma style, three taskbar plasmoids, a
cascading Start menu, a classic notification daemon, Clippy, the Shut Down
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
| `lib/` | `chicago95ui.py`, the shared PySide6 look module |
| `data/` | Menu stylesheet for plasmashell, tray arrow, Clippy sprites and sounds, KRunner QML override, fastfetch preset |
| `config/` | Colour scheme, KWin rules, systemd drop-in and unit, environment.d, autostart entries, Thunar, xsettingsd, GTK CSS, Dolphin toolbar, Firefox `user.js` |
| `kwin-effects/` | `chicago95notifications`, the slide-in effect |
| `lockscreen/` | The `contents/lockscreen` override for the Plasma desktop shell |
| `splash/` | `chicago95.splashscreen` KSplash package |
| `install.sh`, `setup/` | Chicago95 Setup: detection, component and option screens, install steps |
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

Setup runs as a full-screen text installer in the classic
style: it collects information about the computer, lets you pick
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
Dolphin), lock screen, splash screen, boot screen (Plymouth), login screen
(SDDM), Firefox colours.

Options are pre-filled from detection and editable on the Setup Options
screen or as flags:

| Flag | Default | Effect |
| --- | --- | --- |
| `--screen=WxH@scale` | detected | Positions of Start menu, Clippy, notifications; X11 DPI |
| `--panel=28` | 28 | Taskbar height used in the window rules |
| `--explorer=thunar` or `dolphin` | Thunar if installed | Which file manager gets the Explorer setup |
| `--saver=deepstars` | deepstars | Screensaver, also chosen and previewed on its own Setup screen |
| `--idle=5` | 5 | Minutes before the screensaver starts |
| `--cursor=48` | 48 at fractional scale, else 32 | Cursor size |
| `--clippy=yes` or `no` | yes | Start the Office Assistant at login |
| `--font="MS W98 UI"` | MS W98 UI | UI font family, applied if installed |
| `--font-scope=everywhere` | everywhere | Where the UI font goes: `everywhere` (all programs, also web pages that ask for the system font), `desktop` (window title bars only) or `none`; Setup asks when the flag is missing. The Start menu, notifications, Clippy, Shut Down and the login screen always use it |

Other modes: `--yes` takes every default without questions,
`--components base,look,taskbar` installs only those, `--dry-run` writes
nothing and logs every action, `--plain` replaces the full-screen UI with
plain output.

Setup starts with an intro screen, waits for ENTER (Next) on every page
and lists each file as it copies it. When Chicago95 is already installed it
offers Reinstall, Uninstall or Exit.

Every file Setup replaces is backed up to
`~/.local/share/chicago95/backup-<date>/`, and every file it writes is
listed in `~/.local/share/chicago95/installed-files.txt`. A reinstall adds
to that list and never backs up a file Setup wrote itself, so the backups
always hold your originals. `./uninstall.sh` reads the list, removes the
files and window rules, restores the oldest backup of each file and
switches Plasma back to Breeze. Window rules are merged into an existing
`~/.config/kwinrulesrc` as text, so your own rules are kept.

At the end Setup offers to replace your panels with the Chicago95 taskbar
(the old layout is backed up) and to log out, which the autostart entries
need. It does neither without a yes.

The screensaver runs from Plasma's power management
(`~/.config/powerdevilrc`, "Run script" after the idle time), because
Wayland does not give the idle time to ordinary programs. Any key, click or
mouse movement ends it.

The "Boot screen" and "Login screen" components ask for the administrator
password on the Setup screen and list the exact commands first. The boot
screen copies `~/src/Chicago95/Plymouth/Chicago95` and rebuilds the boot
image with `plymouth-set-default-theme -R`; uninstall switches back to the
previous theme.

The "Login screen" component asks for the administrator password on the
Setup screen, installs the Chicago95 log on dialog from `sddm/Chicago95Plasma` (with the UI font, which the greeter cannot read from your home) and
writes `/etc/sddm.conf.d/zz-chicago95.conf`. SDDM reads that folder in name
order and the last file wins, so the `zz-` name beats a leftover theme
setting from another file there. Both are off with `--yes`; ask for them with
`--components=plymouth,sddm`.

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
