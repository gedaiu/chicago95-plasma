# shellcheck shell=bash disable=SC2034
# One function per component. Sourced by install.sh after detect.sh and ui.sh.
# Every file written goes through put_file/put_tree so it is backed up and recorded
# in the manifest that uninstall.sh reads.

PANEL_HEIGHT=28
LUNA_PANEL_HEIGHT=30
AERO_PANEL_HEIGHT=40 # the Windows 7 superbar
LUNA_GENERATORS=~/.local/share/chicago95/luna-generators

STATE_DIR="$HOME/.local/share/chicago95"
MANIFEST="$STATE_DIR/installed-files.txt"
BACKUP_DIR="$STATE_DIR/backup-$(date +%Y%m%d-%H%M%S)"

# shellcheck disable=SC2153 # SETUP_LOG is set by install.sh, which sources this file
run() { if [ "${SETUP_DRY_RUN:-0}" = 1 ]; then printf '  would: %s\n' "$*" >>"$SETUP_LOG"; else "$@"; fi; }

record() { [ "${SETUP_DRY_RUN:-0}" = 1 ] || installed_by_setup "$1" || {
  mkdir -p "$STATE_DIR"
  printf '%s\n' "$1" >>"$MANIFEST"
}; }

installed_by_setup() { [ -f "$MANIFEST" ] && grep -qxF "$1" "$MANIFEST"; }

backup() { # backup <path>  keeps the pre-install version; a file Setup put there earlier is not backed up
  local path="$1"
  [ -e "$path" ] || [ -L "$path" ] || return 0
  [ "${SETUP_DRY_RUN:-0}" = 1 ] && return 0
  installed_by_setup "$path" && return 0
  local dest="$BACKUP_DIR/${path#"$HOME"/}"
  mkdir -p "$(dirname "$dest")"
  [ -e "$dest" ] || cp -a "$path" "$dest"
}

short_path() {
  local path="${2#"$REPO"/}"
  printf -v "$1" '%s' "${path/#"$HOME"/\~}"
} # short_path <variable> <path>

# show_copy <source> <destination>   on screen and in the Setup log, one line per file. Thousands of files
# pass through here (the icon sets), so it starts no programs: no subshells, no tput.
show_copy() {
  local source dest verb=copied
  short_path source "$1"
  short_path dest "$2"
  [ "${SETUP_DRY_RUN:-0}" = 1 ] && verb=would-copy
  printf '%s: %s -> %s\n' "$verb" "$1" "$2" >>"$SETUP_LOG"
  COPIED=$((COPIED + 1))
  ui_progress "$COPIED" "$TO_COPY" "$source → $dest"
}

put_file() { # put_file <source> <destination>
  local source="$1" dest="$2"
  backup "$dest"
  run mkdir -p "$(dirname "$dest")"
  [ "$source" -ef "$dest" ] || run cp "$source" "$dest" # a saved choice can point at the file already installed
  record "$dest"
  show_copy "$source" "$dest"
}

put_tree() { # put_tree <source dir> <destination dir>
  local source="$1" dest="$2" file
  backup "$dest"
  run rm -rf "$dest"
  run mkdir -p "$(dirname "$dest")"
  run cp -r "$source" "$dest"
  record "$dest"
  while IFS= read -r file; do show_copy "$file" "$dest/${file#"$source"/}"; done < <(find "$source" -type f | sort)
}

# installed_differs <source> <destination>  true when a file of source is missing or different at destination
installed_differs() {
  local source="$1" dest="$2" file
  if [ ! -d "$source" ]; then
    ! cmp -s "$source" "$dest"
    return
  fi
  while IFS= read -r file; do
    cmp -s "$file" "$dest/${file#"$source"/}" || return 0
  done < <(find "$source" -type f)
  return 1
}

# Set by the steps that change what plasmashell loads; finish_session restarts it only then.
SHELL_CHANGED=${SHELL_CHANGED:-0}

substitute_home() { [ "${SETUP_DRY_RUN:-0}" = 1 ] || { grep -rlIZ '@HOME@' "$@" 2>/dev/null || true; } | xargs -0 -r sed -i "s|@HOME@|$HOME|g"; }

kconf() {
  run kwriteconfig6 --file "$1" --group "$2" --key "$3" "${@:4}"
  record "kconf:$1:$2:$3"
}

# python_applier [--into=DIR] <applier>...   lib/chicago95appliers.py's appliers, with this run's choices (every SETUP_*
# variable); the Control Panel's Apply runs the same ones. What they leave for the session comes back as variables:
# SHELL_CHANGED and the other flags, the choices they changed (SETUP_START_LOGO), the copy count; their status lines
# are shown here.
python_applier() {
  local into="" report key value status=0
  case "${1:-}" in --into=*)
    into=${1#--into=}
    shift
    ;;
  esac
  report=$(mktemp "${TMPDIR:-/tmp}/chicago95-apply-XXXXXX") || return 1
  (
    export REPO HOME PANEL_HEIGHT STATE_DIR MANIFEST BACKUP_DIR UI_PLAIN SHELL_CHANGED GLASS_EFFECT_CHANGED AERO_FRAME_CHANGED \
      CAPTION_RELOAD TASKBAR_CHANGED START_MENU_CHANGED SHELL_MENU_DONE LOOK_STEP_DONE "${!SETUP_@}"
    export COMPONENTS="${COMPONENTS:-}" COPIED="${COPIED:-0}" TO_COPY="${TO_COPY:-0}" APPLY_INTO="$into"
    python3 "$REPO/lib/chicago95apply.py" --environment --report="$report" --appliers="$(IFS=,; printf '%s' "$*")"
  ) || status=$?
  while IFS='=' read -r key value; do
    case "$key" in
    STATUS) if declare -F ui_status >/dev/null; then ui_status "$value"; else printf '   %s\n' "$value"; fi ;;
    COPIED | SETUP_* | SHELL_CHANGED | GLASS_EFFECT_CHANGED | AERO_FRAME_CHANGED | CAPTION_RELOAD | TASKBAR_CHANGED | \
      START_MENU_CHANGED | SHELL_MENU_DONE | LOOK_STEP_DONE) printf -v "$key" '%s' "$value" ;;
    esac
  done <"$report"
  rm -f "$report"
  return "$status"
}

# The choices the Control Panel saves in ~/.config/chicago95/setup.conf, one KEY=value per line; KEY sets SETUP_KEY.
SETTINGS_KEYS="$(sed '/^#/d' "$REPO/setup/settings.keys" | tr '\n' ' ')$(sed -n 's/^EVENT|\([^|]*\)|.*/\1/p' "$REPO/setup/animations.conf" | tr '\n' ' ')"

# Colours are #RRGGBB, or two separated by a comma for a gradient; banner stops with @N sit N pixels above its bottom.
# The running distribution's branding (lib/chicago95distro.py): KEY<TAB>value lines, read as data; nothing when
# there is no os-release. SETUP_OS_RELEASE and SETUP_DATA_DIRS point it elsewhere (tests).
DISTRO_BRANDING_KEYS="BANNER_TEXT EDITION COMPANY LOADING_FOOTER START_LOGO LOGIN_LOGO COMPANY_LOGO"
distro_branding_lines() {
  python3 "$REPO/lib/chicago95distro.py" --os-release "${SETUP_OS_RELEASE:-/etc/os-release}" \
    --data-dirs "${SETUP_DATA_DIRS:-${XDG_DATA_DIRS:-/usr/local/share:/usr/share}}" 2>/dev/null || true
}
apply_distro_branding() { # the distribution's names and logos over the look's Windows ones; only known keys
  local key value
  while IFS=$'\t' read -r key value; do
    [[ " $DISTRO_BRANDING_KEYS " == *" $key "* ]] && printf -v "SETUP_$key" '%s' "$value"
  done < <(distro_branding_lines)
  return 0
}
detected_distro_name() { distro_branding_lines | awk -F'\t' '$1 == "BANNER_TEXT" { print $2 }'; }

known_looks() { (cd "$REPO/looks" && ls -- *.conf) | sed 's/\.conf$//' | sort | tr '\n' ' ' | sed 's/ $//'; }

apply_look() { # apply_look <look>   every KEY=value of looks/<look>.conf, read as data, sets SETUP_KEY
  local lookFile="$REPO/looks/$1.conf" key value
  if [ ! -f "$lookFile" ]; then
    printf 'Unknown look "%s"; known looks: %s\n' "$1" "$(known_looks)" >&2
    return 1
  fi
  SETUP_LOOK=$1
  while IFS='=' read -r key value; do
    [ -n "$key" ] && [ "${key#\#}" = "$key" ] || continue
    case "$key:$value" in SPLASH_IMAGE:*/* | BACKGROUND_IMAGE:*/*) value="$REPO/$value" ;; esac
    printf -v "SETUP_$key" '%s' "$value"
  done <"$lookFile"
  [ -z "${OPT_ICONS:-}" ] || SETUP_ICONS=$OPT_ICONS
  [ -z "${OPT_SOUNDS:-}" ] || SETUP_SOUND_THEME=$OPT_SOUNDS
}

save_settings() { # keys this run did not set keep their saved values
  [ "${SETUP_DRY_RUN:-0}" = 1 ] && return 0
  local file=~/.config/chicago95/setup.conf key variable previous=""
  [ -f "$file" ] && previous=$(cat "$file")
  backup "$file"
  mkdir -p "$(dirname "$file")"
  {
    for key in $SETTINGS_KEYS; do
      variable=SETUP_$key
      if [ -n "${!variable+x}" ]; then printf '%s=%s\n' "$key" "${!variable}"; else grep -m1 "^$key=" <<<"$previous" || true; fi
    done
    printf 'COMPONENTS=%s\n' "$(remembered_components "$previous")"
    printf 'REPO=%s\n' "$REPO"
    printf 'COMMIT=%s\n' "$(git -C "$REPO" rev-parse HEAD 2>/dev/null || echo unknown)" # the update check compares it with the origin
  } >"$file"
  record "$file"
}

remembered_components() { # remembered_components <previous setup.conf text>   every component installed so far, in order
  local component known
  known=" $(sed -n 's/^COMPONENTS=//p' <<<"$1" | tail -1) "
  for component in ${COMPONENTS:-}; do
    [[ "$known" == *" $component "* ]] || known+="$component "
  done
  known="${known# }"
  known="${known% }"
  printf '%s' "${known# }"
}

load_settings() { # load_settings <file>   values are data: the file is read, never executed
  local key value look
  look=$(sed -n 's/^LOOK=//p' "$1" | tail -1)
  [ -z "$look" ] || [ ! -f "$REPO/looks/$look.conf" ] || apply_look "$look"
  while IFS='=' read -r key value; do
    case " ${SETTINGS_KEYS//$'\n'/ } COMPONENTS CLASSIC_EFFECTS " in *" $key "*) printf -v "SETUP_$key" '%s' "$value" ;; esac
  done <"$1"
  classic_effects_as_animations
}

classic_effects_as_animations() { # the old single "no animations" choice, as every animation event turned off
  [ "${SETUP_CLASSIC_EFFECTS:-}" = yes ] || return 0
  local key
  for key in $(animation_events); do [ -n "$(animation_choice "$key")" ] && return 0; done
  for key in $(animation_events); do
    case "$key" in
    ANIM_SPEED) SETUP_ANIM_SPEED=0 ;;
    ANIM_WOBBLY) SETUP_ANIM_WOBBLY=no ;;
    *) printf -v "SETUP_$key" none ;;
    esac
  done
}

# --- KWin rules: merged as text, never through kwriteconfig6 (it drops every other group) ---

kwin_rule() { # kwin_rule <group> <body lines...>   replaces or appends the group and lists it in Order=
  local group="$1"
  shift
  local file="$HOME/.config/kwinrulesrc"
  [ "${SETUP_DRY_RUN:-0}" = 1 ] && {
    printf '  would: write kwin rule [%s]\n' "$group" >>"$SETUP_LOG"
    return
  }
  backup "$file"
  mkdir -p "$(dirname "$file")"
  touch "$file"
  python3 - "$file" "$group" "$@" <<'EOF'
import sys, re
path, group, *lines = sys.argv[1:]
text = open(path).read()
block = "[%s]\n%s\n" % (group, "\n".join(lines))
pattern = re.compile(r"^\[%s\]\n(?:(?!\[).*\n?)*" % re.escape(group), re.M)
text = pattern.sub("", text).rstrip("\n") + "\n\n" + block
if "[General]" not in text:
    text = "[General]\nOrder=%s\n\n" % group + text
else:
    m = re.search(r"^Order=(.*)$", text, re.M)
    if m:
        names = [n for n in m.group(1).split(",") if n]
        if group not in names:
            names.append(group)
        text = text[:m.start()] + "Order=" + ",".join(names) + text[m.end():]
    else:
        text = text.replace("[General]\n", "[General]\nOrder=%s\n" % group, 1)
open(path, "w").write(text)
EOF
  record "kwinrule:$group"
}

kwin_reconfigure() { run gdbus call --session --dest org.kde.KWin --object-path /KWin --method org.kde.KWin.reconfigure >/dev/null 2>&1 || true; }

# --- components ---

widget_style_is_luna() { [ "$SETUP_WIDGET_STYLE" = luna ]; }

gtk_theme_name() {
  case "$SETUP_WIDGET_STYLE" in
  aero) echo Chicago95Aero ;;
  luna) echo Chicago95Luna ;;
  *) echo Chicago95 ;;
  esac
}

xsettingsd_source() { widget_style_is_luna && echo "$REPO/config/xsettingsd/xsettingsd-luna.conf" || echo "$REPO/config/xsettingsd/xsettingsd.conf"; }

# edit_xsettings <key> <value as written in the file>   a key of the installed xsettingsd.conf
edit_xsettings() {
  [ -f ~/.config/xsettingsd/xsettingsd.conf ] || [ "${SETUP_DRY_RUN:-0}" = 1 ] || return 0
  run sed -i "s|^$1 .*|$1 $2|" ~/.config/xsettingsd/xsettingsd.conf
  [ "${SETUP_DRY_RUN:-0}" = 1 ] || pkill -HUP xsettingsd 2>/dev/null || true
}

# set_gtk_interface <key> <value>   GTK programs on Wayland (Electron's dialogs among them) ignore XSETTINGS and
# settings.ini: they read the theme and font from GSettings.
set_gtk_interface() {
  command -v gsettings >/dev/null 2>&1 || [ "${SETUP_DRY_RUN:-0}" = 1 ] || return 0
  run gsettings set org.gnome.desktop.interface "$1" "$2"
  record "gsettings:$1"
}

set_gtk_font() { # set_gtk_font <Pango font description>   X11, Wayland and settings.ini GTK programs
  local version
  edit_xsettings Gtk/FontName "\"$1\""
  set_gtk_interface font-name "$1"
  for version in 3.0 4.0; do
    backup ~/.config/gtk-"$version"/settings.ini
    run kwriteconfig6 --file ~/.config/gtk-"$version"/settings.ini --group Settings --key gtk-font-name "$1"
  done
}

set_gtk_caption_layout() {
  local version settings layout=icon:minimize,maximize,close
  for version in 3.0 4.0; do
    settings="$HOME/.config/gtk-$version/settings.ini"
    backup "$settings"
    run mkdir -p "$(dirname "$settings")"
    run kwriteconfig6 --file "$settings" --group Settings --key gtk-decoration-layout "$layout"
    record "$settings"
  done
  if command -v gsettings >/dev/null 2>&1 || [ "${SETUP_DRY_RUN:-0}" = 1 ]; then
    if run gsettings set org.gnome.desktop.wm.preferences button-layout "$layout"; then
      record "gsettings-wm:button-layout"
    fi
  fi
}

set_gtk_theme() { # set_gtk_theme <theme name>   GTK 3 and GTK 4 settings
  local version
  if [ "$1" = Chicago95 ] && [ -d ~/.themes/Chicago95 ]; then
    run python3 "$REPO/lib/gtk_palette.py"
  fi
  for version in 3.0 4.0; do
    backup ~/.config/gtk-$version/settings.ini
    run mkdir -p ~/.config/gtk-$version
    run kwriteconfig6 --file ~/.config/gtk-$version/settings.ini --group Settings --key gtk-theme-name "$1"
    run kwriteconfig6 --file ~/.config/gtk-$version/settings.ini --group Settings --key gtk-overlay-scrolling false # the originals' scroll bars never hid
    record ~/.config/gtk-$version/settings.ini
  done
  set_gtk_interface gtk-theme "$1"
  import_gtk4_theme "$1"
  import_gtk_progress "$1"
}

# Keep shared classic progress/frame rules in both GTK versions; remove them when selecting Luna.
grab_hand_for_moves() { # KWin draws its move pointer while it drags a window (Clippy among them): the grabbing hand
  local cursors=~/.icons/Chicago95_Animated_Hourglass_Cursors_HiDPI/cursors name
  [ -f "$cursors/grabbing" ] || return 0
  for name in move fleur size_all all-scroll; do
    run cp "$cursors/grabbing" "$cursors/$name"
  done
}

drop_static_busy_frames() { # the busy cursors open on a flat black/white frame that flashes before the coloured animation
  local cursors=~/.icons/Chicago95_Animated_Hourglass_Cursors_HiDPI/cursors name
  [ -d "$cursors" ] || return 0
  for name in watch wait left_ptr_watch progress half-busy; do
    [ -f "$cursors/$name" ] && run python3 -I "$REPO/setup/busy_cursor_frames.py" "$cursors/$name"
  done
  return 0
}

