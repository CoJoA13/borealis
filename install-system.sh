#!/usr/bin/env bash
# Borealis for the login screen (Plasma Login Manager) — run with sudo.
#
# The Fedora 44 login screen can't load custom themes; it copies your Plasma
# settings instead, and those can only point at themes installed system-wide.
# This copies Borealis to /usr/local/share so the login screen can use it.
#
#   sudo ./install-system.sh                   install / update (login screen)
#   sudo ./install-system.sh --remove          remove again
#   sudo ./install-system.sh --plymouth        also install + select the Borealis
#                                              boot splash (rebuilds the initramfs)
#   sudo ./install-system.sh --plymouth-revert go back to the previous boot splash
set -euo pipefail

[ "$(id -u)" = 0 ] || { echo "Please run with sudo:  sudo $0 $*" >&2; exit 1; }
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$HERE/build/share"
DEST=/usr/local/share
ITEMS=(
    "color-schemes/BorealisDark.colors" "color-schemes/BorealisLight.colors"
    "plasma/desktoptheme/Borealis"
    "plasma/look-and-feel/Borealis-Dark" "plasma/look-and-feel/Borealis-Light"
    "aurorae/themes/Borealis-Dark" "aurorae/themes/Borealis-Light"
    "icons/Borealis-Dark" "icons/Borealis-Light"
    "icons/Borealis-Snow-Cursors" "icons/Borealis-Ink-Cursors"
    "wallpapers/Borealis" "wallpapers/Borealis-Lock"
)

PLY=/usr/share/plymouth/themes/borealis
if [ "${1:-}" = --plymouth-revert ]; then
    prev="$(cat "$PLY/.previous-theme" 2>/dev/null || echo bgrt)"
    [ "$prev" = borealis ] && prev=bgrt
    echo "Switching the boot splash back to '$prev' (rebuilding the initramfs, this takes a minute)…"
    plymouth-set-default-theme -R "$prev"
    rm -rf "$PLY"
    echo "Done."
    exit 0
fi

if [ "${1:-}" = --remove ]; then
    for item in "${ITEMS[@]}"; do
        [ -e "$DEST/$item" ] && rm -rf "${DEST:?}/$item" && echo "  - $DEST/$item"
    done
    echo "Removed. In System Settings › Login Screen, use 'Apply Plasma Settings…' again (or Reset)."
    exit 0
fi

[ -d "$SRC" ] || { echo "build/share not found — run ./build.py first (as your user)" >&2; exit 1; }
for item in "${ITEMS[@]}"; do
    mkdir -p "$DEST/$(dirname "$item")"
    rm -rf "${DEST:?}/$item"
    cp -r --no-preserve=ownership "$SRC/$item" "$DEST/$item"
    chmod -R a+rX,go-w "$DEST/$item"
    echo "  + $DEST/$item"
done
# SELinux is enforcing on Fedora: give the copies system labels
command -v restorecon >/dev/null && restorecon -R "$DEST/color-schemes" "$DEST/plasma" \
    "$DEST/aurorae" "$DEST/icons" "$DEST/wallpapers" || true

if [ "${1:-}" = --plymouth ]; then
    [ -d "$SRC/plymouth/themes/borealis" ] || { echo "Boot splash not built — run ./build.py first" >&2; exit 1; }
    current="$(plymouth-set-default-theme 2>/dev/null || echo bgrt)"
    rm -rf "$PLY"
    mkdir -p "$PLY"
    cp -r --no-preserve=ownership "$SRC/plymouth/themes/borealis/." "$PLY/"
    # keyboard-layout indicator artwork from Fedora's own spinner theme, if present
    [ -f /usr/share/plymouth/themes/spinner/keymap-render.png ] && \
        cp /usr/share/plymouth/themes/spinner/keymap-render.png "$PLY/"
    [ "$current" != borealis ] && echo "$current" > "$PLY/.previous-theme"
    chmod -R a+rX,go-w "$PLY"
    command -v restorecon >/dev/null && restorecon -R "$PLY" || true
    echo "Selecting the Borealis boot splash (rebuilding the initramfs, this takes a minute)…"
    plymouth-set-default-theme -R borealis
    echo "Boot splash installed (previous: $current). Revert with: sudo $0 --plymouth-revert"
    echo "Only the running kernel's initramfs was rebuilt; older kernels follow with: sudo dracut -f --regenerate-all"
    echo "If the splash ever misbehaves: in the GRUB menu press e and add  plymouth.splash=details  to the linux line."
fi

cat <<EOF

Installed system-wide. Now, as your normal user:
  1. Switch your own session to Borealis (System Settings › Global Theme).
  2. System Settings › Login Screen › "Apply Plasma Settings…" › Apply
     (copies your colors, Plasma style, cursor and fonts to the login screen).
  3. Same page › "Configure Appearance…" › Wallpaper type "Image", add:
       $DEST/wallpapers/Borealis/contents/images_dark/3840x2400.jpg   (night)
       $DEST/wallpapers/Borealis/contents/images/3840x2400.jpg        (dawn)
  4. Log out to see it.
EOF
