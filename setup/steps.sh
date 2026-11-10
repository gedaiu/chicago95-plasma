# One function per component. Sourced by install.sh after detect.sh and ui.sh.
# Every file written goes through put_file/put_tree so it is backed up and recorded
# in the manifest that uninstall.sh reads.

PANEL_HEIGHT=28
MENU_HEIGHT=239  # fallback only; place_start_menu measures the real height
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
    # GTK programs draw their own widgets, and GTK 4 its own title bars: both take the classic theme.
    local version
    for version in 3.0 4.0; do
        backup ~/.config/gtk-$version/settings.ini; run mkdir -p ~/.config/gtk-$version
        run kwriteconfig6 --file ~/.config/gtk-$version/settings.ini --group Settings --key gtk-theme-name Chicago95
        record ~/.config/gtk-$version/settings.ini
    done
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
    run plasma-apply-cursortheme Chicago95_Animated_Hourglass_Cursors_HiDPI --size "${SETUP_CURSOR:-32}" >>"$SETUP_LOG" 2>&1 || true
    pkill -HUP xsettingsd 2>/dev/null || true
}

rgb() { printf '%d,%d,%d' "0x${1:1:2}" "0x${1:3:2}" "0x${1:5:2}"; }

# The colour scheme holds the title colours; System Settings > Colors can change them later, and
# chicago95-colors.path redraws the decoration whenever it does.
apply_title_colors() {
    local active="${SETUP_TITLE_ACTIVE:-#000080}" inactive="${SETUP_TITLE_INACTIVE:-#808080}"
    kconf kdeglobals WM activeBackground "$(rgb "${active%%,*}")"
    kconf kdeglobals WM activeBlend "$(rgb "${active##*,}")"
    kconf kdeglobals WM inactiveBackground "$(rgb "${inactive%%,*}")"
    kconf kdeglobals WM inactiveBlend "$(rgb "${inactive##*,}")"
    step_tools_common
    put_file "$REPO/bin/chicago95-sync-colors" ~/.local/bin/chicago95-sync-colors; run chmod +x ~/.local/bin/chicago95-sync-colors
    put_file "$REPO/config/systemd/chicago95-colors.path" ~/.config/systemd/user/chicago95-colors.path
    put_file "$REPO/config/systemd/chicago95-colors.service" ~/.config/systemd/user/chicago95-colors.service
    run systemctl --user daemon-reload
    run systemctl --user enable --now chicago95-colors.path >>"$SETUP_LOG" 2>&1
    run python3 ~/.local/bin/chicago95-sync-colors --force >>"$SETUP_LOG"
    show_copy "(title bars: active $active, inactive $inactive)" ~/.local/share/aurorae/themes/Chicago95/decoration.svg
}

# Icon set per look: 1995 Chicago95 (installed by the base step), 1998 SE98, 2000 ClassicOS-2000.
# The packs are downloaded into ~/src like the Chicago95 checkout; ClassicOS-2000 ships SVG sources and
# builds its theme with its own script (copies and links only), and falls back to SE98 for missing icons.
install_icon_pack() {   # install_icon_pack se98|classicos2000   -> 0 when the theme is in ~/.local/share/icons
    local theme repo source built
    case "$1" in
        se98) theme=SE98; repo=https://github.com/nestoris/Win98SE; source="$HOME/src/Win98SE"; built="$source/SE98";;
        classicos2000) theme=ClassicOS-2000; repo=https://github.com/ClassicOS-Themes/ClassicOS-2000-Icons
                       source="$HOME/src/ClassicOS-2000-Icons"; built="$source/build/ClassicOS-2000";;
    esac
    if [ ! -d "$source" ]; then
        ui_status "Downloading the $theme icon set..."
        run git clone --depth 1 "$repo" "$source" >>"$SETUP_LOG" 2>&1 || return 1
    fi
    if [ "$1" = classicos2000 ] && [ ! -d "$built" ]; then
        run bash -c "cd '$source' && ICON_THEME_NAME=ClassicOS-2000 MAKEFREEDESKTOP=TRUE MAKEPNG=FALSE ./build-icons.sh" >>"$SETUP_LOG" 2>&1
    fi
    if [ -d "$built" ]; then put_tree "$built" "$HOME/.local/share/icons/$theme"; else show_copy "$built" "$HOME/.local/share/icons/$theme"; fi
}

