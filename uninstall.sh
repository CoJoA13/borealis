#!/usr/bin/env bash
# Borealis — restore / uninstall.
#
#   ./uninstall.sh --restore <backup-dir>   put back the settings saved by
#                                           ./install.sh --apply (panels included)
#   ./uninstall.sh --remove                 delete every Borealis file from
#                                           ~/.local/share (switch themes first)
set -euo pipefail

DEST="${XDG_DATA_HOME:-$HOME/.local/share}"
CONF="${XDG_CONFIG_HOME:-$HOME/.config}"
GTKCSS="borealis-libadwaita.css"

# Take back only the Flatpak permission Borealis added (a --nofilesystem
# override would instead block it for apps that ask for it themselves).
drop_flatpak_override() {
    local f="${XDG_DATA_HOME:-$HOME/.local/share}/flatpak/overrides/global"
    [ -f "$f" ] || return 0
    sed -i -e 's#^\(filesystems=.*\)xdg-config/gtk-4\.0:ro;#\1#' -e '/^filesystems=$/d' "$f"
    grep -qvxE '\[Context\]|' "$f" || rm -f "$f"
    echo "  removed the Flatpak read access to ~/.config/gtk-4.0"
}
MODE=""; BACKUP=""
case "${1:-}" in
    --restore) MODE=restore; BACKUP="${2:-}" ;;
    --remove) MODE=remove ;;
    *) sed -n '2,8p' "$0"; exit 2 ;;
esac

if [ "$MODE" = restore ]; then
    [ -d "$BACKUP" ] || { echo "no such backup: $BACKUP" >&2; exit 1; }
    # plasmashell saves its layout on exit, so stop it before copying files back
    systemctl --user stop plasma-plasmashell.service 2>/dev/null || kquitapp6 plasmashell 2>/dev/null || true
    for f in "$BACKUP"/*; do
        case "$(basename "$f")" in kdedefaults|gtk-4.0|firefox|flatpak-override-added|bashrc|bashrc.absent) continue ;; esac
        cp -a "$f" "$CONF/"
        echo "  restored $(basename "$f")"
    done
    if [ -f "$BACKUP/.absent" ]; then
        while read -r f; do
            [ -n "$f" ] && rm -f "${CONF:?}/$f" && echo "  removed $f (did not exist before)"
        done < "$BACKUP/.absent"
    fi
    if [ -d "$BACKUP/kdedefaults" ]; then
        rm -rf "${CONF:?}/kdedefaults"
        cp -a "$BACKUP/kdedefaults" "$CONF/kdedefaults"
        echo "  restored kdedefaults/"
    fi
    if [ -d "$BACKUP/gtk-4.0" ]; then
        rm -f "$CONF/gtk-4.0/$GTKCSS"
        if [ -f "$BACKUP/gtk-4.0/gtk.css" ]; then cp -a "$BACKUP/gtk-4.0/gtk.css" "$CONF/gtk-4.0/gtk.css"
        else rm -f "$CONF/gtk-4.0/gtk.css"; fi
        echo "  restored GTK4 settings"
    fi
    if [ -d "$BACKUP/firefox" ]; then
        ffp="$(cat "$BACKUP/firefox/profile-path" 2>/dev/null || true)"
        if [ -n "$ffp" ] && [ -d "$ffp" ]; then
            rm -f "$ffp"/chrome/borealis*-user*.css
            for f in userChrome.css userContent.css; do
                if [ -f "$BACKUP/firefox/$f" ]; then cp -a "$BACKUP/firefox/$f" "$ffp/chrome/$f"
                else rm -f "$ffp/chrome/$f"; fi
            done
            if [ -f "$BACKUP/firefox/user.js" ]; then cp -a "$BACKUP/firefox/user.js" "$ffp/user.js"
            else rm -f "$ffp/user.js"; fi
            echo "  restored Firefox (restart it)"
        fi
    fi
    [ -f "$BACKUP/flatpak-override-added" ] && drop_flatpak_override
    if [ -f "$BACKUP/bashrc" ]; then cp -a "$BACKUP/bashrc" "$HOME/.bashrc"; echo "  restored ~/.bashrc"
    elif [ -f "$BACKUP/bashrc.absent" ]; then rm -f "$HOME/.bashrc"; fi
    # tell running apps about the restored look
    scheme="$(kreadconfig6 --file kdeglobals --group General --key ColorScheme)"
    cursor="$(kreadconfig6 --file kcminputrc --group Mouse --key cursorTheme)"
    icons="$(kreadconfig6 --file kdeglobals --group Icons --key Theme)"
    style="$(kreadconfig6 --file plasmarc --group Theme --key name)"
    [ -n "$scheme" ] && plasma-apply-colorscheme "$scheme" >/dev/null 2>&1 || true
    [ -n "$cursor" ] && plasma-apply-cursortheme "$cursor" >/dev/null 2>&1 || true
    [ -n "$icons" ] && /usr/libexec/plasma-changeicons "$icons" >/dev/null 2>&1 || true
    [ -n "$style" ] && plasma-apply-desktoptheme "$style" >/dev/null 2>&1 || true
    qdbus-qt6 org.kde.KWin /KWin reconfigure >/dev/null 2>&1 || true
    systemctl --user start plasma-plasmashell.service 2>/dev/null || (kstart plasmashell >/dev/null 2>&1 &)
    echo "Restored settings from $BACKUP"
    exit 0
fi

current="$(kreadconfig6 --file kdeglobals --group KDE --key LookAndFeelPackage)"
MANIFEST="$CONF/borealis/installed.list"
if [ -f "$MANIFEST" ]; then
    mapfile -t ITEMS < "$MANIFEST"
else            # older install, or the list was removed: fall back to the names we ship
    ITEMS=(
        plasma/look-and-feel/Borealis-Dark plasma/look-and-feel/Borealis-Light
        plasma/desktoptheme/Borealis aurorae/themes/Borealis-Dark aurorae/themes/Borealis-Light
        color-schemes/BorealisDark.colors color-schemes/BorealisLight.colors
        icons/Borealis-Dark icons/Borealis-Light icons/Borealis-Snow-Cursors icons/Borealis-Ink-Cursors
        wallpapers/Borealis wallpapers/Borealis-Lock plasma/wallpapers/org.borealis.aurora
        sounds/Borealis konsole/BorealisDark.colorscheme konsole/BorealisLight.colorscheme
        "konsole/Borealis Dark.profile" "konsole/Borealis Light.profile"
        org.kde.syntax-highlighting/themes/borealisdark.theme
        org.kde.syntax-highlighting/themes/borealislight.theme
    )
fi
for item in "${ITEMS[@]}"; do
    case "$item" in plasma/look-and-feel/*)
        [ "$current" = "${item##*/}" ] && {
            echo "${item##*/} is the active Global Theme — switch to another one first." >&2; exit 1; }
    esac
