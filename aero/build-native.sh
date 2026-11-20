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
"" | --install | --build-wobbly | --install-wobbly) ;;
*)
  echo "Usage: $0 [--install|--install-built|--build-wobbly|--install-wobbly]" >&2
  exit 2
  ;;
esac

fetch_source() {
  local project=$1 revision=$2 digest=$3 source="$work/$1-$2" archive="$work/$1-$2.tar.gz"
  if [ ! -d "$source" ]; then
    curl -fLsS "https://codeload.github.com/${4:-aeroshell-desktop}/$project/tar.gz/$revision" -o "$archive"
    printf '%s  %s\n' "$digest" "$archive" | sha256sum -c -
    local stage
    stage=$(mktemp -d "$work/source.XXXXXX")
    tar -xf "$archive" --strip-components=1 -C "$stage"
    mv -T "$stage" "$source"
  fi
}

if [[ "${1:-}" == --build-wobbly || "${1:-}" == --install-wobbly ]]; then
  if [ "$1" = --install-wobbly ]; then
    elevate=(sudo)
    [ -z "${SUDO_ASKPASS:-}" ] || elevate+=(-A)
    if command -v dnf >/dev/null && rpm -q fedora-release-common >/dev/null 2>&1; then
      deps=(gcc-c++ cmake ninja-build extra-cmake-modules kf6-kcmutils-devel qt6-qtbase-private-devel qt6-qttools-devel
        libdrm-devel mesa-libgbm-devel libxkbcommon-devel libinput-devel vulkan-headers vulkan-loader-devel libepoxy-devel wayland-devel wayland-protocols-devel)
      # Match the installed compositor even when a different kwin-devel is already present.
      kwin_build=$(rpm -q --qf '%{VERSION}-%{RELEASE}.%{ARCH}' kwin)
      deps+=("kwin-devel-$kwin_build")
      if ! rpm -q "${deps[@]}" >/dev/null 2>&1; then
        "${elevate[@]}" dnf install --setopt=install_weak_deps=False -y "${deps[@]}"
        rpm -q "${deps[@]}" >/dev/null || { echo "The live-blur build dependencies are incomplete." >&2; exit 1; }
      fi
    fi
  fi
  tools=(cmake ctest ninja tar mktemp install)
  if [ "$1" = --install-wobbly ]; then tools+=(qtpaths6); fi
  revision=a6d6443a54dc731e5784cf9a0fec77f378a126f9
  if [ ! -d "$work/BetterWobblyWindows-$revision" ]; then tools+=(curl sha256sum); fi
  missing=()
  for tool in "${tools[@]}"; do command -v "$tool" >/dev/null || missing+=("$tool"); done
  if [ "${#missing[@]}" -gt 0 ]; then
    echo "Missing commands for the live-blur build: ${missing[*]}" >&2
    exit 1
  fi
  fetch_source BetterWobblyWindows "$revision" 216ed129d09846aa8323b248b106d46f74c09133b423fe01e46ee6fee9114289 GoldenBilly
  cmake -S "$work/BetterWobblyWindows-$revision" -B "$work/wobbly" -G Ninja -DCMAKE_BUILD_TYPE=Release
  cmake --build "$work/wobbly"
  ctest --test-dir "$work/wobbly" --output-on-failure
  # KWin discovers effects by their module basename. Drop the default CMake lib prefix.
  dest="$work/wobbly-plugins/kwin/effects"
  install -Dm755 "$work/wobbly/libbetter_wobblywindows.so" "$dest/plugins/better_wobblywindows.so"
  install -Dm755 "$work/wobbly/libbetter_wobblywindows_config.so" "$dest/configs/better_wobblywindows_config.so"
  if [ "$1" = --install-wobbly ]; then
    plugins=$(qtpaths6 --plugin-dir)/kwin/effects
    "${elevate[@]}" install -Dm755 "$dest/plugins/better_wobblywindows.so" "$plugins/plugins/better_wobblywindows.so"
    "${elevate[@]}" install -Dm755 "$dest/configs/better_wobblywindows_config.so" "$plugins/configs/better_wobblywindows_config.so"
  fi
  exit
fi

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
