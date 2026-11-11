# shellcheck shell=bash disable=SC2034
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
  SETUP_DISTRO=unknown
  SETUP_DISTRO_LIKE=""
  SETUP_PKG=""
  [ -r /etc/os-release ] && SETUP_DISTRO=$(
    . /etc/os-release
    printf '%s' "${ID:-unknown}"
  )
  [ -r /etc/os-release ] && SETUP_DISTRO_LIKE=$(
    . /etc/os-release
    printf '%s' "${ID_LIKE:-}"
  )
  for manager in dnf apt-get pacman zypper; do command -v $manager >/dev/null 2>&1 && {
    SETUP_PKG=$manager
    break
  }; done
}

detect_plasma() {
  # Offscreen: without a display plasmashell aborts, and every abort is a crash report raised in the session.
  SETUP_PLASMA_VERSION=$(QT_QPA_PLATFORM=offscreen plasmashell --version 2>/dev/null | awk '{print $2}' || true)
  SETUP_SESSION=${XDG_SESSION_TYPE:-unknown}
  SETUP_DESKTOP=${XDG_CURRENT_DESKTOP:-unknown}
  SETUP_PLASMA_MAJOR=${SETUP_PLASMA_VERSION%%.*}
  SETUP_IN_PLASMA=0
  if [[ ":$SETUP_DESKTOP:" == *:KDE:* ]]; then SETUP_IN_PLASMA=1; fi
}

# Logical geometry of the primary (first enabled) output and its scale, from kscreen-doctor.
detect_screen() {
  SETUP_WIDTH=2560
  SETUP_HEIGHT=1440
  SETUP_SCALE=1
  SETUP_SCREEN_SOURCE=default
  local dump geometry scale
  # kscreen-doctor asks the compositor: without one (no display) it aborts, which is a crash report.
  dump=""
  if [ -n "${WAYLAND_DISPLAY:-}${DISPLAY:-}" ]; then dump=$(kscreen-doctor -o 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g' || true); fi
  geometry=$(printf '%s\n' "$dump" | awk '/enabled/{on=1} on && /Geometry:/{print $3; exit}')
  scale=$(printf '%s\n' "$dump" | awk '/enabled/{on=1} on && /Scale:/{print $2; exit}')
  if [[ "$geometry" =~ ^([0-9]+)x([0-9]+)$ ]]; then
    SETUP_WIDTH=${BASH_REMATCH[1]}
    SETUP_HEIGHT=${BASH_REMATCH[2]}
    SETUP_SCREEN_SOURCE=kscreen-doctor
  fi
  if [[ "$scale" =~ ^[0-9.]+$ ]]; then SETUP_SCALE=$scale; fi
  SETUP_DPI=$(awk -v s="$SETUP_SCALE" 'BEGIN{printf "%d", 96*s + 0.5}')
}

detect_paths() {
  SETUP_CHICAGO95_SRC=""
  for candidate in "${CHICAGO95_SRC:-}" "$HOME/src/Chicago95" "$HOME/Chicago95" "$HOME/git/Chicago95" /usr/share/Chicago95; do
    [ -n "$candidate" ] && [ -d "$candidate/Theme/Chicago95" ] && {
      SETUP_CHICAGO95_SRC=$candidate
      break
    }
  done
  SETUP_HACK_DIR=""
  for candidate in /usr/libexec/xscreensaver /usr/lib/xscreensaver /usr/lib64/xscreensaver /usr/lib/x86_64-linux-gnu/xscreensaver; do
    [ -d "$candidate" ] && {
      SETUP_HACK_DIR=$candidate
      break
    }
  done
  SETUP_FIREFOX_PROFILE=""
  # The profile in daily use is the one whose prefs.js changed last.
  local newest
  newest=$(find "$HOME/.mozilla/firefox" -mindepth 2 -maxdepth 2 -name prefs.js -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2- || true)
  [ -n "$newest" ] && SETUP_FIREFOX_PROFILE=$(dirname "$newest")
  SETUP_HAS_THUNAR=0
  command -v thunar >/dev/null 2>&1 && SETUP_HAS_THUNAR=1
  SETUP_HAS_QMMP=0
  command -v qmmp >/dev/null 2>&1 && SETUP_HAS_QMMP=1
  SETUP_HAS_SDDM=0
  command -v sddm >/dev/null 2>&1 && SETUP_HAS_SDDM=1
  SETUP_HAS_GIT=0
  command -v git >/dev/null 2>&1 && SETUP_HAS_GIT=1
  SETUP_HAS_XSETTINGSD=0
  command -v xsettingsd >/dev/null 2>&1 && SETUP_HAS_XSETTINGSD=1
  SETUP_HAS_KWINRULES=0
  [ -f "$HOME/.config/kwinrulesrc" ] && SETUP_HAS_KWINRULES=1
  SETUP_SHELL_SRC=""
  if [ -d /usr/share/plasma/shells/org.kde.plasma.desktop ]; then SETUP_SHELL_SRC=/usr/share/plasma/shells/org.kde.plasma.desktop; fi
}

detect_python() {
  SETUP_PY_MISSING=""
  for module in PySide6:python3-pyside6 xdg:python3-pyxdg dbus:python3-dbus gi:python3-gobject; do
    python3 -c "import ${module%%:*}" 2>/dev/null || SETUP_PY_MISSING="$SETUP_PY_MISSING ${module#*:}"
  done
}

# Package names differ per distribution, not per package manager: Fedora and RHEL both use dnf.
detect_plasma_hint() {
  case " $SETUP_DISTRO $SETUP_DISTRO_LIKE " in
  *" fedora "*)
    [ "$SETUP_DISTRO" = fedora ] && {
      echo "sudo dnf install @kde-desktop-environment"
      return
    }
    echo "sudo dnf install epel-release && sudo dnf group install \"KDE Plasma Workspaces\""
    ;;
  *" ubuntu "* | *" debian "*) echo "sudo apt install kde-plasma-desktop   (Plasma 6 needs Debian 13 / Ubuntu 25.04 or newer)" ;;
  *" arch "*) echo "sudo pacman -S plasma-meta" ;;
  *" suse "* | *" opensuse "*) echo "sudo zypper install -t pattern kde_plasma" ;;
  *) echo "install KDE Plasma 6 with your distribution's package manager" ;;
  esac
}

