# One function per component. Sourced by install.sh after detect.sh and ui.sh.
# Every file written goes through put_file/put_tree so it is backed up and recorded
# in the manifest that uninstall.sh reads.

PANEL_HEIGHT=28
MENU_HEIGHT=189
CLIPPY_W=124; CLIPPY_H=93; CLIPPY_MARGIN=24
NOTIFY_W=340

STATE_DIR="$HOME/.local/share/chicago95"
MANIFEST="$STATE_DIR/installed-files.txt"
BACKUP_DIR="$STATE_DIR/backup-$(date +%Y%m%d-%H%M%S)"

run() { if [ "${SETUP_DRY_RUN:-0}" = 1 ]; then printf '  would: %s\n' "$*" >>"$SETUP_LOG"; else "$@"; fi; }

record() { [ "${SETUP_DRY_RUN:-0}" = 1 ] || installed_by_setup "$1" || { mkdir -p "$STATE_DIR"; printf '%s\n' "$1" >>"$MANIFEST"; }; }

installed_by_setup() { [ -f "$MANIFEST" ] && grep -qxF "$1" "$MANIFEST"; }

backup() {          # backup <path>  keeps the pre-install version; a file Setup put there earlier is not backed up
    local path="$1"
    [ -e "$path" ] || [ -L "$path" ] || return 0
    [ "${SETUP_DRY_RUN:-0}" = 1 ] && return 0
    installed_by_setup "$path" && return 0
    local dest="$BACKUP_DIR/${path#"$HOME"/}"
    mkdir -p "$(dirname "$dest")"
    [ -e "$dest" ] || cp -a "$path" "$dest"
}

short_path() { local path="${1#"$REPO"/}"; printf '%s' "${path/#"$HOME"/\~}"; }

show_copy() {       # show_copy <source> <destination>   on screen and in the Setup log, one line per file
    local line
    line="$(short_path "$1") → $(short_path "$2")"
    printf '%s: %s -> %s\n' "$([ "${SETUP_DRY_RUN:-0}" = 1 ] && echo would-copy || echo copied)" "$1" "$2" >>"$SETUP_LOG"
    COPIED=$((COPIED + 1)); ui_progress "$COPIED" "$TO_COPY" "$line"
}

put_file() {        # put_file <source> <destination>
    local source="$1" dest="$2"
    backup "$dest"; run mkdir -p "$(dirname "$dest")"; run cp "$source" "$dest"; record "$dest"
    show_copy "$source" "$dest"
}

put_tree() {        # put_tree <source dir> <destination dir>
    local source="$1" dest="$2" file
    backup "$dest"; run rm -rf "$dest"; run mkdir -p "$(dirname "$dest")"; run cp -r "$source" "$dest"; record "$dest"
    while IFS= read -r file; do show_copy "$file" "$dest/${file#"$source"/}"; done < <(find "$source" -type f | sort)
}

substitute_home() { [ "${SETUP_DRY_RUN:-0}" = 1 ] || grep -rlI '@HOME@' "$@" 2>/dev/null | xargs -r sed -i "s|@HOME@|$HOME|g"; }

kconf() { run kwriteconfig6 --file "$1" --group "$2" --key "$3" "${@:4}"; record "kconf:$1:$2:$3"; }


# --- KWin rules: merged as text, never through kwriteconfig6 (it drops every other group) ---

