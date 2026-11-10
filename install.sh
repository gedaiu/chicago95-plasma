#!/usr/bin/env bash
# Chicago95 for Plasma: Setup.
#
#   ./install.sh                 interactive, Chicago95 Setup look
#   ./install.sh --yes           every default component, no questions
#   ./install.sh --components base,look,taskbar,startmenu
#   ./install.sh --dry-run       show what would change, touch nothing
#   ./install.sh --plain         no full-screen UI (logs, CI, screen readers)
#   Options (asked interactively, or given as flags):
#     --screen=2560x1440@1.5  --panel=28  --explorer=thunar|dolphin  --saver=maze
#     --idle=5  --cursor=48  --clippy=yes|no  --font="MS W98 UI"  --font-scope=everywhere|desktop|none
#     --start-text=Start  --start-logo=flag|penguin|/path/to/image  --banner-text=Chicago95
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
        --font-scope=*) OPT_FONT_SCOPE="${arg#*=}";;
        --start-text=*) OPT_START_TEXT="${arg#*=}";;
        --start-logo=*) OPT_START_LOGO="${arg#*=}";;
        --banner-text=*) OPT_BANNER_TEXT="${arg#*=}";;
        --help|-h) sed -n '2,12p' "$0"; exit 0;;
        *) [ -z "$WANTED" ] && [[ "$arg" != --* ]] && WANTED="$arg";;
    esac
done

. "$REPO/setup/ui.sh"
. "$REPO/setup/detect.sh"
. "$REPO/setup/steps.sh"

ui_init "$UI_MODE"
ui_set_steps "Collecting information about your computer" "Selecting components" "Copying files" "Finishing Setup"

# Shows the reason on the Setup screen, then leaves it in the terminal once the screen is gone.
setup_abort() {
    ui_message "Setup cannot continue" "$@"
    ui_restore
    [ "$UI_PLAIN" = 1 ] || printf '%s\n' "Setup cannot continue." "$@" >&2
    exit 1
}

ui_intro

if [ -s "$MANIFEST" ] && [ "$SETUP_DRY_RUN" = 0 ]; then
    ui_card "Chicago95 is already installed" \
        "Setup found an earlier installation on this computer." "" \
        "  1. Reinstall: copy the files again. Your original files, saved the first" \
        "     time Setup ran, stay saved, so uninstalling still brings them back." \
        "  2. Uninstall: remove Chicago95 and restore your original files." \
        "  3. Exit Setup without changing anything."
    case "$(ui_ask "Type 1, 2 or 3 and press ENTER" 1)" in
        2) ui_restore; exec "$REPO/uninstall.sh";;
        3) ui_restore; exit 0;;
    esac
fi

# ui_pick_text <prompt> <default> <choice>...   a number picks a choice, anything else is taken as typed
ui_pick_text() {
    local prompt="$1" default="$2" answer; shift 2
    local choices=("$@")
    answer=$(ui_ask "$prompt" "$default")
    if [[ "$answer" =~ ^[0-9]+$ ]] && [ "$answer" -ge 1 ] && [ "$answer" -le ${#choices[@]} ]; then
        printf '%s' "${choices[$((answer - 1))]}"
    else
        printf '%s' "$answer"
    fi
}

choose_start_menu() {
    local logo
    ui_card "Start button and menu" \
        "Choose what the Start button and the Start menu's side banner show." \
        "Type a number for one of the suggestions, or type your own." "" \
        "  Button text:  1. Start    2. Linux    or your own text" \
        "  Button logo:  1. Classic flag    2. Penguin    3. Your own image (Setup asks for the file)" \
        "  Banner text:  1. Chicago95    2. Linux    or your own text" "" \
        "Press ENTER to keep the current choice. The logo you pick is copied to" \
        "   $START_LOGO_FILE" \
        "Replace that file and log out to change the logo later; right-click the Start" \
        "button and choose Configure to change its text."
    [ -n "${OPT_START_TEXT:-}" ] || SETUP_START_TEXT=$(ui_pick_text "Button text" "$SETUP_START_TEXT" Start Linux)
    if [ -z "${OPT_START_LOGO:-}" ]; then
        logo=$(ui_pick_text "Button logo" "$SETUP_START_LOGO" flag penguin custom)
        case "$logo" in [Cc]lassic*|[Ff]lag) logo=flag;; [Pp]enguin) logo=penguin;; [Cc]ustom) logo="";; esac
        while [ "$logo" != flag ] && [ "$logo" != penguin ] && [ ! -f "${logo/#\~/$HOME}" ]; do
            [ -n "$logo" ] && ui_status "No image at $logo"
            logo=$(ui_ask "Image file for the logo (PNG or SVG, full path; 1 = Classic flag)" "")
            [ "$logo" = 1 ] && logo=flag
        done
        SETUP_START_LOGO=${logo/#\~/$HOME}
    fi
    [ -n "${OPT_BANNER_TEXT:-}" ] || SETUP_BANNER_TEXT=$(ui_pick_text "Banner text" "$SETUP_BANNER_TEXT" Chicago95 Linux)
    return 0
}

