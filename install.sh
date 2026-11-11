#!/usr/bin/env bash
# shellcheck disable=SC2034,SC2030,SC2031 # the dry run that counts the steps runs in a subshell on purpose
# Chicago95 for Plasma: Setup.
#
#   ./install.sh                 interactive, Chicago95 Setup look
#   ./install.sh --yes           every default component, no questions
#   ./install.sh --components base,look,taskbar,startmenu
#   ./install.sh --dry-run       show what would change, touch nothing
#   ./install.sh --plain         no full-screen UI (logs, CI, screen readers)
#   Options (asked interactively, or given as flags):
#     --screen=2560x1440@1.5  --panel=28  --explorer=thunar|dolphin  --saver=maze
#     --idle=5  --cursor=48  --clippy=yes|no  --quick-launch=yes|no|auto  --font="MS W98 UI"  --font-scope=everywhere|desktop|none
#     --start-text=Start  --start-logo=flag|penguin|/path/to/image  --banner-text=Chicago95
#     --look=1995|1998|2000|"active;inactive;banner background;banner text"  (colours: #RRGGBB, a,b = gradient)
#     --login-style=classic|2000  --icons=chicago95|se98|classicos2000
#     --sounds=Chicago95|Windows98|Windows2000|Plus98-Jungle|...  (data/sound-themes/)
#     --settings=FILE  choices saved by the Control Panel (KEY=value lines), applied over the defaults
#     --task-button-width=160  longest a task button on the taskbar may be, in pixels
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SETUP_YES=0
SETUP_DRY_RUN=0
UI_MODE=screen
WANTED=""
SETUP_LOG="${TMPDIR:-/tmp}/chicago95-setup-$(date +%Y%m%d-%H%M%S).log"

for arg in "$@"; do
  case "$arg" in
  --yes | -y) SETUP_YES=1 ;;
  --dry-run) SETUP_DRY_RUN=1 ;;
  --plain) UI_MODE=plain ;;
  --components=*) WANTED="${arg#*=}" ;;
  --components) ;; # value follows
  --screen=*) OPT_SCREEN="${arg#*=}" ;;
  --panel=*) OPT_PANEL="${arg#*=}" ;;
  --explorer=*) OPT_EXPLORER="${arg#*=}" ;;
  --saver=*) OPT_SAVER="${arg#*=}" ;;
  --idle=*) OPT_IDLE="${arg#*=}" ;;
  --cursor=*) OPT_CURSOR="${arg#*=}" ;;
  --clippy=*) OPT_CLIPPY="${arg#*=}" ;;
  --quick-launch=*) OPT_QUICK_LAUNCH="${arg#*=}" ;;
  --font=*) OPT_FONT="${arg#*=}" ;;
  --font-scope=*) OPT_FONT_SCOPE="${arg#*=}" ;;
  --start-text=*) OPT_START_TEXT="${arg#*=}" ;;
  --start-logo=*) OPT_START_LOGO="${arg#*=}" ;;
  --banner-text=*) OPT_BANNER_TEXT="${arg#*=}" ;;
  --look=*) OPT_LOOK="${arg#*=}" ;;
  --icons=*) OPT_ICONS="${arg#*=}" ;;
  --login-style=*) OPT_LOGIN_STYLE="${arg#*=}" ;;
  --sounds=*) OPT_SOUNDS="${arg#*=}" ;;
  --settings=*) OPT_SETTINGS="${arg#*=}" ;;
  --task-button-width=*) OPT_TASK_BUTTON_WIDTH="${arg#*=}" ;;
  --help | -h)
    sed -n '2,15p' "$0"
    exit 0
    ;;
  *) [ -z "$WANTED" ] && [[ "$arg" != --* ]] && WANTED="$arg" ;;
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
  2)
    ui_restore
    exec "$REPO/uninstall.sh"
    ;;
  3)
    ui_restore
    exit 0
    ;;
  esac
fi

