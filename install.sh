#!/usr/bin/env bash
# Borealis — user-local installer (no root needed).
#
#   ./install.sh                      install/update every component in ~/.local/share
#   ./install.sh --apply dark         ...and switch to Borealis Dark (keeps your panels)
#   ./install.sh --apply light        ...and switch to Borealis Light
#
# Extra options (with --apply):
#   --layout    also replace your panels with the Borealis top bar + dock
#   --auto      follow day/night: Borealis Light by day, Borealis Dark at night
#   --konsole   make the matching Borealis profile Konsole's default
#   --live      use the animated Borealis Aurora wallpaper (desktop + lock screen)
#   --gtk       Borealis colors for GTK4/libadwaita apps
#   --terminal  Borealis for bat, tmux, git, ls, fzf and the bash prompt
#   --from DIR  install a build from elsewhere (e.g. a remix built with
#               ./build.py --accent … --name "Borealis Ember" --out DIR)
#   --flatpak   ...for Flatpak apps too (implies --gtk; lets every Flatpak app
#               read ~/.config/gtk-4.0, read-only)
#
# Whenever --apply is used, your current settings are backed up first; the
# exact restore command is printed at the end.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="${BOREALIS_SRC:-$HERE/build/share}"
DEST="${XDG_DATA_HOME:-$HOME/.local/share}"
CONF="${XDG_CONFIG_HOME:-$HOME/.config}"

APPLY=""; LAYOUT=0; AUTO=0; KONSOLE=0; LIVE=0; GTK=0; FLATPAK=0; TERMINAL=0
while [ $# -gt 0 ]; do
    case "$1" in
        --apply) APPLY="${2:-}"; shift 2 ;;
        --layout) LAYOUT=1; shift ;;
        --auto) AUTO=1; shift ;;
        --konsole) KONSOLE=1; shift ;;
        --live) LIVE=1; shift ;;
        --gtk) GTK=1; shift ;;
        --flatpak) GTK=1; FLATPAK=1; shift ;;
        --terminal) TERMINAL=1; shift ;;
        --from) SRC="${2:-}"; shift 2 ;;
        -h|--help) sed -n '2,23p' "$0"; exit 0 ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
done
case "$APPLY" in ""|dark|light) ;; *) echo "--apply takes 'dark' or 'light'" >&2; exit 2 ;; esac
if [ -z "$APPLY" ] && { [ $LAYOUT = 1 ] || [ $AUTO = 1 ] || [ $KONSOLE = 1 ] || [ $LIVE = 1 ] || [ $GTK = 1 ] || [ $TERMINAL = 1 ]; }; then
    echo "--layout, --auto, --konsole, --live, --gtk, --flatpak and --terminal need --apply dark|light" >&2; exit 2
fi

if [ ! -d "$SRC" ]; then
    echo "build/share not found — building first…"
    python3 "$HERE/build.py"
fi

# Everything the build produced, discovered rather than hard-coded, so a remix
# (./build.py --accent … --name "Borealis Ember") installs the same way.
CATEGORIES=(plasma/look-and-feel plasma/desktoptheme plasma/wallpapers aurorae/themes
            color-schemes icons wallpapers sounds konsole org.kde.syntax-highlighting/themes)
