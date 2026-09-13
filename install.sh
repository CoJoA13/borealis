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
#   --firefox   Borealis for Firefox's own window (userChrome.css)
#   --panels    put the Borealis dock and Quick Settings into the panels you
#               already have (no layout reset)
#   --dock      switch to the standalone Borealis Dock: runs it now and at every
#               login, enables its KWin bridge, and retires the panel dock
#               (your pinned apps come along)
#   --dock-revert   back to the panel dock
#   --dock-merge    --dock, and fold the rest of a bottom panel into the top bar
#               (its tray and clock, where the top bar has none) and remove it
#   --from DIR  install a build from elsewhere (e.g. a remix built with
#               ./build.py --accent … --name "Borealis Ember" --out DIR)
#   --flatpak   ...for Flatpak apps too (implies --gtk; lets every Flatpak app
#               read ~/.config/gtk-4.0, read-only)
#
# --konsole, --gtk, --flatpak, --terminal and --firefox also work without
# --apply: then they style the variant you already use.
#
# Whenever --apply or one of those is used, the settings it changes are backed
# up first; the exact restore command is printed at the end.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="${BOREALIS_SRC:-$HERE/build/share}"
DEST="${XDG_DATA_HOME:-$HOME/.local/share}"
CONF="${XDG_CONFIG_HOME:-$HOME/.config}"

APPLY=""; LAYOUT=0; AUTO=0; KONSOLE=0; LIVE=0; GTK=0; FLATPAK=0; TERMINAL=0; FIREFOX=0; PANELS=0; DOCK=0; DOCK_REVERT=0; DOCK_MERGE=0
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
        --firefox) FIREFOX=1; shift ;;
        --panels) PANELS=1; shift ;;
        --dock) DOCK=1; shift ;;
        --dock-revert) DOCK_REVERT=1; shift ;;
        --dock-merge) DOCK=1; DOCK_MERGE=1; shift ;;
        --from) SRC="${2:-}"; shift 2 ;;
        -h|--help) sed -n '2,36p' "$0"; exit 0 ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
done
case "$APPLY" in ""|dark|light) ;; *) echo "--apply takes 'dark' or 'light'" >&2; exit 2 ;; esac
if [ $DOCK = 1 ] && [ $DOCK_REVERT = 1 ]; then
    echo "--dock and --dock-revert contradict each other" >&2; exit 2
fi
if [ -z "$APPLY" ] && { [ $LAYOUT = 1 ] || [ $AUTO = 1 ] || [ $LIVE = 1 ]; }; then
    echo "--layout, --auto and --live need --apply dark|light" >&2; exit 2
fi
EXTRAS=0
if [ $KONSOLE = 1 ] || [ $GTK = 1 ] || [ $TERMINAL = 1 ] || [ $FIREFOX = 1 ]; then EXTRAS=1; fi

if [ ! -d "$SRC" ]; then
    echo "build/share not found — building first…"
    python3 "$HERE/build.py"
fi

# Everything the build produced, discovered rather than hard-coded, so a remix
# (./build.py --accent … --name "Borealis Ember") installs the same way.
CATEGORIES=(plasma/look-and-feel plasma/desktoptheme plasma/wallpapers plasma/plasmoids kwin/scripts
            aurorae/themes color-schemes icons wallpapers sounds konsole
            org.kde.syntax-highlighting/themes)
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
FFSRC="$(ls -d "$SRC"/firefox/* 2>/dev/null | head -1)"
# Firefox' default profile (XDG path first: Firefox 128+ moved there)
ff_profile() {
    python3 - <<'PYEOF'
import configparser, os, sys
for root in (os.path.join(os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"),
                          "mozilla", "firefox"),
             os.path.expanduser("~/.mozilla/firefox")):
    ini = os.path.join(root, "profiles.ini")
    if not os.path.exists(ini):
        continue
    cp = configparser.ConfigParser()
    cp.read(ini)
    path = ""
    for sec in cp.sections():                    # the install's own default wins
        if sec.startswith("Install") and cp[sec].get("Default"):
            path = cp[sec]["Default"]
            break
    if not path:
        for sec in cp.sections():
            if sec.startswith("Profile") and cp[sec].get("Default") == "1":
                path = cp[sec].get("Path", "")
                break
    if not path:
        for sec in cp.sections():
            if sec.startswith("Profile") and cp[sec].get("Path"):
                path = cp[sec]["Path"]
                break
    if path:
        full = path if os.path.isabs(path) else os.path.join(root, path)
        if os.path.isdir(full):
            print(full)
            sys.exit(0)
sys.exit(1)
PYEOF
}

