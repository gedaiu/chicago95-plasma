#!/usr/bin/env bash
# Build the Plasma 6.8 Wayland decoration, theme and backdrop shader against the local KWin ABI.
set -euo pipefail
repo=$(cd "$(dirname "$0")/.." && pwd)
work="$repo/build/aero-native"
mkdir -p "$work"
install_built() {
  local plugins
  plugins=$(qtpaths6 --plugin-dir)
  sudo install -Dm644 "$work/decoration/theme/theme.rcc" /usr/share/smod/decorations/Aero.smod.rcc
  sudo install -Dm755 "$work/decoration/bin/org.smod.smod.so" "$plugins/org.kde.kdecoration3/org.smod.smod.so"
  sudo install -Dm755 "$work/effects/bin/aeroglassblur.so" "$plugins/kwin/effects/plugins/aeroglassblur.so"
}

case "${1:-}" in
--install-built)
  if [ "$(kwin_wayland --version)" != "$(cat "$work/kwin-version")" ]; then
    echo "Rebuild the plugins against the installed KWin version." >&2
    exit 1
  fi
  install_built
  exit
  ;;
"" | --install) ;;
*)
  echo "Usage: $0 [--install|--install-built]" >&2
  exit 2
  ;;
esac

fetch_source() {
  local project=$1 revision=$2 digest=$3 source="$work/$1-$2" archive="$work/$1-$2.tar.gz"
  if [ ! -d "$source" ]; then
    curl -fLsS "https://codeload.github.com/aeroshell-desktop/$project/tar.gz/$revision" -o "$archive"
    printf '%s  %s\n' "$digest" "$archive" | sha256sum -c -
    local stage
    stage=$(mktemp -d "$work/source.XXXXXX")
    tar -xf "$archive" --strip-components=1 -C "$stage"
    mv -T "$stage" "$source"
  fi
}

frame=67e24c0212a955a8684701cdde05c27215618e7b
glass=4a28963f1f751e93350e86e2b5bf1afb5380fcd6
fetch_source smod "$frame" 6bd9ff041868f25268097f7f2344f7db1255003de6ef8c7a6b0ce4daf89f09c8
fetch_source aeroshell-kwin-components "$glass" e4366cef6db34dbb7efd9868d1244c54f0382c143ec88e83b96504d96e67044f
cmake -S "$work/smod-$frame" -B "$work/decoration" -G Ninja -DBUILD_EFFECT=OFF -DCMAKE_INSTALL_PREFIX=/usr
cmake --build "$work/decoration" --target theme smoddecoration
cmake -S "$work/aeroshell-kwin-components-$glass" -B "$work/effects" -G Ninja -DKWIN_INSTALL_MISC=OFF -DCMAKE_INSTALL_PREFIX=/usr
cmake --build "$work/effects" --target aeroglassblur
kwin_wayland --version >"$work/kwin-version"
if [ "${1:-}" = --install ]; then install_built; fi