ITEMS=()
for cat in "${CATEGORIES[@]}"; do
    [ -d "$SRC/$cat" ] || continue
    for path in "$SRC/$cat"/*; do
        [ -e "$path" ] && ITEMS+=("$cat/$(basename "$path")")
    done
done
[ ${#ITEMS[@]} -gt 0 ] || { echo "nothing to install in $SRC — run ./build.py" >&2; exit 1; }

# The theme's own names come from the build, not from this script
THEME_DARK="$(basename "$(ls -d "$SRC"/plasma/look-and-feel/*-Dark 2>/dev/null | head -1)")"
THEME_LIGHT="$(basename "$(ls -d "$SRC"/plasma/look-and-feel/*-Light 2>/dev/null | head -1)")"
THEME_NAME="${THEME_DARK%-Dark}"
LIVE_ID="$(basename "$(ls -d "$SRC"/plasma/wallpapers/* 2>/dev/null | head -1)")"
SOUND_ID="$(basename "$(ls -d "$SRC"/sounds/* 2>/dev/null | head -1)")"
GTKCSS="$(basename "$(ls "$SRC"/gtk/*/*-libadwaita.css 2>/dev/null | head -1)")"
TERMSRC="$(ls -d "$SRC"/terminal/* 2>/dev/null | head -1)"
meta_name() { python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["KPlugin"]["Name"])' "$1" 2>/dev/null; }
TITLE_DARK="$(meta_name "$SRC/plasma/look-and-feel/$THEME_DARK/metadata.json")"
TITLE_LIGHT="$(meta_name "$SRC/plasma/look-and-feel/$THEME_LIGHT/metadata.json")"
: "${TITLE_DARK:=$THEME_DARK}" "${TITLE_LIGHT:=$THEME_LIGHT}"

echo "Installing $THEME_NAME into $DEST"
for item in "${ITEMS[@]}"; do
    [ -e "$SRC/$item" ] || { echo "  skip (not built): $item"; continue; }
    mkdir -p "$DEST/$(dirname "$item")"
    rm -rf "${DEST:?}/$item"
    cp -a "$SRC/$item" "$DEST/$item"
    echo "  + $item"
done

# What we installed, for ./uninstall.sh --remove
mkdir -p "$CONF/borealis"
printf '%s\n' "${ITEMS[@]}" > "$CONF/borealis/installed.list"

# Drop stale SVG caches so Plasma re-reads the style
CACHE="${XDG_CACHE_HOME:-$HOME/.cache}"
rm -f "$CACHE"/plasma_theme_"$THEME_NAME"*.kcache "$CACHE"/ksvg-elements 2>/dev/null || true
command -v kbuildsycoca6 >/dev/null && kbuildsycoca6 >/dev/null 2>&1 || true

if [ -z "$APPLY" ]; then
    echo
    echo "Done. Pick '$TITLE_DARK' or '$TITLE_LIGHT' in"
    echo "System Settings › Colors & Themes › Global Theme  (or run ./install.sh --apply dark)."
    exit 0
fi

PKG="$THEME_DARK"; PROFILE="$TITLE_DARK.profile"
[ "$APPLY" = light ] && { PKG="$THEME_LIGHT"; PROFILE="$TITLE_LIGHT.profile"; }

# --- back up everything we may touch -------------------------------------
BACKUP="$HOME/.local/state/borealis-backup/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP"
for f in kdeglobals kwinrc kcminputrc plasmarc ksplashrc kscreenlockerrc konsolerc \
         plasma-org.kde.plasma.desktop-appletsrc plasmashellrc; do
    if [ -f "$CONF/$f" ]; then cp -a "$CONF/$f" "$BACKUP/"; else echo "$f" >> "$BACKUP/.absent"; fi
done
if [ -d "$CONF/kdedefaults" ]; then cp -a "$CONF/kdedefaults" "$BACKUP/kdedefaults"; fi
if [ $TERMINAL = 1 ]; then
    if [ -f "$HOME/.bashrc" ]; then cp -a "$HOME/.bashrc" "$BACKUP/bashrc"; else touch "$BACKUP/bashrc.absent"; fi
fi
if [ $GTK = 1 ]; then
    mkdir -p "$BACKUP/gtk-4.0"
    if [ -f "$CONF/gtk-4.0/gtk.css" ]; then cp -a "$CONF/gtk-4.0/gtk.css" "$BACKUP/gtk-4.0/"; else touch "$BACKUP/gtk-4.0/.absent"; fi
fi
echo "Backed up your current settings to $BACKUP"

# --- apply ----------------------------------------------------------------
KEEP_AUTO=()
if [ $AUTO = 1 ]; then
    kwriteconfig6 --file kdeglobals --group KDE --key DefaultLightLookAndFeel Borealis-Light
    kwriteconfig6 --file kdeglobals --group KDE --key DefaultDarkLookAndFeel Borealis-Dark
    kwriteconfig6 --file kdeglobals --group KDE --key AutomaticLookAndFeel true
    KEEP_AUTO=(--keep-auto)
