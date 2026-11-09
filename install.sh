#!/usr/bin/env bash
# Chicago95 for Plasma: Setup.
#
#   ./install.sh                 interactive, Windows 95 Setup look
#   ./install.sh --yes           every default component, no questions
#   ./install.sh --components base,look,taskbar,startmenu
#   ./install.sh --dry-run       show what would change, touch nothing
#   ./install.sh --plain         no full-screen UI (logs, CI, screen readers)
#   Options (asked interactively, or given as flags):
#     --screen=2560x1440@1.5  --panel=28  --explorer=thunar|dolphin  --saver=maze
#     --idle=5  --cursor=48  --clippy=yes|no  --font="MS W98 UI"
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SETUP_YES=0; SETUP_DRY_RUN=0; UI_MODE=screen; WANTED=""
SETUP_LOG="${TMPDIR:-/tmp}/chicago95-setup-$(date +%Y%m%d-%H%M%S).log"

for arg in "$@"; do
    case "$arg" in
        --yes|-y) SETUP_YES=1;;
        --dry-run) SETUP_DRY_RUN=1;;
        --plain) UI_MODE=plain;;
        --components=*) WANTED="${arg#*=}";;
        --components) ;;  # value follows
        --screen=*) OPT_SCREEN="${arg#*=}";;
        --panel=*) OPT_PANEL="${arg#*=}";;
        --explorer=*) OPT_EXPLORER="${arg#*=}";;
        --saver=*) OPT_SAVER="${arg#*=}";;
        --idle=*) OPT_IDLE="${arg#*=}";;
        --cursor=*) OPT_CURSOR="${arg#*=}";;
        --clippy=*) OPT_CLIPPY="${arg#*=}";;
        --font=*) OPT_FONT="${arg#*=}";;
        --help|-h) sed -n '2,12p' "$0"; exit 0;;
        *) [ -z "$WANTED" ] && [[ "$arg" != --* ]] && WANTED="$arg";;
    esac
done

. "$REPO/setup/ui.sh"
. "$REPO/setup/detect.sh"
. "$REPO/setup/steps.sh"

ui_init "$UI_MODE"
ui_set_steps "Collecting information about your computer" "Selecting components" "Copying files" "Finishing Setup"

# ---- 1. collect -------------------------------------------------------------
ui_step_start 0
detect_all
ui_message "Welcome to Setup" \
    "Setup prepares Chicago95 for KDE Plasma on this computer." "" \
    "$(detect_summary | sed -n 1p)" "$(detect_summary | sed -n 2p)" "$(detect_summary | sed -n 3p)" \
    "$(detect_summary | sed -n 4p)" "$(detect_summary | sed -n 5p)" "$(detect_summary | sed -n 6p)" \
    "$(detect_summary | sed -n 7p)" "$(detect_summary | sed -n 8p)" "" \
    "Setup log: $SETUP_LOG"
detect_summary >"$SETUP_LOG"

if [ -z "${SETUP_PLASMA_VERSION:-}" ]; then
    ui_message "Setup cannot continue" "plasmashell was not found. This is a KDE Plasma 6 theme." ; exit 1
fi
if [ "${SETUP_PLASMA_MAJOR:-0}" -lt 6 ]; then
    ui_message "Setup cannot continue" "Plasma $SETUP_PLASMA_VERSION found; Plasma 6 is required."; exit 1
fi
if [ -n "$SETUP_PY_MISSING" ]; then
    ui_message "Missing packages" "The Start menu, notifications and Clippy need:" "   $SETUP_PY_MISSING" "" \
        "Install them with:" "   $(detect_install_hint)" "" "Those components will be skipped if you continue now."
fi
ui_step_done 0

# ---- 2. components ----------------------------------------------------------
ui_step_start 1
py_ok=1; [ -n "$SETUP_PY_MISSING" ] && py_ok=0
if [ -n "$WANTED" ]; then
    COMPONENTS=$(printf '%s' "$WANTED" | tr ',' ' ')
else
    COMPONENTS=$(ui_pick_components \
        "base:Chicago95 base theme (GTK, icons, cursors, sounds):1" \
        "look:Window decoration, Plasma style, colours, widget style:1" \
        "taskbar:Taskbar plasmoids (Start button, grips, tray frame):1" \
        "startmenu:Start menu and Shut Down dialog:$py_ok" \
        "notifications:Windows 95 notifications:$py_ok" \
        "clippy:Office Assistant:$py_ok" \
        "extras:System Properties, Device Manager, Dial-Up Networking, login chime:$py_ok" \
        "screensaver:Screensaver (XScreenSaver hacks):$([ -n "$SETUP_HACK_DIR" ] && echo 1 || echo 0)" \
        "winamp:Winamp (qmmp launch entries and window rule):$SETUP_HAS_QMMP" \
        "explorer:Explorer (Thunar settings, GTK CSS, Dolphin toolbar):$SETUP_HAS_THUNAR" \
        "lockscreen:Lock screen:1" \
        "splash:Splash screen:1" \
        "firefox:Firefox system colours (user.js):$([ -n "$SETUP_FIREFOX_PROFILE" ] && echo 1 || echo 0)")
fi
printf 'Components: %s\n' "$COMPONENTS" >>"$SETUP_LOG"