import_gtk_progress() {
  local version target radio_assets=""
  [ "${SETUP_DRY_RUN:-0}" = 1 ] && return 0
  if [ "$1" = Chicago95 ] && [ "${SETUP_DPI:-96}" = 120 ] && [[ "${SETUP_LOOK:-}" =~ ^(1998|2000|2001)$ ]]; then
    radio_assets="$STATE_DIR/gtk-classic-radio"
    backup "$radio_assets"
    record "$radio_assets"
  fi
  local thunar_rule=62-chicago95-thunar-tahoma.conf thunar_tahoma=""
  local fontconfig_dir="${XDG_CONFIG_HOME:-$HOME/.config}/fontconfig/conf.d"
  case "$1:${SETUP_LOOK:-}:${SETUP_DPI:-96}" in
    Chicago95:2000:120 | Chicago95:2001:120) thunar_tahoma=$SETUP_LOOK ;;
    Chicago95Luna:*:120) thunar_tahoma=luna ;;
  esac
  if [ -n "$thunar_tahoma" ]; then
    put_file "$REPO/config/fontconfig/$thunar_rule" "$fontconfig_dir/$thunar_rule"
  elif cmp -s "$REPO/config/fontconfig/$thunar_rule" "$fontconfig_dir/$thunar_rule"; then
    run rm -f "$fontconfig_dir/$thunar_rule"
  fi
  if [ "$1" = Chicago95 ] && [ "${SETUP_LOOK:-}" = 1998 ]; then
    put_file "$REPO/config/win98-rebar.svg" "$HOME/.config/gtk-3.0/win98-rebar.svg"
  fi
  for version in 3.0 4.0; do
    target=~/.config/gtk-$version/gtk.css
    backup "$target"
    mkdir -p "$(dirname "$target")"
    python3 - "$target" "$REPO/config/gtk-progress-classic.css" "$1" "$version" \
      "$radio_assets" "${SETUP_LOOK:-}" "${SETUP_DPI:-96}" "$thunar_tahoma" <<'PYPROGRESS'
import re
import sys
from pathlib import Path
from string import Template

target, source = map(Path, sys.argv[1:3])
sys.path.insert(0, str(source.parent.parent / "lib"))
from gtk_inputs import classic_radio_css, input_css
from gtk_sliders import slider_css
from gtk_header import without_gtk4_properties
begin, end = "/* Chicago95 progress BEGIN */", "/* Chicago95 progress END */"
text = target.read_text() if target.exists() else ""
text = re.sub(re.escape(begin) + r".*?" + re.escape(end) + r"\n?", "", text, flags=re.S)
block = ""
if sys.argv[3] == "Chicago95Aero":
    toolbar = "gtk-toolbar-icons-gtk3.css" if sys.argv[4] == "3.0" else "gtk-toolbar-icons.css"
    text = text.replace(source.with_name(toolbar).read_text(), "")
if sys.argv[3] == "Chicago95":
    block = (source.read_text() + source.with_name("gtk-frames-classic.css").read_text()
             + input_css(Path.home() / ".themes/Chicago95", sys.argv[4]) + slider_css(sys.argv[4]))
    if sys.argv[5]:
        block += classic_radio_css(Path(sys.argv[5]), sys.argv[6], gtk3=sys.argv[4] == "3.0")
    if sys.argv[4] == "3.0":  # GTK 3 warns on every start about properties only GTK 4 knows
        if sys.argv[6] == "1995":
            block += source.with_name("gtk-thunar-win95.css").read_text()
        elif sys.argv[6] == "1998":
            block += source.with_name("gtk-thunar-win98.css").read_text()
        block = without_gtk4_properties(block)
elif sys.argv[3] == "Chicago95Luna" and sys.argv[7] == "120":
    theme = Path.home() / ".themes/Chicago95Luna"
    rules = source.parent.parent / "luna/gtk/Chicago95Luna/radio-120dpi.css"
    block = rules.read_text().replace('url("radio-120dpi/', f'url("{theme.as_uri()}/radio-120dpi/')
if sys.argv[4] == "3.0" and sys.argv[8]:
    # Leading space for the 2000 grip, item insets, then the label size and baseline.
    leading, left, right, size, top = {
        "2000": (8, 6, 9, 0.88, -1),
        "2001": (0, 7, 8, 0.88, -1),
        "luna": (0, 5, 9, 0.945, 0),
    }[sys.argv[8]]
    rules = Template(source.with_name("gtk-thunar-tahoma-120.css.in").read_text())
    block += rules.substitute(leading=leading, left=left, right=right, size=size, top=top, bottom=-top)
if block:
    text = text.rstrip() + "\n" + begin + "\n" + block + end + "\n"
target.write_text(text)
PYPROGRESS
    record "$target"
  done
}

# import_gtk4_theme <theme name>   libadwaita programs (GNOME Files among them) ignore gtk-theme-name: the user's
# gtk.css is all they read. The theme's GTK 4 sheet is imported there, between the markers the Chicago95 installer
# uses for the same import, so the two never stack; whatever the user wrote around the block stays.
import_gtk4_theme() {
  local target=~/.config/gtk-4.0/gtk.css sheet=~/.themes/$1/gtk-4.0/gtk.css
  # libadwaita supplies its own base stylesheet. Only apply our overrides at user priority.
  [ "$1" != Chicago95Aero ] || sheet=~/.themes/Chicago95Aero/gtk-4.0/aero.css
  local begin='/* >>> Chicago95 GTK4 BEGIN - managed by the Chicago95 installer, do not edit */' end='/* <<< Chicago95 GTK4 END */'
  if [ "${SETUP_DRY_RUN:-0}" = 1 ]; then
    printf '  would: import %s into %s\n' "$sheet" "$target" >>"$SETUP_LOG"
    return
  fi
  backup "$target"
  mkdir -p "$(dirname "$target")"
  python3 - "$target" "$sheet" "$begin" "$end" <<'PY'
import sys
from pathlib import Path

target, sheet, begin, end = Path(sys.argv[1]), *sys.argv[2:]
block = f'{begin}\n@import url("file://{sheet}");\n{end}\n'
text = target.read_text() if target.exists() else ""
if begin in text and end in text:
    head, rest = text.split(begin, 1)
    tail = rest.split(end, 1)[1].lstrip("\n")
    text = head + block + tail
else:
    text = block + text
target.write_text(text)
PY
  # Match the original GTK3 notebook assets, rather than GTK4's approximate bevels.
  if [ "$1" = Chicago95 ] && [ -f ~/.themes/Chicago95/gtk-3.0/gtk-notebooks.css ]; then
    python3 - "$REPO/lib" ~/.themes/Chicago95 ~/.config/gtk-4.0/chicago95-notebooks.css <<'PYTABS'
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from gtk_notebooks import notebook_css
from gtk_scrollbars import scrollbar_css
Path(sys.argv[3]).write_text(notebook_css(Path(sys.argv[2])))
Path(sys.argv[3]).with_name("chicago95-scrollbars.css").write_text(scrollbar_css(Path(sys.argv[2])))
PYTABS
    # Keep this import inside the managed block so switching to Luna removes it.
    sed -i '\|/\* <<< Chicago95 GTK4 END \*/|i @import url("chicago95-notebooks.css");\n@import url("chicago95-scrollbars.css");' "$target"
    record ~/.config/gtk-4.0/chicago95-notebooks.css
    record ~/.config/gtk-4.0/chicago95-scrollbars.css
  fi
  record "$target"
}

install_aero_asset_pack() ( # <kind> <destination>
  local stage
  stage=$(mktemp -d) || return 1
  trap 'rm -rf "$stage"' EXIT
  run bash "$REPO/aero/fetch-desktop-assets.sh" "$1" "$stage" || return 1
  put_tree "$stage" "$2"
)

apply_pointer_theme() { python_applier pointer; }

step_base() {
  if [ -z "$SETUP_CHICAGO95_SRC" ]; then
    ui_status "Downloading Chicago95 (about 100 MB)..."
    run git clone --depth 1 https://github.com/grassmunk/Chicago95 "$HOME/src/Chicago95" >>"$SETUP_LOG" 2>&1 && SETUP_CHICAGO95_SRC="$HOME/src/Chicago95"
  fi
  [ -n "$SETUP_CHICAGO95_SRC" ] || {
    ui_status "Chicago95 unavailable; skipping base theme"
    return
  }
  local src="$SETUP_CHICAGO95_SRC"
  [ -d ~/.themes/Chicago95 ] || put_tree "$src/Theme/Chicago95" ~/.themes/Chicago95
  put_tree "$src/Theme/Chicago95" ~/.local/share/chicago95/gtk-original
  [ -d ~/.icons/Chicago95 ] || put_tree "$src/Icons/Chicago95" ~/.icons/Chicago95
  [ -d ~/.icons/Chicago95_Animated_Hourglass_Cursors_HiDPI ] || put_tree "$src/Cursors/Chicago95_Animated_Hourglass_Cursors_HiDPI" ~/.icons/Chicago95_Animated_Hourglass_Cursors_HiDPI
  [ -d ~/.local/share/sounds/Chicago95 ] || put_tree "$src/sounds/Chicago95" ~/.local/share/sounds/Chicago95
  run mkdir -p ~/.local/share/icons
  run ln -sfn ~/.icons/Chicago95 ~/.local/share/icons/Chicago95
  record ~/.local/share/icons/Chicago95
  append_gtk_css "$REPO/config/gtk-toolbar-icons-gtk3.css" 3.0 # GTK 3 has no icon filters: its icons dim instead
  append_gtk_css "$REPO/config/gtk-toolbar-icons.css" 4.0
  # GTK programs draw their own widgets, and GTK 4 its own title bars: both take the look's widget theme.
  set_gtk_theme "$(gtk_theme_name)"
  show_copy ~/.icons/Chicago95 ~/.local/share/icons/Chicago95
  if [ "${SETUP_DRY_RUN:-0}" != 1 ] && ! grep -q '^Inherits=' ~/.icons/Chicago95/index.theme; then
    sed -i '/^\[Icon Theme\]/a Inherits=hicolor,breeze' ~/.icons/Chicago95/index.theme
  fi
  local font
  for font in "$src"/Fonts/vga_font/*.ttf; do
    [ -e "$font" ] && put_file "$font" ~/.local/share/fonts/Chicago95/"$(basename "$font")"
  done
  run fc-cache -f ~/.local/share/fonts >/dev/null 2>&1 || true
  put_file "$(xsettingsd_source)" ~/.config/xsettingsd/xsettingsd.conf
  grab_hand_for_moves
  drop_static_busy_frames
  apply_pointer_theme
  pkill -HUP xsettingsd 2>/dev/null || true
}

rgb() { printf '%d,%d,%d' "0x${1:1:2}" "0x${1:3:2}" "0x${1:5:2}"; }

# The colour scheme holds the title colours; System Settings > Colors can change them later, and
# chicago95-colors.path redraws the decoration whenever it does.
set_title_colors() {
  python_applier title_values
  write_title_bar_css
}

write_title_bar_css() { # GTK's own title bars in the title colours
  write_gtk_titlebar_css "${SETUP_TITLE_ACTIVE:-#000080}" "${SETUP_TITLE_INACTIVE:-#808080}" "$([ -n "${SETUP_FACE:-}" ] && echo "rgb($SETUP_FACE)" || echo "#C0C0C0")"
}

redraw_title_bars() { python_applier title_bars_redraw; }

apply_title_colors() {
  set_title_colors
  step_tools_common
  put_file "$REPO/bin/chicago95-sync-colors" ~/.local/bin/chicago95-sync-colors
  run chmod +x ~/.local/bin/chicago95-sync-colors
  put_file "$REPO/config/systemd/chicago95-colors.path" ~/.config/systemd/user/chicago95-colors.path
  put_file "$REPO/config/systemd/chicago95-colors.service" ~/.config/systemd/user/chicago95-colors.service
  run systemctl --user daemon-reload
  run systemctl --user enable --now chicago95-colors.path >>"$SETUP_LOG" 2>&1
  redraw_title_bars
}

# Icon set per look: 1995 Chicago95 (installed by the base step), 1998 SE98, 2000 ClassicOS-2000.
# The packs are downloaded into ~/src like the Chicago95 checkout; ClassicOS-2000 ships SVG sources and
# builds its theme with its own script (copies and links only), and falls back to SE98 for missing icons.
install_icon_pack() { # install_icon_pack se98|classicos2000|windowsxp   -> 0 when the theme is in ~/.local/share/icons
  local theme repo source built
  case "$1" in
  windows7)
    theme=Windows-7
    repo=https://github.com/B00merang-Artwork/Windows-7
    source="$HOME/src/Windows-7-icons"
    built="$source"
    ;;
  windowsxp)
    theme=Windows-XP
    repo=https://github.com/B00merang-Artwork/Windows-XP
    source="$HOME/src/Windows-XP"
    built="$source"
    ;;
  se98)
    theme=SE98
    repo=https://github.com/nestoris/Win98SE
    source="$HOME/src/Win98SE"
    built="$source/SE98"
    ;;
  classicos2000)
    theme=ClassicOS-2000
    repo=https://github.com/ClassicOS-Themes/ClassicOS-2000-Icons
    source="$HOME/src/ClassicOS-2000-Icons"
    built="$source/build/ClassicOS-2000"
    ;;
  esac
  if [ "$1" = windows7 ] && [ ! -d "$source" ]; then
    local installed="$HOME/.local/share/icons/$theme"
    if [ -s "$installed/index.theme" ] && [ -s "$installed/apps/file-manager.png" ] &&
      [ -s "$installed/apps/32/system-file-manager.png" ] && [ -s "$installed/filesystems/user-desktop.png" ]; then
      return 0
    fi
  fi
  if [ ! -d "$source" ]; then
    ui_status "Downloading the $theme icon set..."
    run git clone --depth 1 "$repo" "$source" >>"$SETUP_LOG" 2>&1 || return 1
  fi
  if [ "$1" = classicos2000 ] && [ ! -d "$built" ]; then
    run bash -c "cd '$source' && ICON_THEME_NAME=ClassicOS-2000 MAKEFREEDESKTOP=TRUE MAKEPNG=FALSE ./build-icons.sh" >>"$SETUP_LOG" 2>&1
  fi
  [ "${KEEP_INSTALLED:-0}" = 1 ] && [ -f "$HOME/.local/share/icons/$theme/index.theme" ] &&
    [ ! -L "$HOME/.local/share/icons/$theme" ] && return 0
  if [ -L "$built" ]; then built=$(readlink -f "$built") || return 1; fi
  if [ -d "$built" ]; then put_tree "$built" "$HOME/.local/share/icons/$theme"; else show_copy "$built" "$HOME/.local/share/icons/$theme"; fi
}

# The user's own XP icon archives (ICON.zip, High-Res_XP_Icons.zip in SETUP_XP_ICON_ARCHIVES, ~/Downloads by
# default) become Windows-XP-Originals, built by luna/icons/xp_originals.py; the B00merang set looks there first
# for an icon it lacks, then in Chicago95. No archive: Chicago95 alone.
xp_icon_fallback() {
  local archives="${SETUP_XP_ICON_ARCHIVES:-$HOME/Downloads}" icons=~/.local/share/icons inherits=Chicago95,hicolor
  if [ -f "$archives/ICON.zip" ] || [ -f "$archives/High-Res_XP_Icons.zip" ]; then
    ui_status "Building the Windows XP fallback icons from your archives..."
    run python3 -I "$REPO/luna/icons/xp_originals.py" --out "$icons/Windows-XP-Originals" \
      --numbered "$archives/ICON.zip" --named "$archives/High-Res_XP_Icons.zip" >>"$SETUP_LOG" 2>&1 &&
      record "$icons/Windows-XP-Originals" && inherits=Windows-XP-Originals,$inherits
  fi
  [ "${SETUP_DRY_RUN:-0}" = 1 ] || [ ! -f "$icons/Windows-XP/index.theme" ] || {
    sed -i '/^Inherits=/d' "$icons/Windows-XP/index.theme"
    sed -i "/^\[Icon Theme\]/a Inherits=$inherits" "$icons/Windows-XP/index.theme"
    drop_scalable_folders "$icons/Windows-XP/index.theme"
  }
  show_copy "(Inherits=$inherits)" "$icons/Windows-XP/index.theme"
}

# The B00merang pack's scalable/ SVGs wrap 16px bitmaps yet claim 8..512 pixels, so Qt stretched them into every
# size between the pack's PNGs (the Control Panel's 48px icons at 1.5x): the index lists the PNG folders alone.
drop_scalable_folders() { # drop_scalable_folders <index.theme>
  python3 -I - "$1" <<'PY'
import sys
from pathlib import Path

index = Path(sys.argv[1])
kept, skipping = [], False
for line in index.read_text().splitlines():
    if line.startswith("["):
        skipping = line.startswith("[scalable/")
    if line.startswith("Directories="):
        line = "Directories=" + ",".join(d for d in line[12:].split(",") if not d.startswith("scalable/"))
    if not skipping:
        kept.append(line)
index.write_text("\n".join(kept) + "\n")
PY
}

install_aero_icon_aliases() {
  local icons="$1"
  local pair name target folder
  for pair in org.kde.konsole:konsole org.kde.systemsettings:control-center org.kde.khelpcenter:khelpcenter org.kde.plasma.printqueue:preferences-desktop-printer; do
    name=${pair%:*}
    target=${pair#*:}
    for folder in "$icons/apps" "$icons/apps/32"; do
      [ ! -f "$folder/$target.png" ] || run ln -sf "$target.png" "$folder/$name.png"
    done
  done
}

select_desktop_icons() {
  local theme="$1" version
  kconf kdeglobals Icons Theme "$theme"
  local changeicons
  changeicons=$(command -v plasma-changeicons || true)
  if [ -z "$changeicons" ] && [ -x /usr/libexec/plasma-changeicons ]; then changeicons=/usr/libexec/plasma-changeicons; fi
  if [ -z "$changeicons" ] && command -v qtpaths6 >/dev/null; then
    changeicons="$(qtpaths6 --query QT_INSTALL_LIBEXECS)/plasma-changeicons"
  fi
  if [ -x "$changeicons" ] && [ -n "${DBUS_SESSION_BUS_ADDRESS:-}" ]; then
    run "$changeicons" "$theme"
  fi
  for version in 3.0 4.0; do
    kconf "$HOME/.config/gtk-$version/settings.ini" Settings gtk-icon-theme-name "$theme"
  done
  set_gtk_interface icon-theme "$theme"
  edit_xsettings Net/IconThemeName "\"$theme\""
}

step_icons() { apply_icon_set; }

apply_icon_set() {
  local theme=Chicago95 group
  case "${SETUP_ICONS:-chicago95}" in
  windows7)
    install_icon_pack windows7 || return 1
    local icons="$HOME/.local/share/icons/Windows-7" app
    for app in org.xfce.thunar org.kde.dolphin; do
      run ln -sf file-manager.png "$icons/apps/$app.png"
      run ln -sf system-file-manager.png "$icons/apps/32/$app.png"
    done
    install_aero_icon_aliases "$icons"
    # The pack's apps/user-desktop.png is fully transparent. Its Places artwork is the desktop icon.
    run cp "$icons/filesystems/user-desktop.png" "$icons/apps/user-desktop.png"
    run sed -i 's/^Inherits=Gnome,hicolor$/Inherits=gnome,breeze,hicolor/' "$icons/index.theme"
    local vectors="$HOME/.local/share/icons/Windows-7-SVG"
    if [ "${KEEP_INSTALLED:-0}" != 1 ] || [ ! -f "$vectors/index.theme" ]; then
      run python3 "$REPO/aero/vector_art.py" icons "$icons" "$vectors" || return 1
    fi
    record "$vectors"
    select_desktop_icons Windows-7-SVG
    for group in MainToolbarIcons ToolbarIcons; do
      kconf kdeglobals "$group" DefaultEffect none
      kconf kdeglobals "$group" ActiveEffect none
    done
    return
    ;;
  se98)
    if install_icon_pack se98; then
      theme=SE98
      install_se98_taskbar_icons || return 1
    fi
    ;;
  classicos2000)
    install_icon_pack se98
    if install_icon_pack classicos2000; then
      theme=ClassicOS-2000
      install_taskbar_icon_frames "$theme" win2k || return 1
      run python3 -I "$REPO/setup/classic_icon_fallbacks.py" "$HOME/.local/share/icons/$theme/index.theme" || return 1
    fi
    ;;
  windowsxp)
    if install_icon_pack windowsxp; then
      theme=Windows-XP
      xp_icon_fallback
      install_taskbar_icon_frames "$theme" winxp-classic || return 1
    fi
    ;;
  esac
  [ "$theme" = Chicago95 ] && [ "${SETUP_ICONS:-chicago95}" != chicago95 ] && ui_status "That icon set is unavailable; keeping Chicago95"
  install_toolbar_icons "$theme"
  select_desktop_icons Chicago95-Toolbar
  # Classic Explorer's toolbar icons turn to colour on hover. XP draws them in colour at rest.
  local effect=togray
  case "${SETUP_START_MENU_STYLE:-}" in 2001|luna) effect=none ;; esac
  for group in MainToolbarIcons ToolbarIcons; do
    kconf kdeglobals "$group" DefaultEffect "$effect"
    kconf kdeglobals "$group" DefaultValue 1
    kconf kdeglobals "$group" ActiveEffect none
  done
}

# Register the fixed-size VM frames in the selected pack alongside its larger artwork.
install_taskbar_icon_frames() {
  local dest="$HOME/.local/share/icons/$1" frames="$REPO/data/taskbar-icons/$2"
  local index="$dest/index.theme" folder size added=""
  put_tree "$frames" "$dest/taskbar" || return 1
  [ "${SETUP_DRY_RUN:-0}" = 1 ] && return 0
  for folder in "$frames"/*; do
    size=${folder##*/}
    grep -qFx "[taskbar/$size]" "$index" && continue
    added+="taskbar/$size,"
    printf '\n[taskbar/%s]\nSize=%s\nContext=Applications\nType=Fixed\n' "$size" "$size" >>"$index" || return 1
  done
  if [ -n "$added" ]; then
    sed -i "/^Directories=/s|=|=$added|" "$index" || return 1
  fi
}