# choose_text <title> <question> <current> <suggestion>...   prints the chosen text; the last entry
# is always "Your own text", which asks for it on the same screen.
choose_text() {
  local title="$1" question="$2" current="$3" index choice
  shift 3
  local suggestions=("$@") marked=$(($# + 1))
  for index in "${!suggestions[@]}"; do [ "${suggestions[$index]//%h/$(hostname)}" = "${current//%h/$(hostname)}" ] && marked=$((index + 1)); done
  choice=$(ui_choose "$title" "$question" "$marked" "${suggestions[@]//%h/$(hostname)}" "Your own text")
  if [ "$choice" -le $# ]; then printf '%s' "${suggestions[$((choice - 1))]}"; else ui_ask "Text" "${current//%h/$(hostname)}"; fi
}

# choose_image <title> <question> <current> <name|label>...   prints a bundled image's name or the path of the
# user's file; the last entry is always "Your own image", which asks for the file until it exists.
choose_image() {
  local title="$1" question="$2" current="$3" index choice path
  shift 3
  local names=() labels=() marked=$(($# + 1))
  for index in $(seq 1 $#); do
    names+=("${!index%%|*}")
    labels+=("${!index#*|}")
  done
  for index in "${!names[@]}"; do [ "${names[$index]}" = "$current" ] && marked=$((index + 1)); done
  choice=$(ui_choose "$title" "$question" "$marked" "${labels[@]}" "Your own image (PNG or SVG)")
  if [ "$choice" -le $# ]; then
    printf '%s' "${names[$((choice - 1))]}"
    return
  fi
  [ "${SETUP_YES:-0}" = 1 ] && [ ! -f "${current/#\~/$HOME}" ] && {
    printf '%s' "${names[0]}"
    return
  }
  until [ -f "${path:-}" ]; do
    path=$(ui_ask "Full path of the image file" "$current")
    path=${path/#\~/$HOME}
  done
  printf '%s' "$path"
}

choose_start_menu() {
  [ -n "${OPT_START_TEXT:-}" ] || SETUP_START_TEXT=$(choose_text "Start button text" "What should the Start button say?" \
    "$SETUP_START_TEXT" "Start" "Linux")
  [ -n "${OPT_START_LOGO:-}" ] || SETUP_START_LOGO=$(choose_image "Start button logo" \
    "Which logo should the Start button show?\nIt is copied to ~/.local/share/chicago95/start-logo (keeping its extension);\nreplace that file and log out to change the logo later." \
    "$SETUP_START_LOGO" "flag|Classic flag" "penguin|Penguin")
  [ -n "${OPT_BANNER_TEXT:-}" ] || SETUP_BANNER_TEXT=$(choose_text "Start menu banner" "What should the strip along the Start menu say?" \
    "$SETUP_BANNER_TEXT" "Chicago95" "Linux")
  return 0
}

# Texts and pictures of the login and loading screens; one gate first, so ENTER keeps every default.
choose_branding() {
  local choice
  choice=$(ui_choose "Login and loading screen texts" "The login and loading screens show a logo, an edition, a tagline and a few lines of text." 1 \
    "Keep the default texts and pictures" "Customize them (one short question each)")
  [ "$choice" = 2 ] || return 0
  SETUP_LOGIN_TITLE=$(choose_text "Login title bar" "What should the login window's title say?" "$SETUP_LOGIN_TITLE" \
    "Log On to %h" "Welcome to %h")
  if [ "$SETUP_LOGIN_STYLE" = classic ]; then
    SETUP_LOGIN_MESSAGE=$(choose_text "Login message" "What should the line above the fields say?" "$SETUP_LOGIN_MESSAGE" \
      "Type a user name and password to log on." "Welcome. Please log on.")
    SETUP_LOGIN_ICON=$(choose_image "Login picture" "Which picture should sit beside the fields?" "$SETUP_LOGIN_ICON" \
      "keys|Keys" "padlock|Padlock")
    SETUP_SPLASH_IMAGE=$(choose_image "Loading screen picture" "Which picture should fill the screen while Plasma loads?" \
      "$SETUP_SPLASH_IMAGE" "classic|Chicago95 picture")
  else
    SETUP_LOGIN_LOGO=$(choose_image "Login and loading logo" "Which logo should the login and loading screens show?" "$SETUP_LOGIN_LOGO" \
      "start|Same as the Start button" "waving-flag|Waving flag (downloaded from Wikimedia Commons)" \
      "flag|Classic flag" "penguin|Penguin")
    SETUP_EDITION=$(choose_text "Edition" "Which edition should follow the name?" "$SETUP_EDITION" \
      "Professional" "Home Edition" "Workstation")
    SETUP_COMPANY=$(choose_text "Company" "Which company should stand above the name (and top right, without a logo)?" \
      "$SETUP_COMPANY" "KDE" "Linux")
    SETUP_COMPANY_LOGO=$(choose_image "Company logo" "What should the top-right corner of the login and loading screens show?" \
      "$SETUP_COMPANY_LOGO" "text|The company's name in heavy italics")
    SETUP_TAGLINE=$(choose_text "Tagline" "What should the small line under the edition say?" "$SETUP_TAGLINE" \
      "Built on Linux Technology" "Built on KDE Plasma")
    SETUP_LOADING_TEXT=$(choose_text "Loading text" "What should stand beside the progress bar?" "$SETUP_LOADING_TEXT" \
      "Starting up..." "Loading Plasma...")
    SETUP_LOADING_FOOTER=$(choose_text "Loading screen footer" "What should the bottom line of the loading screen say?" \
      "$SETUP_LOADING_FOOTER" "Chicago95 for KDE Plasma" "Welcome to %h")
  fi
  return 0
}

valid_colors() { [[ "$1" =~ ^#[0-9A-Fa-f]{6}(,#[0-9A-Fa-f]{6})?$ ]]; }

ask_colors() { # ask_colors <prompt> <current>   repeats until the answer is one or two #RRGGBB colours
  local answer
  until valid_colors "${answer:-}"; do answer=$(ui_ask "$1" "$2"); done
  printf '%s' "$answer"
}

choose_sounds() {
  local themes=(Chicago95) names=("Chicago95 (Windows 95)") theme choice
  for theme in Windows98 Windows2000 "$REPO"/data/sound-themes/Plus98-*/; do
    theme=${theme%/}
    theme=${theme##*/}
    themes+=("$theme")
    names+=("$(sed -n 's/^Name=//p' "$REPO/data/sound-themes/$theme/index.theme")")
  done
  local marked=1 index
  for index in "${!themes[@]}"; do [ "${themes[$index]}" = "${SETUP_SOUND_THEME:-}" ] && marked=$((index + 1)); done
  choice=$(ui_choose "Sounds" "Which sound scheme should play for log on, log off, errors and windows?" "$marked" "${names[@]}")
  SETUP_SOUND_THEME=${themes[$((choice - 1))]}
  return 0
}

choose_look() {
  local choice marked=1
  case "${SETUP_LOOK:-}" in 1998) marked=2 ;; 2000) marked=3 ;; custom) marked=4 ;; esac
  choice=$(ui_choose "Look" "How should title bars and the Start menu banner look?" "$marked" \
    "1995: solid navy title bars, grey banner" \
    "1998: navy-to-blue title bars, navy banner with a blue glow, taller menu rows" \
    "2000: warm grey windows, navy-to-light-blue title bars, black-to-blue banner" \
    "Your own colours")
  [ "$choice" = "$marked" ] && [ -n "${SETUP_LOOK:-}" ] && return 0 # the remembered look keeps its saved colours
  case "$choice" in
  1) apply_look 1995 ;;
  2) apply_look 1998 ;;
  3) apply_look 2000 ;;
  4)
    SETUP_LOOK=custom
    ui_card "Your own colours" "Type a colour as #RRGGBB, or two separated by a comma for a gradient" \
      "(left to right on title bars, top to bottom on the banner). ENTER keeps the shown value." >/dev/tty
    SETUP_TITLE_ACTIVE=$(ask_colors "Active title bar" "$SETUP_TITLE_ACTIVE")
    SETUP_TITLE_INACTIVE=$(ask_colors "Inactive title bar" "$SETUP_TITLE_INACTIVE")
    SETUP_BANNER_BG=$(ask_colors "Start menu banner background" "$SETUP_BANNER_BG")
    SETUP_BANNER_FG=$(ask_colors "Start menu banner text" "$SETUP_BANNER_FG")
    ;;
  esac
  return 0
}

# "P1"/"P2" open the real login screen in test mode with that style; close it with Alt+F4.
choose_login_style() {
  local styles=(classic 2000) answer index greeter
  greeter=$(command -v sddm-greeter-qt6 || command -v sddm-greeter || true)
  while :; do
    local lines=("How should the login and loading screens look?" "")
    for index in "${!styles[@]}"; do
      lines+=("$(printf '  %d. [%s] %s' $((index + 1)) "$([ "${styles[$index]}" = "$SETUP_LOGIN_STYLE" ] && echo X || echo ' ')" \
        "$([ "${styles[$index]}" = classic ] && echo "Classic (1995/1998): key dialog on teal, picture while loading" || echo "2000: your logo and banner text on white, progress bar while loading")")")
    done
    lines+=("")
    [ -n "$greeter" ] && lines+=("Type P and a number (P2) to preview it full screen; close the preview with Alt+F4.")
    lines+=("Type a number to choose it, or press ENTER to keep the marked one.")
    ui_card "Login and loading screens" "${lines[@]}"
    answer=$(ui_ask "Choice" "")
    case "$answer" in
    "") break ;;
    [Pp][12]) [ -n "$greeter" ] && preview_login "$greeter" "${styles[$((${answer#?} - 1))]}" ;;
    [12]) SETUP_LOGIN_STYLE=${styles[$((answer - 1))]} ;;
    esac
  done
  return 0
}

preview_login() { # preview_login <greeter> <style>   the theme from the repo, styled as Setup would install it
  local preview
  preview=$(mktemp -d)
  cp -r "$SDDM_THEME_SRC/." "$preview/"
  [ -f "$SDDM_FONT" ] && cp "$SDDM_FONT" "$preview/"
  cp "$(start_logo_source)" "$preview/brand-logo.$(start_logo_source | sed 's/.*\.//')"
  SETUP_LOGIN_STYLE=$2 sddm_theme_conf >"$preview/theme.conf"
  ui_shell "$1" --test-mode --theme "$preview" 2>/dev/null
  rm -rf "$preview"
}

choose_font_scope() {
  ui_card "Where should the classic font be used?" \
    "The Start menu, notifications, Clippy, the Shut Down dialog and the login screen" \
    "always use ${SETUP_FONT:-MS W98 UI}. For everything else:" "" \
    "  1. Everywhere: all programs, including Firefox's menus and web pages that" \
    "     ask for the system font." \
    "  2. Desktop only: window title bars. Programs and web pages keep your font." \
    "  3. Nowhere: Setup leaves your font settings alone."
  local marked=1
  case "${SETUP_FONT_SCOPE:-}" in desktop) marked=2 ;; none) marked=3 ;; esac
  case "$(ui_ask "Type 1, 2 or 3 and press ENTER" "$marked")" in
  2) SETUP_FONT_SCOPE=desktop ;;
  3) SETUP_FONT_SCOPE=none ;;
  *) SETUP_FONT_SCOPE=everywhere ;;
  esac
}