apply_icon_set() {
    local theme=Chicago95
    case "${SETUP_ICONS:-chicago95}" in
        se98) install_icon_pack se98 && theme=SE98;;
        classicos2000) install_icon_pack se98; install_icon_pack classicos2000 && theme=ClassicOS-2000;;
    esac
    [ "$theme" = Chicago95 ] && [ "${SETUP_ICONS:-chicago95}" != chicago95 ] && ui_status "That icon set is unavailable; keeping Chicago95"
    kconf kdeglobals Icons Theme "$theme"
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
    apply_icon_set
    if [ -n "${SETUP_FACE:-}" ]; then   # the 2000 look: warm grey face and its selection colour
        local group
        for group in Colors:Window Colors:Button Colors:Header Colors:Complementary; do kconf kdeglobals "$group" BackgroundNormal "$SETUP_FACE"; done
        kconf kdeglobals Colors:Selection BackgroundNormal "$SETUP_SELECTION"
        kconf kdeglobals WM inactiveForeground "$SETUP_FACE"   # 2000's inactive title text is the face colour
    fi
    # The originals' title bar: the window icon on the left; minimize, maximize and close on the right.
    kconf kwinrc org.kde.kdecoration2 ButtonsOnLeft M
    kconf kwinrc org.kde.kdecoration2 ButtonsOnRight IAX
    # chicago95-sync-colors draws the bevels with the look's colours, and reads the look from here.
    run kwriteconfig6 --file chicago95rc --group StartMenu --key style "${SETUP_MENU_STYLE:-1995}"
    apply_title_colors
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
    put_file "$REPO/lib/chicago95ui.py" ~/.local/lib/chicago95/chicago95ui.py
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
    # Whatever logo was picked lands in one known file, so it can be swapped later without Setup.
    local logo_file; logo_file=$(start_logo_file)
    put_file "$(start_logo_source)" "$logo_file"
    SETUP_START_LOGO=$logo_file
    run kwriteconfig6 --file chicago95rc --group StartMenu --key bannerText "${SETUP_BANNER_TEXT:-Chicago95}"
    run kwriteconfig6 --file chicago95rc --group StartMenu --key bannerBackground "${SETUP_BANNER_BG:-#808080}"
    run kwriteconfig6 --file chicago95rc --group StartMenu --key bannerTextColor "${SETUP_BANNER_FG:-#C0C0C0}"
    run kwriteconfig6 --file chicago95rc --group StartMenu --key style "${SETUP_MENU_STYLE:-1995}"
    write_branding
    show_copy "(Start menu banner: ${SETUP_BANNER_TEXT:-Chicago95}, ${SETUP_BANNER_BG:-#808080} / ${SETUP_BANNER_FG:-#C0C0C0})" ~/.config/chicago95rc
    place_start_menu
}

# The menu's height depends on its style and font, so it is measured (offscreen, with the settings just
# written) rather than assumed; the rule puts the menu's bottom edge just above the taskbar (one pixel up:
# at fractional scales the menu's height rounds up and would otherwise cover the taskbar's top line).
place_start_menu() {
    local height
    height=$(QT_QPA_PLATFORM=offscreen QT_SCALE_FACTOR=1 python3 "$REPO/bin/chicago95-startmenu" --root-height 2>/dev/null | tail -1)
    [[ "$height" =~ ^[0-9]+$ ]] || height=$MENU_HEIGHT
    kwin_rule chicago95-startmenu "Description=Chicago95 Start menu" "wmclass=chicago95-startmenu" "wmclassmatch=1" \
        "title=chicago95-startmenu-root" "titlematch=1" "position=0,$(( SETUP_HEIGHT - PANEL_HEIGHT - height - 1 ))" "positionrule=2" \
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
    [ "${SETUP_DRY_RUN:-0}" = 1 ] || sed -i "s|@SOUND_THEME@|${SETUP_SOUND_THEME:-Chicago95}|g" ~/.config/autostart/chicago95-startup.desktop
}

