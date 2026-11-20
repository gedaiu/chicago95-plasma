#!/usr/bin/env bash
# Stage an upstream asset pack in a private directory before Setup selects it.
set -eu
kind=${1:?expected cursors or sounds}
out=${2:?expected output directory}
case "$kind" in
  cursors)
    repo=lLexian/Windows-7-Aero-Cursors_Linux
    rev=f14c659082d38be7cbde2101ea5ab71987ead64e
    digest=3edb8c138d021d0514128b52513db872c54f6c62a6b4730ac8db79781e9029bc
    subdir=Windows-7-Aero-Cursors_Default ;;
  sounds)
    repo=Pendrag00n/Windows7Sounds
    rev=0c0c85f2d0a8205f85582cb94a9f6520dfb9b8ae
    digest=270441a82152db30421963010fb576bf9662f6821dc004ba7732e68ef4079365
    subdir=sounds ;;
  *) exit 2 ;;
esac
cache="${XDG_CACHE_HOME:-$HOME/.cache}/chicago95"
mkdir -p "$cache" "$out"
tmp=$(mktemp -d "$cache/desktop-assets.XXXXXXXX")
trap 'rm -rf "$tmp"' EXIT
archive="$cache/$rev.tar.gz"
valid() { printf '%s  %s\n' "$digest" "$1" | sha256sum --check --status; }
if [ ! -f "$archive" ] || ! valid "$archive"; then
  curl -fsSL --retry 2 "https://codeload.github.com/$repo/tar.gz/$rev" -o "$tmp/download"
  valid "$tmp/download"
  mv "$tmp/download" "$archive"
fi
tar -xzf "$archive" -C "$tmp" --strip-components=1 "${repo##*/}-$rev/$subdir"
if [ "$kind" = cursors ]; then
  cp -a "$tmp/$subdir/." "$out/"
  exit
fi
mkdir -p "$out/stereo"
while IFS='|' read -r event asset; do
  cp "$tmp/sounds/Windows $asset.wav" "$out/stereo/$event.wav"
done <<'SOUNDS'
desktop-login|Logon Sound
desktop-logout|Logoff Sound
system-ready|Startup
system-shutdown|Shutdown
dialog-error|Critical Stop
dialog-warning|Exclamation
dialog-information|Balloon
dialog-question|Default
bell-window-system|Ding
bell|Ding
message-new-instant|Notify
device-added|Hardware Insert
device-removed|Hardware Remove
device-error|Hardware Fail
battery-low|Battery Low
battery-caution|Battery Critical
trash-empty|Recycle
complete-print|Print complete
window-minimized|Minimize
window-unminimized|Restore
menu-click|Menu Command
SOUNDS
cp "$(dirname "$0")/sounds/index.theme" "$out/"