choose_font_scope() {
    ui_card "Where should the classic font be used?" \
        "The Start menu, notifications, Clippy, the Shut Down dialog and the login screen" \
        "always use ${SETUP_FONT:-MS W98 UI}. For everything else:" "" \
        "  1. Everywhere: all programs, including Firefox's menus and web pages that" \
        "     ask for the system font." \
        "  2. Desktop only: window title bars. Programs and web pages keep your font." \
        "  3. Nowhere: Setup leaves your font settings alone."
    case "$(ui_ask "Type 1, 2 or 3 and press ENTER" 1)" in
        2) SETUP_FONT_SCOPE=desktop;;
        3) SETUP_FONT_SCOPE=none;;
        *) SETUP_FONT_SCOPE=everywhere;;
    esac
}

# Lists the installed savers; "P" and a number previews one full screen with the real screensaver.
choose_screensaver() {
    local names=() labels=() name label answer index lock_minutes
    while IFS=$'\t' read -r name label; do names+=("$name"); labels+=("$label"); done \
        < <(python3 "$REPO/bin/chicago95-screensaver" --list 2>/dev/null)
    [ ${#names[@]} -gt 0 ] || return 0
    lock_minutes=$(kreadconfig6 --file kscreenlockerrc --group Daemon --key Timeout 2>/dev/null); lock_minutes=${lock_minutes:-5}
    while :; do
        local lines=("It starts after ${SETUP_IDLE_MIN:-5} minutes without input; your screen locks after $lock_minutes." "")
        for index in "${!names[@]}"; do
            lines+=("$(printf '  %d. [%s] %s' $((index + 1)) "$([ "${names[$index]}" = "$SETUP_SAVER" ] && echo X || echo ' ')" "${labels[$index]}")")
        done
        lines+=("" "Type a number to choose it. Type P and a number (P2) to preview it;" \
                "a key or a mouse movement ends the preview. ENTER on an empty line goes on.")
        ui_card "Choose a screensaver" "${lines[@]}"
        answer=$(ui_ask "Choice" "")
        case "$answer" in
            "") break;;
            [Pp][0-9]*) index=$((${answer#?} - 1))
                [ "$index" -ge 0 ] && [ "$index" -lt ${#names[@]} ] && ui_shell python3 "$REPO/bin/chicago95-screensaver" --hack "${names[$index]}";;
            *[!0-9]*) ;;
            *) index=$((answer - 1)); [ "$index" -ge 0 ] && [ "$index" -lt ${#names[@]} ] && SETUP_SAVER=${names[$index]};;
        esac
    done
    [ "$SETUP_IDLE_MIN" -lt "$lock_minutes" ] || ui_message "The lock screen comes first" \
        "Your screen locks after $lock_minutes minutes, before the screensaver's ${SETUP_IDLE_MIN} minutes," \
        "so you will not see it. Lower the screensaver time in Setup's options, or raise the" \
        "lock time in System Settings > Screen Locking."
    return 0
}

# ---- 1. collect -------------------------------------------------------------
ui_step_start 0
detect_all
ui_message "Welcome to Setup" \
    "Setup prepares Chicago95 for KDE Plasma on this computer." "" \
    "$(detect_summary | sed -n 1p)" "$(detect_summary | sed -n 2p)" "$(detect_summary | sed -n 3p)" \
    "$(detect_summary | sed -n 4p)" "$(detect_summary | sed -n 5p)" "$(detect_summary | sed -n 6p)" \
    "$(detect_summary | sed -n 7p)" "$(detect_summary | sed -n 8p)" "" \
    "Setup log: $SETUP_LOG"

if [ -z "$SETUP_PLASMA_VERSION" ] && [ "$SETUP_DRY_RUN" = 1 ]; then
    ui_message "KDE Plasma not found" "This is a KDE Plasma 6 theme; you are running $SETUP_DESKTOP." \
        "The dry run continues so you can see what Setup would do." "" \
        "To install Plasma:" "   $(detect_plasma_hint)"
elif [ -z "$SETUP_PLASMA_VERSION" ]; then
    setup_abort "This is a KDE Plasma 6 theme, and Plasma is not installed." \
        "You are running $SETUP_DESKTOP." "" \
        "1. Install Plasma:" "      $(detect_plasma_hint)" \
        "2. Log out, pick \"Plasma\" on the login screen, and run ./install.sh again." "" \
        "To preview the changes without Plasma: ./install.sh --dry-run"
elif [ "${SETUP_PLASMA_MAJOR:-0}" -lt 6 ]; then
    setup_abort "Plasma $SETUP_PLASMA_VERSION found; Plasma 6 is required."
elif [ "$SETUP_IN_PLASMA" = 0 ]; then
    ui_message "Not in a Plasma session" "Plasma $SETUP_PLASMA_VERSION is installed, but you are running $SETUP_DESKTOP." \
        "Setup installs the files now; you will see them the next time you log into Plasma."
fi
# Prerequisites: shown every run, with an offer to install the missing packages.
detect_install_command
mapfile -t prerequisites < <(detect_prerequisites)
if ! detect_packages_missing; then
    ui_message "Checking prerequisites" "${prerequisites[@]}"
elif [ ${#SETUP_INSTALL_CMD[@]} -eq 0 ] || [ "$SETUP_DRY_RUN" = 1 ] || [ "$SETUP_YES" = 1 ]; then
    ui_message "Checking prerequisites" "${prerequisites[@]}" "" "Install command:" "   $(detect_install_hint)" \
        "Components whose prerequisites are missing are skipped."
else
    ui_card "Checking prerequisites" "${prerequisites[@]}" "" "Install command:" "   $(detect_install_hint)"
    if ui_confirm "Install the missing packages now? (no = skip those components)"; then
        if ui_sudo "To install the missing programs, Setup must use the system package manager." "${SETUP_INSTALL_CMD[*]}"; then
            ui_shell "${SETUP_INSTALL_CMD[@]}" || install_failed=1
        else
            install_failed=1
        fi
        detect_paths; detect_python
        mapfile -t prerequisites < <(detect_prerequisites)
        ui_message "Checking prerequisites" "${prerequisites[@]}" "" \
            "$([ "${install_failed:-0}" = 1 ] && echo "The install command failed; components still missing prerequisites are skipped.")"
    fi
fi
detect_summary >"$SETUP_LOG"
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
        "notifications:Chicago95 notifications:$py_ok" \
        "clippy:Office Assistant:$py_ok" \
        "extras:System Properties, Device Manager, Dial-Up Networking, login chime:$py_ok" \
        "screensaver:Screensaver (XScreenSaver hacks):$([ -n "$SETUP_HACK_DIR" ] && echo 1 || echo 0)" \
        "winamp:Winamp (qmmp launch entries and window rule):$SETUP_HAS_QMMP" \
        "explorer:Explorer (Thunar settings, GTK CSS, Dolphin toolbar):$SETUP_HAS_THUNAR" \
        "lockscreen:Lock screen:1" \
        "splash:Splash screen:1" \
        "plymouth:Boot screen (asks for the administrator password):$(command -v plymouth-set-default-theme >/dev/null && [ "$SETUP_YES" = 0 ] && echo 1 || echo 0)" \
        "sddm:Login screen (asks for the administrator password):$([ "$SETUP_HAS_SDDM" = 1 ] && [ "$SETUP_YES" = 0 ] && echo 1 || echo 0)" \
        "firefox:Firefox system colours (user.js):$([ -n "$SETUP_FIREFOX_PROFILE" ] && echo 1 || echo 0)")
fi
printf 'Components: %s\n' "$COMPONENTS" >>"$SETUP_LOG"

# Values that differ between machines. Flags pre-fill them; the screen lets the user edit.
while IFS='=' read -r name value; do
    case $name in
        screen) [[ "$value" =~ ^([0-9]+)x([0-9]+)@([0-9.]+)$ ]] && { SETUP_WIDTH=${BASH_REMATCH[1]}; SETUP_HEIGHT=${BASH_REMATCH[2]}; SETUP_SCALE=${BASH_REMATCH[3]}; };;
        panel) SETUP_PANEL=$value;;
        idle) SETUP_IDLE_MIN=$value;;
        explorer) SETUP_EXPLORER=$value;;
        cursor) SETUP_CURSOR=$value;;
        clippy) SETUP_CLIPPY_AUTOSTART=$value;;
        font) SETUP_FONT=$value;;
    esac