# Lists the installed savers; "P" and a number previews one full screen with the real screensaver.
choose_screensaver() {
  local names=() labels=() name label answer index lock_minutes
  while IFS=$'\t' read -r name label; do
    names+=("$name")
    labels+=("$label")
  done \
    < <(python3 "$REPO/bin/chicago95-screensaver" --list 2>/dev/null)
  [ ${#names[@]} -gt 0 ] || return 0
  lock_minutes=$(kreadconfig6 --file kscreenlockerrc --group Daemon --key Timeout 2>/dev/null)
  lock_minutes=${lock_minutes:-5}
  while :; do
    local lines=("It starts after ${SETUP_IDLE_MIN:-5} minutes without input; your screen locks after $lock_minutes." "")
    for index in "${!names[@]}"; do
      lines+=("$(printf '  %d. [%s] %s' $((index + 1)) "$([ "${names[$index]}" = "$SETUP_SAVER" ] && echo X || echo ' ')" "${labels[$index]}")")
    done
    lines+=("" "Type a number to choose it. Type P and a number (P2) to preview it;"
      "a key or a mouse movement ends the preview. ENTER on an empty line goes on.")
    ui_card "Choose a screensaver" "${lines[@]}"
    answer=$(ui_ask "Choice" "")
    case "$answer" in
    "") break ;;
    [Pp][0-9]*)
      index=$((${answer#?} - 1))
      [ "$index" -ge 0 ] && [ "$index" -lt ${#names[@]} ] && ui_shell python3 "$REPO/bin/chicago95-screensaver" --hack "${names[$index]}"
      ;;
    *[!0-9]*) ;;
    *)
      index=$((answer - 1))
      [ "$index" -ge 0 ] && [ "$index" -lt ${#names[@]} ] && SETUP_SAVER=${names[$index]}
      ;;
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
    detect_paths
    detect_python
    mapfile -t prerequisites < <(detect_prerequisites)
    ui_message "Checking prerequisites" "${prerequisites[@]}" "" \
      "$([ "${install_failed:-0}" = 1 ] && echo "The install command failed; components still missing prerequisites are skipped.")"
  fi
fi
detect_summary >"$SETUP_LOG"
ui_step_done 0

# ---- 2. components ----------------------------------------------------------
ui_step_start 1
py_ok=1
[ -n "$SETUP_PY_MISSING" ] && py_ok=0
# Earlier runs' choices and components are this run's defaults; flags and the screens still change them.
SAVED_SETTINGS=~/.config/chicago95/setup.conf
[ -f "$SAVED_SETTINGS" ] && load_settings "$SAVED_SETTINGS"
remembered() { # remembered <component> <default>   1 when an earlier run installed it, 0 when it was left out
  [ -n "${SETUP_COMPONENTS:-}" ] && [ "$2" = 1 ] || {
    echo "$2"
    return
  }
  [[ " $SETUP_COMPONENTS " == *" $1 "* ]] && echo 1 || echo 0
}
if [ -n "$WANTED" ]; then
  COMPONENTS=$(printf '%s' "$WANTED" | tr ',' ' ')
else
  COMPONENTS=$(ui_pick_components \
    "base:Chicago95 base theme (GTK, icons, cursors, sounds):$(remembered base 1)" \
    "look:Window decoration, Plasma style, colours, widget style:$(remembered look 1)" \
    "animations:Animations (windows, menus, notifications, taskbar):$(remembered animations 1)" \
    "taskbar:Taskbar (Start button, Quick Launch, task buttons, tray, clock):$(remembered taskbar 1)" \
    "startmenu:Start menu and Shut Down dialog:$(remembered startmenu $py_ok)" \
    "notifications:Chicago95 notifications:$(remembered notifications $py_ok)" \
    "clippy:Office Assistant:$(remembered clippy $py_ok)" \
    "extras:System Properties, Device Manager, Dial-Up Networking, login chime:$(remembered extras $py_ok)" \
    "controlpanel:Control Panel (change every choice later):$(remembered controlpanel $py_ok)" \
    "sounds:Sound scheme (Windows 98, Plus! 98, Windows 2000):$(remembered sounds 1)" \
    "background:Desktop background (colour, pattern or picture):$(remembered background 1)" \
    "screensaver:Screensaver (XScreenSaver hacks):$(remembered screensaver "$([ -n "$SETUP_HACK_DIR" ] && echo 1 || echo 0)")" \
    "winamp:Winamp (qmmp launch entries and window rule):$(remembered winamp $SETUP_HAS_QMMP)" \
    "explorer:Explorer (Thunar settings, GTK CSS, Dolphin toolbar):$(remembered explorer $SETUP_HAS_THUNAR)" \
    "lockscreen:Lock screen:$(remembered lockscreen 1)" \
    "splash:Splash screen:$(remembered splash 1)" \
    "plymouth:Boot screen (asks for the administrator password):$(remembered plymouth "$(command -v plymouth-set-default-theme >/dev/null && [ "$SETUP_YES" = 0 ] && echo 1 || echo 0)")" \
    "sddm:Login screen (asks for the administrator password):$(remembered sddm "$([ "$SETUP_HAS_SDDM" = 1 ] && [ "$SETUP_YES" = 0 ] && echo 1 || echo 0)")" \
    "firefox:Firefox system colours (user.js):$(remembered firefox "$([ -n "$SETUP_FIREFOX_PROFILE" ] && echo 1 || echo 0)")")
fi
printf 'Components: %s\n' "$COMPONENTS" >>"$SETUP_LOG"

# Values that differ between machines. Flags pre-fill them; the screen lets the user edit.
while IFS='=' read -r name value; do
  case $name in
  screen) [[ "$value" =~ ^([0-9]+)x([0-9]+)@([0-9.]+)$ ]] && {
    SETUP_WIDTH=${BASH_REMATCH[1]}
    SETUP_HEIGHT=${BASH_REMATCH[2]}
    SETUP_SCALE=${BASH_REMATCH[3]}
  } ;;
  panel) SETUP_PANEL=$value ;;
  idle) SETUP_IDLE_MIN=$value ;;
  explorer) SETUP_EXPLORER=$value ;;
  cursor) SETUP_CURSOR=$value ;;
  clippy) SETUP_CLIPPY_AUTOSTART=$value ;;
  quicklaunch) SETUP_QUICK_LAUNCH=$value ;;
  font) SETUP_FONT=$value ;;
  esac