install_se98_taskbar_icons() {
  local dest="$HOME/.local/share/icons/SE98"
  install_taskbar_icon_frames SE98 win98 || return 1
  [ "${SETUP_DRY_RUN:-0}" = 1 ] && return 0
  # SE98 calls the mail application internet-mail. Keep its larger frames available to both names.
  local mail alias
  for mail in "$dest"/apps/*/internet-mail.png; do
    alias="${mail%/*}/mail-client.png"
    if [ -f "$mail" ] && [ ! -e "$alias" ] && [ ! -L "$alias" ]; then
      ln -s internet-mail.png "$alias" || return 1
      record "$alias"
    fi
  done
}

# Explorer's toolbar buttons as a small theme over the selected icon set.
install_toolbar_icons() { # install_toolbar_icons <icon set it inherits>
  local dest=~/.local/share/icons/Chicago95-Toolbar buttons=1995 release=95 directory=actions/22
  local size sizes=(22)
  if [ "${SETUP_BEVEL:-1995}" = 2000 ]; then buttons=2000; release=2000; fi
  case "${SETUP_START_MENU_STYLE:-}" in
  2001|luna)
    release=XP
    directory=actions/16,actions/24
    sizes=(16 24)
    for size in "${sizes[@]}"; do
      put_tree "$REPO/data/toolbar-icons/2001/$size" "$dest/actions/$size"
    done
    ;;
  *) put_tree "$REPO/data/toolbar-icons/$buttons" "$dest/actions/22" ;;
  esac
  {
    cat <<EOF
[Icon Theme]
Name=Chicago95 Toolbar
Comment=Windows $release Explorer toolbar buttons over $1
Inherits=$1,hicolor
Directories=$directory
EOF
    for size in "${sizes[@]}"; do
      cat <<EOF

[actions/$size]
Size=$size
Context=Actions
Type=Fixed
EOF
    done
  } | run tee "$dest/index.theme" >/dev/null
  record "$dest"
}

# --- Animations: setup/animations.conf lists each event, its choices and the KWin effects they turn on ---

ANIMATIONS_FILE="$REPO/setup/animations.conf"
KWIN_BUILTIN_EFFECTS=/usr/share/kwin/builtin-effects

animation_events() { sed -n 's/^EVENT|\([^|]*\)|.*/\1/p' "$ANIMATIONS_FILE"; }
animation_choice() {
  local variable="SETUP_$1"
  printf '%s' "${!variable:-}"
}
animation_category() { awk -F'|' -v key="$1" '$1 == "EVENT" && $2 == key && $4 != "-" { print $4 }' "$ANIMATIONS_FILE"; }

effects_in_category() { # effects_in_category <category>   installed KWin effects of an exclusive category, by id
  [ -n "$1" ] || return 0
  local file
  for file in "$HOME/.local/share/kwin/effects"/*/metadata.json /usr/share/kwin/effects/*/metadata.json; do
    [ -f "$file" ] && grep -q "\"X-KWin-Exclusive-Category\": *\"$1\"" "$file" && basename "$(dirname "$file")"
  done
  for file in "$KWIN_BUILTIN_EFFECTS"/*.json; do
    [ -f "$file" ] && grep -q "\"exclusiveGroup\": *\"$1\"" "$file" && basename "$file" .json
  done
}

choice_effects() { # choice_effects <event> <value>   the effects a choice turns on; any other value is an effect's id
  local listed
  listed=$(awk -F'|' -v key="$1" -v value="$2" '$1 == "CHOICE" && $2 == key && $3 == value { print $5 "|" }' "$ANIMATIONS_FILE")
  if [ -n "$listed" ]; then printf '%s\n' "${listed%|}"; else printf '%s\n' "$2"; fi
}

event_effects() { # event_effects <event>   every effect its choices name, and the installed ones of its category
  awk -F'|' -v key="$1" '$1 == "CHOICE" && $2 == key { print $5 }' "$ANIMATIONS_FILE"
  effects_in_category "$(animation_category "$1")"
}

configure_zoom_titlebar() { python_applier zoom_titlebar; }

step_animations() { # the saved animation choices into KWin, KDE's speed and our own tools; unset events stay as they are
  put_tree "$REPO/kwin-effects/chicago95zoom" ~/.local/share/kwin/effects/chicago95zoom
  put_tree "$REPO/kwin-effects/chicago95aerominimize" ~/.local/share/kwin/effects/chicago95aerominimize
  apply_animations
}

ensure_live_blur() { # the wobble with live blur is a KWin effect of its own, built here when it is not installed
  [ "${SETUP_ANIM_WOBBLY:-}" = blurred ] && ! live_blur_available || return 0
  ui_status "Building and installing Better Wobbly Windows"
  run "$REPO/aero/build-native.sh" --install-wobbly || setup_abort \
    "Could not install Better Wobbly Windows. Check the build output and the KWin development requirements in aero/README.md."
  if [ "$SETUP_DRY_RUN" = 0 ] && ! live_blur_available; then
    setup_abort "KWin cannot load Better Wobbly Windows. Check that the running KWin version matches the installed build and the compositor supports the effect."
  fi
}

apply_animations() {
  python_applier animations
  if [[ " ${COMPONENTS:-} " != *" look "* && -n "${SETUP_ANIM_WOBBLY:-}" ]] && current_aero_decoration >/dev/null; then
    select_aero_blur
  fi
}

default_panel_height() {
  # At 120 DPI the reference Classic and Luna panels are 32–33 and 34 device
  # pixels high. Plasma stores logical heights as whole pixels.
  if [[ "${SETUP_SCALE:-1}" =~ ^1\.250*$ ]]; then
    case "$SETUP_TASKBAR_STYLE" in
      classic) echo 26; return ;;
      luna) echo 27; return ;;
    esac
  fi
  case "$SETUP_TASKBAR_STYLE" in
  luna) echo "$LUNA_PANEL_HEIGHT" ;;
  aero) echo "$AERO_PANEL_HEIGHT" ;;
  *) echo 28 ;;
  esac
}

COMPONENT_STYLES=(classic luna aero)
choose_component_style() { # choose_component_style <variable> <title> <question> <three descriptions>   the look's own marked
  local variable=$1 title=$2 question=$3 choice marked=1 index
  shift 3
  for index in "${!COMPONENT_STYLES[@]}"; do [ "${COMPONENT_STYLES[$index]}" = "${!variable:-classic}" ] && marked=$((index + 1)); done
  choice=$(ui_choose "$title" "$question" "$marked" "$@")
  printf -v "$variable" '%s' "${COMPONENT_STYLES[$((choice - 1))]}"
}

choose_decoration() { # any look can wear any frames
  choose_component_style SETUP_DECORATION "Window frames" "Which window frames should the windows wear?" \
    "Classic: the look's flat title bars and raised borders" \
    "Windows XP: Luna's blue rounded frames" \
    "Windows 7: Aero glass frames (KWin blurs what lies behind them)"
}

choose_taskbar_style() {
  choose_component_style SETUP_TASKBAR_STYLE "Taskbar" "Which taskbar should the screen have?" \
    "Classic: the look's grey bar with labelled buttons" \
    "Windows XP: Luna's blue bar and green Start button" \
    "Windows 7: the glass superbar, its orb and program icons"
}

plasma_style_theme() { # the Plasma style of the chosen taskbar
  case "$SETUP_TASKBAR_STYLE" in
  luna) echo Chicago95Luna ;;
  aero) echo Chicago95Aero ;;
  *) echo Chicago95 ;;
  esac
}

decoration_theme() { # the Aurorae theme of the chosen decoration
  case "$SETUP_DECORATION" in
  luna) echo Chicago95Luna ;;
  aero) echo Chicago95Aero ;;
  *) echo Chicago95 ;;
  esac
}

# Closest discrete KWin setting to the edge spread in win7dragedge.png, measured at 96 DPI.
AERO_BLUR_STRENGTH=2
native_effect_available() {
  local plugins="${SETUP_QT_PLUGIN_DIR:-$(qtpaths6 --plugin-dir 2>/dev/null)}"
  [ -f "$plugins/kwin/effects/plugins/$1.so" ]
}

live_blur_available() {
  native_effect_available better_wobblywindows || return 1
  # When KWin is reachable, ask its loader to check the effect ABI and shared libraries.
  # Offline installs can only check the installed module until the next Plasma login.
  local supported
  if [ "${SETUP_IN_PLASMA:-0}" = 1 ] &&
    supported=$(gdbus call --session --dest org.kde.KWin --object-path /Effects --method org.kde.kwin.Effects.isEffectSupported better_wobblywindows 2>/dev/null); then
    [ "$supported" = "(true,)" ]
  fi
}

select_aero_blur() {
  local wobbly=no native=false builtin=true
  if [[ " ${COMPONENTS:-} " == *" animations "* && -n "${SETUP_ANIM_WOBBLY:-}" ]]; then
    wobbly=$SETUP_ANIM_WOBBLY
  elif kreadconfig6 --file kwinrc --group Plugins --key wobblywindowsEnabled --type bool --default false 2>/dev/null ||
    kreadconfig6 --file kwinrc --group Plugins --key better_wobblywindowsEnabled --type bool --default false 2>/dev/null; then
    wobbly=yes
  fi
  kconf kwinrc Effect-blur BlurStrength "$AERO_BLUR_STRENGTH"
  if [[ "$wobbly" = blurred ]] || kreadconfig6 --file kwinrc --group Plugins --key better_wobblywindowsEnabled --type bool --default false 2>/dev/null; then
    kconf kwinrc Effect-better_wobblywindows EmbeddedDXBlurUseBetterBlurDXSettings false
    kconf kwinrc Effect-better_wobblywindows EmbeddedDXBlurStrength "$AERO_BLUR_STRENGTH"
    kconf kwinrc Effect-better_wobblywindows EmbeddedDXBlurSaturation 100
    kconf kwinrc Effect-better_wobblywindows EmbeddedDXBlurNoiseStrength 0
  fi
  # KWin's blur skips the rectangular backdrop while an effect bends the window mesh.
  if native_effect_available aeroglassblur && [ "$wobbly" = no ]; then
    native=true
    builtin=false
  fi
  kconf kwinrc Plugins blurEnabled "$builtin"
  local style="$HOME/.local/share/plasma/desktoptheme/Chicago95Aero"
  if [ -d "$style" ]; then
    run kwriteconfig6 --file "$style/plasmarc" --group BlurBehindEffect --key enabled "$builtin"
  fi
  if native_effect_available aeroglassblur || installed_by_setup kconf:kwinrc:Plugins:aeroglassblurEnabled; then
    kconf kwinrc Plugins aeroglassblurEnabled "$native"
    GLASS_EFFECT_CHANGED=1
  fi
  if [ "$native" = true ]; then
    kconf kwinrc Effect-aeroglassblur EnableTransparency true
    kconf kwinrc Effect-aeroglassblur BasicColorization false
    kconf kwinrc Effect-aeroglassblur ReflectionIntensity 75
    kconf kwinrc Effect-aeroglassblur EnableCornerGlow false
    kconf kwinrc Effect-aeroglassblur CalibratedCaptionTint true
    # Fit the active glass against the Windows 7 VM's dark, light and blue mattes.
    kconf kwinrc Effect-aeroglassblur AeroIntensity 101
    kconf kwinrc Effect-aeroglassblur AeroHue 210
    kconf kwinrc Effect-aeroglassblur AeroSaturation 60
    kconf kwinrc Effect-aeroglassblur AeroBrightness 93
  fi
  select_aero_frame_glass "$native"
}

select_aero_frame_glass() { # <true|false>   the Aero frame drawn for KWin's glass, or for its plain blur
  local SETUP_NATIVE_GLASS=$1
  python_applier frame_glass
}

current_aero_decoration() {
  local theme
  theme=$(kreadconfig6 --file kwinrc --group org.kde.kdecoration2 --key theme) || return 1
  case "$theme" in
  __aurorae__svg__Chicago95Aero | org.chicago95.aero) printf '%s\n' "$theme" ;;
  *) return 1 ;;
  esac
}

apply_decoration() {
  local artwork renderer package plugins theme reapply=0
  artwork=$(decoration_theme)
  theme="__aurorae__svg__$artwork"
  renderer=$(qtpaths6 --locate-file GenericDataLocation kwin/aurorae/aurorae.qml 2>/dev/null) || renderer=
  if [ "$SETUP_DECORATION" = aero ]; then
    apply_aero_glass
    if [ -f "$renderer" ] && [ -f "$(qtpaths6 --query QT_INSTALL_QML)/Qt5Compat/GraphicalEffects/qmldir" ]; then
      theme=org.chicago95.aero
      package="$HOME/.local/share/kwin/decorations/$theme"
      put_tree "$REPO/aero/aurorae/caption" "$package"
      put_file "$REPO/aurorae/Theme.js" "$package/contents/ui/Theme.js"
      put_file "$REPO/aurorae/caption/contents/ui/CaptionInput.qml" "$package/contents/ui/CaptionInput.qml"
      run python3 "$REPO/aero/aurorae/install_caption.py" "$package" "$HOME/.local/share/aurorae/themes/$artwork" "$renderer"
    fi
    select_aero_blur
  elif installed_by_setup kconf:kwinrc:Plugins:aeroglassblurEnabled; then
    kconf kwinrc Plugins aeroglassblurEnabled false
    kconf kwinrc Plugins blurEnabled true
    GLASS_EFFECT_CHANGED=1
  fi
  if [ "$SETUP_DECORATION" != aero ] && [ -f "$renderer" ]; then
    plugins=$(qtpaths6 --plugin-dir 2>/dev/null) || plugins=
    if [ -f "$plugins/org.kde.kdecoration3/org.kde.kwin.aurorae.v2.so" ]; then
      # KWin migrates plain SVG themes to Aurorae v2, which hides disabled buttons.
      theme="org.chicago95.$SETUP_DECORATION"
      package="$HOME/.local/share/kwin/decorations/$theme"
      put_tree "$REPO/aurorae/caption" "$package"
      put_file "$REPO/aurorae/Theme.js" "$package/contents/ui/Theme.js"
      run python3 "$REPO/aero/aurorae/install_caption.py" "$package" "$HOME/.local/share/aurorae/themes/$artwork" "$renderer"
    fi
  fi
  case "$theme" in
  org.chicago95.aero | org.chicago95.luna)
    if [ "$(kreadconfig6 --file kwinrc --group org.kde.kdecoration2 --key theme)" = "$theme" ]; then
      reapply=1
    fi
    ;;
  esac
  kconf kwinrc org.kde.kdecoration2 library org.kde.kwin.aurorae
  kconf kwinrc org.kde.kdecoration2 theme "$theme"
  configure_zoom_titlebar
  [ "$reapply" = 0 ] || CAPTION_RELOAD=$theme
}

apply_aero_glass() {
  put_tree "$REPO/aero/aurorae/theme" ~/.local/share/aurorae/themes/Chicago95Aero
  kconf kwinrc Effect-blur NoiseStrength 0
  kconf kwinrc Effect-blur Saturation 100 # a percentage; KWin's default saturates the glass, DWM's did not
}

wants_luna() { [ "$SETUP_DECORATION" = luna ] || [ "$SETUP_TASKBAR_STYLE" = luna ] || [ "$SETUP_WIDGET_STYLE" = luna ]; }

install_luna_decoration_files() (
  local source="$REPO/luna/aurorae/theme" stage
  if [ "${SETUP_DRY_RUN:-0}" != 1 ]; then
    stage=$(mktemp -d) || return 1
    trap 'rm -rf "$stage"' EXIT
    python3 "$REPO/luna/aurorae/make_luna_aurorae.py" --dpi "${SETUP_DPI:-96}" --out "$stage" || return 1
    source="$stage"
  fi
  put_tree "$source" ~/.local/share/aurorae/themes/Chicago95Luna
)

install_luna_theme_files() {
  local luna_file
  install_luna_decoration_files || return 1
  put_tree "$REPO/luna/plasma-style/theme" ~/.local/share/plasma/desktoptheme/Chicago95Luna
  put_file "$REPO/luna/Luna.colors" ~/.local/share/color-schemes/Chicago95Luna.colors
  put_file "$REPO/aurorae/bevel.py" "$LUNA_GENERATORS/aurorae/bevel.py"
  put_file "$REPO/luna/palette.py" "$LUNA_GENERATORS/luna/palette.py"
  for luna_file in "$REPO"/luna/aurorae/*.py "$REPO"/luna/plasma-style/*.py; do
    put_file "$luna_file" "$LUNA_GENERATORS/luna/${luna_file#"$REPO"/luna/}"
  done
}

apply_aero_qt_style() {
  local archive=https://raw.githubusercontent.com/aeroshell-desktop/aerothemeplasma/f51ca15f4668a81d908505b422e5d560f35fe241/misc/kvantum/Windows7Aero
  local cache="${XDG_CACHE_HOME:-$HOME/.cache}/chicago95/kvantum-f51ca15" extension
  if [ "${SETUP_HAS_KVANTUM:-0}" != 1 ]; then
    ui_status "Install the Qt 6 Kvantum style for Aero controls in KDE applications. Using Fusion until then."
    kconf kdeglobals KDE widgetStyle Fusion
    return
  fi
  run mkdir -p "$cache"
  for extension in kvconfig svg; do
    if [ ! -s "$cache/Windows7Aero.$extension" ]; then
      run curl -fsSL "$archive/Windows7Aero.$extension" -o "$cache/Windows7Aero.$extension.part" &&
        run mv "$cache/Windows7Aero.$extension.part" "$cache/Windows7Aero.$extension" || return 1
    fi
  done
  run python3 "$REPO/aero/vector_art.py" controls "$cache/Windows7Aero.svg" "$cache/Windows7Aero-paths.svg" || return 1
  put_file "$cache/Windows7Aero.kvconfig" "$HOME/.config/Kvantum/Windows7Aero/Windows7Aero.kvconfig"
  put_file "$cache/Windows7Aero-paths.svg" "$HOME/.config/Kvantum/Windows7Aero/Windows7Aero.svg"
  kconf ~/.config/Kvantum/kvantum.kvconfig General theme Windows7Aero
  kconf kdeglobals KDE widgetStyle kvantum
}

apply_luna_qt_style() {
  if [ "${SETUP_HAS_KVANTUM:-0}" != 1 ]; then
    printf 'note: Kvantum is not installed, so the Windows XP widgets use the Fusion style; install kvantum and run Setup again\n' >>"$SETUP_LOG"
    ui_status "Kvantum not installed; Windows XP widgets use the Fusion style"
    kconf kdeglobals KDE widgetStyle Fusion
    return
  fi
  put_tree "$REPO/luna/kvantum/Chicago95Luna" ~/.config/Kvantum/Chicago95Luna
  kconf ~/.config/Kvantum/kvantum.kvconfig General theme Chicago95Luna
  kconf kdeglobals KDE widgetStyle kvantum
}

apply_luna_gtk_theme() {
  put_tree "$REPO/luna/gtk/Chicago95Luna" ~/.themes/Chicago95Luna
  set_gtk_theme Chicago95Luna
  edit_xsettings Net/ThemeName '"Chicago95Luna"'
}

apply_classic_widget_themes() {
  kconf kdeglobals KDE widgetStyle Windows
  { [ -d ~/.themes/Chicago95Luna ] || [ -d ~/.themes/Chicago95Aero ]; } && [ -d ~/.themes/Chicago95 ] || return 0
  set_gtk_theme Chicago95
  edit_xsettings Net/ThemeName '"Chicago95"'
}

apply_widget_themes() { # Qt applications (Kvantum, or Fusion without it) and GTK applications
  if [ "$SETUP_WIDGET_STYLE" = aero ]; then
    put_file "$REPO/aero/Chicago95Aero.colors" ~/.local/share/color-schemes/Chicago95Aero.colors
    put_tree "$REPO/aero/gtk/Chicago95Aero" ~/.themes/Chicago95Aero
    set_gtk_theme Chicago95Aero
    edit_xsettings Net/ThemeName '"Chicago95Aero"'
    if command -v gsettings >/dev/null 2>&1; then
      case "$(gsettings get org.gnome.desktop.interface enable-animations 2>/dev/null)" in
      true) edit_xsettings Gtk/EnableAnimations 1 ;;
      false) edit_xsettings Gtk/EnableAnimations 0 ;;
      esac
    fi
    apply_aero_qt_style
    return
  fi
  widget_style_is_luna || {
    apply_classic_widget_themes
    return
  }
  apply_luna_qt_style
  apply_luna_gtk_theme
}

AERO_PLASMA_STYLE=~/.local/share/plasma/desktoptheme/Chicago95Aero

apply_plasma_style() { run plasma-apply-desktoptheme "$(plasma_style_theme)" >>"$SETUP_LOG" 2>&1 || true; }

apply_color_scheme() { python_applier color_scheme; }

apply_face_colors() { python_applier face_colors; }

write_look_rc() { python_applier look_rc; }

sync_gtk_palette() { python_applier gtk_palette; }

step_look() { # decoration, Plasma style, colours, widget style, DPI
  SHELL_CHANGED=1
  apply_shell_menu
  put_tree "$REPO/aurorae/theme" ~/.local/share/aurorae/themes/Chicago95
  for extra in bevel.py make_chicago95_aurorae.py start-button.png start-button-pressed.png; do put_file "$REPO/aurorae/$extra" ~/.local/share/aurorae/themes/Chicago95/$extra; done
  put_file "$REPO/plasma-style/make_chicago95_plasmastyle.py" ~/.local/share/aurorae/themes/Chicago95/make_chicago95_plasmastyle.py
  put_tree "$REPO/plasma-style/theme" ~/.local/share/plasma/desktoptheme/Chicago95
  put_file "$REPO/config/Chicago95.colors" ~/.local/share/color-schemes/Chicago95.colors
  apply_widget_themes
  kconf kdeglobals General AccentColor --delete
  if wants_luna; then install_luna_theme_files || return 1; fi
  [ "$SETUP_TASKBAR_STYLE" != aero ] || put_tree "$REPO/aero/plasma-style/theme" "$AERO_PLASMA_STYLE"
  apply_decoration
  kconf kwinrc org.kde.kdecoration2 BorderSize Normal
  apply_color_scheme
  apply_icon_set || setup_abort "Could not apply the selected icon theme."
  if [ "$SETUP_WIDGET_STYLE" = aero ] || [ "$(kreadconfig6 --file kcminputrc --group Mouse --key cursorTheme 2>/dev/null)" = Windows-7-Aero-Cursors_Default ]; then
    apply_pointer_theme || return 1
  fi
  apply_face_colors
  # The originals' title bar: the window icon on the left; minimize, maximize and close on the right.
  kconf kwinrc org.kde.kdecoration2 ButtonsOnLeft M
  kconf kwinrc org.kde.kdecoration2 ButtonsOnRight IAX
  set_gtk_caption_layout
  write_look_rc
  sync_gtk_palette
  apply_title_colors
  [ "$SETUP_WIDGET_STYLE" != classic ] || theme_wine
  theme_firefox
  apply_plasma_style
  if [ "$SETUP_SCALE" != 1 ]; then
    backup ~/.Xresources
    if [ "${SETUP_DRY_RUN:-0}" != 1 ]; then
      grep -v '^Xft.dpi:' ~/.Xresources 2>/dev/null >~/.Xresources.chicago95 || true
      printf 'Xft.dpi: %s\n' "$SETUP_DPI" >>~/.Xresources.chicago95
      mv ~/.Xresources.chicago95 ~/.Xresources
      xrdb -merge ~/.Xresources 2>/dev/null || true
    fi
    show_copy "(Xft.dpi: $SETUP_DPI)" ~/.Xresources
    record ~/.Xresources
    kconf kcmfonts General forceFontDPI "$SETUP_DPI"
    scale_x11_programs
  fi
}

# Wine's classic controls in the look's colours, its own visual theme off (lib/wine_look.py). Only the default
# prefix: Wine creates it on first run, and a later Setup run themes it then.
theme_wine() { python_applier wine; }

# Wine and Steam draw their own interfaces and follow neither Xft.dpi nor the desktop's scale: Wine keeps its own DPI
# (96 unless set) in its registry, and Steam reads its scale from its environment. Wine 11 reads the DPI from the
# machine's current configuration (what winecfg's Graphics tab sets); older Wines read the user's desktop settings.
scale_x11_programs() {
  local steam_env=~/.config/environment.d/chicago95-scale.conf key prefix
  while IFS= read -r prefix; do
    [ -n "$prefix" ] || continue
    for key in 'HKCC\Software\Fonts' 'HKCU\Control Panel\Desktop'; do
      run env WINEPREFIX="$prefix" WINEDEBUG=-all wine reg add "$key" /v LogPixels /t REG_DWORD /d "$SETUP_DPI" /f >>"${SETUP_LOG:-/dev/null}" 2>&1 ||
        wine_failed "$prefix"
    done
  done <<<"$(wine_prefixes)"
  backup "$steam_env"
  if [ "${SETUP_DRY_RUN:-0}" != 1 ]; then
    mkdir -p "$(dirname "$steam_env")"
    printf 'STEAM_FORCE_DESKTOPUI_SCALING=%s\n' "$SETUP_SCALE" >"$steam_env"
  fi
  record "$steam_env"
  show_copy "(STEAM_FORCE_DESKTOPUI_SCALING=$SETUP_SCALE)" "$steam_env"
  run systemctl --user set-environment "STEAM_FORCE_DESKTOPUI_SCALING=$SETUP_SCALE"
}

AERO_ORB_LOGO=~/.local/share/chicago95/icons/fedora-orb-logo.svg

draw_aero_orb_logo() { # the distribution's logo as the superbar's orb draws it
  local fedora=/usr/share/icons/hicolor/256x256/apps/fedora-logo-icon.png
  [ -f "$fedora" ] && [ "$SETUP_TASKBAR_STYLE" = aero ] || return 0
  run python3 "$REPO/aero/vector_art.py" bitmap "$fedora" "$AERO_ORB_LOGO" && record "$AERO_ORB_LOGO"
}

install_aero_plasmoid_files() { # the superbar's parts, beside each plasmoid's own (styleParts.js picks them)
  local part
  draw_aero_orb_logo
  for part in "$REPO"/aero/plasmoids/org.chicago95.*/contents/ui/aero; do
    put_tree "$part" ~/.local/share/plasma/plasmoids/"${part#"$REPO"/aero/plasmoids/}"
  done
}

install_luna_plasmoid_files() {
  local plasmoid installed image
  [ -d "$REPO/luna/plasmoids" ] || return 0
  for plasmoid in "$REPO"/luna/plasmoids/org.chicago95.*; do
    installed=~/.local/share/plasma/plasmoids/"$(basename "$plasmoid")"
    [ -d "$plasmoid/contents/ui/luna" ] && put_tree "$plasmoid/contents/ui/luna" "$installed/contents/ui/luna"
    [ -f "$REPO/luna/plasmoids/family.js" ] && put_file "$REPO/luna/plasmoids/family.js" "$installed/contents/ui/luna/family.js"
  done
  for image in "$REPO"/luna/plasmoids/org.chicago95.start/contents/images/*; do
    [ -f "$image" ] && put_file "$image" ~/.local/share/plasma/plasmoids/org.chicago95.start/contents/images/"$(basename "$image")"
  done
  [ -f "$REPO/luna/plasmoids/images/tray-chevron-xp.png" ] &&
    put_file "$REPO/luna/plasmoids/images/tray-chevron-xp.png" ~/.local/share/chicago95/icons/tray-chevron-xp.png
  return 0
}

# Build only from the imported VM fonts. The standard Tahoma face remains the fallback.
install_nt_task_fonts() {
  local root="${XDG_DATA_HOME:-$HOME/.local/share}/fonts/Chicago95" edition source dest
  for edition in 2000 XP; do
    source="$root/Windows$edition/tahomabd.ttf"
    dest="$root/Windows$edition/Taskbar-120-Bold.ttf"
    [ -f "$source" ] || continue
    if [[ "$dest" -nt "$source" && "$dest" -nt "$REPO/setup/make_nt_task_font.py" && "$dest" -nt "$REPO/setup/font_strikes.py" ]]; then
      continue
    fi
    if run python3 "$REPO/setup/make_nt_task_font.py" "$source" "$dest" "$edition" &&
      [ -f "$dest" ]; then
      record "$dest"
      run fc-cache "${dest%/*}"
    fi
  done
  return 0
}

step_taskbar() {
  SHELL_CHANGED=1
  install_nt_task_fonts
  for plasmoid in "$REPO"/plasmoids/org.chicago95.*; do put_tree "$plasmoid" ~/.local/share/plasma/plasmoids/"$(basename "$plasmoid")"; done
  put_file "$REPO/lib/chicago95recent.py" ~/.local/share/plasma/plasmoids/org.chicago95.tasks/contents/ui/chicago95recent.py
  install_luna_plasmoid_files
  install_aero_plasmoid_files
  put_file "$REPO/plasmoids/panel-layout.js" ~/.local/share/chicago95/panel-layout.js
  put_file "$REPO/config/applications/chicago95-showdesktop.desktop" ~/.local/share/applications/chicago95-showdesktop.desktop
  put_file "$REPO/data/icons/tray-chevron.png" ~/.local/share/chicago95/icons/tray-chevron.png
  substitute_home ~/.local/share/plasma/plasmoids/org.chicago95.start ~/.local/share/plasma/plasmoids/org.chicago95.tasks ~/.local/share/plasma/plasmoids/org.chicago95.trayframe
  # The taskbar menu's Cascade, Tile and Minimize All: a KWin script, invoked through kglobalaccel
  put_tree "$REPO/kwin-scripts/chicago95windows" ~/.local/share/kwin/scripts/chicago95windows
  kconf kwinrc Plugins chicago95windowsEnabled true
  kwin_reconfigure
}

# complete_qml_module <system module dir> <our module dir>   our files shadow the module (QML_IMPORT_PATH): the rest
# of it is linked from the system's, and its qmldir copied without the `prefer` line that would send Qt back
# to the compiled-in copy.
complete_qml_module() {
  local system="$1" ours="$2" file relative
  [ -d "$system" ] || return 0
  while IFS= read -r file; do
    relative=${file#"$system"/}
    [ -e "$ours/$relative" ] && [ ! -L "$ours/$relative" ] && continue
    run mkdir -p "$ours/$(dirname "$relative")"
    if [ "$relative" = qmldir ]; then
      [ "${SETUP_DRY_RUN:-0}" = 1 ] || grep -v '^prefer ' "$file" >"$ours/qmldir"
      show_copy "$file" "$ours/qmldir"
    else
      run ln -sfn "$file" "$ours/$relative"
    fi
  done < <(find "$system" -type f | sort)
  record "$ours"
}

qt_qml_dir() {
  qtpaths6 --query QT_INSTALL_QML 2>/dev/null || echo /usr/lib64/qt6/qml
}

apply_shell_menu() { python_applier shell_menu; }

step_tools_common() { # shared by every PySide6 component; idempotent
  local luna_module lib_module
  [ "${TOOLS_COMMON_DONE:-0}" = 1 ] && return
  TOOLS_COMMON_DONE=1
  apply_shell_menu
  if installed_differs "$REPO/data/qml" ~/.local/share/chicago95/qml; then SHELL_CHANGED=1; fi
  # Every module of lib/: the tools import them from here, and one left out stops them at start.
  for lib_module in "$REPO"/lib/*.py; do put_file "$lib_module" ~/.local/lib/chicago95/"$(basename "$lib_module")"; done
  put_file "$REPO/data/2000-logon-banner.png" ~/.local/share/chicago95/2000-logon-banner.png
  put_file "$REPO/data/xp-logon-banner.png" ~/.local/share/chicago95/xp-logon-banner.png
  put_file "$REPO/aero/shutdown-button.svg" ~/.local/share/chicago95/aero-shutdown-button.svg
  # The XP modules and screens whatever the look: the Control Panel previews XP's screens from any look (its log on,
  # boot and Distro Setup pages), and the interactive boot/login flow test runs without the source checkout.
  for luna_module in "$REPO"/luna/lib/*.py; do put_file "$luna_module" ~/.local/lib/chicago95/"$(basename "$luna_module")"; done
  put_tree "$REPO/luna/lib/images" ~/.local/lib/chicago95/images
  for screen_tree in qml images splash sddm; do
    put_tree "$REPO/luna/$screen_tree" "$HOME/.local/share/chicago95/luna/$screen_tree"
  done
  put_file "$REPO/luna/palette.py" ~/.local/lib/chicago95/chicago95lunapalette.py
  put_file "$REPO/luna/images/windows-xp-flag.svg" ~/.local/lib/chicago95/images/windows-xp-flag.svg
  put_file "$REPO/setup/animations.conf" ~/.local/lib/chicago95/animations.conf
  put_file "$REPO/setup/post_xp_boot.script.in" ~/.local/share/chicago95/post_xp_boot.script.in
  put_tree "$REPO/data/qml" ~/.local/share/chicago95/qml
  complete_qml_module "$(qt_qml_dir)/org/kde/plasma/components" ~/.local/share/chicago95/qml/org/kde/plasma/components
  put_file "$REPO/config/environment.d/chicago95.conf" ~/.config/environment.d/chicago95.conf
  substitute_home ~/.config/environment.d/chicago95.conf
  run systemctl --user set-environment "QML_IMPORT_PATH=$HOME/.local/share/chicago95/qml"
}

step_controlpanel() { # one window for every choice Setup asked; it saves them and runs Setup again for what changed
  step_tools_common
  for tool in control-panel askpass; do
    put_file "$REPO/bin/chicago95-$tool" ~/.local/bin/chicago95-$tool
    run chmod +x ~/.local/bin/chicago95-$tool
  done
  put_file "$REPO/config/applications/chicago95-control-panel.desktop" ~/.local/share/applications/chicago95-control-panel.desktop
  put_tree "$REPO/data/screensaver-previews" ~/.local/share/chicago95/screensaver-previews # the Screen Saver tab's monitor
  put_tree "$REPO/data/control-panel" ~/.local/share/chicago95/control-panel               # the Mouse page's pictures
  put_tree "$REPO/looks" ~/.local/share/chicago95/looks                                    # the looks' defaults
  substitute_home ~/.local/share/applications
}

put_start_logo() { python_applier start_logo; }

write_start_menu_rc() { python_applier start_menu; }

step_startmenu() {
  step_tools_common
  put_file "$REPO/bin/chicago95-startmenu" ~/.local/bin/chicago95-startmenu
  put_tree "$REPO/data/start-menu" ~/.local/share/chicago95/start-menu
  run chmod +x ~/.local/bin/chicago95-startmenu
  put_file "$REPO/bin/chicago95-shutdown" ~/.local/bin/chicago95-shutdown
  put_tree "$REPO/kwin-effects/chicago95shutdown" ~/.local/share/kwin/effects/chicago95shutdown
  kconf kwinrc Plugins chicago95shutdownEnabled true
  # Wayland clients cannot enforce their own stacking order; KWin keeps every
  # shutdown/log-off dialog above ordinary windows, regardless of the chosen look.
  kwin_rule chicago95-shutdown "Description=Chicago95 shutdown and log-off dialogs" \
    "wmclass=chicago95-shutdown" "wmclassmatch=1" "above=true" "aboverule=3" \
    "skiptaskbar=true" "skiptaskbarrule=3"
  kwin_reconfigure
  run chmod +x ~/.local/bin/chicago95-shutdown
  # Reconfigure alone may leave newly installed scripted effects unloaded. Reload
  # this effect explicitly so both first installs and script updates take effect.
  run gdbus call --session --dest org.kde.KWin --object-path /Effects --method org.kde.kwin.Effects.unloadEffect chicago95shutdown >/dev/null 2>&1 || true
  run gdbus call --session --dest org.kde.KWin --object-path /Effects --method org.kde.kwin.Effects.loadEffect chicago95shutdown >/dev/null 2>&1 || true
  put_tree "$REPO/data/run" ~/.local/share/chicago95/run
  put_file "$REPO/bin/chicago95-run" ~/.local/bin/chicago95-run
  run chmod +x ~/.local/bin/chicago95-run
  for entry in chicago95-startmenu chicago95-shutdown chicago95-run; do put_file "$REPO/config/applications/$entry.desktop" ~/.local/share/applications/$entry.desktop; done
  put_file "$REPO/config/autostart/chicago95-startmenu.desktop" ~/.config/autostart/chicago95-startmenu.desktop
  substitute_home ~/.local/share/applications ~/.config/autostart
  put_start_logo
  write_start_menu_rc
  sync_gtk_palette
  write_branding
  show_copy "(Start menu banner: $SETUP_BANNER_TEXT, ${SETUP_BANNER_BG:-#808080} / ${SETUP_BANNER_FG:-#C0C0C0})" ~/.config/chicago95rc
  place_start_menu
  place_run_dialog
  step_shortcuts
}

# The Run dialog opens at the bottom left, just above the taskbar, as the original's did.
place_run_dialog() { python_applier place_run_dialog; }

step_shortcuts() { python_applier shortcuts; }

# The menu's height depends on its style and font, so it is measured (offscreen, with the settings just
# written) rather than assumed; the rule puts the menu's bottom edge just above the taskbar (one pixel up:
# at fractional scales the menu's height rounds up and would otherwise cover the taskbar's top line).
place_start_menu() { python_applier place_start_menu; }

step_notifications() {
  step_tools_common
  put_file "$REPO/bin/chicago95-notifyd" ~/.local/bin/chicago95-notifyd
  run chmod +x ~/.local/bin/chicago95-notifyd
  put_file "$REPO/config/applications/chicago95-notifyd.desktop" ~/.local/share/applications/chicago95-notifyd.desktop
  put_file "$REPO/config/systemd/chicago95-notifyd.service" ~/.config/systemd/user/chicago95-notifyd.service
  put_tree "$REPO/kwin-effects/chicago95notifications" ~/.local/share/kwin/effects/chicago95notifications
  substitute_home ~/.local/share/applications
  place_notifications
  [ "${SETUP_ANIM_NOTIFICATIONS:-}" = none ] || kconf kwinrc Plugins chicago95notificationsEnabled true # the Effects tab can turn their motion off
  run systemctl --user daemon-reload
  run systemctl --user enable chicago95-notifyd.service >>"$SETUP_LOG" 2>&1
}

place_notifications() { python_applier place_notifications; }

step_clippy() {
  step_tools_common
  put_file "$REPO/bin/chicago95-clippy" ~/.local/bin/chicago95-clippy
  run chmod +x ~/.local/bin/chicago95-clippy
  local clippy_asset
  for clippy_asset in agent.js map.png sounds-ogg.js; do
    put_file "$REPO/data/clippy/$clippy_asset" ~/.local/share/chicago95/clippy/"$clippy_asset"
  done
  # Blender sources, source sheets and review videos are authoring assets.
  if [ -d "$REPO/data/clippy/hd-animations" ]; then
    put_tree "$REPO/data/clippy/hd-animations" ~/.local/share/chicago95/clippy/hd-animations
  fi
  put_file "$REPO/config/applications/chicago95-clippy.desktop" ~/.local/share/applications/chicago95-clippy.desktop
  set_clippy_autostart
  substitute_home ~/.local/share/applications
  place_clippy
  restart_clippy
}

set_clippy_autostart() { python_applier clippy_autostart; }

place_clippy() { python_applier place_clippy; }

restart_clippy() { python_applier clippy_restart; }

step_extras() { # System Properties, Device Manager, Kubernetes Viewer, Dial-Up, Deezer helper, login chime
  step_tools_common
  for tool in sysprops devmgr k8sview dialup deezer; do
    put_file "$REPO/bin/chicago95-$tool" ~/.local/bin/chicago95-$tool
    run chmod +x ~/.local/bin/chicago95-$tool
  done
  put_tree "$REPO/data/device-manager" ~/.local/share/chicago95/device-manager
  put_tree "$REPO/data/sounds" ~/.local/share/chicago95/sounds
  put_file "$REPO/config/autostart/chicago95-startup.desktop" ~/.config/autostart/chicago95-startup.desktop
  substitute_home ~/.config/autostart
  [ "${SETUP_DRY_RUN:-0}" = 1 ] || sed -i "s|@SOUND_THEME@|$SETUP_SOUND_THEME|g" ~/.config/autostart/chicago95-startup.desktop
}

step_mouse() { python_applier mouse; }

step_sounds() { # install the bundled sound themes and select the scheme for desktop events
  local theme
  for theme in "$REPO"/data/sound-themes/*/; do
    theme=${theme%/}
    put_tree "$theme" ~/.local/share/sounds/"${theme##*/}"
  done
  if [ "$SETUP_SOUND_THEME" = Windows7 ]; then
    install_aero_asset_pack sounds "$HOME/.local/share/sounds/Windows7" || return 1
  fi
  select_sound_theme
}

select_sound_theme() { python_applier sound_theme; }

step_screensaver() {
  [ -n "$SETUP_HACK_DIR" ] || ui_status "XScreenSaver hacks not installed; the screensaver will do nothing until they are"
  step_tools_common
  put_file "$REPO/bin/chicago95-screensaver" ~/.local/bin/chicago95-screensaver
  run chmod +x ~/.local/bin/chicago95-screensaver
  # Earlier versions polled an idle time that Wayland never reports, from an autostart entry.
  if [ -e ~/.config/autostart/chicago95-screensaver.desktop ]; then
    run systemctl --user stop 'app-chicago95\x2dscreensaver@autostart.service'
    run rm -f ~/.config/autostart/chicago95-screensaver.desktop
  fi
  set_screensaver
}

set_screensaver() { python_applier screensaver; }

step_winamp() {
  [ "$SETUP_HAS_QMMP" = 1 ] || {
    ui_status "qmmp not installed; skipping Winamp"
    return
  }
  put_file "$REPO/config/applications/qmmp.desktop" ~/.local/share/applications/qmmp.desktop
  # Only the skinned player (its window class is "player Qmmp") draws its own frame; the visualizers don't.
  kwin_rule qmmp "Description=Chicago95 Winamp (qmmp) without frame" "wmclass=^player qmmp$" "wmclasscomplete=true" "wmclassmatch=3" \
    "noborder=true" "noborderrule=2" "types=1"
  run mkdir -p ~/.qmmp/skins
  [ -n "$SETUP_CHICAGO95_SRC" ] && [ -d "$SETUP_CHICAGO95_SRC/Extras/qmmp" ] && put_tree "$SETUP_CHICAGO95_SRC/Extras/qmmp" ~/.qmmp/skins/chicago95 || true
  size_winamp
}

# qmmp runs unscaled under X11: the player's skin pixel follows the screen's scale, single or Winamp's own Double
# Size (lib/qmmp_double_size.py). qmmp rewrites its settings when it quits, so a running player keeps its size until
# then. A player never started has no settings to change.
size_winamp() {
  local conf=~/.config/qmmp/qmmp.conf
  [ -f "$conf" ] || [ "${SETUP_SCALE:-1}" != 1 ] || return 0
  backup "$conf"
  run python3 "$REPO/lib/qmmp_double_size.py" "$conf" "${SETUP_SCALE:-1}"
  show_copy "(Winamp at the screen's scale, ${SETUP_SCALE:-1}x)" "$conf"
}

gtk_gradient() { # gtk_gradient <colour[,colour]>   a CSS background for a title bar colour or left-to-right pair
  case "$1" in
  *,*) printf 'linear-gradient(to right, %s, %s)' "${1%%,*}" "${1##*,}" ;;
  *) printf 'linear-gradient(to right, %s, %s)' "$1" "$1" ;;
  esac
}