done < <(ui_pick_options \
    "screen|Screen size and scale (WxH@scale)|${OPT_SCREEN:-${SETUP_WIDTH}x${SETUP_HEIGHT}@${SETUP_SCALE}}" \
    "panel|Taskbar height in pixels (classic is 28)|${OPT_PANEL:-28}" \
    "explorer|File manager for Explorer (thunar/dolphin)|${OPT_EXPLORER:-$([ "$SETUP_HAS_THUNAR" = 1 ] && echo thunar || echo dolphin)}" \
    "idle|Screensaver after (minutes)|${OPT_IDLE:-5}" \
    "cursor|Cursor size (24/32/48)|${OPT_CURSOR:-$(awk -v s="$SETUP_SCALE" 'BEGIN{print (s>1)?48:32}')}" \
    "clippy|Office Assistant at login (yes/no)|${OPT_CLIPPY:-yes}" \
    "font|UI font family|${OPT_FONT:-MS W98 UI}")
SETUP_FONT_SCOPE=${OPT_FONT_SCOPE:-everywhere}
[ -n "${OPT_FONT_SCOPE:-}" ] || choose_font_scope
SETUP_START_TEXT=${OPT_START_TEXT:-Start}
SETUP_START_LOGO=${OPT_START_LOGO:-flag}
SETUP_BANNER_TEXT=${OPT_BANNER_TEXT:-Chicago95}
[[ " $COMPONENTS " == *" startmenu "* || " $COMPONENTS " == *" taskbar "* ]] && choose_start_menu
SETUP_SAVER=${OPT_SAVER:-deepstars}
[[ " $COMPONENTS " == *" screensaver "* ]] && [ "$py_ok" = 1 ] && choose_screensaver
SETUP_DPI=$(awk -v s="$SETUP_SCALE" 'BEGIN{printf "%d", 96*s + 0.5}')
PANEL_HEIGHT=${SETUP_PANEL:-28}
printf 'Options: screen=%sx%s@%s panel=%s explorer=%s saver=%s idle=%s cursor=%s clippy=%s font=%s\n' \
    "$SETUP_WIDTH" "$SETUP_HEIGHT" "$SETUP_SCALE" "$PANEL_HEIGHT" "$SETUP_EXPLORER" "$SETUP_SAVER" "$SETUP_IDLE_MIN" "$SETUP_CURSOR" "$SETUP_CLIPPY_AUTOSTART" "$SETUP_FONT" >>"$SETUP_LOG"
