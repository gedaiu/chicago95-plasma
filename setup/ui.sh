# Text-mode Setup screen in the style of the 1995 original: blue field, white band,
# step list, copy progress. Sourced by install.sh. Falls back to plain output when
# stdout is not a terminal or --plain is given.

UI_PLAIN=0
UI_TITLE="Chicago95 Setup"
UI_COLS=80
UI_ROWS=25
UI_STEPS=()
UI_STEP_DONE=()
UI_ON_STEPS=0

ui_init() {
    if [ "${1:-}" = plain ] || [ ! -t 1 ] || ! command -v tput >/dev/null 2>&1; then
        UI_PLAIN=1
        return
    fi
    UI_COLS=$(tput cols); UI_ROWS=$(tput lines)
    [ "$UI_COLS" -ge 60 ] && [ "$UI_ROWS" -ge 20 ] || UI_PLAIN=1
    [ "$UI_PLAIN" = 1 ] && return
    tput civis
    # A trap replaces the default action, so INT and TERM must exit themselves; EXIT then restores the screen.
    trap ui_restore EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM
}

ui_restore() {
    [ "$UI_PLAIN" = 1 ] && return
    printf '\e[0m'; tput cnorm; tput clear
}

ui_field() {        # paint the blue field and the title band
    UI_ON_STEPS=0; UI_CARD_END=""
    printf '\e[44m\e[97m'; tput clear
    tput cup 0 0; printf '\e[47m\e[34m%-*s\e[44m\e[97m' "$UI_COLS" "  $UI_TITLE"
    # One cell short, then erase-to-end in the same colour: writing the last cell of the last row
    # wraps the cursor and scrolls the whole screen up a line.
    tput cup $((UI_ROWS - 1)) 0; printf '\e[47m\e[34m%-*s\e[K\e[44m\e[97m' $((UI_COLS - 1)) "  ENTER=Continue   Ctrl+C=Exit Setup"
}

