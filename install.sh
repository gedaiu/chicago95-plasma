#!/usr/bin/env bash
# Installs chicago95-plasma into the current user's home. Re-runnable.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHICAGO95_SRC="${CHICAGO95_SRC:-$HOME/src/Chicago95}"

say() { printf '\033[1m%s\033[0m\n' "$*"; }

install_tree() {
    local source="$1" target="$2"
    mkdir -p "$(dirname "$target")"
    rm -rf "$target"
    cp -r "$source" "$target"
}

substitute_home() {
    grep -rlI '@HOME@' "$@" 2>/dev/null | xargs -r sed -i "s|@HOME@|$HOME|g"
}

require() {
    command -v "$1" >/dev/null 2>&1 || { echo "missing: $1" >&2; exit 1; }
}

require python3
require kwriteconfig6
require plasma-apply-colorscheme
python3 -c 'import PySide6, xdg, dbus' 2>/dev/null || { echo "need python3-pyside6, python3-pyxdg, python3-dbus" >&2; exit 1; }

say "Chicago95 base"
if [ -d "$CHICAGO95_SRC" ]; then
    mkdir -p ~/.themes ~/.icons ~/.local/share/icons ~/.local/share/sounds
    [ -d ~/.themes/Chicago95 ] || cp -r "$CHICAGO95_SRC/Theme/Chicago95" ~/.themes/
    [ -d ~/.icons/Chicago95 ] || cp -r "$CHICAGO95_SRC/Icons/Chicago95" ~/.icons/
    [ -d ~/.icons/Chicago95_Animated_Hourglass_Cursors_HiDPI ] || cp -r "$CHICAGO95_SRC/Cursors/Chicago95_Animated_Hourglass_Cursors_HiDPI" ~/.icons/
    [ -d ~/.local/share/sounds/Chicago95 ] || cp -r "$CHICAGO95_SRC/sounds/Chicago95" ~/.local/share/sounds/
    ln -sfn ~/.icons/Chicago95 ~/.local/share/icons/Chicago95
    grep -q '^Inherits=' ~/.icons/Chicago95/index.theme || sed -i '/^\[Icon Theme\]/a Inherits=hicolor,breeze' ~/.icons/Chicago95/index.theme
else
    echo "Chicago95 not found at $CHICAGO95_SRC; skipping the base theme (set CHICAGO95_SRC to override)" >&2
fi

say "Decoration and Plasma style"
install_tree "$REPO/aurorae/theme" ~/.local/share/aurorae/themes/Chicago95
cp "$REPO"/aurorae/{bevel.py,make_chicago95_aurorae.py,start-button.png,start-button-pressed.png} ~/.local/share/aurorae/themes/Chicago95/
cp "$REPO/plasma-style/make_chicago95_plasmastyle.py" ~/.local/share/aurorae/themes/Chicago95/
install_tree "$REPO/plasma-style/theme" ~/.local/share/plasma/desktoptheme/Chicago95
mkdir -p ~/.local/share/color-schemes
cp "$REPO/config/Chicago95.colors" ~/.local/share/color-schemes/

say "Plasmoids, tools, data"
for plasmoid in "$REPO"/plasmoids/org.chicago95.*; do
    install_tree "$plasmoid" ~/.local/share/plasma/plasmoids/"$(basename "$plasmoid")"
done
mkdir -p ~/.local/bin ~/.local/lib/chicago95 ~/.local/share/chicago95
cp "$REPO"/bin/chicago95-* ~/.local/bin/
chmod +x ~/.local/bin/chicago95-*
cp "$REPO/lib/win95ui.py" ~/.local/lib/chicago95/
cp -r "$REPO"/data/. ~/.local/share/chicago95/
install_tree "$REPO/kwin-effects/chicago95notifications" ~/.local/share/kwin/effects/chicago95notifications
install_tree "$REPO/splash/chicago95.splashscreen" ~/.local/share/plasma/look-and-feel/chicago95.splashscreen
substitute_home ~/.local/share/plasma/plasmoids/org.chicago95.start ~/.local/share/plasma/plasmoids/org.chicago95.trayframe