# The packages for the detected manager, as an argument list Setup can show or run.
detect_install_command() {
  case "$SETUP_PKG" in
  dnf) SETUP_INSTALL_CMD=(sudo dnf install -y python3-pyside6 python3-pyxdg python3-dbus python3-gobject thunar xsettingsd tumbler qmmp qmmp-plugin-pack xscreensaver-extras xscreensaver-gl-extras) ;;
  apt-get) SETUP_INSTALL_CMD=(sudo apt install -y python3-pyside6.qtcore python3-pyside6.qtgui python3-pyside6.qtwidgets python3-xdg python3-dbus python3-gi thunar xsettingsd tumbler qmmp qmmp-plugin-pack xscreensaver-data-extra xscreensaver-gl-extra) ;;
  pacman) SETUP_INSTALL_CMD=(sudo pacman -S --needed pyside6 python-pyxdg python-dbus python-gobject thunar xsettingsd tumbler qmmp xscreensaver) ;;
  zypper) SETUP_INSTALL_CMD=(sudo zypper install -y python3-PySide6 python3-pyxdg python3-dbus-python python3-gobject thunar xsettingsd tumbler qmmp xscreensaver-data-extra) ;;
  *) SETUP_INSTALL_CMD=() ;;
  esac
}

detect_install_hint() {
  detect_install_command
  if [ ${#SETUP_INSTALL_CMD[@]} -gt 0 ]; then echo "${SETUP_INSTALL_CMD[*]}"; else
    echo "install PySide6, pyxdg, dbus-python, PyGObject, thunar, xsettingsd, qmmp and the xscreensaver hacks with your package manager"
  fi
}

font_installed() { fc-list : family 2>/dev/null | grep -iF "$1" >/dev/null; }

# Nonzero when something the package command provides is absent.
detect_packages_missing() {
  [ -n "$SETUP_PY_MISSING" ] || [ "$SETUP_HAS_THUNAR" = 0 ] || [ "$SETUP_HAS_QMMP" = 0 ] ||
    [ -z "$SETUP_HACK_DIR" ] || [ "$SETUP_HAS_XSETTINGSD" = 0 ]
}

# One line per prerequisite: name, status, what it is for.
detect_prerequisites() {
  local font="${SETUP_FONT:-MS W98 UI}"
  row() { printf '%-20s %-11s %s\n' "$1" "$2" "$3"; }
  row "KDE Plasma 6" "${SETUP_PLASMA_VERSION:-MISSING}" "required"
  if [ -n "$SETUP_CHICAGO95_SRC" ]; then
    row "Chicago95 checkout" "OK" "$SETUP_CHICAGO95_SRC"
  elif [ "$SETUP_HAS_GIT" = 1 ]; then
    row "Chicago95 checkout" "will clone" "into ~/src/Chicago95"
  else row "Chicago95 checkout" "MISSING" "install git so Setup can clone it"; fi
  row "Python modules" "$([ -z "$SETUP_PY_MISSING" ] && echo OK || echo MISSING)" "${SETUP_PY_MISSING:-Start menu, notifications, Clippy}"
  row "xsettingsd" "$([ "$SETUP_HAS_XSETTINGSD" = 1 ] && echo OK || echo missing)" "GTK theme for X11 apps"
  row "Thunar" "$([ "$SETUP_HAS_THUNAR" = 1 ] && echo OK || echo missing)" "Explorer (Dolphin is used otherwise)"
  row "qmmp" "$([ "$SETUP_HAS_QMMP" = 1 ] && echo OK || echo missing)" "Winamp"
  row "XScreenSaver hacks" "$([ -n "$SETUP_HACK_DIR" ] && echo OK || echo missing)" "Screensaver"
  if font_installed "More Perfect DOS VGA"; then
    row "DOS VGA font" "OK" "terminal and Clippy text"
  else row "DOS VGA font" "will copy" "from the Chicago95 checkout"; fi
  if font_installed "$font"; then
    row "$font font" "OK" "UI text"
  else row "$font font" "missing" "copy the OTF to ~/.local/share/fonts"; fi
}

detect_summary() {
  cat <<EOF
Distribution:      $SETUP_DISTRO ($SETUP_PKG)
Plasma:            ${SETUP_PLASMA_VERSION:-not found}, running $SETUP_DESKTOP on $SETUP_SESSION
Screen (logical):  ${SETUP_WIDTH}x${SETUP_HEIGHT} at ${SETUP_SCALE}x  (${SETUP_SCREEN_SOURCE}); X11 DPI will be $SETUP_DPI
Chicago95 source:  ${SETUP_CHICAGO95_SRC:-not found (will clone)}
XScreenSaver:      ${SETUP_HACK_DIR:-hacks not installed}
Firefox profile:   ${SETUP_FIREFOX_PROFILE:-none}
Thunar / qmmp:     $([ "$SETUP_HAS_THUNAR" = 1 ] && echo yes || echo no) / $([ "$SETUP_HAS_QMMP" = 1 ] && echo yes || echo no)
Python modules:    ${SETUP_PY_MISSING:+missing:$SETUP_PY_MISSING}${SETUP_PY_MISSING:-all present}
EOF
}