step_sounds() {     # the Windows 98, Plus! and Windows 2000 sound themes, and the one chosen for events
    local theme
    for theme in "$REPO"/data/sound-themes/*/; do
        theme=${theme%/}; put_tree "$theme" ~/.local/share/sounds/"${theme##*/}"
    done
    kconf kdeglobals Sounds Theme "${SETUP_SOUND_THEME:-Chicago95}"
    if [ -f ~/.config/xsettingsd/xsettingsd.conf ]; then
        run sed -i "s|^Net/SoundThemeName .*|Net/SoundThemeName \"${SETUP_SOUND_THEME:-Chicago95}\"|" ~/.config/xsettingsd/xsettingsd.conf
        [ "${SETUP_DRY_RUN:-0}" = 1 ] || pkill -HUP xsettingsd 2>/dev/null || true
    fi
    if [ -f ~/.config/autostart/chicago95-startup.desktop ]; then
        run sed -i "s|sounds/[^/]*/stereo|sounds/${SETUP_SOUND_THEME:-Chicago95}/stereo|" ~/.config/autostart/chicago95-startup.desktop
    fi
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

step_splash() {     # the loading screen follows the login style; its texts and pictures go into settings.js
    local dir=~/.local/share/plasma/look-and-feel/chicago95.splashscreen/contents/splash logo image
    put_tree "$REPO/splash/chicago95.splashscreen" ~/.local/share/plasma/look-and-feel/chicago95.splashscreen
    ensure_waving_flag
    put_company_logo
    logo=$(login_logo)
    image=$(image_source "${SETUP_SPLASH_IMAGE:-classic}")
    if [ "${SETUP_DRY_RUN:-0}" = 1 ]; then run tee "$dir/settings.js"; else
        { echo ".pragma library"
          echo "var style = $(js_string "${SETUP_LOGIN_STYLE:-classic}")"
          echo "var brandText = $(js_string "${SETUP_BANNER_TEXT:-Chicago95}")"
          echo "var brandLogo = $(js_string "$logo")"
          echo "var edition = $(js_string "${SETUP_EDITION:-Professional}")"
          echo "var tagline = $(js_string "${SETUP_TAGLINE:-Built on Linux Technology}")"
          echo "var company = $(js_string "${SETUP_COMPANY:-KDE}")"
          echo "var companyLogo = $(js_string "$(company_logo_file)")"
          echo "var loadingText = $(js_string "${SETUP_LOADING_TEXT:-Starting up...}")"
          echo "var footer = $(js_string "$(printf '%s' "${SETUP_LOADING_FOOTER:-Chicago95 for KDE Plasma}" | sed "s/%h/$(hostname)/g")")"
          echo "var picture = $(js_string "$image")"
        } >"$dir/settings.js"
    fi
    show_copy "(loading screen: ${SETUP_LOGIN_STYLE:-classic}, ${SETUP_BANNER_TEXT:-Chicago95})" "$dir/settings.js"
    kconf ksplashrc KSplash Theme chicago95.splashscreen
    kconf ksplashrc KSplash Engine KSplashQML
}

SDDM_THEME_SRC="$REPO/sddm/Chicago95Plasma"
SDDM_THEME_DIR=/usr/share/sddm/themes/Chicago95Plasma
# The greeter runs as the sddm user, who cannot read fonts in a home folder, so the UI font goes next to the theme.
SDDM_FONT="$HOME/.local/share/fonts/MSW98UI-Regular.otf"
# sddm.conf.d is read in name order and the last file wins, so zz- beats leftovers such as
# another theme's sddm.conf that would otherwise override Plasma's kde_settings.conf.
SDDM_OVERRIDE=/etc/sddm.conf.d/zz-chicago95.conf

# The waving flag is a trademark, so it isn't bundled: Setup downloads the public-domain picture from
# Wikimedia Commons on this machine when it is picked, and cuts the flag out of it.
WAVING_FLAG="$HOME/.local/share/chicago95/waving-flag.png"