say "Config"
mkdir -p ~/.config/{autostart,environment.d,xsettingsd,gtk-3.0,xfce4/xfconf/xfce-perchannel-xml} \
         ~/.config/systemd/user/plasma-plasmashell.service.d ~/.local/share/applications ~/.local/share/kxmlgui6/dolphin
cp "$REPO"/config/autostart/*.desktop ~/.config/autostart/
cp "$REPO"/config/applications/*.desktop ~/.local/share/applications/
cp "$REPO/config/environment.d/chicago95.conf" ~/.config/environment.d/
cp "$REPO/config/systemd/plasma-plasmashell.service.d-chicago95-menus.conf" ~/.config/systemd/user/plasma-plasmashell.service.d/chicago95-menus.conf
cp "$REPO/config/systemd/chicago95-notifyd.service" ~/.config/systemd/user/
cp "$REPO/config/xsettingsd/xsettingsd.conf" ~/.config/xsettingsd/
cp "$REPO/config/dolphin/dolphinui.rc" ~/.local/share/kxmlgui6/dolphin/
substitute_home ~/.config/autostart ~/.local/share/applications ~/.config/environment.d/chicago95.conf
if [ ! -f ~/.config/xfce4/xfconf/xfce-perchannel-xml/thunar.xml ]; then
    cp "$REPO/config/thunar/thunar.xml" ~/.config/xfce4/xfconf/xfce-perchannel-xml/
fi
if ! grep -q 'Chicago95 Thunar' ~/.config/gtk-3.0/gtk.css 2>/dev/null; then
    cat "$REPO/config/gtk-3.0/gtk.css" >> ~/.config/gtk-3.0/gtk.css
fi
if [ ! -f ~/.config/kwinrulesrc ]; then
    cp "$REPO/config/kwin/kwinrulesrc" ~/.config/kwinrulesrc
else
    echo "~/.config/kwinrulesrc exists; merge the rule groups from config/kwin/kwinrulesrc by hand (text editor, not kwriteconfig6)" >&2
fi

say "Lock screen override"
shell_src=/usr/share/plasma/shells/org.kde.plasma.desktop
shell_dst=~/.local/share/plasma/shells/org.kde.plasma.desktop
if [ -d "$shell_src" ]; then
    rm -rf "$shell_dst"
    mkdir -p "$shell_dst/contents"
    for entry in "$shell_src"/*; do
        [ "$(basename "$entry")" = contents ] || ln -s "$entry" "$shell_dst/"
    done
    for entry in "$shell_src"/contents/*; do
        [ "$(basename "$entry")" = lockscreen ] || ln -s "$entry" "$shell_dst/contents/"
    done
    cp -r "$REPO/lockscreen/lockscreen" "$shell_dst/contents/lockscreen"
fi

say "Settings"
kwriteconfig6 --file kdeglobals --group KDE --key widgetStyle Windows
kwriteconfig6 --file kdeglobals --group Icons --key Theme Chicago95
kwriteconfig6 --file kdeglobals --group General --key AccentColor --delete
kwriteconfig6 --file kwinrc --group org.kde.kdecoration2 --key library org.kde.kwin.aurorae
kwriteconfig6 --file kwinrc --group org.kde.kdecoration2 --key theme __aurorae__svg__Chicago95
kwriteconfig6 --file kwinrc --group Plugins --key chicago95notificationsEnabled true
kwriteconfig6 --file ksplashrc --group KSplash --key Theme chicago95.splashscreen
plasma-apply-colorscheme Chicago95 >/dev/null
plasma-apply-desktoptheme Chicago95 >/dev/null
plasma-apply-cursortheme Chicago95_Animated_Hourglass_Cursors_HiDPI --size 48 >/dev/null 2>&1 || true

say "Services"
systemctl --user daemon-reload
systemctl --user enable chicago95-notifyd.service >/dev/null
rm -rf ~/.cache/plasmashell/qmlcache ~/.cache/ksvg-elements ~/.cache/plasma_theme_Chicago95.kcache
gdbus call --session --dest org.kde.KWin --object-path /KWin --method org.kde.KWin.reconfigure >/dev/null 2>&1 || true
systemctl --user stop plasma-plasmashell.service
systemctl --user restart chicago95-notifyd.service
systemctl --user start plasma-plasmashell.service

say "Done. Build the panel with plasmoids/panel-layout.js, then log out and back in once for the autostart entries and environment.d."