ui_center() {       # ui_center <row> <text>
    local row="$1" text="$2"
    tput cup "$row" $(( (UI_COLS - ${#text}) / 2 )); printf '%s' "$text"
}

ui_text() {         # ui_text <row> <text>   (left column, indented)
    tput cup "$1" 6; printf '%s' "$2"
}

ui_set_steps() { UI_STEPS=("$@"); UI_STEP_DONE=(); for _ in "$@"; do UI_STEP_DONE+=(0); done; }

ui_steps() {        # draws the checklist from row 4 with the current step highlighted
    local index=0 marker
    [ "$UI_ON_STEPS" = 1 ] || { ui_field; UI_ON_STEPS=1; }
    for step in "${UI_STEPS[@]}"; do
        marker="[ ]"; [ "${UI_STEP_DONE[$index]}" = 1 ] && marker="[X]"
        tput cup $((4 + index)) 6
        if [ "${UI_STEP_DONE[$index]}" = 2 ]; then printf '\e[93m%s %s\e[97m' "$marker" "$step"; else printf '%s %s' "$marker" "$step"; fi
        index=$((index + 1))
    done
}

ui_step_start() {   # ui_step_start <index>
    UI_STEP_DONE[$1]=2
    if [ "$UI_PLAIN" = 1 ]; then printf '\n== %s\n' "${UI_STEPS[$1]}"; elif [ "$UI_ON_STEPS" = 1 ]; then ui_steps; fi
}

# The checklist is drawn when a step has something to show; painting it for a step that ends
# in a fraction of a second only flashes before the next screen replaces it.
ui_step_done() { UI_STEP_DONE[$1]=1; [ "$UI_PLAIN" = 0 ] && [ "$UI_ON_STEPS" = 1 ] && ui_steps; return 0; }

ui_status() {       # one-line status under the step list
    if [ "$UI_PLAIN" = 1 ]; then printf '   %s\n' "$1"; return; fi
    [ "$UI_ON_STEPS" = 1 ] || ui_steps
    tput cup $((6 + ${#UI_STEPS[@]})) 6; printf '%-*s' $((UI_COLS - 12)) "$1"
}

ui_repeat() {       # ui_repeat <count> <char>   prints the (multibyte-safe) character count times
    local index
    for ((index = 0; index < $1; index++)); do printf '%s' "$2"; done
}

ui_fit() {          # ui_fit <width> <text>   keeps the end of a long path, which is the part that tells files apart
    if [ "${#2}" -le "$1" ]; then printf '%s' "$2"; else printf '…%s' "${2: -$(($1 - 1))}"; fi
}

UI_COPIED_LINES=()

# ui_progress <done> <total> <line>   every copied file gets its own line: plain output prints them all,
# the Setup screen scrolls the most recent ones under the bar.
ui_progress() {
    local done="$1" total="$2" line="$3" width=50 filled
    if [ "$UI_PLAIN" = 1 ]; then printf '   (%d/%d) %s\n' "$done" "$total" "$line"; return 0; fi
    [ "$UI_ON_STEPS" = 1 ] || ui_steps
    filled=$(( total > 0 && done < total ? done * width / total : width ))
    local row=$((UI_ROWS / 2)) col=$(( (UI_COLS - width - 2) / 2 )) text_width=$((UI_COLS - 12))
    local visible=$((UI_ROWS - row - 4)) index
    ui_center $((row - 3)) "Setup is now copying files to your computer..."
    tput cup "$row" "$col"; printf '\e[93m['; ui_repeat "$filled" '█'; ui_repeat $((width - filled)) '░'; printf ']\e[97m %3d%%' $(( total > 0 && done < total ? done * 100 / total : 100 ))
    UI_COPIED_LINES+=("$line")
    for ((index = 0; index < visible; index++)); do
        local entry=$(( ${#UI_COPIED_LINES[@]} - visible + index ))
        tput cup $((row + 2 + index)) 6
        if [ "$entry" -ge 0 ]; then printf '%-*s' "$text_width" "$(ui_fit "$text_width" "${UI_COPIED_LINES[$entry]}")"; else printf '%-*s' "$text_width" ''; fi
    done
}

ui_card() {         # ui_card <title> <line>...   draws a titled page; leaves the cursor below it
    local title="$1"; shift
    if [ "$UI_PLAIN" = 1 ]; then printf '\n%s\n' "$title"; printf '  %s\n' "$@"; return; fi
    ui_field; ui_center 3 "$title"; UI_CARD_END=6
    for line in "$@"; do ui_text "$UI_CARD_END" "$line"; UI_CARD_END=$((UI_CARD_END + 1)); done
}

# ui_next   shows a Next button and waits for ENTER; Setup never moves on by itself.
# Only --yes (no questions) and output that is not a terminal skip the wait.
ui_next() {
    [ "${SETUP_YES:-0}" = 1 ] && return 0
    if [ "$UI_PLAIN" = 1 ]; then
        [ -t 1 ] || return 0
        printf '\n  Press ENTER for Next > '; read -r _ </dev/tty; return 0
    fi
    local label="  Next >  "
    tput cup $((UI_ROWS - 3)) $((UI_COLS - ${#label} - 6)); printf '\e[47m\e[30m%s\e[44m\e[97m' "$label"
    read -r _ </dev/tty
}

ui_message() {      # ui_message <title> <line>...   waits for Next
    ui_card "$@"
    ui_next
}

UI_INTRO_ART=(
    " ███  █  █  ███   ███   ██    ███   ██    ██   ████"
    "█     █  █   █   █     █  █  █     █  █  █  █  █   "
    "█     ████   █   █     ████  █ ██  █  █   ███  ███ "
    "█     █  █   █   █     █  █  █  █  █  █     █     █"
    " ███  █  █  ███   ███  █  █   ███   ██    ██   ███ "
)

ui_intro() {        # title screen before anything is checked or changed
    local lines=("for KDE Plasma 6" "" \
        "Setup will look at this computer, let you choose what to install," \
        "and show every file as it is copied." \
        "Nothing changes until you have seen the list of components." "" \
        "Press ENTER for Next, or Ctrl+C to leave Setup at any time.")
    if [ "$UI_PLAIN" = 1 ]; then printf '\n%s\n' "${UI_INTRO_ART[@]}"; printf '  %s\n' "${lines[@]}"; ui_next; return; fi
    ui_field
    local row=4 line
    printf '\e[93m'
    for line in "${UI_INTRO_ART[@]}"; do ui_center "$row" "$line"; row=$((row + 1)); done
    printf '\e[97m'
    row=$((row + 1))
    for line in "${lines[@]}"; do ui_center "$row" "$line"; row=$((row + 1)); done
    ui_next
}

# ui_choose <title> <intro, \n between lines> <current index> <option>...   numbered list, current one marked;
# prints the 1-based index of the chosen option
ui_choose() {
    local title="$1" intro="$2" current="$3" answer index; shift 3
    local options=("$@") lines=()
    mapfile -t lines < <(printf '%b\n' "$intro"); lines+=("")
    for index in "${!options[@]}"; do
        lines+=("$(printf '  %d. [%s] %s' $((index + 1)) "$([ $((index + 1)) = "$current" ] && echo X || echo ' ')" "${options[$index]}")")
    done
    # Called as $(ui_choose ...): the screen goes to the terminal, only the answer to the caller.
    while :; do
        ui_card "$title" "${lines[@]}" >/dev/tty
        answer=$(ui_ask "Type a number and press ENTER" "$current")
        [[ "$answer" =~ ^[0-9]+$ ]] && [ "$answer" -ge 1 ] && [ "$answer" -le ${#options[@]} ] && { printf '%s' "$answer"; return; }
    done
}

# ui_sudo <why> <command>...  -> 0 once administrator rights are granted, 1 when skipped or refused.
# Asks in plain words, on the Setup screen, and shows exactly what will run as administrator.
ui_sudo() {
    [ "${SETUP_DRY_RUN:-0}" = 1 ] && return 0
    sudo -n true 2>/dev/null && return 0
    local why="$1"; shift
    local attempt password retry=() commands=("" "Setup will run:")
    local command
    for command in "$@"; do
        mapfile -t -O "${#commands[@]}" commands < <(printf '%s\n' "$command" | fold -s -w $((UI_COLS - 20)) | sed '1s/^/   /; 2,$s/^/       /')
    done
    for attempt in 1 2 3; do
        [ "$attempt" -gt 1 ] && retry=("That password was not accepted. Please try again." "")
        ui_card "Administrator password needed" "${retry[@]}" "$why" "${commands[@]}" "" \
            "Type the password you use to log in to this computer, then press ENTER." \
            "Nothing appears on screen while you type; that is normal." \
            "To skip this part, press ENTER without typing anything."
        if [ "$UI_PLAIN" = 1 ]; then printf '  Password: '; else tput cup $((UI_CARD_END + 1)) 6; printf 'Password: '; tput cnorm; fi
        IFS= read -rs password </dev/tty; printf '\n'
        [ "$UI_PLAIN" = 1 ] || tput civis
        [ -n "$password" ] || return 1
        sudo -S -p '' -v <<<"$password" 2>/dev/null && return 0
    done
    return 1
}

ui_shell() {        # ui_shell <command>...   runs a command on the bare terminal (sudo prompts, package output)
    if [ "$UI_PLAIN" = 0 ]; then printf '\e[0m'; tput cnorm; tput clear; fi
    local status=0
    "$@" </dev/tty || status=$?
    if [ "$UI_PLAIN" = 0 ]; then tput civis; UI_ON_STEPS=0; fi
    return $status
}

ui_confirm() {      # ui_confirm <question>  -> 0 yes / 1 no ; honours SETUP_YES
    [ "${SETUP_YES:-0}" = 1 ] && return 0
    local answer
    if [ "$UI_PLAIN" = 1 ]; then printf '%s [Y/n] ' "$1"; read -r answer </dev/tty; else
        local row; row=$(ui_prompt_row); tput cup "$row" 6; printf '%-*s' $((UI_COLS - 12)) ''; tput cup "$row" 6; printf '%s [Y/n] ' "$1"; tput cnorm; read -r answer </dev/tty; tput civis
    fi
    case "${answer:-y}" in [Yy]*) return 0;; *) return 1;; esac
}

ui_prompt_row() {   # questions sit right under the card they belong to, not at the bottom of a tall terminal
    if [ -n "${UI_CARD_END:-}" ] && [ $((UI_CARD_END + 1)) -lt $((UI_ROWS - 4)) ]; then echo $((UI_CARD_END + 1)); else echo $((UI_ROWS - 4)); fi
}

ui_ask() {          # ui_ask <prompt> <default>  prints the answer; honours SETUP_YES
    local answer
    [ "${SETUP_YES:-0}" = 1 ] && { printf '%s' "$2"; return; }
    exec 4>&1 1>/dev/tty
    if [ "$UI_PLAIN" = 1 ]; then printf '%s [%s]: ' "$1" "$2" >/dev/tty; else
        local row; row=$(ui_prompt_row); tput cup "$row" 6; printf '%-*s' $((UI_COLS - 12)) ''; tput cup "$row" 6; printf '%s [%s]: ' "$1" "$2"; tput cnorm
    fi
    read -r answer </dev/tty; [ "$UI_PLAIN" = 1 ] || tput civis
    printf '%s' "${answer:-$2}" >&4
}

# ui_pick_options <name|label|value>...   lets the user change values; prints name=value lines
ui_pick_options() {
    local names=() labels=() values=() index=0 entry answer
    for entry in "$@"; do
        names+=("${entry%%|*}"); entry="${entry#*|}"; labels+=("${entry%%|*}"); values+=("${entry#*|}")
    done
    if [ "${SETUP_YES:-0}" != 1 ]; then
        exec 4>&1 1>/dev/tty
        while :; do
            if [ "$UI_PLAIN" = 1 ]; then
                printf '\nSetup Options (type a number to change it, ENTER to continue):\n'
                for index in "${!names[@]}"; do printf '  %2d. %-42s %s\n' $((index + 1)) "${labels[$index]}" "${values[$index]}"; done
                printf '> '
            else
                ui_field; ui_center 2 "Setup Options"
                ui_text 4 "Setup detected these values. Type a number to change one, ENTER to accept."
                for index in "${!names[@]}"; do tput cup $((6 + index)) 8; printf '%2d. %-42s %s' $((index + 1)) "${labels[$index]}" "${values[$index]}"; done
                tput cup $((8 + ${#names[@]})) 8; printf 'Option number: '; tput cnorm
            fi
            read -r answer </dev/tty; [ "$UI_PLAIN" = 1 ] || tput civis
            [ -z "$answer" ] && break
            case "$answer" in *[!0-9]*) continue;; esac
            index=$((answer - 1)); [ "$index" -ge 0 ] && [ "$index" -lt "${#names[@]}" ] || continue
            values[$index]=$(ui_ask "${labels[$index]}" "${values[$index]}")
        done
        exec 1>&4
    fi
    for index in "${!names[@]}"; do printf '%s=%s\n' "${names[$index]}" "${values[$index]}"; done
}

# ui_pick_components <name:label:default>...   prints the selected names, space separated
ui_pick_components() {
    local names=() labels=() picked=() index=0 entry answer
    for entry in "$@"; do
        names+=("${entry%%:*}"); entry="${entry#*:}"; labels+=("${entry%:*}"); picked+=("${entry##*:}")
    done
    if [ "${SETUP_YES:-0}" != 1 ]; then
        exec 4>&1 1>/dev/tty
        while :; do
            if [ "$UI_PLAIN" = 1 ]; then
                printf '\nSelect Components (type a number to toggle, ENTER to continue):\n'
                for index in "${!names[@]}"; do printf '  %2d. [%s] %s\n' $((index + 1)) "$([ "${picked[$index]}" = 1 ] && echo X || echo ' ')" "${labels[$index]}"; done
                printf '> '
            else
                ui_field; ui_center 2 "Select Components"
                ui_text 4 "To add or remove a component, type its number and press ENTER."
                ui_text 5 "Press ENTER on an empty line when the list is right."
                for index in "${!names[@]}"; do tput cup $((7 + index)) 8; printf '%2d. [%s] %s' $((index + 1)) "$([ "${picked[$index]}" = 1 ] && echo X || echo ' ')" "${labels[$index]}"; done
                tput cup $((9 + ${#names[@]})) 8; printf 'Component number: '; tput cnorm
            fi
            read -r answer </dev/tty; [ "$UI_PLAIN" = 1 ] || tput civis
            [ -z "$answer" ] && break
            case "$answer" in
                all) for index in "${!names[@]}"; do picked[$index]=1; done;;
                none) for index in "${!names[@]}"; do picked[$index]=0; done;;
                *[!0-9]*) ;;
                *) index=$((answer - 1)); [ "$index" -ge 0 ] && [ "$index" -lt "${#names[@]}" ] && picked[$index]=$(( 1 - picked[$index] ));;
            esac
        done
        exec 1>&4
    fi
    for index in "${!names[@]}"; do
        if [ "${picked[$index]}" = 1 ]; then printf '%s ' "${names[$index]}"; fi
    done
}