ensure_waving_flag() {  # falls back to the classic flag when the download fails
    [ "${SETUP_LOGIN_LOGO:-start}" = waving-flag ] && [ ! -f "$WAVING_FLAG" ] || return 0
    run mkdir -p "$(dirname "$WAVING_FLAG")"
    if run python3 "$REPO/setup/fetch-waving-flag.py" "$WAVING_FLAG"; then
        record "$WAVING_FLAG"; show_copy "(downloaded from Wikimedia Commons)" "$WAVING_FLAG"; return
    fi
    ui_status "Could not download the waving flag; the login and loading screens show the classic flag"
    SETUP_LOGIN_LOGO=flag
}

# The company logo, when the user picked one, lands in one known file like the Start logo; "text" means
# the corner shows the company's name instead.
company_logo_file() {
    [ "${SETUP_COMPANY_LOGO:-text}" = text ] || printf '%s' "$HOME/.local/share/chicago95/company-logo.$(extension "$SETUP_COMPANY_LOGO")"
}

put_company_logo() { local file; file=$(company_logo_file); [ -z "$file" ] || put_file "$SETUP_COMPANY_LOGO" "$file"; }

# The login and loading screens' logo; "start" is the Start button's, from its copy once Setup made one.
login_logo() {
    if [ "${SETUP_LOGIN_LOGO:-start}" = start ] && [ -f "$(start_logo_file)" ]; then start_logo_file; else image_source "${SETUP_LOGIN_LOGO:-start}"; fi
}

write_branding() {  # [Branding] in chicago95rc: what the 2000 banners show (Shut Down dialog, login banner)
    put_company_logo
    ensure_waving_flag
    run kwriteconfig6 --file chicago95rc --group Branding --key osName "${SETUP_BANNER_TEXT:-Chicago95}"
    run kwriteconfig6 --file chicago95rc --group Branding --key osLogo "$(login_logo)"
    run kwriteconfig6 --file chicago95rc --group Branding --key osCompany "${SETUP_COMPANY:-KDE}"
    run kwriteconfig6 --file chicago95rc --group Branding --key osEdition "${SETUP_EDITION:-Professional}"
    run kwriteconfig6 --file chicago95rc --group Branding --key tagline "${SETUP_TAGLINE:-Built on Linux Technology}"
    run kwriteconfig6 --file chicago95rc --group Branding --key companyLogo "$(company_logo_file)"
    record ~/.config/chicago95rc
}

start_logo_source() {  # the image behind the Start logo choice: a bundled logo name, or the user's file
    case "${SETUP_START_LOGO:-flag}" in
        flag) printf '%s' "$REPO/plasmoids/org.chicago95.start/contents/images/logo-flag-16.png";;   # pixel art at the button's size
        penguin) printf '%s' "$REPO/plasmoids/org.chicago95.start/contents/images/logo-penguin.svg";;
        *) printf '%s' "$SETUP_START_LOGO";;
    esac
}

# image_source <choice>   the file behind a picture choice: a bundled name, or the user's own file.
image_source() {
    case "$1" in
        start) start_logo_source;;
        flag) printf '%s' "$REPO/plasmoids/org.chicago95.start/contents/images/logo-flag.png";;
        penguin) printf '%s' "$REPO/plasmoids/org.chicago95.start/contents/images/logo-penguin.svg";;
        waving-flag) printf '%s' "$WAVING_FLAG";;
        keys) printf '%s' "$SDDM_THEME_SRC/key.svg";;
        padlock) printf '%s' "$SDDM_THEME_SRC/padlock.svg";;
        classic) printf '%s' "$REPO/splash/chicago95.splashscreen/contents/splash/images/background.png";;
        *) printf '%s' "$1";;
    esac
}

extension() { printf '%s' "${1##*.}"; }

# The copy keeps the source's extension, so the image loader never has to guess PNG from SVG.
start_logo_file() { local source; source=$(start_logo_source); printf '%s' "$HOME/.local/share/chicago95/start-logo.${source##*.}"; }