fi
if [ $LAYOUT = 1 ]; then
    lookandfeeltool --apply "$PKG" --resetLayout "${KEEP_AUTO[@]}"
else
    lookandfeeltool --apply "$PKG" "${KEEP_AUTO[@]}"
    # a Global Theme only *defaults* the wallpaper; set it explicitly
    plasma-apply-wallpaperimage "$DEST/wallpapers/$THEME_NAME" >/dev/null 2>&1 || true
fi
# Fedora pins the lock screen to its own wallpaper; point it at Borealis
kwriteconfig6 --file kscreenlockerrc --group Greeter --group Wallpaper --group org.kde.image \
    --group General --key Image "file://$DEST/wallpapers/$THEME_NAME-Lock/"
if [ $KONSOLE = 1 ]; then
    kwriteconfig6 --file konsolerc --group "Desktop Entry" --key DefaultProfile "$PROFILE"
fi
# Global Themes can't set the sound theme; do it here
kwriteconfig6 --file kdeglobals --group Sounds --key Theme "$SOUND_ID"
if [ $LIVE = 1 ]; then
    qdbus-qt6 org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript \
        "var d = desktops(); for (var i = 0; i < d.length; i++) { d[i].wallpaperPlugin = '$LIVE_ID'; }" \
        >/dev/null 2>&1 || echo "  (couldn't reach plasmashell; pick the '$THEME_NAME' animated wallpaper under Configure Desktop › Wallpaper)"
    kwriteconfig6 --file kscreenlockerrc --group Greeter --key WallpaperPlugin "$LIVE_ID"
fi
if [ $TERMINAL = 1 ]; then
    TERMDIR="$CONF/borealis/terminal"
    mkdir -p "$TERMDIR" "$CONF/bat/themes"
    cp "$TERMSRC/"* "$TERMDIR/"
    cp "$TERMSRC/"*.tmTheme "$CONF/bat/themes/"
    command -v bat >/dev/null && bat cache --build >/dev/null 2>&1 || true
    LINE="source $TERMDIR/borealis-$APPLY.bash"
    if ! grep -qxF "$LINE" "$HOME/.bashrc" 2>/dev/null; then
        printf '\n# Borealis colors for the command line\n%s\n' "$LINE" >> "$HOME/.bashrc"
    fi
    echo "  terminal kit in $TERMDIR (new shells pick it up; see its README.md for tmux and git)"
fi
if [ $GTK = 1 ]; then
    # our own file + one import line; KDE rewrites gtk.css but keeps extra lines
    install -Dm644 "$(ls "$SRC"/gtk/*/"$GTKCSS")" "$CONF/gtk-4.0/$GTKCSS"
    grep -qxF "@import '$GTKCSS';" "$CONF/gtk-4.0/gtk.css" 2>/dev/null || \
        printf "\n@import '%s';\n" "$GTKCSS" >> "$CONF/gtk-4.0/gtk.css"
    echo "  GTK4 apps pick up the Borealis colors when they next start."
fi
if [ $FLATPAK = 1 ] && command -v flatpak >/dev/null; then
    if ! flatpak override --user --show | grep -q 'xdg-config/gtk-4\.0'; then
        flatpak override --user --filesystem=xdg-config/gtk-4.0:ro
        touch "$BACKUP/flatpak-override-added"
    fi
    echo "  Flatpak apps may now read ~/.config/gtk-4.0 (read-only); restart open ones."
fi
if ! fc-list | grep -qi "Inter" || ! fc-list | grep -qi "JetBrains Mono"; then
    echo
    echo "Note: the Borealis fonts aren't installed yet. For the intended look run:"
    echo "  sudo dnf install rsms-inter-fonts jetbrains-mono-fonts"
fi

echo
echo "Applied $PKG."
[ $AUTO = 1 ] && echo "Day/night switching is on — set the schedule in System Settings › Global Theme › Configure Day/Night Cycle…"
echo "To undo:  ./uninstall.sh --restore \"$BACKUP\""
