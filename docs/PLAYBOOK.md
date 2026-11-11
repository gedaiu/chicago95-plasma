# Working in this repository

A guide for an agent (or a person) making changes here. It says how the code is organised, how a change is
proven, and the traps that have cost time before. Read it before the first edit.

## What this is

Chicago95 for KDE Plasma recreates the Windows 95, 98 and 2000 desktops ("looks" `1995`, `1998`, `2000`)
pixel by pixel. Every visual claim is checked against a reference screenshot of the original. The user
installs from the checkout with `install.sh`; the installed copies live under `~/.local` (tools in
`~/.local/bin`, shared Python in `~/.local/lib/chicago95`, data in `~/.local/share/chicago95`).

## Rules that are not negotiable

1. **Test first, always.** Write the failing test, run it red, write the least code that passes, run it
   green, then tidy. No production code without a test that needed it.
2. **Never commit.** The user commits. Do not mention Claude or any assistant in files or messages.
3. **No Windows trademarks in scripts and themes**: no Microsoft logos, fonts or bitmaps bundled. Our own
   drawings may resemble the originals in style; crops of reference screenshots are allowed only for
   generic artwork the user has asked for (see `data/control-panel/`). The word "Windows" stays out of
   code and theme files.
4. **House style** (`ruff`, `shellcheck`, `shfmt`, eslint, prettier run by `make check`): descriptive
   names, no `x`/`tmp`/`data`, no emojis, comments only for what the code cannot say, no nested `if`
   pyramids, no try/except around code that cannot raise. Test names are natural-language sentences
   without "should": `def test_the_slot_is_clamped_to_the_sections_ends`. Assert once per test, on a
   tuple or dict of everything that matters.
5. **Report honestly.** If a test fails, say so with the output. If something was not verified, say that.

## Map

| Path | What it is |
| --- | --- |
| `bin/chicago95-*` | PySide6 tools: `control-panel`, `startmenu`, `shutdown`, `notifyd`, `clippy`, `screensaver`, `sysprops`, `devmgr` (Device Manager), `k8sview`, `dialup`, `askpass`, `sync-colors`, `splash-image`. Loaded in tests with `load_script("chicago95-name")`. |
| `lib/chicago95ui.py` | The shared Qt style (`ClassicStyle`, a `QProxyStyle` over "Windows") and helpers: bitmaps for check boxes/radios/arrows, tab drawing, `dialog_button`, `make_app`, `quit_on_signals`, `SingleInstance`. Every pixel rule for Qt controls lives here. |
| `lib/chicago95update.py`, `lib/login_preview.py` | Update check (git ls-remote, daily cache); the SDDM theme outside SDDM for previews and tests. |
| `plasmoids/org.chicago95.*` | Plasma applets (taskbar `tasks`, `start`, `trayframe`). Pure logic goes in `.pragma library` JS files beside the QML so it can be unit-tested. |
| `plasma-style/`, `aurorae/` | Generators for the Plasma SVG theme and the KWin decoration. Edit the Python, never the generated SVG. |
| `data/qml/` | QML modules that shadow Plasma's through `QML_IMPORT_PATH` (KRunner results, Plasma's `ButtonContent`). Setup completes a shadowed module from the system copy (`complete_qml_module`). |
| `setup/steps.sh`, `install.sh`, `uninstall.sh` | Setup: one `step_<component>` per component, `kconf`/`put_file`/`put_tree`/`record` helpers, dry-run support, `save_settings` to `~/.config/chicago95/setup.conf`. |
| `tests/` | pytest. `conftest.py` (fixtures, `load_script`, `run_bash_with_steps`, `needs_ui_font`), `reference.py` (screenshots, pixel helpers), `js_library.py` (runs QML JS libraries in a bare engine), `plasma_session.py` (real nested desktops), `controls_gallery.py` and `render_report.py` (the showcase pictures in `docs/compare`). |
| `tests/references/` | The original screenshots, each listed with its source in `SOURCES.md`. Add the line when you add a picture. |

## How a change is proven

Pick the strongest kind of test that applies; often two of them.

- **Pure logic**: a function outside any class, tested directly. For QML JS libraries use
  `load_js_library(path)` and `call(engine, "name", *args)`.
- **Qt controls**: render the widget offscreen (`qt_app` fixture, `render(widget)` /
  `qimage_to_pil(widget.grab().toImage())`) and compare rows or columns of pixels with the reference crop.
  Reference GIF-derived pictures are 16-colour: `#DFDFDF` quantises to `#C0C0C0`, and the inverted
  focus-rectangle grey (`#3F3F3F`) shows as black; map before comparing.
- **Layout against an original**: measure the original once (a short PIL script dumping rows as
  characters is the fastest way), put the numbers in a constant with the picture's name, and write a
  *differential* probe that runs the same measurement on both pictures (see `tests/test_mouse_page.py`).
- **QML components**: load them in a `QQuickView`/`QQmlComponent` under the offscreen platform and drive
  them with `QTest.mousePress/mouseMove/mouseRelease` after `QTest.qWaitForWindowExposed(view)`
  (see `tests/test_drag_sort.py`). Plain-QtQuick components only; Plasma imports do not load there.
- **Real desktop**: `desktop_session(look, work, ...)` in `tests/plasma_session.py` starts a nested
  `kwin_wayland --virtual` with a throwaway HOME, installs the theme, opens test windows and returns a
  screenshot. Slow (40 s+), used for the taskbar, tray and windows. Skipped when the programs are missing.