# write_gtk_titlebar_css <active> <inactive> <inactive text>   GTK programs on Wayland (Firefox among them) draw their
# own title bars; this block in gtk.css paints them with the window manager's colours, active and inactive. The Luna
# decoration gets the XP gradient, rounded top corners and caption instead.
gtk_titlebar_rules() {
  if [ "$SETUP_DECORATION" = aero ]; then
    python3 "$REPO/aero/gtk/caption.py" "$STATE_DIR/gtk4-caption" "${SETUP_DPI:-96}"
    return
  fi
  if [ "$SETUP_DECORATION" = luna ]; then
    python3 "$REPO/luna/gtk/make_luna_gtk.py" --titlebar \
      --caption-assets "$STATE_DIR/gtk-luna-caption" --dpi "${SETUP_DPI:-96}"
    return
  fi
  local -a caption_args=()
  if [ -n "${GTK_CLASSIC_CAPTION_ASSETS:-}" ]; then
    caption_args+=(--caption-assets "$GTK_CLASSIC_CAPTION_ASSETS")
  fi
  cat <<RULES
headerbar.titlebar, .titlebar.default-decoration {
  background-image: $(gtk_gradient "$1"); background-color: ${1%%,*}; color: #FFFFFF; font-weight: bold; text-shadow: none; }
headerbar.titlebar .title, .titlebar.default-decoration .title { color: #FFFFFF; font-weight: bold; text-shadow: none; }
headerbar.titlebar:backdrop, .titlebar.default-decoration:backdrop {
  background-image: $(gtk_gradient "$2"); background-color: ${2%%,*}; color: $3; }
headerbar.titlebar:backdrop .title, .titlebar.default-decoration:backdrop .title { color: $3; }
RULES
  if [ "${SETUP_BEVEL:-1995}" = 2000 ]; then
    caption_args+=(--face "$(face_hex)" --light "$(face_hex)" --dark "#404040")
  fi
  python3 "$REPO/lib/gtk_header.py" --gtk "${GTK_VERSION:-4.0}" --dpi "${SETUP_DPI:-96}" \
    --active "$1" --inactive "$2" --inactive-text "$3" "${caption_args[@]}"
}

write_gtk_titlebar_css() {
  local begin="/* >>> Chicago95 title bars BEGIN */" end="/* <<< Chicago95 title bars END */" version target block rules
  local GTK_CLASSIC_CAPTION_ASSETS=
  if [ "$SETUP_DECORATION" = aero ]; then
    local buttons="$STATE_DIR/gtk4-caption"
    backup "$buttons"
    run python3 "$REPO/aero/gtk/caption.py" --write-buttons "$buttons" "${SETUP_DPI:-96}" || return 1
    record "$buttons"
  elif [ "$SETUP_DECORATION" = luna ]; then
    local buttons="$STATE_DIR/gtk-luna-caption"
    put_tree "$REPO/luna/gtk/Chicago95Luna/caption" "$buttons"
    if [ "${SETUP_DPI:-96}" = 120 ]; then
      run python3 "$REPO/luna/gtk/make_luna_gtk.py" --write-gtk3-hidpi-captions --caption-assets "$buttons" || return 1
    fi
  elif [ "$SETUP_DECORATION" = classic ] && [ "${SETUP_DRY_RUN:-0}" != 1 ]; then
    # GTK 3 does not load the embedded data URLs used by the CSS preview.
    GTK_CLASSIC_CAPTION_ASSETS="$STATE_DIR/gtk-classic-caption"
    backup "$GTK_CLASSIC_CAPTION_ASSETS"
    record "$GTK_CLASSIC_CAPTION_ASSETS"
  fi
  for version in 3.0 4.0; do
    rules=$(GTK_VERSION=$version gtk_titlebar_rules "$@") || return 1
    block="$begin
$rules
$end"
    target=~/.config/gtk-$version/gtk.css
    backup "$target"
    if [ "${SETUP_DRY_RUN:-0}" = 1 ]; then
      printf '  would: write the title bar colours into %s\n' "$target" >>"$SETUP_LOG"
      continue
    fi
    mkdir -p "$(dirname "$target")"
    python3 - "$target" "$begin" "$end" 3<<<"$block" <<'PYHEADER'
import os
import re
import sys
from pathlib import Path

target, begin, end = Path(sys.argv[1]), *sys.argv[2:]
with os.fdopen(3) as stream:
    block = stream.read()
text = target.read_text() if target.exists() else ""
# Older installs sometimes put the first marker immediately after a user's @import.
text = re.sub(re.escape(begin) + r".*?" + re.escape(end) + r"\n?", "", text, flags=re.S)
staging = target.with_suffix(".chicago95")
staging.write_text(text.rstrip("\n") + ("\n" if text else "") + block)
staging.replace(target)
PYHEADER
    record "$target"
  done
}

append_gtk_css() { # append_gtk_css <css file> <gtk version>...   once per file: its first line marks it
  local css="$1" version target marker
  marker=$(head -1 "$css")
  for version in "${@:2}"; do
    target=~/.config/gtk-$version/gtk.css
    backup "$target"
    grep -qF "$marker" "$target" 2>/dev/null && continue
    [ "${SETUP_DRY_RUN:-0}" = 1 ] || {
      mkdir -p "$(dirname "$target")"
      cat "$css" >>"$target"
      record "$target"
    }
    show_copy "$css" "$target"
  done
}

step_explorer() {
  if [ "${SETUP_EXPLORER:-thunar}" = dolphin ] || [ "$SETUP_HAS_THUNAR" != 1 ]; then
    [ "$SETUP_HAS_THUNAR" = 1 ] || ui_status "Thunar not installed; configuring Dolphin instead"
    put_file "$REPO/config/dolphin/dolphinui.rc" ~/.local/share/kxmlgui6/dolphin/dolphinui.rc
    kconf dolphinrc General ShowFullPath true
    if [ "$SETUP_WIDGET_STYLE" = aero ]; then kconf dolphinrc General EditableUrl false; else kconf dolphinrc General EditableUrl true; fi
    kconf dolphinrc General ShowStatusBar true
    kconf dolphinrc General ShowSpaceInfo true
    return
  fi
  local thunar_xml=~/.config/xfce4/xfconf/xfce-perchannel-xml/thunar.xml
  if [ -f "$thunar_xml" ]; then ui_status "Keeping your existing Thunar settings (see config/thunar/thunar.xml)"; else
    pkill -x thunar 2>/dev/null || true
    pkill -x xfconfd 2>/dev/null || true
    sleep 1
    put_file "$REPO/config/thunar/thunar.xml" "$thunar_xml"
  fi
  local -a navigation=(--style "$SETUP_WIDGET_STYLE" --look "${SETUP_LOOK:-}")
  if [ "${SETUP_IN_PLASMA:-0}" = 1 ] && command -v xfconf-query >/dev/null 2>&1; then
    navigation+=(--live)
  fi
  run python3 "$REPO/setup/thunar-navigation.py" "$thunar_xml" "${navigation[@]}"
  backup ~/.config/gtk-3.0/gtk.css
  if ! grep -q 'Chicago95 Thunar' ~/.config/gtk-3.0/gtk.css 2>/dev/null; then
    [ "${SETUP_DRY_RUN:-0}" = 1 ] || {
      mkdir -p ~/.config/gtk-3.0
      cat "$REPO/config/gtk-3.0/gtk.css" >>~/.config/gtk-3.0/gtk.css
      record ~/.config/gtk-3.0/gtk.css
    }
    show_copy "$REPO/config/gtk-3.0/gtk.css" ~/.config/gtk-3.0/gtk.css
  fi
  put_file "$REPO/config/dolphin/dolphinui.rc" ~/.local/share/kxmlgui6/dolphin/dolphinui.rc
  run kwriteconfig6 --file mimeapps.list --group "Default Applications" --key inode/directory thunar.desktop
}

lockscreen_style() { printf '%s' "$SETUP_LOGIN_STYLE"; }

write_lockscreen_settings() { python_applier "--into=${1:-}" lockscreen_settings; }

step_lockscreen() {
  [ -n "$SETUP_SHELL_SRC" ] || {
    ui_status "Plasma desktop shell package not found; skipping lock screen"
    return
  }
  local dst=~/.local/share/plasma/shells/org.kde.plasma.desktop
  local art="${XDG_CACHE_HOME:-$HOME/.cache}/chicago95/sddm-f51ca15"
  if [ "$(lockscreen_style)" = aero ]; then
    run bash "$REPO/aero/fetch-login-art.sh" "$art" || return 1
  fi
  backup "$dst"
  run rm -rf "$dst"
  run mkdir -p "$dst/contents"
  for entry in "$SETUP_SHELL_SRC"/*; do [ "$(basename "$entry")" = contents ] || {
    run ln -s "$entry" "$dst/"
    show_copy "$entry" "$dst/$(basename "$entry")"
  }; done
  for entry in "$SETUP_SHELL_SRC"/contents/*; do [ "$(basename "$entry")" = lockscreen ] || {
    run ln -s "$entry" "$dst/contents/"
    show_copy "$entry" "$dst/contents/$(basename "$entry")"
  }; done
  put_tree "$REPO/lockscreen/lockscreen" "$dst/contents/lockscreen"
  if [ "$(lockscreen_style)" = luna ]; then
    for luna_tree in qml sddm images lockscreen; do put_tree "$REPO/luna/$luna_tree" "$dst/contents/lockscreen/luna/$luna_tree"; done
  else
    put_tree "$SDDM_THEME_SRC" "$dst/contents/lockscreen/classic"
    if [ "$(lockscreen_style)" = aero ]; then
      put_tree "$art" "$dst/contents/lockscreen/classic/aero-art"
      put_file "$(login_logo)" "$dst/contents/lockscreen/classic/brand-logo.$(extension "$(login_logo)")"
    elif [ "$(lockscreen_style)" = 2000 ]; then
      local banner="$STATE_DIR/lock-banner.png"
      write_branding
      run mkdir -p "$STATE_DIR"
      run env QT_QPA_PLATFORM=offscreen python3 "$REPO/bin/chicago95-shutdown" --login-banner "$banner" || return 1
      put_file "$banner" "$dst/contents/lockscreen/classic/brand-banner.png"
    fi
  fi
  write_lockscreen_settings "$dst/contents/lockscreen"
  record "$dst"
}

# The boot and loading screens' style, chosen on its own (Control Panel: Booting Screen); until then, the login's.
boot_style() { printf '%s' "${SETUP_BOOT_STYLE:-${SETUP_LOGIN_STYLE:-classic}}"; }

write_splash_settings() { python_applier --into="$1" splash_file; } # <dir>

PLYMOUTH_RETAIN_DROPIN=/etc/systemd/system/plymouth-quit.service.d/zz-chicago95.conf

retain_boot_screen() { # Plymouth leaves its last frame up until the login screen draws, not seconds of black
  run sudo mkdir -p "${PLYMOUTH_RETAIN_DROPIN%/*}"
  printf '[Service]\nExecStart=\nExecStart=-/usr/bin/plymouth quit --retain-splash\n' | run sudo tee "$PLYMOUTH_RETAIN_DROPIN" >/dev/null
  run sudo systemctl daemon-reload
}

install_seven_session_art() {
  local art="${XDG_CACHE_HOME:-$HOME/.cache}/chicago95/sddm-f51ca15" target="${XDG_DATA_HOME:-$HOME/.local/share}/chicago95/session"
  local upstream=https://raw.githubusercontent.com/aeroshell-desktop/aerothemeplasma/f51ca15f4668a81d908505b422e5d560f35fe241/plasma
  run mkdir -p "$art"
  if [ ! -s "$art/background" ]; then
    run curl -fsSL --retry 2 "$upstream/sddm/sddm-theme-mod/background" -o "$art/background.tmp" || return 1
    run mv "$art/background.tmp" "$art/background" || return 1
  fi
  if [ ! -s "$art/spinner.png" ]; then
    run curl -fsSL --retry 2 "$upstream/look-and-feel/authui7/contents/images/100/Bitmap5002.png" -o "$art/spinner.tmp" || return 1
    run mv "$art/spinner.tmp" "$art/spinner.png" || return 1
  fi
  put_file "$art/background" "$target/background"
  put_file "$REPO/sddm/Chicago95Plasma/AeroBackground4x3.jpg" "$target/background-4x3.jpg"
  put_file "$REPO/sddm/Chicago95Plasma/AeroBackground1024x768.jpg" "$target/background-1024x768.jpg"
  put_file "$art/spinner.png" "$target/spinner.png" # Plymouth consumes raster frames.
  run python3 "$REPO/aero/vector_art.py" bitmap "$art/spinner.png" "$art/spinner.svg" || return 1
  put_file "$art/spinner.svg" "$target/spinner.svg"
}

step_splash() { # the loading screen: KSplash shows it after log on, in the login style; its texts and pictures go into settings.js
  local dir=~/.local/share/plasma/look-and-feel/chicago95.splashscreen/contents/splash
  put_tree "$REPO/splash/chicago95.splashscreen" ~/.local/share/plasma/look-and-feel/chicago95.splashscreen
  if [ "$(boot_style)" = luna ] || xp_login; then
    put_tree "$REPO/luna/qml" "$dir/luna/qml"
    put_tree "$REPO/luna/images" "$dir/luna/images"
    put_tree "$REPO/luna/splash" "$dir/luna/splash"
    put_tree "$REPO/luna/sddm" "$dir/luna/sddm"
  fi
  if [ "$SETUP_LOGIN_STYLE" = aero ]; then install_seven_session_art || return 1; fi
  python_applier splash_settings
  kconf ksplashrc KSplash Theme chicago95.splashscreen
  kconf ksplashrc KSplash Engine KSplashQML
}

SDDM_THEME_SRC="$REPO/sddm/Chicago95Plasma"
SDDM_THEME_DIR=/usr/share/sddm/themes/Chicago95Plasma
# The greeter runs as the sddm user, who cannot read fonts in a home folder, so the UI font goes next to the theme.
SDDM_FONT="$HOME/.local/share/fonts/MSW98UI-Regular.otf"
native_sddm_font() {
  [ "$SETUP_LOGIN_STYLE" = classic ] && [ -z "${OPT_FONT:-}" ] || return 0
  case "${SETUP_LOOK:-}" in
    1995|1998)
      local source="$HOME/.local/share/fonts/Chicago95/Windows${SETUP_LOOK:2}/MS-Sans-Serif-96-Regular.ttf"
      [ ! -r "$source" ] || printf '%s' "$source"
      ;;
  esac
}
# sddm.conf.d is read in name order and the last file wins, so zz- beats leftovers such as
# another theme's sddm.conf that would otherwise override Plasma's kde_settings.conf.
SDDM_OVERRIDE=/etc/sddm.conf.d/zz-chicago95.conf

# The waving flag is a trademark, so it isn't bundled: Setup downloads the public-domain picture from
# Wikimedia Commons on this machine when it is picked, and cuts the flag out of it.
WAVING_FLAG="$HOME/.local/share/chicago95/waving-flag.png"

# The login and loading screens' logo; "start" is the Start button's, from its copy once Setup made one.
login_logo() {
  if [ "$SETUP_LOGIN_LOGO" = start ] && [ -f "$(start_logo_file)" ]; then start_logo_file; else image_source "$SETUP_LOGIN_LOGO"; fi
}

write_branding() { python_applier branding; }

start_logo_source() { # the image behind the Start logo choice: a bundled logo name, or the user's file
  case "$SETUP_START_LOGO" in
  flag) printf '%s' "$REPO/plasmoids/org.chicago95.start/contents/images/logo-flag-16.png" ;; # pixel art at the button's size
  xp) printf '%s' "$REPO/plasmoids/org.chicago95.start/contents/images/logo-xp-16.png" ;;
  penguin) printf '%s' "$REPO/plasmoids/org.chicago95.start/contents/images/logo-penguin.svg" ;;
  *) printf '%s' "$SETUP_START_LOGO" ;;
  esac
}

# image_source <choice>   the file behind a picture choice: a bundled name, or the user's own file.
image_source() {
  case "$1" in
  start) start_logo_source ;;
  flag) printf '%s' "$REPO/plasmoids/org.chicago95.start/contents/images/logo-flag.png" ;;
  win2k-flag) printf '%s' "$SDDM_THEME_SRC/Windows2000Flag.svg" ;;
  aero-flag) printf '%s' "$SDDM_THEME_SRC/AeroBrandFlag.svg" ;;
  penguin) printf '%s' "$REPO/plasmoids/org.chicago95.start/contents/images/logo-penguin.svg" ;;
  waving-flag) printf '%s' "$WAVING_FLAG" ;;
  keys) printf '%s' "$SDDM_THEME_SRC/key-9x.png" ;;
  padlock) printf '%s' "$SDDM_THEME_SRC/padlock.svg" ;;
  classic) printf '%s' "$REPO/splash/chicago95.splashscreen/contents/splash/images/background.png" ;;
  *) printf '%s' "$1" ;;
  esac
}

extension() { printf '%s' "${1##*.}"; }

# The copy keeps the source's extension, so the image loader never has to guess PNG from SVG.
start_logo_file() {
  local source
  source=$(start_logo_source)
  printf '%s' "$HOME/.local/share/chicago95/start-logo.${source##*.}"
}

# The login theme's settings. Values travel through the environment into awk, so any text the user
# typed (slashes, ampersands, quotes) lands in theme.conf as written.
xp_login() { [ "$SETUP_LOGIN_STYLE" = luna ]; }

sddm_theme_conf() {
  LOGIN_STYLE="$SETUP_LOGIN_STYLE" \
    LOGIN_FONT="$([ -z "$(native_sddm_font)" ] || printf '%s' MS-Sans-Serif-96-Regular.ttf)" \
    LOGIN_TITLE="$SETUP_LOGIN_TITLE" LOGIN_MESSAGE="$SETUP_LOGIN_MESSAGE" \
    LOGIN_ICON="login-icon.$(extension "$(image_source "$SETUP_LOGIN_ICON")")" \
    TITLE_ACTIVE="$([ "$SETUP_LOGIN_STYLE" = 2000 ] && echo '#0A246A,#A6CAF0')" \
    LOGIN_DESKTOP_COLOR="$([ "${SETUP_LOOK:-}" = 2001 ] && echo '#000000')" \
    BRAND_TEXT="$({ xp_login || [ "$SETUP_LOGIN_STYLE" = aero ]; } && printf '%s' "$SETUP_BANNER_TEXT")" \
    BRAND_LOGO="$({ xp_login || [ "$SETUP_LOGIN_STYLE" = aero ]; } && printf 'brand-logo.%s' "$(extension "$(login_logo)")")" \
    COMPANY="$(xp_login && printf '%s' "$SETUP_COMPANY")" \
    EDITION="$({ xp_login || [ "$SETUP_LOGIN_STYLE" = aero ]; } && printf '%s' "$SETUP_EDITION")" \
    SCALE="$(awk -v s="${SETUP_SCALE:-0}" 'BEGIN { print int(s + 0.5) }')" \
    awk -F= 'BEGIN {
            value["loginStyle"] = ENVIRON["LOGIN_STYLE"]; value["loginTitle"] = ENVIRON["LOGIN_TITLE"]
            value["loginFont"] = ENVIRON["LOGIN_FONT"]
            value["loginMessage"] = ENVIRON["LOGIN_MESSAGE"]; value["loginIcon"] = ENVIRON["LOGIN_ICON"]
            value["titleActive"] = ENVIRON["TITLE_ACTIVE"]
            value["desktopColor"] = ENVIRON["LOGIN_DESKTOP_COLOR"]
            value["brandText"] = ENVIRON["BRAND_TEXT"]; value["brandLogo"] = ENVIRON["BRAND_LOGO"]
            value["company"] = ENVIRON["COMPANY"]; value["edition"] = ENVIRON["EDITION"]
            value["scale"] = ENVIRON["SCALE"]
        }
        /^[A-Za-z]+=/ && ($1 in value) { print $1 "=" value[$1]; next }
        { print }' "$SDDM_THEME_SRC/theme.conf"
}

step_sddm() { # login screen; system files, so it asks for the administrator password first
  local commands=("sudo mkdir -p $SDDM_THEME_DIR" "sudo cp -r $SDDM_THEME_SRC/. $SDDM_THEME_DIR/")
  [ -f "$SDDM_FONT" ] && commands+=("sudo cp $SDDM_FONT $SDDM_THEME_DIR/")
  local native_font
  native_font=$(native_sddm_font)
  [ -z "$native_font" ] || commands+=("sudo cp $native_font $SDDM_THEME_DIR/")
  local icon banner="$STATE_DIR/login-banner.png"
  icon=$(image_source "$SETUP_LOGIN_ICON")
  commands+=("sudo cp $icon $SDDM_THEME_DIR/login-icon.$(extension "$icon")")
  # The 2000 banner is drawn here, as the user, by the Shut Down dialog's code; the greeter shows the picture.
  if [ "$SETUP_LOGIN_STYLE" = 2000 ]; then
    write_branding
    run mkdir -p "$STATE_DIR"
    run env QT_QPA_PLATFORM=offscreen python3 "$REPO/bin/chicago95-shutdown" --login-banner "$banner"
    record "$banner"
    commands+=("sudo cp $banner $SDDM_THEME_DIR/brand-banner.png")
  fi
  local brand_logo
  if xp_login; then
    brand_logo=$(login_logo)
    commands+=("sudo cp -r $REPO/luna/qml $SDDM_THEME_DIR/luna/qml" "sudo cp -r $REPO/luna/sddm $SDDM_THEME_DIR/luna/sddm" "sudo cp -r $REPO/luna/images $SDDM_THEME_DIR/luna/images")
    commands+=("sudo cp $brand_logo $SDDM_THEME_DIR/brand-logo.$(extension "$brand_logo")")
  fi
  commands+=("sudo tee $SDDM_THEME_DIR/theme.conf   (writes: login style $SETUP_LOGIN_STYLE)")
  commands+=("sudo tee $SDDM_OVERRIDE   (writes: [Theme] Current=Chicago95Plasma)")
  if ! ui_sudo "To change the login screen, Setup must write to a system folder." "${commands[@]}"; then
    ui_message "Login screen not changed" "No administrator password was accepted, so Setup skipped the login screen." \
      "Everything else is installed. Run ./install.sh --components=sddm to try again."
    return
  fi
  if [ "$SETUP_LOGIN_STYLE" = aero ]; then
    local art="${XDG_CACHE_HOME:-$HOME/.cache}/chicago95/sddm-f51ca15"
    run bash "$REPO/aero/fetch-login-art.sh" "$art" || return 1
    run sudo mkdir -p "$SDDM_THEME_DIR/aero-art"
    run sudo cp -r "$art/." "$SDDM_THEME_DIR/aero-art/" || return 1
    run sudo rm -f -- "$SDDM_THEME_DIR/aero-art/user.svg"
    brand_logo=$(login_logo)
    run sudo cp "$brand_logo" "$SDDM_THEME_DIR/brand-logo.$(extension "$brand_logo")" || return 1
  fi
  run sudo mkdir -p "$SDDM_THEME_DIR"
  run sudo cp -r "$SDDM_THEME_SRC/." "$SDDM_THEME_DIR/"
  local file luna_tree
  while IFS= read -r file; do show_copy "$file" "$SDDM_THEME_DIR/${file#"$SDDM_THEME_SRC"/}"; done < <(find "$SDDM_THEME_SRC" -type f | sort)
  if [ -f "$SDDM_FONT" ]; then
    run sudo cp "$SDDM_FONT" "$SDDM_THEME_DIR/"
    show_copy "$SDDM_FONT" "$SDDM_THEME_DIR/$(basename "$SDDM_FONT")"
  fi
  if [ -n "$native_font" ]; then
    run sudo cp "$native_font" "$SDDM_THEME_DIR/" || return 1
    show_copy "$native_font" "$SDDM_THEME_DIR/$(basename "$native_font")"
  fi
  run sudo cp "$icon" "$SDDM_THEME_DIR/login-icon.$(extension "$icon")"
  show_copy "$icon" "$SDDM_THEME_DIR/login-icon.$(extension "$icon")"
  if [ "$SETUP_LOGIN_STYLE" = 2000 ]; then
    run sudo cp "$banner" "$SDDM_THEME_DIR/brand-banner.png"
    show_copy "$banner" "$SDDM_THEME_DIR/brand-banner.png"
  fi
  if [ "$SETUP_LOGIN_STYLE" = luna ]; then
    run sudo rm -rf "$SDDM_THEME_DIR/luna"
    run sudo mkdir -p "$SDDM_THEME_DIR/luna"
    for luna_tree in qml sddm images; do
      run sudo cp -r "$REPO/luna/$luna_tree" "$SDDM_THEME_DIR/luna/$luna_tree"
      while IFS= read -r file; do show_copy "$file" "$SDDM_THEME_DIR/luna/${file#"$REPO"/luna/}"; done < <(find "$REPO/luna/$luna_tree" -type f | sort)
    done
    run sudo cp "$brand_logo" "$SDDM_THEME_DIR/brand-logo.$(extension "$brand_logo")"
    show_copy "$brand_logo" "$SDDM_THEME_DIR/brand-logo.$(extension "$brand_logo")"
  fi
  if [ "${SETUP_DRY_RUN:-0}" = 1 ]; then run sudo tee "$SDDM_THEME_DIR/theme.conf"; else sddm_theme_conf | sudo tee "$SDDM_THEME_DIR/theme.conf" >/dev/null; fi
  show_copy "(login style: $SETUP_LOGIN_STYLE)" "$SDDM_THEME_DIR/theme.conf"
  if [ "${SETUP_DRY_RUN:-0}" = 1 ]; then run sudo tee "$SDDM_OVERRIDE"; else printf '[Theme]\nCurrent=Chicago95Plasma\n' | sudo tee "$SDDM_OVERRIDE" >/dev/null; fi
  record "root:$SDDM_OVERRIDE"
  record "root-dir:$SDDM_THEME_DIR"
  show_copy "(Setup)" "$SDDM_OVERRIDE"
}

stage_luna_plymouth() {
  local build="$1"
  run cp -r "$REPO/luna/plymouth/Chicago95-XP" "$build" || return 1
  if [ -n "${SETUP_BANNER_TEXT-Chicago95}" ]; then
    run env QT_QPA_PLATFORM=offscreen python3 "$REPO/luna/plymouth/branded_logo.py" --out "$build" \
      --name "${SETUP_BANNER_TEXT-Chicago95}" --company "$SETUP_COMPANY" --edition "$SETUP_EDITION" \
      --logo "$(login_logo)"
  else
    run cp "$REPO/luna/splash/boot-stock-640.png" "$build/boot-stock-640.png" || return 1
    run sed -i 's/native_background = "";/native_background = "boot-stock-640.png";/' "$build/Chicago95-XP.script"
  fi
}

step_plymouth() { # boot screen; system files and a rebuilt boot image, so it asks for the administrator password
  local theme_src="${SETUP_CHICAGO95_SRC:-$HOME/src/Chicago95}/Plymouth/Chicago95" name=Chicago95 current build=""
  command -v plymouth-set-default-theme >/dev/null 2>&1 || {
    ui_status "Plymouth is not installed; skipping the boot screen"
    return
  }
  # The classic boot screens are Chicago95's own theme, the 9x ones drawn over it: the others are drawn here.
  if [[ " vista 7 8 8.1 10 11 luna 2000 " != *" $(boot_style) "* ]] && [ ! -d "$theme_src" ]; then
    ui_status "Chicago95 Plymouth theme not found in $theme_src; skipping the boot screen"
    return
  fi
  if [[ " vista 7 8 8.1 10 11 " == *" $(boot_style) "* ]]; then
    if [ "$(boot_style)" = 7 ]; then install_seven_session_art || return 1; fi
    name="Chicago95-$(boot_style)"
    [ "$(boot_style)" = vista ] && name=Chicago95-Vista
    build="${TMPDIR:-/tmp}/chicago95-plymouth-$$"
    run mkdir -p "$build/splash"
    run cp -r "$REPO/splash/chicago95.splashscreen/contents/splash/." "$build/splash"
    write_splash_settings "$build/splash"
    run env QT_QPA_PLATFORM=offscreen python3 "$REPO/bin/chicago95-post-xp-boot" \
      --splash "$build/splash" --out "$build" --size "${SETUP_WIDTH:-1920}x${SETUP_HEIGHT:-1080}" \
      --scale "${SETUP_SCALE:-1}" || return 1
    run rm -rf "$build/splash"
    theme_src="$build"
  elif [ "$(boot_style)" = luna ]; then
    name=Chicago95-XP
    build="${TMPDIR:-/tmp}/chicago95-plymouth-$$"
    run rm -rf "$build"
    stage_luna_plymouth "$build" || return 1
    theme_src="$build"
  elif [ "$(boot_style)" = classic ] && [[ "${SETUP_LOOK:-}" == 199[58] ]]; then
    local images="$REPO/splash/chicago95.splashscreen/contents/splash/images" artwork
    if [ "$SETUP_LOOK" = 1998 ]; then
      name=Chicago95-98
      artwork="$images/windows98.png"
    else
      artwork="$images/windows95-boot.gif"
    fi
    build="${TMPDIR:-/tmp}/chicago95-plymouth-$$"
    run python3 "$REPO/setup/make_9x_boot.py" "$theme_src" "$artwork" "$build" --look "${SETUP_LOOK:2}" || return 1
    theme_src="$build"
  elif [ "$(boot_style)" = 2000 ]; then
    # The 2000 start-up screen: our loading screen, rendered at the monitor's size, under the Plymouth
    # script's progress blocks (plymouth/Chicago95-2000); the classic look keeps Chicago95's own theme.
    name=Chicago95-2000
    build="${TMPDIR:-/tmp}/chicago95-plymouth-$$"
    run rm -rf "$build"
    run mkdir -p "$build/splash"
    run cp -r "$REPO/plymouth/Chicago95-2000/." "$build"
    run cp -r "$REPO/splash/chicago95.splashscreen/contents/splash/." "$build/splash"
    write_splash_settings "$build/splash"
    run env QT_QPA_PLATFORM=offscreen python3 "$REPO/bin/chicago95-splash-image" --splash "$build/splash" \
      --size "${SETUP_WIDTH:-1920}x${SETUP_HEIGHT:-1080}" --scale "${SETUP_SCALE:-1}" --out "$build/screen.png" \
      --progress-strip "$build/Chicago95-2000.script" || return 1
    run env QT_QPA_PLATFORM=offscreen python3 "$REPO/bin/chicago95-splash-image" --splash "$build/splash" \
      --size "${SETUP_WIDTH:-1920}x${SETUP_HEIGHT:-1080}" --scale "${SETUP_SCALE:-1}" --text "Shutting down" --out "$build/shutdown.png"
    run env QT_QPA_PLATFORM=offscreen python3 "$REPO/bin/chicago95-splash-image" --splash "$build/splash" \
      --size "${SETUP_WIDTH:-1920}x${SETUP_HEIGHT:-1080}" --scale "${SETUP_SCALE:-1}" --text-loader --out "$build/loader.png"
    run rm -rf "$build/splash"
    theme_src="$build"
  fi
  current=$(plymouth-set-default-theme 2>/dev/null || true)
  [ "$current" = "$name" ] && [ "$name" = Chicago95 ] && {
    ui_status "The boot screen is already Chicago95"
    return
  }
  if ! ui_sudo "To change the boot screen, Setup must copy the theme to a system folder and rebuild the boot image. That takes a minute or two." \
    "sudo rm -rf /usr/share/plymouth/themes/$name" "sudo cp -r $theme_src /usr/share/plymouth/themes/$name" "sudo plymouth-set-default-theme -R $name" \
    "sudo tee $PLYMOUTH_RETAIN_DROPIN"; then
    ui_message "Boot screen not changed" "No administrator password was accepted, so Setup skipped the boot screen." \
      "Everything else is installed. Run ./install.sh --components=plymouth to try again."
    return
  fi
  run sudo rm -rf "/usr/share/plymouth/themes/$name"
  run sudo cp -r "$theme_src" "/usr/share/plymouth/themes/$name"
  show_copy "$theme_src" "/usr/share/plymouth/themes/$name"
  ui_status "Rebuilding the boot image; this takes a minute or two..."
  run sudo plymouth-set-default-theme -R "$name" >>"$SETUP_LOG" 2>&1
  retain_boot_screen
  [[ "$current" == Chicago95* ]] || record "plymouth:$current" # uninstall returns to the theme that was there before Setup's
  [ -z "$build" ] || run rm -rf "$build"
}

plasma_script() { gdbus call --session --dest org.kde.plasmashell --object-path /PlasmaShell --method org.kde.PlasmaShell.evaluateScript "$1"; }

offer_taskbar() { # replaces the panels with the Chicago95 taskbar once the user agrees; skipped when it is already there
  [ "$SETUP_IN_PLASMA" = 1 ] && [ "${SETUP_DRY_RUN:-0}" = 0 ] || return 0
  local attempt
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    plasma_script 'print("ready")' >/dev/null 2>&1 && break
    sleep 1
  done
  if [[ "$(plasma_script 'print(panels().some(panel => panel.widgets().some(widget => widget.type == "org.chicago95.tasks")))' 2>/dev/null)" == *true* ]]; then
    ui_status "The Chicago95 taskbar is already in place"
    return 0
  fi
  ui_card "Build the taskbar" \
    "Setup can replace your Plasma panels with the Chicago95 taskbar: Start button," \
    "Quick Launch, task list and tray, $PANEL_HEIGHT pixels high, along the bottom of the screen." "" \
    "Your current panel layout is saved first, and ./uninstall.sh puts it back." "" \
    "Setup will run in Plasma's scripting interface:" \
    "   remove every panel, then ~/.local/share/chicago95/panel-layout.js"
  ui_confirm "Build the taskbar now?" || return 0
  backup ~/.config/plasma-org.kde.plasma.desktop-appletsrc
  plasma_script "panels().forEach(panel => panel.remove());
$(panel_layout_script ~/.local/share/chicago95/panel-layout.js)" >>"$SETUP_LOG" 2>&1
}

only_digits() { printf '%s' "${1//[!0-9]/}"; }

panel_hiding() { # the panel.hiding value the saved choices ask for; nothing when none was saved
  if [ "${SETUP_TASKBAR_AUTOHIDE:-}" = yes ]; then
    echo autohide
  elif [ "${SETUP_TASKBAR_ON_TOP:-}" = no ]; then
    echo windowsgobelow
  elif [ -n "${SETUP_TASKBAR_AUTOHIDE:-}${SETUP_TASKBAR_ON_TOP:-}" ]; then
    echo none
  fi
}

clock_hours() { case "${SETUP_CLOCK_HOURS:-}" in locale | 12 | 24) printf '%s' "$SETUP_CLOCK_HOURS" ;; esac }

panel_layout_script() { # panel_layout_script <layout file>   the layout with this run's height, look and task button width
  local width hiding hours edits=(-e "s/^panel.height = 28;/panel.height = $PANEL_HEIGHT;/" -e "s/^const look = \"1995\";/const look = \"$SETUP_START_MENU_STYLE\";/" -e "s/^const taskbarStyle = \"classic\";/const taskbarStyle = \"$SETUP_TASKBAR_STYLE\";/" -e "s/^const bevel = \"1995\";/const bevel = \"${SETUP_BEVEL:-1995}\";/")
  width=$(only_digits "${SETUP_TASK_BUTTON_WIDTH:-}")
  edits+=(-e "s/^tasks.writeConfig(\"referenceDpi\", 96);/tasks.writeConfig(\"referenceDpi\", ${SETUP_DPI:-96});/")
  [ -n "$width" ] && edits+=(-e "/^tasks.writeConfig(\"look\", look);/a tasks.writeConfig(\"maxButtonWidth\", $width);")
  if [ -n "${SETUP_LAUNCHERS+x}" ]; then
    edits+=(-e "/^tasks.writeConfig(\"look\", look);/a tasks.writeConfig(\"launchers\", $(js_list "$SETUP_LAUNCHERS"));")
  elif [ "$SETUP_TASKBAR_STYLE" = aero ]; then
    edits+=(-e "/^tasks.writeConfig(\"look\", look);/a tasks.writeConfig(\"launchers\", $(quick_launch_defaults));")
  fi
  hiding=$(panel_hiding)
  [ -n "$hiding" ] && edits+=(-e "s/^panel.hiding = \"none\";/panel.hiding = \"$hiding\";/")
  hours=$(clock_hours)
  if [ "${SETUP_CLOCK_SHOW:-}" = no ]; then
    edits+=(-e '/^const clock = panel.addWidget/,/^clock.writeConfig("bevel"/d')
  elif [ -n "$hours" ]; then edits+=(-e "/^clock.writeConfig(\"look\", look);/a clock.writeConfig(\"hourFormat\", \"$hours\");"); fi
  sed "${edits[@]}" "$1"
}

js_string() { python3 -c 'import json, sys; print(json.dumps(sys.argv[1]))' "$1"; }
js_list() { python3 -c 'import json, sys; print(json.dumps([entry for entry in sys.argv[1].split(",") if entry]))' "$1"; }

apply_taskbar() { python_applier taskbar; }

quick_launch_defaults() { # the task list's default Quick Launch programs, from its settings file, as a JS list
  sed -n '/name="launchers"/,/<\/entry>/s/.*<default>\(.*\)<\/default>.*/\1/p' "$REPO/plasmoids/org.chicago95.tasks/contents/config/main.xml" |
    python3 -c 'import json, sys
pins = sys.stdin.read().strip().split(",")
if sys.argv[1] == "aero":
    pins = [pin for pin in pins if pin != "applications:chicago95-showdesktop.desktop"]
print(json.dumps(pins))' "$SETUP_TASKBAR_STYLE"
}

step_background() { python_applier background; }

step_desktop() { python_applier desktop_icons; }

face_hex() { # the look's face as #RRGGBB (SETUP_FACE is "r,g,b" for 2000, empty otherwise)
  local red green blue
  IFS=, read -r red green blue <<<"${SETUP_FACE:-192,192,192}"
  printf '#%02X%02X%02X' "$red" "$green" "$blue"
}

step_switcher() { # Alt+Tab: our KWin switcher layout, chosen in kwinrc
  local dir=~/.local/share/kwin/tabbox/chicago95
  put_tree "$REPO/kwin-tabbox/chicago95" "$dir"
  [ "$SETUP_START_MENU_STYLE" = luna ] && put_tree "$REPO/luna/kwin-tabbox" "$dir/contents/ui/luna"
  select_switcher "$dir"
}

select_switcher() { python_applier switcher_settings; }

restart_start_menu() { python_applier start_menu_restart; }

offer_logout() { # some parts start only with a new session; never logs out without a yes
  [ "$SETUP_IN_PLASMA" = 1 ] && [ "${SETUP_DRY_RUN:-0}" = 0 ] && [ "${SETUP_YES:-0}" = 0 ] || return 0
  ui_card "Log out to finish" \
    "A few parts start only with a new session: the Start menu, Clippy and the" \
    "notification popups (autostart entries), and the settings in ~/.config/environment.d." "" \
    "Save your work in other programs before you log out."
  ui_confirm "Log out now?" || return 0
  ui_restore
  gdbus call --session --dest org.kde.Shutdown --object-path /Shutdown --method org.kde.Shutdown.logout >/dev/null
  exit 0
}

step_firefox() {
  [ -n "$SETUP_FIREFOX_PROFILE" ] || {
    ui_status "No default Firefox profile found; skipping"
    return
  }
  local target="$SETUP_FIREFOX_PROFILE/user.js"
  backup "$target"
  if [ "${SETUP_DRY_RUN:-0}" != 1 ]; then
    {
      [ -f "$target" ] && grep -vxF -f "$REPO/config/firefox-user.js" "$target"
      cat "$REPO/config/firefox-user.js"
    } >"$target.chicago95" && mv "$target.chicago95" "$target"
  fi
  record "$target"
  show_copy "$REPO/config/firefox-user.js" "$target"
  theme_firefox
}

# Firefox draws its own controls whatever the GTK theme; a sheet of the look's (lib/firefox_chrome.py), imported first
# thing from the profile's userChrome.css, where an @import is valid ahead of the user's own rules. Luna takes it out.
theme_firefox() { python_applier firefox; }

# Runs before the components, so the login screen copies the repaired font too.
fix_font_spaces() { # MS W98 UI Regular's no-break space is a third as wide as its space; editors draw spaces with it
  local family="${SETUP_FONT:-MS W98 UI}" file
  while IFS= read -r file; do
    backup "$file"
    run python3 "$REPO/setup/fix-font-spaces.py" "$file" >>"$SETUP_LOG"
    show_copy "(no-break space made as wide as space)" "$file"
  done < <(fc-list -f '%{file}\n' "$family" 2>/dev/null | grep "^$HOME/" | sort)
  run fc-cache -f "$HOME/.local/share/fonts"
}

APP_FONT_KEYS=(font menuFont toolBarFont smallestReadableFont)

PIXEL_FONT_RULE=~/.config/fontconfig/conf.d/60-chicago95-pixel-font.conf

# Tahoma is smoothed text: the pixel font's no-smoothing rule would spoil it.
apply_luna_gtk_font() {
  set_gtk_font "Tahoma 8"
  backup "$PIXEL_FONT_RULE"
  run rm -f "$PIXEL_FONT_RULE"
}

# Luna's text is Tahoma, which no free font matches; without it fontconfig falls back to DejaVu Sans Condensed.
warn_without_tahoma() {
  fc-match Tahoma 2>/dev/null | grep -i tahoma >/dev/null && return 0
  ui_status "Tahoma is not installed: Luna text falls back to DejaVu Sans Condensed. Install Wine's Tahoma (wine-tahoma-fonts) or put tahoma.ttf in ~/.local/share/fonts, then log out and in."
}

# The Start button's "start" is Franklin Gothic Medium; Libre Franklin (Impallari Type, SIL Open Font License) is
# its open counterpart, fetched from Google Fonts' repository the way the icon sets are cloned.
LIBRE_FRANKLIN_URL=https://raw.githubusercontent.com/google/fonts/main/ofl/librefranklin
fetch_libre_franklin() {
  local folder=~/.local/share/fonts/LibreFranklin name source
  # Not grep -q: it leaves at its first match, the list's writer dies on the closed pipe, and pipefail fails the check.
  fc-list : family 2>/dev/null | grep -i "Libre Franklin" >/dev/null && return 0
  ui_status "Downloading Libre Franklin (the Start button's lettering)..."
  run mkdir -p "$folder"
  for name in "LibreFranklin-Variable.ttf=LibreFranklin%5Bwght%5D.ttf" "LibreFranklin-Italic-Variable.ttf=LibreFranklin-Italic%5Bwght%5D.ttf" "OFL.txt=OFL.txt"; do
    source="${name#*=}"
    run curl -fsSL -o "$folder/${name%%=*}" "$LIBRE_FRANKLIN_URL/$source" >>"$SETUP_LOG" 2>&1 || {
      ui_status "Libre Franklin could not be downloaded; the Start button keeps the system's sans serif"
      return 0
    }
    record "$folder/${name%%=*}"
  done
  run fc-cache -f ~/.local/share/fonts >/dev/null 2>&1 || true
}

step_luna_fonts() {
  local key
  put_file "$REPO/luna/fontconfig/61-chicago95-luna-fonts.conf" ~/.config/fontconfig/conf.d/61-chicago95-luna-fonts.conf
  warn_without_tahoma
  fetch_libre_franklin
  [ "${SETUP_FONT_SCOPE:-everywhere}" = none ] && return 0
  [ "${SETUP_FONT_SCOPE:-everywhere}" = everywhere ] && for key in "${APP_FONT_KEYS[@]}"; do kconf kdeglobals General "$key" "Tahoma,8,-1,5,50,0,0,0,0,0"; done
  widget_style_is_luna && [ "${SETUP_FONT_SCOPE:-everywhere}" = everywhere ] && apply_luna_gtk_font
  kconf kdeglobals WM activeFont "Trebuchet MS,10,-1,5,75,0,0,0,0,0"
  return 0
}

# A pixel font: drawn without smoothing at 11px and 22px, its edges stay as sharp as the originals' text. GTK 4 asks
# fontconfig with the logical size and draws at the screen's scale, so on a fractional scale those bands would come out
# jagged (11px drawn at 16.5): there the rule smooths every size.
install_pixel_font_rule() {
  put_file "$REPO/config/fontconfig/60-chicago95-pixel-font.conf" "$PIXEL_FONT_RULE"
  case "${SETUP_SCALE:-1}" in
  1 | 1.0 | 2 | 2.0 | 3 | 3.0) ;;
  *) [ "${SETUP_DRY_RUN:-0}" = 1 ] || sed -i '/<!-- whole pixels BEGIN -->/,/<!-- whole pixels END -->/d' "$PIXEL_FONT_RULE" ;;
  esac
}