panels_update() {
        STANDALONE=0
        ls "$HOME"/.local/bin/*-dock >/dev/null 2>&1 && STANDALONE=1
        DOCK_ID="$(basename "$(ls -d "$SRC"/plasma/plasmoids/*.dock 2>/dev/null | head -1)")"
        QUICK_ID="$(basename "$(ls -d "$SRC"/plasma/plasmoids/*.quicksettings 2>/dev/null | head -1)")"
        qdbus-qt6 org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript "
    var ps = panels();
    for (var i = 0; i < ps.length; i++) {
        var p = ps[i];
        var ids = p.widgetIds;
        var types = [];
        for (var j = 0; j < ids.length; j++) { types.push(String(p.widgetById(ids[j]).type)); }
        if ($STANDALONE === 0 && String(p.location) === 'bottom' && types.indexOf('$DOCK_ID') < 0) {
            for (var j = 0; j < ids.length; j++) {
                var w = p.widgetById(ids[j]);
                var t = String(w.type);
                if (t.indexOf('icontasks') >= 0 || t.indexOf('taskmanager') >= 0
                    || t.indexOf('plasma.trash') >= 0 || t.indexOf('marginsseparator') >= 0) { w.remove(); }
            }
            p.height = 2 * Math.ceil(gridUnit * 5.3 / 2);   // room for the magnified icons
            var dock = p.addWidget('$DOCK_ID');
            dock.currentConfigGroup = ['General'];
            dock.writeConfig('iconSize', 48);
            dock.writeConfig('magnification', 130);
        } else if (String(p.location) === 'top' && types.indexOf('$QUICK_ID') < 0) {
            p.addWidget('$QUICK_ID');
        }
    }
    " >/dev/null 2>&1 && echo "  panels updated (drag the widgets where you want them in Edit Mode)" \
          || echo "  (couldn't reach plasmashell; add the widgets from the panel's Add Widgets menu)"
}

# --- the standalone dock ------------------------------------------------------
DOCK_EXE=""; DOCK_BRIDGE=""; DOCK_SLUG=""; DOCK_PLASMOID=""
dock_ids() {
    DOCK_EXE="$(basename "$(ls -d "$SRC"/*-dock 2>/dev/null | head -1)")"
    DOCK_BRIDGE="$(basename "$(ls -d "$SRC"/kwin/scripts/*-dockbridge 2>/dev/null | head -1)")"
    DOCK_PLASMOID="$(basename "$(ls -d "$SRC"/plasma/plasmoids/*.dock 2>/dev/null | head -1)")"
    if [ -z "$DOCK_EXE" ] || [ -z "$DOCK_BRIDGE" ]; then
        echo "  the dock isn't built — run ./build.py dock" >&2
        return 1
    fi
    DOCK_SLUG="$(sed -n "s/^SLUG = ['\"]\(.*\)['\"]\$/\1/p" "$SRC/$DOCK_EXE/ids.py")"
}
kwin_bridge() {     # on | off
    local value=false copy
    [ "$1" = on ] && value=true
    kwriteconfig6 --file kwinrc --group Plugins --key "${DOCK_BRIDGE}Enabled" "$value"
    qdbus-qt6 org.kde.KWin /Scripting org.kde.kwin.Scripting.unloadScript "$DOCK_BRIDGE" >/dev/null 2>&1 || true
    [ "$1" = on ] || return 0
    # KWin compiles a script's QML once per file path for the whole session, so
    # reloading the installed file would run the old code again. This version
    # loads from a path of its own (gone at logout; the next login reads the
    # installed package as usual).
    copy="${XDG_RUNTIME_DIR:-/tmp}/borealis-dockbridge/$(cat "$DEST/kwin/scripts/$DOCK_BRIDGE/contents/ui/"* | sha1sum | cut -c1-12)"
    mkdir -p "$copy"
    cp "$DEST/kwin/scripts/$DOCK_BRIDGE/contents/ui/"* "$copy/"
    qdbus-qt6 org.kde.KWin /Scripting org.kde.kwin.Scripting.loadDeclarativeScript "$copy/main.qml" "$DOCK_BRIDGE" >/dev/null 2>&1 \
        && qdbus-qt6 org.kde.KWin /Scripting org.kde.kwin.Scripting.start >/dev/null 2>&1 || true
}
task_manager_keys() {  # none | meta
    # plasmashell keeps Meta+1…9 for a task manager even when there is none, and
    # the first owner of a key wins. "none" is a user setting Plasma remembers;
    # "meta" hands the keys back.
    local n keys
    for n in 1 2 3 4 5 6 7 8 9 10; do
        keys="0"
        [ "$1" = meta ] && [ "$n" -lt 10 ] && keys="1 1 $(( 0x10000000 | (0x30 + n) ))"
        # shellcheck disable=SC2086
        busctl --user call org.kde.kglobalaccel /kglobalaccel org.kde.KGlobalAccel setForeignShortcutKeys \
            'asa(ai)' 4 plasmashell "activate task manager entry $n" plasmashell \
            "Activate Task Manager Entry $n" $keys >/dev/null 2>&1 || true
    done
}
dock_refresh() {    # after an update: the running dock and bridge pick up the new files
    dock_ids 2>/dev/null || return 0
    [ -L "$HOME/.local/bin/$DOCK_EXE" ] || return 0
    kwin_bridge on
    systemctl --user daemon-reload
    systemctl --user try-restart "$DOCK_EXE.service" >/dev/null 2>&1 || true
    echo "  the dock and its KWin bridge reloaded"
}
dock_enable() {
    dock_ids || return 1
    local state pins settings
    state="$HOME/.local/state/borealis-backup/$(date +%Y%m%d-%H%M%S)-dock"
    mkdir -p "$state"
    for f in plasma-org.kde.plasma.desktop-appletsrc plasmashellrc; do
        if [ -f "$CONF/$f" ]; then cp -a "$CONF/$f" "$state/"; fi
    done
    task_manager_keys none
    kwin_bridge on
    # the command doubles as the Global Theme layout's hint to skip the panel dock
    mkdir -p "$HOME/.local/bin"
    ln -sfn "$DEST/$DOCK_EXE/main.py" "$HOME/.local/bin/$DOCK_EXE"
    # retire the panel dock (and a task manager or trash in a bottom panel); keep its pins
    pins="$(qdbus-qt6 org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript "
    var pins = [];
    var ps = panels();
    for (var i = 0; i < ps.length; i++) {
        var p = ps[i];
        if (String(p.location) !== 'bottom') { continue; }
        var ids = p.widgetIds;
        var removed = 0;
        for (var j = 0; j < ids.length; j++) {
            var w = p.widgetById(ids[j]);
            var t = String(w.type);
            if (t === '$DOCK_PLASMOID' || t.indexOf('icontasks') >= 0 || t.indexOf('taskmanager') >= 0
                || t.indexOf('plasma.trash') >= 0) {
                if (pins.length === 0 && t.indexOf('trash') < 0) {
                    w.currentConfigGroup = ['General'];
                    var l = w.readConfig('launchers');
                    if (l && String(l).length) { pins = String(l).split(','); }
                }
                w.remove();
                removed++;
            }
        }
        if (removed > 0) {
            var left = p.widgetIds;
            var useful = [];
            for (var k = 0; k < left.length; k++) {
                var lt = String(p.widgetById(left[k]).type);
                if (lt.indexOf('panelspacer') < 0 && lt.indexOf('marginsseparator') < 0) { useful.push(lt); }
            }
            if (useful.length === 0) {
                p.remove();
            } else if ($DOCK_MERGE === 1) {
                // fold the tray and clock into the top bar (where it lacks them), then retire the panel
                var top = null;
                for (var m = 0; m < ps.length; m++) {
                    if (String(ps[m].location) === 'top') { top = ps[m]; }
                }
                if (top) {
                    var topTypes = [];
                    var tids = top.widgetIds;
                    for (var n = 0; n < tids.length; n++) { topTypes.push(String(top.widgetById(tids[n]).type)); }
                    var carry = ['org.kde.plasma.digitalclock', 'org.kde.plasma.systemtray'];
                    for (var c = 0; c < carry.length; c++) {
                        if (useful.indexOf(carry[c]) >= 0 && topTypes.indexOf(carry[c]) < 0) { top.addWidget(carry[c]); }
                    }
                    p.remove();
                }
            }
        }
    }
    print(pins.join('\n'));
    " 2>/dev/null)" || echo "  (couldn't reach plasmashell: remove the bottom dock panel yourself in Edit Mode)"
    settings="$CONF/$DOCK_SLUG/dock.json"
    if [ ! -f "$settings" ] && [ -n "$pins" ]; then
        mkdir -p "$(dirname "$settings")"
        printf '%s\n' "$pins" | python3 -c 'import json, sys
pins = [line.strip() for line in sys.stdin if line.strip()]
with open(sys.argv[1], "w") as f:
    json.dump({"pinned": pins}, f, indent=2)' "$settings"
        echo "  your pinned apps came along ($settings)"
    fi
    systemctl --user daemon-reload
    systemctl --user enable "$DOCK_EXE.service" >/dev/null 2>&1 || true
    if systemctl --user restart "$DOCK_EXE.service" >/dev/null 2>&1; then
        echo "  $DOCK_EXE is running, and starts with every Plasma session"
    else
        echo "  couldn't start $DOCK_EXE.service — see: journalctl --user -u $DOCK_EXE"
    fi
    echo "  your panels were backed up to $state"
}
dock_revert() {
    dock_ids || return 1
    local launchers
    systemctl --user disable --now "$DOCK_EXE.service" >/dev/null 2>&1 || true
    kwin_bridge off
    task_manager_keys meta
    rm -f "$HOME/.local/bin/$DOCK_EXE"
    launchers="$(python3 -c 'import json, sys
try:
    pins = json.load(open(sys.argv[1])).get("pinned", [])
except (OSError, ValueError):
    pins = []
out = []
for p in pins:
    if not p.startswith(("preferred://", "applications:", "file:")):
        p = "applications:" + p + ".desktop"
    out.append(json.dumps(p))
print(", ".join(out))' "$CONF/$DOCK_SLUG/dock.json")"
    [ -n "$DOCK_PLASMOID" ] || { echo "  standalone dock stopped (no panel dock built to bring back)"; return 0; }
    if qdbus-qt6 org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript "
    var ps = panels();
    for (var i = 0; i < ps.length; i++) {
        var ids = ps[i].widgetIds;
        for (var j = 0; j < ids.length; j++) {
            if (String(ps[i].widgetById(ids[j]).type) === '$DOCK_PLASMOID') { throw 'the panel dock is already there'; }
        }
    }
    var dock = new Panel;
    dock.location = 'bottom';
    dock.height = 2 * Math.ceil(gridUnit * 5.3 / 2);
    dock.floating = true;
    dock.lengthMode = 'fit';
    dock.alignment = 'center';
    dock.hiding = 'dodgewindows';
    dock.opacity = 'translucent';
    var tasks = dock.addWidget('$DOCK_PLASMOID');
    tasks.currentConfigGroup = ['General'];
    tasks.writeConfig('launchers', [$launchers]);
    tasks.writeConfig('iconSize', 48);
    tasks.writeConfig('magnification', 130);
    " >/dev/null 2>&1; then
        echo "  standalone dock stopped; the panel dock is back"
    else
        echo "  standalone dock stopped (the panel dock was already there, or plasmashell didn't answer)"
    fi
}

meta_name() { python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["KPlugin"]["Name"])' "$1" 2>/dev/null; }
TITLE_DARK="$(meta_name "$SRC/plasma/look-and-feel/$THEME_DARK/metadata.json")"
TITLE_LIGHT="$(meta_name "$SRC/plasma/look-and-feel/$THEME_LIGHT/metadata.json")"
: "${TITLE_DARK:=$THEME_DARK}" "${TITLE_LIGHT:=$THEME_LIGHT}"

# --- the extras: Konsole, the command line, Firefox, GTK and Flatpak apps -----
FFPROFILE=""
backup_extras() {   # into $BACKUP: what the chosen extras are about to change
    if [ $TERMINAL = 1 ]; then
        if [ -f "$HOME/.bashrc" ]; then cp -a "$HOME/.bashrc" "$BACKUP/bashrc"; else touch "$BACKUP/bashrc.absent"; fi
    fi
    if [ $FIREFOX = 1 ]; then
        FFPROFILE="$(ff_profile || true)"
        if [ -n "$FFPROFILE" ]; then
            mkdir -p "$BACKUP/firefox"
            for f in chrome/userChrome.css chrome/userContent.css user.js; do
                if [ -f "$FFPROFILE/$f" ]; then cp -a "$FFPROFILE/$f" "$BACKUP/firefox/$(basename "$f")"; fi
            done
            printf '%s\n' "$FFPROFILE" > "$BACKUP/firefox/profile-path"
        fi
    fi
    if [ $GTK = 1 ]; then
        mkdir -p "$BACKUP/gtk-4.0"
        if [ -f "$CONF/gtk-4.0/gtk.css" ]; then cp -a "$CONF/gtk-4.0/gtk.css" "$BACKUP/gtk-4.0/"; else touch "$BACKUP/gtk-4.0/.absent"; fi
    fi
    return 0
}
apply_extras() {    # variant (dark|light), Konsole profile
    if [ $KONSOLE = 1 ]; then
        kwriteconfig6 --file konsolerc --group "Desktop Entry" --key DefaultProfile "$2"
        echo "  Konsole opens with the ${2%.profile} profile"
    fi
    if [ $TERMINAL = 1 ]; then
        TERMDIR="$CONF/borealis/terminal"
        mkdir -p "$TERMDIR" "$CONF/bat/themes"
        cp "$TERMSRC/"* "$TERMDIR/"
        cp "$TERMSRC/"*.tmTheme "$CONF/bat/themes/"
        if command -v bat >/dev/null; then bat cache --build >/dev/null 2>&1 || true; fi
        LINE="source $TERMDIR/borealis-$1.bash"
        if ! grep -qxF "$LINE" "$HOME/.bashrc" 2>/dev/null; then
            printf '\n# Borealis colors for the command line\n%s\n' "$LINE" >> "$HOME/.bashrc"
        fi
        echo "  terminal kit in $TERMDIR (new shells pick it up; see its README.md for tmux and git)"
    fi
    if [ $FIREFOX = 1 ]; then
        if [ -z "$FFPROFILE" ] || [ -z "$FFSRC" ]; then
            echo "  Firefox: no profile found — start Firefox once, then re-run with --firefox"
        else
            mkdir -p "$FFPROFILE/chrome"
            cp "$FFSRC"/*.css "$FFPROFILE/chrome/"
            for part in userChrome userContent; do
                css="$FFPROFILE/chrome/$part.css"
                imp="@import \"$(basename "$(ls "$FFSRC"/*-$part.css)")\";"
                if ! grep -qxF "$imp" "$css" 2>/dev/null; then
                    # @import has to come first in a CSS file
                    printf '%s\n' "$imp" > "$css.borealis-tmp"
                    if [ -f "$css" ]; then cat "$css" >> "$css.borealis-tmp"; fi
                    mv "$css.borealis-tmp" "$css"
                fi
            done
            pref='user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);'
            grep -qF 'legacyUserProfileCustomizations' "$FFPROFILE/user.js" 2>/dev/null || \
                printf '%s\n' "$pref" >> "$FFPROFILE/user.js"
            echo "  Firefox styled (restart it): $FFPROFILE"
        fi
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
    return 0
}

echo "Installing $THEME_NAME into $DEST"
for item in "${ITEMS[@]}"; do
    [ -e "$SRC/$item" ] || { echo "  skip (not built): $item"; continue; }
    mkdir -p "$DEST/$(dirname "$item")"
    rm -rf "${DEST:?}/$item"
    cp -a "$SRC/$item" "$DEST/$item"
    echo "  + $item"
done

# The apps (Tweaks, the Dock): copy them, then point their launchers and the
# dock's systemd unit at the installed copies
for APPDIR in "$SRC"/*-tweaks "$SRC"/*-dock; do
    [ -d "$APPDIR" ] || continue
    name="$(basename "$APPDIR")"
    rm -rf "${DEST:?}/$name"
    cp -a "$APPDIR" "$DEST/$name"
    chmod +x "$DEST/$name/main.py"
    ITEMS+=("$name")
    echo "  + $name"
done
app_for() {     # the app a generated file belongs to (X-Borealis-App); Tweaks if unmarked
    local app
    app="$(sed -n 's/^X-Borealis-App=//p' "$1" | head -1)"
    [ -n "$app" ] || app="$(basename "$(ls -d "$SRC"/*-tweaks 2>/dev/null | head -1)")"
    printf '%s' "$app"
}
if ls "$SRC"/applications/*.desktop >/dev/null 2>&1; then
    mkdir -p "$DEST/applications"
    for entry in "$SRC"/applications/*.desktop; do
        app="$(app_for "$entry")"
        { [ -n "$app" ] && [ -d "$DEST/$app" ]; } || continue
        sed "s|@EXEC@|$DEST/$app/main.py|" "$entry" > "$DEST/applications/$(basename "$entry")"
        ITEMS+=("applications/$(basename "$entry")")
    done
    command -v update-desktop-database >/dev/null && \
        update-desktop-database "$DEST/applications" >/dev/null 2>&1 || true
fi
for unit in "$SRC"/systemd/user/*.service; do
    [ -e "$unit" ] || continue
    app="$(app_for "$unit")"
    { [ -n "$app" ] && [ -d "$DEST/$app" ]; } || continue
    mkdir -p "$CONF/systemd/user"
    sed "s|@EXEC@|$DEST/$app/main.py|" "$unit" > "$CONF/systemd/user/$(basename "$unit")"
    echo "  + ~/.config/systemd/user/$(basename "$unit") (used once you run ./install.sh --dock)"
done

# What we installed, for ./uninstall.sh --remove
mkdir -p "$CONF/borealis"
printf '%s\n' "$HERE" > "$CONF/borealis/project"
printf '%s\n' "${ITEMS[@]}" > "$CONF/borealis/installed.list"

# Drop stale SVG caches so Plasma re-reads the style
CACHE="${XDG_CACHE_HOME:-$HOME/.cache}"
rm -f "$CACHE"/plasma_theme_"$THEME_NAME"*.kcache "$CACHE"/ksvg-elements 2>/dev/null || true
command -v kbuildsycoca6 >/dev/null && kbuildsycoca6 >/dev/null 2>&1 || true

if [ $DOCK = 0 ] && [ $DOCK_REVERT = 0 ]; then
    dock_refresh
fi
if [ -z "$APPLY" ] && [ $EXTRAS = 1 ]; then
    # just the extras, for the variant already in use
    VARIANT=dark; PROFILE="$TITLE_DARK.profile"
    case "$(kreadconfig6 --file kdeglobals --group KDE --key LookAndFeelPackage 2>/dev/null)" in
        *-Light) VARIANT=light; PROFILE="$TITLE_LIGHT.profile" ;;
    esac
    BACKUP="$HOME/.local/state/borealis-backup/$(date +%Y%m%d-%H%M%S)-extras"
    mkdir -p "$BACKUP"
    if [ $KONSOLE = 1 ]; then
        if [ -f "$CONF/konsolerc" ]; then cp -a "$CONF/konsolerc" "$BACKUP/"; else echo konsolerc >> "$BACKUP/.absent"; fi
    fi
    backup_extras
    echo "Backed up what changes to $BACKUP"
    apply_extras "$VARIANT" "$PROFILE"
fi
if [ -z "$APPLY" ] && { [ $PANELS = 1 ] || [ $DOCK = 1 ] || [ $DOCK_REVERT = 1 ]; }; then
    if [ $PANELS = 1 ]; then panels_update; fi
    if [ $DOCK_REVERT = 1 ]; then dock_revert; fi
    if [ $DOCK = 1 ]; then dock_enable; fi
fi
if [ -z "$APPLY" ]; then
    echo
    if [ $EXTRAS = 1 ]; then
        echo "Done. To undo:  ./uninstall.sh --restore \"$BACKUP\""
    elif [ $PANELS = 1 ] || [ $DOCK = 1 ] || [ $DOCK_REVERT = 1 ]; then
        echo "Done."
    else
        echo "Done. Pick '$TITLE_DARK' or '$TITLE_LIGHT' in"
        echo "System Settings › Colors & Themes › Global Theme  (or run ./install.sh --apply dark)."
    fi
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
backup_extras
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
# Global Themes can't set the sound theme; do it here
kwriteconfig6 --file kdeglobals --group Sounds --key Theme "$SOUND_ID"
if [ $LIVE = 1 ]; then
    qdbus-qt6 org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript \
        "var d = desktops(); for (var i = 0; i < d.length; i++) { d[i].wallpaperPlugin = '$LIVE_ID'; }" \
        >/dev/null 2>&1 || echo "  (couldn't reach plasmashell; pick the '$THEME_NAME' animated wallpaper under Configure Desktop › Wallpaper)"
    kwriteconfig6 --file kscreenlockerrc --group Greeter --key WallpaperPlugin "$LIVE_ID"
fi
apply_extras "$APPLY" "$PROFILE"
if [ $PANELS = 1 ]; then
    panels_update
fi
if [ $DOCK_REVERT = 1 ]; then
    dock_revert
fi
if [ $DOCK = 1 ]; then
    dock_enable
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