done
# the standalone dock and bar: stop them and forget their units, KWin bridge and commands
for unit in "$CONF"/systemd/user/*-dock.service "$CONF"/systemd/user/*-bar.service; do
    [ -f "$unit" ] && grep -q "Installed by the Borealis theme" "$unit" || continue
    systemctl --user disable --now "$(basename "$unit")" >/dev/null 2>&1 || true
    rm -f "$unit"
    systemctl --user daemon-reload 2>/dev/null || true
    echo "  - ~/.config/systemd/user/$(basename "$unit")"
done
for script in "$DEST"/kwin/scripts/*-dockbridge; do
    [ -d "$script" ] || continue
    kwriteconfig6 --file kwinrc --group Plugins --key "$(basename "$script")Enabled" --delete 2>/dev/null || true
    qdbus-qt6 org.kde.KWin /Scripting org.kde.kwin.Scripting.unloadScript "$(basename "$script")" >/dev/null 2>&1 || true
done
for link in "$HOME"/.local/bin/*-dock "$HOME"/.local/bin/*-bar; do
    [ -L "$link" ] || continue
    case "$(readlink "$link")" in
        "$DEST"/*-dock/main.py|"$DEST"/*-bar/main.py) rm -f "$link"; echo "  - ~/.local/bin/$(basename "$link")" ;;
    esac
done
for item in "${ITEMS[@]}"; do
    [ -n "$item" ] || continue
    if [ -e "$DEST/$item" ]; then rm -rf "${DEST:?}/$item"; echo "  - $item"; fi
done
rm -f "$MANIFEST"
if [ -f "$CONF/gtk-4.0/$GTKCSS" ]; then
    rm -f "$CONF/gtk-4.0/$GTKCSS"
    sed -i "/^@import '$GTKCSS';\$/d" "$CONF/gtk-4.0/gtk.css" 2>/dev/null || true
    echo "  - ~/.config/gtk-4.0/$GTKCSS"
    drop_flatpak_override
fi
if [ -d "$CONF/borealis/terminal" ]; then
    rm -rf "$CONF/borealis/terminal"
    rmdir "$CONF/borealis" 2>/dev/null || true
    rm -f "$CONF/bat/themes/Borealis "*.tmTheme
    command -v bat >/dev/null && bat cache --build >/dev/null 2>&1 || true
    sed -i '/# Borealis colors for the command line/d;\#source .*/borealis/terminal/borealis-.*\.bash#d' \
        "$HOME/.bashrc" 2>/dev/null || true
    echo "  - ~/.config/borealis/terminal (and its ~/.bashrc line)"
fi
for ffroot in "$CONF/mozilla/firefox" "$HOME/.mozilla/firefox"; do
    for prof in "$ffroot"/*/chrome; do
        [ -d "$prof" ] || continue
        if ls "$prof"/*-userChrome.css >/dev/null 2>&1; then
            rm -f "$prof"/*-userChrome.css "$prof"/*-userContent.css
            sed -i '/^@import ".*-user\(Chrome\|Content\)\.css";$/d' \
                "$prof/userChrome.css" "$prof/userContent.css" 2>/dev/null || true
            echo "  - Firefox styling in ${prof%/chrome}"
        fi
    done
done
echo "Borealis removed from $DEST."