step_fonts() { # SETUP_FONT_SCOPE: everywhere (all programs), desktop (title bars only) or none
  wants_luna && {
    step_luna_fonts
    return
  }
  local family="${SETUP_FONT:-MS W98 UI}" key app_size=9 caption_size=8 native
  if [ "$SETUP_WIDGET_STYLE" = aero ]; then
    if [ "${SETUP_FONT_SCOPE:-everywhere}" != none ]; then
      put_tree "$SDDM_THEME_SRC/fonts/selawik" "$HOME/.local/share/fonts/Chicago95/Selawik"
      put_file "$REPO/aero/fonts/58-chicago95-segoe.conf" "${XDG_CONFIG_HOME:-$HOME/.config}/fontconfig/conf.d/58-chicago95-segoe.conf"
      run fc-cache "$HOME/.local/share/fonts/Chicago95/Selawik"
    fi
    if [ "$family" = "MS W98 UI" ] && [ -z "${OPT_FONT:-}" ]; then
      family=$(fc-match -f '%{family[0]}' 'Segoe UI,Selawik,Noto Sans')
    fi
    case "${SETUP_FONT_SCOPE:-everywhere}" in
    everywhere)
      for key in "${APP_FONT_KEYS[@]}"; do kconf kdeglobals General "$key" "$family,9,-1,5,50,0,0,0,0,0"; done
      set_gtk_font "$family 9"
      ;;
    esac
    [ "${SETUP_FONT_SCOPE:-everywhere}" = none ] || kconf kdeglobals WM activeFont "$family,9,-1,5,50,0,0,0,0,0"
    return 0
  fi
  if [[ "$SETUP_WIDGET_STYLE" == classic && "$family" == "MS W98 UI" && -z "${OPT_FONT:-}" ]]; then
    case "${SETUP_START_MENU_STYLE:-}" in
      1995|1998)
        case "${SETUP_DPI:-96}" in
          96) native="Chicago95 Windows ${SETUP_START_MENU_STYLE:2}" ;;
          120) native="Chicago95 Windows ${SETUP_START_MENU_STYLE:2} 120 DPI" ;;
        esac
        ;;
      2000) native="Chicago95 Windows 2000 Tahoma" ;;
      2001) native="Tahoma" ;;
    esac
    if [ -n "${native:-}" ] && fc-list -f '%{family[0]}\n' "$native" | grep -Fx "$native" >/dev/null; then
      family="$native"
      # The 8-point GDI raster font used an 11px logical em at 96 DPI.
      app_size=8.25
      caption_size="$app_size"
    fi
  fi
  if ! fc-list : family | grep -i "$family" >/dev/null; then
    ui_status "Font '$family' not installed; UI text keeps your current font until it is in ~/.local/share/fonts"
    return
  fi
  case "${SETUP_FONT_SCOPE:-everywhere}" in
  everywhere)
    kconf kdeglobals General font "$family,$app_size,-1,5,50,0,0,0,0,0"
    kconf kdeglobals General menuFont "$family,$app_size,-1,5,50,0,0,0,0,0"
    kconf kdeglobals General toolBarFont "$family,$app_size,-1,5,50,0,0,0,0,0"
    kconf kdeglobals General smallestReadableFont "$family,8,-1,5,50,0,0,0,0,0"
    set_gtk_font "$family $app_size"
    ;;
  *) # A reinstall with a narrower scope takes back what an earlier "everywhere" set.
    for key in "${APP_FONT_KEYS[@]}"; do
      installed_by_setup "kconf:kdeglobals:General:$key" && run kwriteconfig6 --file kdeglobals --group General --key "$key" --delete
    done
    ;;
  esac
  case "${SETUP_FONT_SCOPE:-everywhere}" in
  none) installed_by_setup "kconf:kdeglobals:WM:activeFont" && run kwriteconfig6 --file kdeglobals --group WM --key activeFont --delete ;;
  *) kconf kdeglobals WM activeFont "$family,$caption_size,-1,5,75,0,0,0,0,0" ;;
  esac
  [ "${SETUP_FONT_SCOPE:-everywhere}" = none ] || install_pixel_font_rule
  return 0
}