done < <(ui_pick_options \
  "screen|Screen size and scale (WxH@scale)|${OPT_SCREEN:-${SETUP_WIDTH}x${SETUP_HEIGHT}@${SETUP_SCALE}}" \
  "panel|Taskbar height in pixels (classic is 28)|${OPT_PANEL:-${SETUP_PANEL:-28}}" \
  "explorer|File manager for Explorer (thunar/dolphin)|${OPT_EXPLORER:-${SETUP_EXPLORER:-$([ "$SETUP_HAS_THUNAR" = 1 ] && echo thunar || echo dolphin)}}" \
  "idle|Screensaver after (minutes)|${OPT_IDLE:-${SETUP_IDLE_MIN:-5}}" \
  "cursor|Cursor size (24/32/48)|${OPT_CURSOR:-${SETUP_CURSOR:-$(awk -v s="$SETUP_SCALE" 'BEGIN{print (s>1)?48:32}')}}" \
  "clippy|Office Assistant at login (yes/no)|${OPT_CLIPPY:-${SETUP_CLIPPY_AUTOSTART:-yes}}" \
  "quicklaunch|Quick Launch on the taskbar (yes/no/auto: from the 1998 look on)|${OPT_QUICK_LAUNCH:-${SETUP_QUICK_LAUNCH:-auto}}" \
  "font|UI font family|${OPT_FONT:-${SETUP_FONT:-MS W98 UI}}")