# The login theme's settings. Values travel through the environment into awk, so any text the user
# typed (slashes, ampersands, quotes) lands in theme.conf as written.
sddm_theme_conf() {
    LOGIN_STYLE="${SETUP_LOGIN_STYLE:-classic}" \
    LOGIN_TITLE="${SETUP_LOGIN_TITLE:-Log On to %h}" LOGIN_MESSAGE="${SETUP_LOGIN_MESSAGE:-Type a user name and password to log on.}" \
    LOGIN_ICON="login-icon.$(extension "$(image_source "${SETUP_LOGIN_ICON:-keys}")")" \
    TITLE_ACTIVE="$([ "${SETUP_LOGIN_STYLE:-classic}" = 2000 ] && echo '#0A246A,#A6CAF0')" \
    awk -F= 'BEGIN {
            value["loginStyle"] = ENVIRON["LOGIN_STYLE"]; value["loginTitle"] = ENVIRON["LOGIN_TITLE"]
            value["loginMessage"] = ENVIRON["LOGIN_MESSAGE"]; value["loginIcon"] = ENVIRON["LOGIN_ICON"]
            value["titleActive"] = ENVIRON["TITLE_ACTIVE"]
        }
        /^[A-Za-z]+=/ && ($1 in value) { print $1 "=" value[$1]; next }
        { print }' "$SDDM_THEME_SRC/theme.conf"
}

step_sddm() {       # login screen; system files, so it asks for the administrator password first
    local commands=("sudo mkdir -p $SDDM_THEME_DIR" "sudo cp -r $SDDM_THEME_SRC/. $SDDM_THEME_DIR/")
    [ -f "$SDDM_FONT" ] && commands+=("sudo cp $SDDM_FONT $SDDM_THEME_DIR/")
    local icon banner="$STATE_DIR/login-banner.png"
    icon=$(image_source "${SETUP_LOGIN_ICON:-keys}")
    commands+=("sudo cp $icon $SDDM_THEME_DIR/login-icon.$(extension "$icon")")
    # The 2000 banner is drawn here, as the user, by the Shut Down dialog's code; the greeter shows the picture.
    if [ "${SETUP_LOGIN_STYLE:-classic}" = 2000 ]; then
        write_branding
        run mkdir -p "$STATE_DIR"
        run env QT_QPA_PLATFORM=offscreen python3 "$REPO/bin/chicago95-shutdown" --login-banner "$banner"; record "$banner"
        commands+=("sudo cp $banner $SDDM_THEME_DIR/brand-banner.png")
    fi
    commands+=("sudo tee $SDDM_THEME_DIR/theme.conf   (writes: login style ${SETUP_LOGIN_STYLE:-classic})")
    commands+=("sudo tee $SDDM_OVERRIDE   (writes: [Theme] Current=Chicago95Plasma)")
    if ! ui_sudo "To change the login screen, Setup must write to a system folder." "${commands[@]}"; then
        ui_message "Login screen not changed" "No administrator password was accepted, so Setup skipped the login screen." \
            "Everything else is installed. Run ./install.sh --components=sddm to try again."
        return
    fi
    run sudo mkdir -p "$SDDM_THEME_DIR"; run sudo cp -r "$SDDM_THEME_SRC/." "$SDDM_THEME_DIR/"
    local file
    while IFS= read -r file; do show_copy "$file" "$SDDM_THEME_DIR/${file#"$SDDM_THEME_SRC"/}"; done < <(find "$SDDM_THEME_SRC" -type f | sort)
    if [ -f "$SDDM_FONT" ]; then run sudo cp "$SDDM_FONT" "$SDDM_THEME_DIR/"; show_copy "$SDDM_FONT" "$SDDM_THEME_DIR/$(basename "$SDDM_FONT")"; fi
    run sudo cp "$icon" "$SDDM_THEME_DIR/login-icon.$(extension "$icon")"; show_copy "$icon" "$SDDM_THEME_DIR/login-icon.$(extension "$icon")"
    if [ "${SETUP_LOGIN_STYLE:-classic}" = 2000 ]; then
        run sudo cp "$banner" "$SDDM_THEME_DIR/brand-banner.png"; show_copy "$banner" "$SDDM_THEME_DIR/brand-banner.png"
    fi
    if [ "${SETUP_DRY_RUN:-0}" = 1 ]; then run sudo tee "$SDDM_THEME_DIR/theme.conf"; else sddm_theme_conf | sudo tee "$SDDM_THEME_DIR/theme.conf" >/dev/null; fi
    show_copy "(login style: ${SETUP_LOGIN_STYLE:-classic})" "$SDDM_THEME_DIR/theme.conf"
    if [ "${SETUP_DRY_RUN:-0}" = 1 ]; then run sudo tee "$SDDM_OVERRIDE"; else printf '[Theme]\nCurrent=Chicago95Plasma\n' | sudo tee "$SDDM_OVERRIDE" >/dev/null; fi
    record "root:$SDDM_OVERRIDE"
    record "root-dir:$SDDM_THEME_DIR"
    show_copy "(Setup)" "$SDDM_OVERRIDE"
}