kwin_rule() {       # kwin_rule <group> <body lines...>   replaces or appends the group and lists it in Order=
    local group="$1"; shift
    local file="$HOME/.config/kwinrulesrc"
    [ "${SETUP_DRY_RUN:-0}" = 1 ] && { printf '  would: write kwin rule [%s]\n' "$group" >>"$SETUP_LOG"; return; }
    backup "$file"; mkdir -p "$(dirname "$file")"; touch "$file"
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

step_base() {
    if [ -z "$SETUP_CHICAGO95_SRC" ]; then
        ui_status "Downloading Chicago95 (about 100 MB)..."
        run git clone --depth 1 https://github.com/grassmunk/Chicago95 "$HOME/src/Chicago95" >>"$SETUP_LOG" 2>&1 && SETUP_CHICAGO95_SRC="$HOME/src/Chicago95"
    fi
    [ -n "$SETUP_CHICAGO95_SRC" ] || { ui_status "Chicago95 unavailable; skipping base theme"; return; }
    local src="$SETUP_CHICAGO95_SRC"
    [ -d ~/.themes/Chicago95 ] || put_tree "$src/Theme/Chicago95" ~/.themes/Chicago95
    [ -d ~/.icons/Chicago95 ] || put_tree "$src/Icons/Chicago95" ~/.icons/Chicago95
    [ -d ~/.icons/Chicago95_Animated_Hourglass_Cursors_HiDPI ] || put_tree "$src/Cursors/Chicago95_Animated_Hourglass_Cursors_HiDPI" ~/.icons/Chicago95_Animated_Hourglass_Cursors_HiDPI
    [ -d ~/.local/share/sounds/Chicago95 ] || put_tree "$src/sounds/Chicago95" ~/.local/share/sounds/Chicago95
    run mkdir -p ~/.local/share/icons; run ln -sfn ~/.icons/Chicago95 ~/.local/share/icons/Chicago95; record ~/.local/share/icons/Chicago95
    show_copy ~/.icons/Chicago95 ~/.local/share/icons/Chicago95
    if [ "${SETUP_DRY_RUN:-0}" != 1 ] && ! grep -q '^Inherits=' ~/.icons/Chicago95/index.theme; then
        sed -i '/^\[Icon Theme\]/a Inherits=hicolor,breeze' ~/.icons/Chicago95/index.theme
    fi
    local font
    for font in "$src"/Fonts/vga_font/*.ttf; do
        [ -e "$font" ] && put_file "$font" ~/.local/share/fonts/Chicago95/"$(basename "$font")"
    done
    run fc-cache -f ~/.local/share/fonts >/dev/null 2>&1 || true
    put_file "$REPO/config/xsettingsd/xsettingsd.conf" ~/.config/xsettingsd/xsettingsd.conf
    kconf kdeglobals Icons Theme Chicago95
    run plasma-apply-cursortheme Chicago95_Animated_Hourglass_Cursors_HiDPI --size "${SETUP_CURSOR:-32}" >>"$SETUP_LOG" 2>&1 || true
    pkill -HUP xsettingsd 2>/dev/null || true
}

step_look() {       # decoration, Plasma style, colours, widget style, DPI
    put_tree "$REPO/aurorae/theme" ~/.local/share/aurorae/themes/Chicago95
    for extra in bevel.py make_chicago95_aurorae.py start-button.png start-button-pressed.png; do put_file "$REPO/aurorae/$extra" ~/.local/share/aurorae/themes/Chicago95/$extra; done
    put_file "$REPO/plasma-style/make_chicago95_plasmastyle.py" ~/.local/share/aurorae/themes/Chicago95/make_chicago95_plasmastyle.py
    put_tree "$REPO/plasma-style/theme" ~/.local/share/plasma/desktoptheme/Chicago95
    put_file "$REPO/config/Chicago95.colors" ~/.local/share/color-schemes/Chicago95.colors
    kconf kdeglobals KDE widgetStyle Windows
    kconf kdeglobals General AccentColor --delete
    kconf kwinrc org.kde.kdecoration2 library org.kde.kwin.aurorae
    kconf kwinrc org.kde.kdecoration2 theme __aurorae__svg__Chicago95
    kconf kwinrc org.kde.kdecoration2 BorderSize Normal
    run plasma-apply-colorscheme Chicago95 >>"$SETUP_LOG" 2>&1 || true
    run plasma-apply-desktoptheme Chicago95 >>"$SETUP_LOG" 2>&1 || true
    if [ "$SETUP_SCALE" != 1 ]; then
        backup ~/.Xresources
        if [ "${SETUP_DRY_RUN:-0}" != 1 ]; then
            grep -v '^Xft.dpi:' ~/.Xresources 2>/dev/null > ~/.Xresources.chicago95 || true
            printf 'Xft.dpi: %s\n' "$SETUP_DPI" >> ~/.Xresources.chicago95; mv ~/.Xresources.chicago95 ~/.Xresources
            xrdb -merge ~/.Xresources 2>/dev/null || true
        fi
        show_copy "(Xft.dpi: $SETUP_DPI)" ~/.Xresources
        record ~/.Xresources
        kconf kcmfonts General forceFontDPI "$SETUP_DPI"
    fi
}

step_taskbar() {
    for plasmoid in "$REPO"/plasmoids/org.chicago95.*; do put_tree "$plasmoid" ~/.local/share/plasma/plasmoids/"$(basename "$plasmoid")"; done
    put_file "$REPO/plasmoids/panel-layout.js" ~/.local/share/chicago95/panel-layout.js
    put_file "$REPO/config/applications/chicago95-showdesktop.desktop" ~/.local/share/applications/chicago95-showdesktop.desktop
    put_file "$REPO/data/icons/tray-arrow-up.png" ~/.local/share/chicago95/icons/tray-arrow-up.png
    substitute_home ~/.local/share/plasma/plasmoids/org.chicago95.start ~/.local/share/plasma/plasmoids/org.chicago95.trayframe
}

step_tools_common() {   # shared by every PySide6 component; idempotent
    [ "${TOOLS_COMMON_DONE:-0}" = 1 ] && return; TOOLS_COMMON_DONE=1
    put_file "$REPO/lib/win95ui.py" ~/.local/lib/chicago95/win95ui.py
    put_file "$REPO/data/plasmashell-menus.qss" ~/.local/share/chicago95/plasmashell-menus.qss
    put_file "$REPO/config/systemd/plasma-plasmashell.service.d-chicago95-menus.conf" ~/.config/systemd/user/plasma-plasmashell.service.d/chicago95-menus.conf
    put_tree "$REPO/data/qml" ~/.local/share/chicago95/qml
    put_file "$REPO/config/environment.d/chicago95.conf" ~/.config/environment.d/chicago95.conf
    substitute_home ~/.config/environment.d/chicago95.conf
    run systemctl --user set-environment "QML_IMPORT_PATH=$HOME/.local/share/chicago95/qml"
}

step_startmenu() {
    step_tools_common
    put_file "$REPO/bin/chicago95-startmenu" ~/.local/bin/chicago95-startmenu; run chmod +x ~/.local/bin/chicago95-startmenu
    put_file "$REPO/bin/chicago95-shutdown" ~/.local/bin/chicago95-shutdown; run chmod +x ~/.local/bin/chicago95-shutdown
    for entry in chicago95-startmenu chicago95-shutdown; do put_file "$REPO/config/applications/$entry.desktop" ~/.local/share/applications/$entry.desktop; done
    put_file "$REPO/config/autostart/chicago95-startmenu.desktop" ~/.config/autostart/chicago95-startmenu.desktop
    substitute_home ~/.local/share/applications ~/.config/autostart
    kwin_rule chicago95-startmenu "Description=Chicago95 Start menu" "wmclass=chicago95-startmenu" "wmclassmatch=1" \
        "title=chicago95-startmenu-root" "titlematch=1" "position=0,$(( SETUP_HEIGHT - PANEL_HEIGHT - MENU_HEIGHT ))" "positionrule=2" \
        "placement=Zero" "placementrule=2" "above=true" "aboverule=2" "skiptaskbar=true" "skiptaskbarrule=2" \
        "skippager=true" "skippagerrule=2" "skipswitcher=true" "skipswitcherrule=2" "noborder=true" "noborderrule=2" "types=1"
}

step_notifications() {
    step_tools_common
    put_file "$REPO/bin/chicago95-notifyd" ~/.local/bin/chicago95-notifyd; run chmod +x ~/.local/bin/chicago95-notifyd
    put_file "$REPO/config/applications/chicago95-notifyd.desktop" ~/.local/share/applications/chicago95-notifyd.desktop
    put_file "$REPO/config/systemd/chicago95-notifyd.service" ~/.config/systemd/user/chicago95-notifyd.service
    put_tree "$REPO/kwin-effects/chicago95notifications" ~/.local/share/kwin/effects/chicago95notifications
    substitute_home ~/.local/share/applications
    local host_h=$(( SETUP_HEIGHT * 3 / 4 + 20 ))
    kwin_rule chicago95-notifyd "Description=Chicago95 notification column" "wmclass=chicago95-notifyd" "wmclassmatch=1" \
        "title=chicago95-notifyd-host" "titlematch=1" "position=$(( SETUP_WIDTH - NOTIFY_W )),$(( SETUP_HEIGHT - PANEL_HEIGHT - host_h ))" "positionrule=2" \
        "placement=Zero" "placementrule=2" "acceptfocus=false" "acceptfocusrule=2" "skiptaskbar=true" "skiptaskbarrule=2" \
        "skippager=true" "skippagerrule=2" "skipswitcher=true" "skipswitcherrule=2" "noborder=true" "noborderrule=2" "above=true" "aboverule=2" "types=1"
    kconf kwinrc Plugins chicago95notificationsEnabled true
    run systemctl --user daemon-reload; run systemctl --user enable chicago95-notifyd.service >>"$SETUP_LOG" 2>&1
}

step_clippy() {
    step_tools_common
    put_file "$REPO/bin/chicago95-clippy" ~/.local/bin/chicago95-clippy; run chmod +x ~/.local/bin/chicago95-clippy
    put_tree "$REPO/data/clippy" ~/.local/share/chicago95/clippy
    put_file "$REPO/config/applications/chicago95-clippy.desktop" ~/.local/share/applications/chicago95-clippy.desktop
    case "${SETUP_CLIPPY_AUTOSTART:-yes}" in y*|Y*) put_file "$REPO/config/autostart/chicago95-clippy.desktop" ~/.config/autostart/chicago95-clippy.desktop;; esac
    substitute_home ~/.local/share/applications ~/.config/autostart
    kwin_rule chicago95-clippy "Description=Chicago95 Office Assistant" "wmclass=chicago95-clippy" "wmclassmatch=1" \
        "position=$(( SETUP_WIDTH - CLIPPY_W - CLIPPY_MARGIN )),$(( SETUP_HEIGHT - PANEL_HEIGHT - CLIPPY_H - CLIPPY_MARGIN ))" "positionrule=3" \
        "placement=Zero" "placementrule=3" "skiptaskbar=true" "skiptaskbarrule=2" "skippager=true" "skippagerrule=2" "noborder=true" "noborderrule=2" "types=1"
}

step_extras() {     # System Properties, Device Manager, Dial-Up, Deezer helper, login chime
    step_tools_common
    for tool in sysprops devmgr dialup deezer; do put_file "$REPO/bin/chicago95-$tool" ~/.local/bin/chicago95-$tool; run chmod +x ~/.local/bin/chicago95-$tool; done
    put_tree "$REPO/data/sounds" ~/.local/share/chicago95/sounds
    put_file "$REPO/config/autostart/chicago95-startup.desktop" ~/.config/autostart/chicago95-startup.desktop
    substitute_home ~/.config/autostart
}

step_screensaver() {
    [ -n "$SETUP_HACK_DIR" ] || ui_status "XScreenSaver hacks not installed; the screensaver will do nothing until they are"
    step_tools_common
    put_file "$REPO/bin/chicago95-screensaver" ~/.local/bin/chicago95-screensaver; run chmod +x ~/.local/bin/chicago95-screensaver
    # Earlier versions polled an idle time that Wayland never reports, from an autostart entry.
    if [ -e ~/.config/autostart/chicago95-screensaver.desktop ]; then
        run systemctl --user stop 'app-chicago95\x2dscreensaver@autostart.service'
        run rm -f ~/.config/autostart/chicago95-screensaver.desktop
    fi
    # Plasma's power management watches idle time on Wayland and runs this command when it is reached.
    local command="$HOME/.local/bin/chicago95-screensaver --hack ${SETUP_SAVER:-deepstars}" profile
    backup ~/.config/powerdevilrc
    for profile in AC Battery LowBattery; do
        run kwriteconfig6 --file powerdevilrc --group "$profile" --group RunScript --key RunScriptIdleTimeoutSec $(( ${SETUP_IDLE_MIN:-5} * 60 ))
        run kwriteconfig6 --file powerdevilrc --group "$profile" --group RunScript --key IdleTimeoutCommand "$command"
    done
    record "powerdevil:RunScript"
    show_copy "(run $command after ${SETUP_IDLE_MIN:-5} min idle)" ~/.config/powerdevilrc
    run systemctl --user restart plasma-powerdevil.service
}

step_winamp() {
    [ "$SETUP_HAS_QMMP" = 1 ] || { ui_status "qmmp not installed; skipping Winamp"; return; }
    put_file "$REPO/config/applications/qmmp.desktop" ~/.local/share/applications/qmmp.desktop
    kwin_rule qmmp "Description=Chicago95 Winamp (qmmp) without frame" "wmclass=qmmp" "wmclassmatch=1" "noborder=true" "noborderrule=2" "types=1"
    run mkdir -p ~/.qmmp/skins
    [ -n "$SETUP_CHICAGO95_SRC" ] && [ -d "$SETUP_CHICAGO95_SRC/Extras/qmmp" ] && put_tree "$SETUP_CHICAGO95_SRC/Extras/qmmp" ~/.qmmp/skins/chicago95 || true
}

step_explorer() {
    if [ "${SETUP_EXPLORER:-thunar}" = dolphin ] || [ "$SETUP_HAS_THUNAR" != 1 ]; then
        [ "$SETUP_HAS_THUNAR" = 1 ] || ui_status "Thunar not installed; configuring Dolphin instead"
        put_file "$REPO/config/dolphin/dolphinui.rc" ~/.local/share/kxmlgui6/dolphin/dolphinui.rc
        kconf dolphinrc General ShowFullPath true
        kconf dolphinrc General EditableUrl true
        kconf dolphinrc General ShowStatusBar true
        kconf dolphinrc General ShowSpaceInfo true
        return
    fi
    local thunar_xml=~/.config/xfce4/xfconf/xfce-perchannel-xml/thunar.xml
    if [ -f "$thunar_xml" ]; then ui_status "Keeping your existing Thunar settings (see config/thunar/thunar.xml)"; else
        pkill -x thunar 2>/dev/null || true; pkill -x xfconfd 2>/dev/null || true; sleep 1
        put_file "$REPO/config/thunar/thunar.xml" "$thunar_xml"
    fi
    backup ~/.config/gtk-3.0/gtk.css
    if ! grep -q 'Chicago95 Thunar' ~/.config/gtk-3.0/gtk.css 2>/dev/null; then
        [ "${SETUP_DRY_RUN:-0}" = 1 ] || { mkdir -p ~/.config/gtk-3.0; cat "$REPO/config/gtk-3.0/gtk.css" >> ~/.config/gtk-3.0/gtk.css; record ~/.config/gtk-3.0/gtk.css; }
        show_copy "$REPO/config/gtk-3.0/gtk.css" ~/.config/gtk-3.0/gtk.css
    fi
    put_file "$REPO/config/dolphin/dolphinui.rc" ~/.local/share/kxmlgui6/dolphin/dolphinui.rc
    run xdg-mime default thunar.desktop inode/directory
}

step_lockscreen() {
    [ -n "$SETUP_SHELL_SRC" ] || { ui_status "Plasma desktop shell package not found; skipping lock screen"; return; }
    local dst=~/.local/share/plasma/shells/org.kde.plasma.desktop
    backup "$dst"; run rm -rf "$dst"; run mkdir -p "$dst/contents"
    for entry in "$SETUP_SHELL_SRC"/*; do [ "$(basename "$entry")" = contents ] || { run ln -s "$entry" "$dst/"; show_copy "$entry" "$dst/$(basename "$entry")"; }; done
    for entry in "$SETUP_SHELL_SRC"/contents/*; do [ "$(basename "$entry")" = lockscreen ] || { run ln -s "$entry" "$dst/contents/"; show_copy "$entry" "$dst/contents/$(basename "$entry")"; }; done
    put_tree "$REPO/lockscreen/lockscreen" "$dst/contents/lockscreen"; record "$dst"
}

step_splash() {
    put_tree "$REPO/splash/chicago95.splashscreen" ~/.local/share/plasma/look-and-feel/chicago95.splashscreen
    kconf ksplashrc KSplash Theme chicago95.splashscreen
    kconf ksplashrc KSplash Engine KSplashQML
}

SDDM_THEME_SRC="$HOME/src/Chicago95/Extras/sddm/Chicago95"
SDDM_THEME_DIR=/usr/share/sddm/themes/Chicago95
# sddm.conf.d is read in name order and the last file wins, so zz- beats leftovers such as
# another theme's sddm.conf that would otherwise override Plasma's kde_settings.conf.
SDDM_OVERRIDE=/etc/sddm.conf.d/zz-chicago95.conf

step_sddm() {       # login screen; system files, so it asks for the administrator password first
    [ -d "$SDDM_THEME_SRC" ] || [ -d "$SDDM_THEME_DIR" ] || { ui_status "Chicago95 SDDM theme not found in $SDDM_THEME_SRC; skipping login screen"; return; }
    local commands=()
    [ -d "$SDDM_THEME_SRC" ] && commands+=("sudo mkdir -p $SDDM_THEME_DIR" "sudo cp -r $SDDM_THEME_SRC/. $SDDM_THEME_DIR/")
    commands+=("sudo tee $SDDM_OVERRIDE   (writes: [Theme] Current=Chicago95)")
    if ! ui_sudo "To change the login screen, Setup must write to a system folder." "${commands[@]}"; then
        ui_message "Login screen not changed" "No administrator password was accepted, so Setup skipped the login screen." \
            "Everything else is installed. Run ./install.sh --components=sddm to try again."
        return
    fi
    if [ -d "$SDDM_THEME_SRC" ]; then
        run sudo mkdir -p "$SDDM_THEME_DIR"; run sudo cp -r "$SDDM_THEME_SRC/." "$SDDM_THEME_DIR/"
        local file
        while IFS= read -r file; do show_copy "$file" "$SDDM_THEME_DIR/${file#"$SDDM_THEME_SRC"/}"; done < <(find "$SDDM_THEME_SRC" -type f | sort)
    fi
    if [ "${SETUP_DRY_RUN:-0}" = 1 ]; then run sudo tee "$SDDM_OVERRIDE"; else printf '[Theme]\nCurrent=Chicago95\n' | sudo tee "$SDDM_OVERRIDE" >/dev/null; fi
    record "root:$SDDM_OVERRIDE"
    show_copy "(Setup)" "$SDDM_OVERRIDE"
}

step_firefox() {
    [ -n "$SETUP_FIREFOX_PROFILE" ] || { ui_status "No default Firefox profile found; skipping"; return; }
    local target="$SETUP_FIREFOX_PROFILE/user.js"
    backup "$target"
    if [ "${SETUP_DRY_RUN:-0}" != 1 ]; then
        { [ -f "$target" ] && grep -v 'Chicago95' "$target"; cat "$REPO/config/firefox-user.js"; } > "$target.chicago95" && mv "$target.chicago95" "$target"
    fi
    record "$target"; show_copy "$REPO/config/firefox-user.js" "$target"
}

step_fonts() {
    local family="${SETUP_FONT:-MS W98 UI}"
    if ! fc-list : family | grep -i "$family" >/dev/null; then
        ui_status "Font '$family' not installed; UI text keeps your current font until it is in ~/.local/share/fonts"; return
    fi
    kconf kdeglobals General font "$family,9,-1,5,50,0,0,0,0,0"
    kconf kdeglobals General menuFont "$family,9,-1,5,50,0,0,0,0,0"
    kconf kdeglobals General toolBarFont "$family,9,-1,5,50,0,0,0,0,0"
    kconf kdeglobals General smallestReadableFont "$family,8,-1,5,50,0,0,0,0,0"
    kconf kdeglobals WM activeFont "$family,9,-1,5,75,0,0,0,0,0"
}

finish_session() {
    run rm -rf ~/.cache/plasmashell/qmlcache ~/.cache/ksvg-elements ~/.cache/plasma_theme_Chicago95.kcache
    run systemctl --user daemon-reload
    kwin_reconfigure
    if [ "${SETUP_DRY_RUN:-0}" != 1 ] && [ "$SETUP_IN_PLASMA" = 1 ]; then
        systemctl --user stop plasma-plasmashell.service 2>/dev/null || true
        systemctl --user is-enabled chicago95-notifyd.service >/dev/null 2>&1 && systemctl --user restart chicago95-notifyd.service || true
        systemctl --user start plasma-plasmashell.service 2>/dev/null || true
    fi
}