SETUP_FONT_SCOPE=${OPT_FONT_SCOPE:-${SETUP_FONT_SCOPE:-everywhere}}
[ -n "${OPT_FONT_SCOPE:-}" ] || choose_font_scope
# A remembered look keeps its saved colours (a custom one has nothing else); a flag or a first run applies the look.
if [ -n "${OPT_LOOK:-}" ] || [ -z "${SETUP_LOOK:-}" ]; then apply_look "${OPT_LOOK:-1995}"; fi
[ -n "${OPT_LOOK:-}" ] || choose_look
SETUP_START_TEXT=${OPT_START_TEXT:-${SETUP_START_TEXT:-Start}}
SETUP_START_LOGO=${OPT_START_LOGO:-${SETUP_START_LOGO:-flag}}
SETUP_BANNER_TEXT=${OPT_BANNER_TEXT:-${SETUP_BANNER_TEXT:-Chicago95}}
[[ " $COMPONENTS " == *" startmenu "* || " $COMPONENTS " == *" taskbar "* ]] && choose_start_menu
SETUP_LOGIN_STYLE=${OPT_LOGIN_STYLE:-${SETUP_LOGIN_STYLE:-classic}}
[[ " $COMPONENTS " == *" sddm "* || " $COMPONENTS " == *" splash "* ]] && [ -z "${OPT_LOGIN_STYLE:-}" ] && choose_login_style
SETUP_LOGIN_TITLE=${SETUP_LOGIN_TITLE:-"Log On to %h"}
SETUP_LOGIN_MESSAGE=${SETUP_LOGIN_MESSAGE:-"Type a user name and password to log on."}
SETUP_LOGIN_ICON=${SETUP_LOGIN_ICON:-keys}
SETUP_SPLASH_IMAGE=${SETUP_SPLASH_IMAGE:-classic}
# The 2000 look's logo is the waving flag of its start-up screen; the others repeat the Start button's logo.
SETUP_LOGIN_LOGO=${SETUP_LOGIN_LOGO:-$([ "$SETUP_MENU_STYLE" = 2000 ] && echo waving-flag || echo start)}
SETUP_EDITION=${SETUP_EDITION:-Professional}
SETUP_TAGLINE=${SETUP_TAGLINE:-"Built on Linux Technology"}
SETUP_COMPANY=${SETUP_COMPANY:-KDE}
SETUP_COMPANY_LOGO=${SETUP_COMPANY_LOGO:-text}
SETUP_LOADING_TEXT=${SETUP_LOADING_TEXT:-"Starting up..."}
SETUP_LOADING_FOOTER=${SETUP_LOADING_FOOTER:-"Chicago95 for KDE Plasma"}
[[ " $COMPONENTS " == *" sddm "* || " $COMPONENTS " == *" splash "* ]] && choose_branding
SETUP_SAVER=${OPT_SAVER:-${SETUP_SAVER:-deepstars}}
[[ " $COMPONENTS " == *" screensaver "* ]] && [ "$py_ok" = 1 ] && choose_screensaver
SETUP_SOUND_THEME=${OPT_SOUNDS:-${SETUP_SOUND_THEME:-Chicago95}}
[[ " $COMPONENTS " == *" sounds "* ]] && [ -z "${OPT_SOUNDS:-}" ] && choose_sounds
[ -n "${OPT_SETTINGS:-}" ] && load_settings "$OPT_SETTINGS"
[ -n "${OPT_TASK_BUTTON_WIDTH:-}" ] && SETUP_TASK_BUTTON_WIDTH=$OPT_TASK_BUTTON_WIDTH
SETUP_DPI=$(awk -v s="$SETUP_SCALE" 'BEGIN{printf "%d", 96*s + 0.5}')
PANEL_HEIGHT=${SETUP_PANEL:-28}
printf 'Options: screen=%sx%s@%s panel=%s explorer=%s saver=%s idle=%s cursor=%s clippy=%s quicklaunch=%s font=%s sounds=%s\n' \
  "$SETUP_WIDTH" "$SETUP_HEIGHT" "$SETUP_SCALE" "$PANEL_HEIGHT" "$SETUP_EXPLORER" "$SETUP_SAVER" "$SETUP_IDLE_MIN" "$SETUP_CURSOR" "$SETUP_CLIPPY_AUTOSTART" "${SETUP_QUICK_LAUNCH:-auto}" "$SETUP_FONT" "$SETUP_SOUND_THEME" >>"$SETUP_LOG"