step_plymouth() {    # boot screen; system files and a rebuilt boot image, so it asks for the administrator password
    local theme_src="${SETUP_CHICAGO95_SRC:-$HOME/src/Chicago95}/Plymouth/Chicago95" current
    command -v plymouth-set-default-theme >/dev/null 2>&1 || { ui_status "Plymouth is not installed; skipping the boot screen"; return; }
    [ -d "$theme_src" ] || { ui_status "Chicago95 Plymouth theme not found in $theme_src; skipping the boot screen"; return; }
    current=$(plymouth-set-default-theme 2>/dev/null || true)
    [ "$current" = Chicago95 ] && { ui_status "The boot screen is already Chicago95"; return; }
    if ! ui_sudo "To change the boot screen, Setup must copy the theme to a system folder and rebuild the boot image. That takes a minute or two." \
            "sudo cp -r $theme_src /usr/share/plymouth/themes/" "sudo plymouth-set-default-theme -R Chicago95"; then
        ui_message "Boot screen not changed" "No administrator password was accepted, so Setup skipped the boot screen." \
            "Everything else is installed. Run ./install.sh --components=plymouth to try again."
        return
    fi
    run sudo cp -r "$theme_src" /usr/share/plymouth/themes/
    show_copy "$theme_src" /usr/share/plymouth/themes/Chicago95
    ui_status "Rebuilding the boot image; this takes a minute or two..."
    run sudo plymouth-set-default-theme -R Chicago95 >>"$SETUP_LOG" 2>&1
    record "plymouth:$current"
}

plasma_script() { gdbus call --session --dest org.kde.plasmashell --object-path /PlasmaShell --method org.kde.PlasmaShell.evaluateScript "$1"; }

offer_taskbar() {   # replaces the panels with the Chicago95 taskbar once the user agrees; skipped when it is already there
    [ "$SETUP_IN_PLASMA" = 1 ] && [ "${SETUP_DRY_RUN:-0}" = 0 ] || return 0
    local attempt
    for attempt in 1 2 3 4 5 6 7 8 9 10; do plasma_script 'print("ready")' >/dev/null 2>&1 && break; sleep 1; done
    if [[ "$(plasma_script 'print(panels().some(panel => panel.widgets().some(widget => widget.type == "org.chicago95.tasks")))' 2>/dev/null)" == *true* ]]; then
        ui_status "The Chicago95 taskbar is already in place"; return 0
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
$(sed -e "s/^panel.height = 28;/panel.height = $PANEL_HEIGHT;/" -e "s/^const look = \"1995\";/const look = \"${SETUP_MENU_STYLE:-1995}\";/" ~/.local/share/chicago95/panel-layout.js)" >>"$SETUP_LOG" 2>&1
}

js_string() { python3 -c 'import json, sys; print(json.dumps(sys.argv[1]))' "$1"; }

apply_start_button() {  # writes the chosen text and logo into every Start button on the panels
    [ "$SETUP_IN_PLASMA" = 1 ] && [ "${SETUP_DRY_RUN:-0}" = 0 ] || return 0
    plasma_script "panels().forEach(panel => panel.widgets('org.chicago95.start').forEach(widget => {
        widget.currentConfigGroup = ['General'];
        widget.writeConfig('buttonText', $(js_string "${SETUP_START_TEXT:-Start}"));
        widget.writeConfig('logo', $(js_string "${SETUP_START_LOGO:-flag}"));
        widget.writeConfig('look', $(js_string "${SETUP_MENU_STYLE:-1995}"));
    }))" >>"$SETUP_LOG" 2>&1
}