finish_session() { python_applier finish; }

# --- appliers: what one changed choice needs (lib/chicago95apply.py maps the choices to them). An applier sets values
# and reloads what shows them. Most are lib/chicago95appliers.py's; these are the ones that stay with the steps they
# share most with. The components' files are their steps' to copy: an applier copies only the files of a variant
# chosen for the first time, and leaves a component that was never installed alone.

# apply_choices <applier>...   install.sh --apply. With APPLY_REPORT, lib/chicago95apply.py ran it for some of its
# appliers: what they leave for the session goes there, and the session is left for it to reload.
apply_choices() {
  local applier
  COPIED=0
  TO_COPY=0
  for applier in "$@"; do
    if declare -F "applier_$applier" >/dev/null; then
      "applier_$applier"
    else
      python_applier "$applier" || {
        [ $? != 2 ] || setup_abort "Apply does not know \"$applier\"."
        setup_abort "Could not apply \"$applier\"; the log has the details: $SETUP_LOG"
      }
    fi
  done
  if [ -n "${APPLY_REPORT:-}" ]; then
    local name
    for name in SHELL_CHANGED GLASS_EFFECT_CHANGED AERO_FRAME_CHANGED CAPTION_RELOAD TASKBAR_CHANGED START_MENU_CHANGED \
      SHELL_MENU_DONE LOOK_STEP_DONE SETUP_START_LOGO SETUP_LOGIN_LOGO; do
      [ -z "${!name:-}" ] || printf '%s=%s\n' "$name" "${!name}"
    done >"$APPLY_REPORT"
    return 0
  fi
  finish_session
  # After the shell is back: the applets take their options from the one that is running.
  [ "${TASKBAR_CHANGED:-0}" = 0 ] || apply_taskbar
  [ "${START_MENU_CHANGED:-0}" = 0 ] || restart_start_menu
}