ui_step_done 1

# ---- 3. copy ----------------------------------------------------------------
ui_step_start 2
# The total comes from a silent dry run of the same steps, so the counter matches the lines shown.
COPIED=0
TO_COPY=$(
  SETUP_DRY_RUN=1
  SETUP_LOG=/dev/null
  UI_PLAIN=1
  TO_COPY=0
  {
    fix_font_spaces
    for component in $COMPONENTS; do declare -F "step_$component" >/dev/null && "step_$component"; done
  } >/dev/null 2>&1
  echo "$COPIED"
)
# A reinstall adds to the manifest instead of replacing it, so uninstall still knows every earlier file.
[ "$SETUP_DRY_RUN" = 1 ] || {
  mkdir -p "$STATE_DIR"
  touch "$MANIFEST"
}
fix_font_spaces
for component in $COMPONENTS; do
  case $component in
  base | look | animations | taskbar | startmenu | notifications | clippy | extras | controlpanel | sounds | background | screensaver | winamp | explorer | lockscreen | splash | plymouth | sddm | firefox) "step_$component" ;;
  *) printf 'unknown component: %s\n' "$component" >>"$SETUP_LOG" ;;
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
apply_taskbar
[[ " $COMPONENTS " == *" startmenu "* ]] && restart_start_menu
save_settings
ui_step_done 3

lines=("Setup has finished installing Chicago95 for Plasma." "")
[ "$SETUP_DRY_RUN" = 1 ] && lines=("Dry run: nothing was changed. The log lists every action:" "   $SETUP_LOG" "")
[ "$SETUP_DRY_RUN" = 1 ] || lines+=("Every file Setup copied is listed in the log: $SETUP_LOG"
  "Your original files are saved in ~/.local/share/chicago95/backup-*"
  "To remove everything and put them back: ./uninstall.sh")
[[ " $COMPONENTS " == *" startmenu "* ]] && lines+=("Start button logo: $(start_logo_file) (replace it and log out to change it)")
ui_message "Setup Complete" "${lines[@]}"
offer_logout
ui_restore
