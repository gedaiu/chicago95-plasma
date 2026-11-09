# Collects everything about the machine that the steps need. Sourced by install.sh.
# Every value lands in a SETUP_* variable; nothing here writes to disk.

detect_all() {
    detect_distro
    detect_plasma
    detect_screen
    detect_paths
    detect_python
}

detect_distro() {
    SETUP_DISTRO=unknown; SETUP_PKG=""
    [ -r /etc/os-release ] && SETUP_DISTRO=$(. /etc/os-release; printf '%s' "${ID:-unknown}")
    for manager in dnf apt-get pacman zypper; do command -v $manager >/dev/null 2>&1 && { SETUP_PKG=$manager; break; }; done
}

detect_plasma() {
    SETUP_PLASMA_VERSION=$(plasmashell --version 2>/dev/null | awk '{print $2}')
    SETUP_SESSION=${XDG_SESSION_TYPE:-unknown}
    SETUP_PLASMA_MAJOR=${SETUP_PLASMA_VERSION%%.*}
}

# Logical geometry of the primary (first enabled) output and its scale, from kscreen-doctor.
detect_screen() {
    SETUP_WIDTH=2560; SETUP_HEIGHT=1440; SETUP_SCALE=1; SETUP_SCREEN_SOURCE=default
    local dump
    dump=$(kscreen-doctor -o 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g') || return 0
    local geometry scale
    geometry=$(printf '%s\n' "$dump" | awk '/enabled/{on=1} on && /Geometry:/{print $3; exit}')
    scale=$(printf '%s\n' "$dump" | awk '/enabled/{on=1} on && /Scale:/{print $2; exit}')
    if [[ "$geometry" =~ ^([0-9]+)x([0-9]+)$ ]]; then
        SETUP_WIDTH=${BASH_REMATCH[1]}; SETUP_HEIGHT=${BASH_REMATCH[2]}; SETUP_SCREEN_SOURCE=kscreen-doctor
    fi
    [[ "$scale" =~ ^[0-9.]+$ ]] && SETUP_SCALE=$scale
    SETUP_DPI=$(awk -v s="$SETUP_SCALE" 'BEGIN{printf "%d", 96*s + 0.5}')
}

detect_paths() {
    SETUP_CHICAGO95_SRC=""
    for candidate in "${CHICAGO95_SRC:-}" "$HOME/src/Chicago95" "$HOME/Chicago95" "$HOME/git/Chicago95" /usr/share/Chicago95; do
        [ -n "$candidate" ] && [ -d "$candidate/Theme/Chicago95" ] && { SETUP_CHICAGO95_SRC=$candidate; break; }
    done
    SETUP_HACK_DIR=""
    for candidate in /usr/libexec/xscreensaver /usr/lib/xscreensaver /usr/lib64/xscreensaver /usr/lib/x86_64-linux-gnu/xscreensaver; do
        [ -d "$candidate" ] && { SETUP_HACK_DIR=$candidate; break; }
    done
    SETUP_FIREFOX_PROFILE=""
    # The profile in daily use is the one whose prefs.js changed last.
    local newest
    newest=$(ls -t "$HOME"/.mozilla/firefox/*/prefs.js 2>/dev/null | head -1)
    [ -n "$newest" ] && SETUP_FIREFOX_PROFILE=$(dirname "$newest")
    SETUP_HAS_THUNAR=0; command -v thunar >/dev/null 2>&1 && SETUP_HAS_THUNAR=1
    SETUP_HAS_QMMP=0; command -v qmmp >/dev/null 2>&1 && SETUP_HAS_QMMP=1
    SETUP_HAS_KWINRULES=0; [ -f "$HOME/.config/kwinrulesrc" ] && SETUP_HAS_KWINRULES=1
    SETUP_SHELL_SRC=""; [ -d /usr/share/plasma/shells/org.kde.plasma.desktop ] && SETUP_SHELL_SRC=/usr/share/plasma/shells/org.kde.plasma.desktop
}

detect_python() {
    SETUP_PY_MISSING=""
    for module in PySide6:python3-pyside6 xdg:python3-pyxdg dbus:python3-dbus gi:python3-gobject; do
        python3 -c "import ${module%%:*}" 2>/dev/null || SETUP_PY_MISSING="$SETUP_PY_MISSING ${module#*:}"
    done
}

# Names the packages for the detected manager; printed, never run.
detect_install_hint() {
    case "$SETUP_PKG" in
        dnf) echo "sudo dnf install python3-pyside6 python3-pyxdg python3-dbus python3-gobject thunar xsettingsd tumbler qmmp qmmp-plugin-pack xscreensaver-extras xscreensaver-gl-extras";;
        apt-get) echo "sudo apt install python3-pyside6.qtcore python3-pyside6.qtgui python3-pyside6.qtwidgets python3-xdg python3-dbus python3-gi thunar xsettingsd tumbler qmmp qmmp-plugin-pack xscreensaver-data-extra xscreensaver-gl-extra";;
        pacman) echo "sudo pacman -S pyside6 python-pyxdg python-dbus python-gobject thunar xsettingsd tumbler qmmp xscreensaver";;
        zypper) echo "sudo zypper install python3-PySide6 python3-pyxdg python3-dbus-python python3-gobject thunar xsettingsd tumbler qmmp xscreensaver-data-extra";;
        *) echo "install PySide6, pyxdg, dbus-python, PyGObject, thunar, xsettingsd, qmmp and the xscreensaver hacks with your package manager";;
    esac
}

detect_summary() {
    cat <<EOF
Distribution:      $SETUP_DISTRO ($SETUP_PKG)
Plasma:            ${SETUP_PLASMA_VERSION:-not found} on $SETUP_SESSION
Screen (logical):  ${SETUP_WIDTH}x${SETUP_HEIGHT} at ${SETUP_SCALE}x  (${SETUP_SCREEN_SOURCE}); X11 DPI will be $SETUP_DPI
Chicago95 source:  ${SETUP_CHICAGO95_SRC:-not found (will clone)}
XScreenSaver:      ${SETUP_HACK_DIR:-hacks not installed}
Firefox profile:   ${SETUP_FIREFOX_PROFILE:-none}
Thunar / qmmp:     $([ $SETUP_HAS_THUNAR = 1 ] && echo yes || echo no) / $([ $SETUP_HAS_QMMP = 1 ] && echo yes || echo no)
Python modules:    ${SETUP_PY_MISSING:+missing:$SETUP_PY_MISSING}${SETUP_PY_MISSING:-all present}
EOF
}
