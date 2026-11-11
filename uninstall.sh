#!/usr/bin/env bash
# Removes what install.sh put in place, using its manifest, and restores the most
# recent backup of every file it replaced. Settings go back to Breeze defaults.
set -euo pipefail

STATE_DIR="$HOME/.local/share/chicago95"
MANIFEST="$STATE_DIR/installed-files.txt"
[ -f "$MANIFEST" ] || {
  echo "No install manifest at $MANIFEST; nothing to do."
  exit 0
}

# Newest first, so the oldest copy of a file (the one from before Chicago95 was ever installed) is restored last and wins.
mapfile -t backups < <(find "$STATE_DIR" -maxdepth 1 -name 'backup-*' 2>/dev/null | sort -r)

remove_kwin_rule() {
  python3 - "$HOME/.config/kwinrulesrc" "$1" <<'EOF'
import sys, re, os
path, group = sys.argv[1:]
if not os.path.exists(path):
    sys.exit()
text = open(path).read()
text = re.sub(r"^\[%s\]\n(?:(?!\[).*\n?)*" % re.escape(group), "", text, flags=re.M)
text = re.sub(r"^Order=(.*)$", lambda m: "Order=" + ",".join(n for n in m.group(1).split(",") if n and n != group), text, flags=re.M)
open(path, "w").write(text)
EOF
}

while IFS= read -r entry; do
  case "$entry" in
  kconf:*)
    IFS=: read -r _ file group key <<<"$entry"
    case "$key" in
    widgetStyle) kwriteconfig6 --file "$file" --group "$group" --key "$key" Breeze ;;
    library) kwriteconfig6 --file "$file" --group "$group" --key "$key" org.kde.breeze ;;
    theme | Theme | Engine | forceFontDPI | chicago95notificationsEnabled | AccentColor | BorderSize | font | menuFont | toolBarFont | smallestReadableFont | activeFont | activeBackground | activeBlend | inactiveBackground | inactiveBlend | AnimationDurationFactor | squashEnabled | magiclampEnabled | fadeEnabled | scaleEnabled | glideEnabled | fallapartEnabled | wobblywindowsEnabled | fadingpopupsEnabled | slidingpopupsEnabled | maximizeEnabled) kwriteconfig6 --file "$file" --group "$group" --key "$key" --delete ;;
    esac
    ;;
  kwinrule:*) remove_kwin_rule "${entry#kwinrule:}" ;;
  root:*) sudo rm -f "${entry#root:}" ;;
  root-dir:/usr/share/sddm/themes/*) sudo rm -rf "${entry#root-dir:}" ;;
  plymouth:*) [ -n "${entry#plymouth:}" ] && sudo plymouth-set-default-theme -R "${entry#plymouth:}" ;;
  powerdevil:RunScript) for profile in AC Battery LowBattery; do
    for key in RunScriptIdleTimeoutSec IdleTimeoutCommand; do
      kwriteconfig6 --file powerdevilrc --group "$profile" --group RunScript --key "$key" --delete
    done
  done ;;
  "$HOME"/*) rm -rf "$entry" ;;
  esac
done <"$MANIFEST"

for backup in "${backups[@]}"; do
  (cd "$backup" && find . -mindepth 1 \( -type f -o -type l \) | while IFS= read -r rel; do
    mkdir -p "$HOME/$(dirname "$rel")"
    cp -a "$rel" "$HOME/$rel"
  done)
  # Renamed, not deleted: kept for reference, but a later uninstall will not restore them again.
  mv "$backup" "${backup%/*}/restored-${backup##*/}"
  echo "Restored backups from $backup"
done

plasma-apply-colorscheme BreezeLight >/dev/null 2>&1 || true
plasma-apply-desktoptheme default >/dev/null 2>&1 || true
systemctl --user disable --now chicago95-notifyd.service >/dev/null 2>&1 || true
systemctl --user disable --now chicago95-colors.path >/dev/null 2>&1 || true
systemctl --user restart plasma-powerdevil.service >/dev/null 2>&1 || true
systemctl --user unset-environment QML_IMPORT_PATH >/dev/null 2>&1 || true
systemctl --user daemon-reload
rm -rf ~/.cache/plasmashell/qmlcache ~/.cache/ksvg-elements ~/.cache/plasma_theme_Chicago95.kcache
gdbus call --session --dest org.kde.KWin --object-path /KWin --method org.kde.KWin.reconfigure >/dev/null 2>&1 || true
systemctl --user restart plasma-plasmashell.service
rm -f "$MANIFEST"
echo "Chicago95 for Plasma removed. The stock panel is not recreated; add one with a right-click on the desktop."