ui_step_done 1

# ---- 3. copy ----------------------------------------------------------------
ui_step_start 2
# The total comes from a silent dry run of the same steps, so the counter matches the lines shown.
COPIED=0
TO_COPY=$(SETUP_DRY_RUN=1; SETUP_LOG=/dev/null; UI_PLAIN=1; TO_COPY=0
          { fix_font_spaces; for component in $COMPONENTS; do declare -F "step_$component" >/dev/null && "step_$component"; done; } >/dev/null 2>&1
          echo "$COPIED")
# A reinstall adds to the manifest instead of replacing it, so uninstall still knows every earlier file.
[ "$SETUP_DRY_RUN" = 1 ] || { mkdir -p "$STATE_DIR"; touch "$MANIFEST"; }
fix_font_spaces
for component in $COMPONENTS; do
    case $component in
        base|look|taskbar|startmenu|notifications|clippy|extras|screensaver|winamp|explorer|lockscreen|splash|plymouth|sddm|firefox) "step_$component";;
        *) printf 'unknown component: %s\n' "$component" >>"$SETUP_LOG";;
    esac
done
step_fonts
ui_status "All files are copied. Press ENTER for Next."
ui_next
ui_step_done 2

# ---- 4. finish --------------------------------------------------------------
ui_step_start 3
[ "$SETUP_IN_PLASMA" = 1 ] && ui_status "Reloading Plasma..."
finish_session
[[ " $COMPONENTS " == *" taskbar "* ]] && offer_taskbar
apply_start_button
ui_step_done 3

lines=("Setup has finished installing Chicago95 for Plasma." "")
[ "$SETUP_DRY_RUN" = 1 ] && lines=("Dry run: nothing was changed. The log lists every action:" "   $SETUP_LOG" "")
[ "$SETUP_DRY_RUN" = 1 ] || lines+=("Every file Setup copied is listed in the log: $SETUP_LOG" \
    "Your original files are saved in ~/.local/share/chicago95/backup-*" \
    "To remove everything and put them back: ./uninstall.sh")
[[ " $COMPONENTS " == *" startmenu "* ]] && lines+=("Start button logo: $START_LOGO_FILE (replace it and log out to change it)")
ui_message "Setup Complete" "${lines[@]}"
offer_logout
ui_restore