# Values that differ between machines. Flags pre-fill them; the screen lets the user edit.
while IFS='=' read -r name value; do
    case $name in
        screen) [[ "$value" =~ ^([0-9]+)x([0-9]+)@([0-9.]+)$ ]] && { SETUP_WIDTH=${BASH_REMATCH[1]}; SETUP_HEIGHT=${BASH_REMATCH[2]}; SETUP_SCALE=${BASH_REMATCH[3]}; };;
        panel) SETUP_PANEL=$value;;
        saver) SETUP_SAVER=$value;;
        idle) SETUP_IDLE_MIN=$value;;
        explorer) SETUP_EXPLORER=$value;;
        cursor) SETUP_CURSOR=$value;;
        clippy) SETUP_CLIPPY_AUTOSTART=$value;;
        font) SETUP_FONT=$value;;
    esac
done < <(ui_pick_options \
    "screen|Screen size and scale (WxH@scale)|${OPT_SCREEN:-${SETUP_WIDTH}x${SETUP_HEIGHT}@${SETUP_SCALE}}" \
    "panel|Taskbar height in pixels (Win95 is 28)|${OPT_PANEL:-28}" \
    "explorer|File manager for Explorer (thunar/dolphin)|${OPT_EXPLORER:-$([ "$SETUP_HAS_THUNAR" = 1 ] && echo thunar || echo dolphin)}" \
    "saver|Screensaver hack (pipes, maze, flyingtoasters, bsod...)|${OPT_SAVER:-deepstars}" \
    "idle|Screensaver after (minutes)|${OPT_IDLE:-5}" \
    "cursor|Cursor size (24/32/48)|${OPT_CURSOR:-$(awk -v s="$SETUP_SCALE" 'BEGIN{print (s>1)?48:32}')}" \
    "clippy|Office Assistant at login (yes/no)|${OPT_CLIPPY:-yes}" \
    "font|UI font family|${OPT_FONT:-MS W98 UI}")
SETUP_DPI=$(awk -v s="$SETUP_SCALE" 'BEGIN{printf "%d", 96*s + 0.5}')
PANEL_HEIGHT=${SETUP_PANEL:-28}
printf 'Options: screen=%sx%s@%s panel=%s explorer=%s saver=%s idle=%s cursor=%s clippy=%s font=%s\n' \
    "$SETUP_WIDTH" "$SETUP_HEIGHT" "$SETUP_SCALE" "$PANEL_HEIGHT" "$SETUP_EXPLORER" "$SETUP_SAVER" "$SETUP_IDLE_MIN" "$SETUP_CURSOR" "$SETUP_CLIPPY_AUTOSTART" "$SETUP_FONT" >>"$SETUP_LOG"
ui_step_done 1

# ---- 3. copy ----------------------------------------------------------------
ui_step_start 2
TO_COPY=0; COPIED=0
for component in $COMPONENTS; do
    case $component in
        base) TO_COPY=$((TO_COPY + 1));;
        look) TO_COPY=$((TO_COPY + $(count_files "$REPO/aurorae/theme" "$REPO/plasma-style/theme") + 6));;
        taskbar) TO_COPY=$((TO_COPY + $(count_files "$REPO"/plasmoids/org.chicago95.*) + 3));;
        startmenu) TO_COPY=$((TO_COPY + 5 + $(count_files "$REPO/data/qml") + 4));;
        notifications) TO_COPY=$((TO_COPY + $(count_files "$REPO/kwin-effects") + 3));;
        clippy) TO_COPY=$((TO_COPY + $(count_files "$REPO/data/clippy") + 3));;
        extras) TO_COPY=$((TO_COPY + $(count_files "$REPO/data/sounds") + 5));;
        screensaver) TO_COPY=$((TO_COPY + 2));;
        winamp) TO_COPY=$((TO_COPY + 1));;
        explorer) TO_COPY=$((TO_COPY + 2));;
        lockscreen) TO_COPY=$((TO_COPY + $(count_files "$REPO/lockscreen")));;
        splash) TO_COPY=$((TO_COPY + $(count_files "$REPO/splash")));;
        firefox) TO_COPY=$((TO_COPY + 1));;
    esac
done
[ "$SETUP_DRY_RUN" = 1 ] || { mkdir -p "$STATE_DIR"; : >"$MANIFEST"; }
for component in $COMPONENTS; do
    case $component in
        base|look|taskbar|startmenu|notifications|clippy|extras|screensaver|winamp|explorer|lockscreen|splash|firefox) "step_$component";;
        *) printf 'unknown component: %s\n' "$component" >>"$SETUP_LOG";;
    esac
done
step_fonts
ui_step_done 2

# ---- 4. finish --------------------------------------------------------------
ui_step_start 3
ui_status "Reloading Plasma..."
finish_session
ui_step_done 3

lines=("Setup has finished installing Chicago95 for Plasma." "")
[ "$SETUP_DRY_RUN" = 1 ] && lines=("Dry run: nothing was changed. The log lists every action:" "   $SETUP_LOG" "")
lines+=("Next:" \
    "  1. Remove the stock panel, then run ~/.local/share/chicago95/panel-layout.js" \
    "     in the Plasma scripting console to build the taskbar." \
    "  2. Log out and back in once, for autostart entries and environment.d." \
    "  3. Plymouth and SDDM need root; see the README for the two commands." "" \
    "Backups of every file Setup replaced: $BACKUP_DIR" \
    "To remove everything: ./uninstall.sh")
ui_message "Setup Complete" "${lines[@]}"
ui_restore
