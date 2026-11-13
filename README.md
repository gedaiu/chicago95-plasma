# chicago95-plasma

A classic desktop for KDE Plasma 6, inspired by Windows 95, pixel for pixel, on Wayland.

![Screenshot](screenshot.png)

This repository holds everything Plasma-specific that sits on top of
[Chicago95](https://github.com/grassmunk/Chicago95): a generated Aurorae
window decoration, a generated Plasma style, three taskbar plasmoids, a
cascading Start menu, a classic notification daemon, Clippy, the Shut Down
dialog, a screensaver runner, the log on and lock screens, and the
configuration that ties it together.

This README is the map. [docs/PLAYBOOK.md](docs/PLAYBOOK.md) explains how the
code is organised and how a change is proven, for anyone working on it.

Built and tested on Fedora 44, Plasma 6.8.2 (Wayland), 3840x2160 at 1.5x.

## The five looks

Setup offers five looks: 1995, 1998, 2000, 2001 (Windows XP Classic) and Luna.
Each image below shows the look's boot screen, log on and a populated 800×600
desktop, then its taskbar idle, with open windows, crowded, and overflowing
(Quick Launch and tray chevrons). They are rendered from the real components by
`tests/render_report.py`.

### 1995 look

![The 1995 look showcase](docs/compare/showcase-1995.jpg)

### 1998 look

![The 1998 look showcase](docs/compare/showcase-1998.jpg)

### 2000 look

![The 2000 look showcase](docs/compare/showcase-2000.jpg)

### 2001 look (Windows XP Classic)

![The 2001 look showcase](docs/compare/showcase-2001.jpg)

### Luna look (Windows XP)

![The Luna look showcase](docs/compare/showcase-luna.jpg)

The controls of each look (Qt, GTK 3, GTK 4, Plasma and the window
decoration), beside the originals' where a screenshot shows them, are in
`docs/compare/showcase-controls-<look>.jpg`.

### Looks are presets of components

A look is a preset. It fills in the window decoration, the controls (widget style), the taskbar, the Start
menu and the login screen, and each of those can be chosen on its own in the Control Panel or with a flag, so
a 1995 desktop can have the Luna taskbar:

```
./install.sh --look=1995 --taskbar-style=luna
./install.sh --look=luna --start-menu-style=2001
```

The flags are `--decoration`, `--widget-style`, `--taskbar-style`, `--start-menu-style` and `--login-style`.
A Luna taskbar is 30 pixels high and switches Plasma's desktop theme, so tooltips and popups follow it.

## Layout

| Folder                 | Contents                                                                                                                                                                                                                                                                                                                                                                                |
| ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `aurorae/`             | `make_chicago95_aurorae.py`, `bevel.py`, Start button images, and the generated theme under `theme/`                                                                                                                                                                                                                                                                                    |
| `plasma-style/`        | `make_chicago95_plasmastyle.py` and the generated style under `theme/`                                                                                                                                                                                                                                                                                                                  |
| `luna/`                | The Windows XP Luna components: `aurorae/` decoration, `plasma-style/`, `plasmoids/` overlays (Start button, task buttons, tray box), `lib/` (widget style, Start menu, Turn Off dialog), `sddm/`, `splash/`, `plymouth/`, `palette.py`; nothing in it is shared with the flat looks (see `luna/README.md`)                                                                             |
| `plasmoids/`           | `org.chicago95.start`, `org.chicago95.tasks` (Quick Launch and task buttons), `org.chicago95.trayframe`, `org.chicago95.clock`                                                                                                                                                                                                                                                          |
| `bin/`                 | `chicago95-startmenu`, `chicago95-notifyd`, `chicago95-clippy`, `chicago95-shutdown`, `chicago95-screensaver`, `chicago95-sysprops`, `chicago95-devmgr` (Device Manager, read-only, from lshw), `chicago95-k8sview` (the Kubernetes cluster as a device tree), `chicago95-dialup`, `chicago95-deezer`, `chicago95-control-panel`, `chicago95-askpass`, `chicago95-run` (the Run dialog) |
| `lib/`                 | `chicago95ui.py`, the shared PySide6 look module                                                                                                                                                                                                                                                                                                                                        |
| `data/`                | Menu stylesheet for plasmashell, tray arrow, Clippy sprites and sounds, KRunner QML override, fastfetch preset                                                                                                                                                                                                                                                                          |
| `data/sound-themes/`   | Freedesktop sound themes for Windows 98, the 16 Plus! 98 schemes and Windows 2000, built by `setup/make_sound_themes.py`                                                                                                                                                                                                                                                                |
| `data/toolbar-icons/`  | Windows 95 and 2000 Explorer toolbar buttons (Back, Up, Cut, Copy...), installed as the `Chicago95-Toolbar` icon theme over the look's icon set; built by `setup/make_toolbar_icons.py`                                                                                                                                                                                                 |
| `config/`              | Colour scheme, KWin rules, systemd drop-in and unit, environment.d, autostart entries, Thunar, xsettingsd, GTK CSS, Dolphin toolbar, Firefox `user.js`                                                                                                                                                                                                                                  |
| `kwin-scripts/`        | `chicago95windows`, the taskbar menu's Cascade Windows, Tile Windows and Minimize All Windows with Undo, a KWin script                                                                                                                                                                                                                                                                  |
| `kwin-tabbox/`         | `chicago95`, the Alt+Tab switcher layout: the classic icon box, or window previews                                                                                                                                                                                                                                                                                                      |
| `config/desktop/`      | The desktop icons' links: My Computer, Network Neighborhood (My Network Places on 2000), Recycle Bin, My Documents                                                                                                                                                                                                                                                                      |
| `kwin-effects/`        | `chicago95notifications`, the slide-in effect; `chicago95zoom`, the title bar zoom                                                                                                                                                                                                                                                                                                      |
| `lockscreen/`          | The `contents/lockscreen` override for the Plasma desktop shell                                                                                                                                                                                                                                                                                                                         |
| `splash/`              | `chicago95.splashscreen` KSplash package                                                                                                                                                                                                                                                                                                                                                |
| `install.sh`, `setup/` | Chicago95 Setup: detection, component and option screens, install steps                                                                                                                                                                                                                                                                                                                 |
| `uninstall.sh`         | Removes what Setup installed and restores backups                                                                                                                                                                                                                                                                                                                                       |

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
style, animations, taskbar plasmoids, Start menu (with the Run dialog and the keys), Shut Down dialog, notifications,
Office Assistant, extra tools, Control Panel, sound scheme, desktop background, desktop icons, Alt+Tab, screensaver, Winamp, Explorer (Thunar or
Dolphin), lock screen, splash screen, boot screen (Plymouth), login screen
(SDDM), Firefox colours. GTK programs on Wayland, Firefox among them, draw their own title
bars: the look writes its title bar colours, active and inactive, into GTK's `gtk.css` so
they match the window manager's.

Selections are the selection colour under white text everywhere: drop-down
rows, selected desktop icons and KRunner's current result (its results view is
a QML override under `data/qml`, loaded ahead of Plasma's through
`QML_IMPORT_PATH`); a row that is only under the pointer keeps black text and
gets an outline instead.