# The look's appliers stand on its files. Where the look was never installed, its step installs and sets all of it,
# once, and the others leave it at that.
applier_look() {
  [ "${SETUP_DRY_RUN:-0}" = 0 ] && [ ! -e ~/.local/share/aurorae/themes/Chicago95 ] || return 0
  step_look
  LOOK_STEP_DONE=1
}

look_step_done() { [ "${LOOK_STEP_DONE:-0}" = 1 ]; }

applier_widgets() {
  ! look_step_done || return 0
  apply_shell_menu
  apply_widget_themes
  kconf kdeglobals General AccentColor --delete
  if [ "$SETUP_WIDGET_STYLE" = aero ] || [ "$(kreadconfig6 --file kcminputrc --group Mouse --key cursorTheme 2>/dev/null)" = Windows-7-Aero-Cursors_Default ]; then
    apply_pointer_theme
  fi
}

applier_decoration() {
  ! look_step_done || return 0
  [ "$SETUP_DECORATION" != luna ] || [ -d ~/.local/share/aurorae/themes/Chicago95Luna ] || install_luna_theme_files
  apply_decoration
  kconf kwinrc org.kde.kdecoration2 BorderSize Normal
}

applier_plasma_style() {
  ! look_step_done || return 0
  case "$SETUP_TASKBAR_STYLE" in
  luna) [ -d ~/.local/share/plasma/desktoptheme/Chicago95Luna ] || install_luna_theme_files ;;
  aero)
    [ -d "$AERO_PLASMA_STYLE" ] || put_tree "$REPO/aero/plasma-style/theme" "$AERO_PLASMA_STYLE"
    [ -s "$AERO_ORB_LOGO" ] || draw_aero_orb_logo
    ;;
  esac
  apply_plasma_style
}