- **Setup**: `run_bash_with_steps(tmp_path, "…")` runs a shell snippet with `setup/steps.sh` sourced in a
  temporary HOME; `dry_run_log(tmp_path, "--components=x")` in `tests/test_install.py` runs the installer
  in dry-run mode and returns its log ("would: …" lines).
- **Static QML checks** (`qml_block(text, "id: launcherCell")`) when a real load is impossible; keep them
  few and precise.

After the targeted tests, run the suite without the desktop sessions:

```
python3 -m pytest tests -q -p no:cacheprovider --ignore=tests/test_plasma_taskbar_reference.py --ignore=tests/test_plasma_quick_launch_band.py
```

and the desktop sessions separately when the taskbar, tray, windows or Setup's taskbar script changed.
`make check` runs every formatter and linter (tools missing locally are skipped). Regenerate the showcase
pictures after a visible change: `python3 tests/render_report.py docs/compare` (it empties the folder
first; if it crashes, run it again).

## Conventions worth knowing

- **Scale**: tests pin the screen scale to 1 (`conftest` does it); the user runs at 1.5. Anything drawn
  with sub-pixel rounding (clips, frames) must be checked at a fractional scale too: run a subprocess
  with `QT_SCALE_FACTOR=1.5` (see `test_the_frame_line_never_runs_under_a_group_title_at_any_screen_scale`).
- **Paths when installed**: `bin/<tool>` resolves its siblings through `Path(__file__)`; the checkout's
  `plasmoids/`, `sddm/`, `splash/` do not exist under `~/.local`. Use `repo_of(values)` (the `REPO` Setup
  saved) with installed fallbacks, and test by copying `bin/` to a temporary folder
  (`test_the_control_panel_installed_outside_the_checkout_opens_passwords_with_working_previews`).
- **Property sheets** are a fixed 398×424 (`SHEET_SIZE`); a tab has about 357×322 px before it scrolls.
  QML previews are shown shrunk through `QmlPreview(size, scale)`; use `preview.dialog()` for the screen's
  root, not `rootObject()`.
- **Settings**: every key in `SETTINGS_KEYS` (`setup/steps.sh`) needs a Control Panel field and an entry in
  `COMPONENTS_BY_KEY`; a test enforces both. New components go into `INSTALL_ORDER`, the picker in
  `install.sh`, and the dispatch `case` there.
- **Pictures**: 16-colour bitmaps carry the button face as `#C0C0C0`; repaint it in the look's face at
  draw time (`control_panel_picture(name, face)`), never ship separate copies per look.
- **GTK**: GTK 3 does not know `-gtk-icon-filter` or `window.background …` descendant selectors on its
  default title bar; verify GTK CSS with a `Gtk.StyleContext` + `Gtk.WidgetPath` probe (no window needed)
  before trusting a rule.
- **KWin decoration**: Aurorae draws a maximized window from the `decoration-maximized-*` centre piece
  only; the generator emits those pieces as the title band.
- **Resident tools** (Start menu, Clippy, notifyd, screensaver) use a pid file in `XDG_RUNTIME_DIR` and a
  wake-up timer so Python signal handlers run (`chicago95ui.quit_on_signals`). The Control Panel is
  single-instance through a local socket.
- **Icons**: toolbar icons are grey until hovered everywhere: KIconLoader effects for KDE/Qt, a CSS rule
  for GTK, and the shadowed `ButtonContent.qml` for Plasma's own buttons.

## Traps that cost time

- `app.setStyle(new style)` deletes the previous style; `classic_style()` re-creates its cached instance
  when shiboken says it is gone. Other tools' tests may leave their own style on the application: pin
  `widget.setStyle(chicago95ui.classic_style())` in a test that renders through the style.
- A lambda connected to a widget that is `deleteLater()`'d can hold the last reference to its owner and
  cause a double free (a segfault that moves around the suite). Connect bound methods instead.
- A `Repeater` keeps delegates across `model.move()`; a `Loader`-created item has no parent during its
  construction, so default property bindings must guard `parent`.
- `Plasmoid.configuration.<newKey>` can be `undefined` in a running plasmashell right after an install;
  default it in QML (`?? Band.fitAll()`) and make JS treat non-numbers as the default.
- `QProcess`-based checks in the Control Panel must be awaited in tests with
  `while tab.check is not None: qt_app.processEvents()`.
- The nested desktop screenshots settle: `desktop_session` keeps shooting until two match. Do not add
  sleeps; make the probe robust instead.
- Btrfs: a full suite run leaves `/tmp/c95-*` folders when it crashes and core dumps under
  `/var/lib/systemd/coredump`; both are the user's to remove.

## Working beside another session

Another agent may be editing the same tree. Before touching a shared file (`bin/chicago95-control-panel`,
`plasmoids/org.chicago95.tasks/contents/ui/main.qml`, `lib/chicago95ui.py`, `setup/steps.sh`), say which
blocks you will edit and re-read the file right before editing. Prefer small python patch scripts that
assert their anchors over blind rewrites. When a test of theirs breaks because of your change, fix the
test only when the change is the intended new behaviour, and tell them.

## Verification checklist before reporting

- The new tests were red first and are green now; the related suites pass; `make check` is clean (or the
  skipped tools are named).
- Visible changes were looked at: render the widget or page and view the picture; compare with the
  reference crop side by side.
- Say which components the user must reinstall (`./install.sh --components a,b`) and whether a logout,
  `plasmashell` restart or program restart is needed.
- Report exactly what was verified and what was not.