Toolbar icons in every program are grey until the pointer is over them, as
Explorer's were: KDE's icon effects for Qt programs, a GTK CSS rule for the
rest, and for Plasma's own buttons (KRunner, the tray's popups, widgets) one
file of Plasma's components module shadowed under `data/qml`; Setup links the
rest of that module from the system's copy.

Setup remembers: the components and choices of earlier runs are the defaults
of the next one (flags and the screens still change them), so a reinstall or
an update keeps your set-up with a few ENTERs.

Options are pre-filled from detection and editable on the Setup Options
screen or as flags:

| Flag                                 | Default                         | Effect                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| ------------------------------------ | ------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--screen=WxH@scale`                 | detected                        | Positions of Start menu, Clippy, notifications; X11 DPI                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| `--panel=28`                         | 28                              | Taskbar height used in the window rules                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| `--explorer=thunar` or `dolphin`     | Thunar if installed             | Which file manager gets the Explorer setup                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| `--saver=deepstars`                  | deepstars                       | Screensaver, also chosen and previewed on its own Setup screen: the classics (`deepstars` Flying Through Space, `beziers` Curves and Colors, `marquee`, `qix` Mystify Your Mind, `blank`, `flowerbox`, `flyingobjects`, `maze3d`, `pipes`, `fliptext`) and `flyingtoasters`, `flurry`, `glmatrix`, `bsod`; each is an XScreenSaver hack with the options that make it look the part                                                                                                                                                    |
| `--idle=5`                           | 5                               | Minutes before the screensaver starts                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `--cursor=48`                        | 48 at fractional scale, else 32 | Cursor size                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `--clippy=yes` or `no`               | yes                             | Start the Office Assistant at login                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| `--quick-launch=yes`, `no` or `auto` | auto                            | Show the Quick Launch (program shortcuts beside Start) on the taskbar; auto shows it from the 1998 look on, as the originals did. Right-click a task to add its program, right-click a shortcut to remove it, or drop programs on it. Drag the separator at its docked edge to carry it to the other end of the taskbar, beside Start or before the tray; drag the separator facing the task buttons to size it, and a chevron lists the shortcuts that do not fit. Drag a task button or a shortcut along the taskbar to reorder them |
| `--task-button-width=160`            | the look's own                  | Longest a window's button on the taskbar may be, in pixels                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| `--settings=FILE`                    | none                            | Choices saved by the Control Panel (`KEY=value` lines, never executed), applied over the defaults; Setup saves its own choices to `~/.config/chicago95/setup.conf`                                                                                                                                                                                                                                                                                                                                                                     |
| `--font="MS W98 UI"`                 | MS W98 UI                       | UI font family, applied if installed                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `--font-scope=everywhere`            | everywhere                      | Where the UI font goes: `everywhere` (all programs, also web pages that ask for the system font), `desktop` (window title bars only) or `none`; Setup asks when the flag is missing. The Start menu, notifications, Clippy, Shut Down and the login screen always use it                                                                                                                                                                                                                                                               |

### Control Panel

![The Control Panel](docs/control-panel.png)

`chicago95-control-panel` (Start, Settings, Control Panel, or Properties in the
right-click menu of the Start button and the taskbar) is one Windows 98
Explorer-style window for every choice Setup asks and more. It covers colours,
icons, the desktop background, the screensaver with Preview, the taskbar, Quick
Launch, the Start button and menu, the login screen, the booting screen, sounds,
fonts, the mouse and the file manager, most with live previews. Booting Screen
picks the start-up screen on its own: the classic picture or the 2000 page with
its progress bar, whatever the login style; it is `BOOT_STYLE` in `setup.conf`
and `--boot-style=classic|2000|luna` for Setup. After log on, while Plasma
starts, the loading screen follows the login instead, as the originals did: the
desktop's colour under the hourglass pointer for 9x and 2000 logins, XP's Welcome
screen with "Loading your personal settings..." for the Welcome login. KWin's
log on fade (Effects, "Log on and log off") then fades it into the desktop.
Distro Setup holds every name, text and logo the screens show (the Start button
and menu, the log on, boot and loading screens, the Shut Down dialog) on one page,
with a preview of each screen; the pages they come from keep their own fields, and
an Apply on either shows on the other. Its "Use this computer's system" button
fills them from the running distribution (`/etc/os-release` and its logo icon),
as Setup's `--branding=distro` does; Setup asks the same question once, with the
detected system first, and `--branding=windows` keeps the look's Windows names.
Display opens its own
Display Properties window with the original's tabs, and its Effects tab picks the
animation of each event with a speed slider from Off to Slow. Classic sets every
list to what the look's Windows did, and the choices live in `setup/animations.conf`.

Back, Forward, Up and the clickable address bar move between pages, and only one
window runs at a time. The panel saves `~/.config/chicago95/setup.conf` and runs
Setup again for only what changed. Its Updates page compares the installed
version with the published one and offers Check now and Install update. Clippy
runs the same check once a day after login and says so in a balloon when a newer
version is out.

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
image with `plymouth-set-default-theme -R`; with the 2000 boot style it
instead renders our 2000 loading screen at the monitor's size
(`bin/chicago95-splash-image`) and installs it as `Chicago95-2000`, a
Plymouth script theme (`plymouth/Chicago95-2000`) that fills in the progress
blocks as the system boots. Uninstall switches back to the previous theme.

The "Login screen" component asks for the administrator password on the
Setup screen, installs the Chicago95 log on dialog from `sddm/Chicago95Plasma` (with the UI font, which the greeter cannot read from your home) and
writes `/etc/sddm.conf.d/zz-chicago95.conf`. SDDM reads that folder in name
order and the last file wins, so the `zz-` name beats a leftover theme
setting from another file there. Both are off with `--yes`; ask for them with
`--components=plymouth,sddm`.

## Desktop, keys, Alt+Tab and the taskbar's menu

The desktop icons are links in `~/Desktop` (My Computer, Network Neighborhood, Recycle Bin, and My Documents
from the 1998 look on), shown by Plasma's Folder View at the originals' 32px with two label lines; Display
Properties > Effects picks the set. Folder View's rows are 90px apart where the originals' were 75, and its
labels keep their shadow.

The originals' keys: the Windows key alone and Ctrl+Esc open the Start menu, Win+R the Run dialog, Win+E Explorer,
Win+D and Win+M show the desktop, Win+F Find. They are service shortcuts in `kglobalshortcutsrc` and take effect
at the next login (Setup offers to log out). The Run dialog is the 1995 original's, pixel for pixel
(`tests/test_run_reference.py`), with a twist: as you type, programs, commands on the PATH, folders and files that
match are listed under the field; Enter runs the first, or the typed line as it is.

Alt+Tab is our KWin switcher layout, measured from a Windows 95 capture (`tests/references/win95alttab.png`): a
379px grey box with the windows' icons in 48px cells, seven to a row and further rows below, the chosen one in a
1px navy frame, and its title in bold in a sunken field under them. Taskbar > Taskbar Options' "Window previews"
(Off, Small, Medium, Large) switches both it and the task buttons' tooltips to live previews of the windows at
that width; the tooltips are otherwise the flat pale yellow title.

A right-click on the taskbar offers the Quick Launch, Cascade Windows, Tile Windows Horizontally, Tile Windows
Vertically, Minimize All Windows, the Undo of the last of those, and Properties. The arrangements are a KWin
script (`kwin-scripts/chicago95windows`) measured from the Windows 98 originals: Cascade steps 22 right and 21
down with every window seven eighths of what is left; Tile splits the work area into equal columns or rows, a grid
past four windows.

## GTK and GNOME programs

GTK programs on Wayland draw their own title bars, and libadwaita programs
(GNOME Files among them) put their toolbar in it. Setup's title bar block in
`~/.config/gtk-3.0/gtk.css` and `~/.config/gtk-4.0/gtk.css`, generated by
`lib/gtk_header.py`, turns them back into 9x windows:

- an 18px title strip in the window manager's active and inactive colours,
  with the title and the 16×14 window buttons in it (drawn from the window
  decoration's own glyphs), over the toolbar on the face colour;
- the 4px raised window frame, dropped when the window is maximized or tiled;
- square 22px toolbar buttons, and the header no longer fades when the window
  loses focus;
- in GNOME Files, the path bar as Explorer's sunken Address bar, the location
  entry (Ctrl+L) the same size, and the list view's column headers edge to
  edge, as in Explorer's Details view.

The block follows the look's colours and is rewritten whenever they change.

## Resolution

Wayland does not let clients position their own windows, so the Start
menu, Clippy and the notification column are placed by KWin rules that
Setup computes from the screen size and taskbar height. After a
resolution change, rerun
`./install.sh --components startmenu,notifications,clippy`.

## Fractional scaling

MS W98 UI is a pixel font drawn on an 11px grid. At 1x and 2x it is drawn
unsmoothed, as sharp as the originals' text. On a fractional scale such as
1.5x Setup smooths it at every size instead
(`~/.config/fontconfig/conf.d/60-chicago95-pixel-font.conf`): GTK 4 picks the
font's rendering at its logical size and draws it at the screen's, so an
unsmoothed 11px would come out jagged at 16.5.

X11 programs on a scaled screen get `Xft.dpi` and KDE's `forceFontDPI` at
96 × scale (144 at 1.5x), with no `QT_SCALE_FACTOR` anywhere. Wine and Steam
follow neither, so Setup also sets Wine's own DPI (`LogPixels` in the default
`~/.wine` prefix) and `STEAM_FORCE_DESKTOPUI_SCALING` in
`~/.config/environment.d/chicago95-scale.conf`. Run `winecfg` (Graphics,
Screen resolution) for any other Wine prefix.

## Linting and formatting

`make check` verifies formatting and lints every source file without changing anything; CI runs it. `make format` rewrites the files into the house style.

| Files                               | Tools                                                                                                  |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Python, including `bin/chicago95-*` | ruff (settings in `pyproject.toml`, line length 120)                                                   |
| Shell                               | shfmt and shellcheck                                                                                   |
| QML                                 | qmlformat and qmllint, from `pyside6-*`                                                                |
| JS                                  | eslint with `@re-cinq/eslint-plugin-re-lint` (it also adds blank lines for readability), then prettier |
| JSON, YAML, CSS, Markdown           | prettier, run through `npx`                                                                            |
| XML, `.desktop`                     | xmllint, desktop-file-validate                                                                         |

`pip install --user -r requirements-dev.txt` brings ruff, shellcheck and shfmt, and `npm ci` the JavaScript tooling (`make` does that itself). A tool that is missing is skipped locally and is an error in CI. SVG files are generated and left alone. The KDE-derived `lockscreen/` and `data/qml/` QML is formatted but not linted, and qmllint only gates on every message when the Plasma QML modules are installed.

## Tests

```
pip install --user -r requirements-dev.txt
python3 -m pytest tests
```

The desktop tests (`tests/test_plasma_*_reference.py`) run Setup into a throwaway home and compare the real KWin
and plasmashell against the originals' screenshots; they need KWin, plasmashell, spectacle, Xwayland and the MS W98
UI font, and are skipped without them. [docs/testing.md](docs/testing.md) covers the rest: the reference
comparisons, the login, boot and power-flow rehearsals, the showcase images and the cross-toolkit consistency
checks.

## Clippy

The Office Assistant plays the original sprite atlas by default. The HD artwork and the Blender 3D prototype, with
their build, review and validation tools, are described in [docs/clippy.md](docs/clippy.md).

## Credits

Chicago95 by grassmunk and contributors (GPL-3.0) for the theme, icons,
cursors, sounds, Plymouth and SDDM themes. React Plus as the starting copy
for the Plasma style. ClippyJS for the Office Assistant sprite data.
Nullsoft's Winamp 2.91 base skin, played by qmmp. XScreenSaver by Jamie
Zawinski. The Windows 98, Plus! 98 and Windows 2000 (remastered) sound
schemes are Microsoft's; they are converted to Ogg for the sound themes.

## Licence

GPL-3.0, matching Chicago95, whose artwork the generated files derive from.
See `LICENSE`.