applier_icons() {
  local KEEP_INSTALLED=1
  apply_icon_set || setup_abort "Could not apply the selected icon theme."
}

applier_gtk_title_bars() {
  ! look_step_done || return 0
  write_title_bar_css
}

applier_fonts() {
  fix_font_spaces
  step_fonts
}

applier_live_blur() { ensure_live_blur; }

applier_aero_blur() { # the wobble chosen now, not the one KWin runs, decides the Aero glass
  [ -n "${SETUP_ANIM_WOBBLY:-}" ] && current_aero_decoration >/dev/null || return 0
  local COMPONENTS=animations
  select_aero_blur
}

applier_explorer() { step_explorer; }

applier_explorer_style() { # the file manager's address bar and navigation in the widgets' style, where Setup configured one
  ! installed_by_setup ~/.local/share/kxmlgui6/dolphin/dolphinui.rc || step_explorer
}

applier_lockscreen() { step_lockscreen; }

applier_splash() { step_splash; }

applier_plymouth() { step_plymouth; }

applier_plymouth_look() { # the classic boot screen is the look's own: Windows 98's, or Chicago95's
  [ "$(boot_style)" = classic ] || return 0
  local wanted=Chicago95 current
  [ "${SETUP_LOOK:-}" != 1998 ] || wanted=Chicago95-98
  current=$(plymouth-set-default-theme 2>/dev/null || true)
  [[ "$current" == Chicago95* ]] && [ "$current" != "$wanted" ] || return 0
  step_plymouth
}

applier_sddm() { step_sddm; }

applier_sddm_look() { # only the 2001 look paints the login screen's desktop black
  local wanted=""
  [ -f "$SDDM_THEME_DIR/theme.conf" ] || return 0
  [ "${SETUP_LOOK:-}" != 2001 ] || wanted='#000000'
  [ "$(sed -n 's/^desktopColor=//p' "$SDDM_THEME_DIR/theme.conf")" = "$wanted" ] || step_sddm
}