restart_start_menu() {  # the menu stays resident; a reinstall must replace the running copy
    [ "${SETUP_DRY_RUN:-0}" = 0 ] || return 0
    local pid_file="${XDG_RUNTIME_DIR:-/tmp}/chicago95-startmenu.pid"
    [ -f "$pid_file" ] && kill -TERM "$(cat "$pid_file")" 2>/dev/null
    systemctl --user start 'app-chicago95\x2dstartmenu@autostart.service' 2>/dev/null || true
}

offer_logout() {    # some parts start only with a new session; never logs out without a yes
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
    [ -n "$SETUP_FIREFOX_PROFILE" ] || { ui_status "No default Firefox profile found; skipping"; return; }
    local target="$SETUP_FIREFOX_PROFILE/user.js"
    backup "$target"
    if [ "${SETUP_DRY_RUN:-0}" != 1 ]; then
        { [ -f "$target" ] && grep -v 'Chicago95' "$target"; cat "$REPO/config/firefox-user.js"; } > "$target.chicago95" && mv "$target.chicago95" "$target"
    fi
    record "$target"; show_copy "$REPO/config/firefox-user.js" "$target"
}

# Runs before the components, so the login screen copies the repaired font too.
fix_font_spaces() {  # MS W98 UI Regular's no-break space is a third as wide as its space; editors draw spaces with it
    local family="${SETUP_FONT:-MS W98 UI}" file
    while IFS= read -r file; do
        backup "$file"
        run python3 "$REPO/setup/fix-font-spaces.py" "$file" >>"$SETUP_LOG"
        show_copy "(no-break space made as wide as space)" "$file"
    done < <(fc-list -f '%{file}\n' "$family" 2>/dev/null | grep "^$HOME/" | sort)
    run fc-cache -f "$HOME/.local/share/fonts"
}

APP_FONT_KEYS=(font menuFont toolBarFont smallestReadableFont)

step_fonts() {      # SETUP_FONT_SCOPE: everywhere (all programs), desktop (title bars only) or none
    local family="${SETUP_FONT:-MS W98 UI}" key
    if ! fc-list : family | grep -i "$family" >/dev/null; then
        ui_status "Font '$family' not installed; UI text keeps your current font until it is in ~/.local/share/fonts"; return
    fi
    case "${SETUP_FONT_SCOPE:-everywhere}" in
        everywhere)
            kconf kdeglobals General font "$family,9,-1,5,50,0,0,0,0,0"
            kconf kdeglobals General menuFont "$family,9,-1,5,50,0,0,0,0,0"
            kconf kdeglobals General toolBarFont "$family,9,-1,5,50,0,0,0,0,0"
            kconf kdeglobals General smallestReadableFont "$family,8,-1,5,50,0,0,0,0,0";;
        *)  # A reinstall with a narrower scope takes back what an earlier "everywhere" set.
            for key in "${APP_FONT_KEYS[@]}"; do
                installed_by_setup "kconf:kdeglobals:General:$key" && run kwriteconfig6 --file kdeglobals --group General --key "$key" --delete
            done;;
    esac
    case "${SETUP_FONT_SCOPE:-everywhere}" in
        none) installed_by_setup "kconf:kdeglobals:WM:activeFont" && run kwriteconfig6 --file kdeglobals --group WM --key activeFont --delete;;
        *) kconf kdeglobals WM activeFont "$family,8,-1,5,75,0,0,0,0,0";;   # 8 points: the originals' 11px titles
    esac
    # A pixel font: drawn without smoothing, its edges stay as sharp as the originals' text.
    [ "${SETUP_FONT_SCOPE:-everywhere}" = none ] || put_file "$REPO/config/fontconfig/60-chicago95-pixel-font.conf" \
        ~/.config/fontconfig/conf.d/60-chicago95-pixel-font.conf
    return 0
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
