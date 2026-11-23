#!/usr/bin/env bash
# Fetch only the login artwork. Authentication and session handling stay in the local SDDM theme.
set -eu
dest=${1:?destination directory required}
base=https://raw.githubusercontent.com/aeroshell-desktop/aerothemeplasma/f51ca15f4668a81d908505b422e5d560f35fe241/plasma/sddm/sddm-theme-mod
mkdir -p "$dest"
temp=$(mktemp -d "$dest/.download.XXXXXXXX")
trap 'rmdir "$temp" 2>/dev/null || true' EXIT
converter="$(dirname "$0")/vector_art.py"
for asset in background Assets/{12223,user,go,gohover,gopressed,input,input-focus,switch-user-button,switch-user-button-hover,switch-user-button-active,power,power-hover,power-active,power-glyph,power-glyph-arrow,12298,12299,12300,12301,12302,access-button,access-button-hover,12213}.png; do
  name=${asset##*/}
  if [ ! -s "$dest/$name" ]; then
    curl -fsSL --retry 2 "$base/$asset" -o "$temp/$name"
    mv "$temp/$name" "$dest/$name"
  fi
  svg="$dest/${name%.png}.svg"
  if [[ "$name" == *.png && "$name" != user.png && ( ! -s "$svg" || "$converter" -nt "$svg" || "$dest/$name" -nt "$svg" ) ]]; then
    python3 "$converter" bitmap "$dest/$name" "$svg"
  fi
done
# Earlier releases generated a traced copy of the account photo in this cache.
# Both greeters now load the original photograph.
rm -f -- "$dest/user.svg"
