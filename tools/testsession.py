#!/usr/bin/env python3
"""Sandboxed Plasma test session for Borealis — never touches your real desktop.

Runs a private D-Bus bus + a nested, virtual (offscreen) KWin with its own
XDG config/data/cache dirs, installs build/share into that sandbox, applies a
Borealis Global Theme there, then takes screenshots with Spectacle.

    tools/testsession.py dark            -> build/shots/dark/*.png
    tools/testsession.py light --keep    (keep sandbox dir for inspection)
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHARE = os.path.join(HERE, "build", "share")

SESSION = r"""#!/bin/bash
# Executed inside the nested KWin session (private bus).
# Only ever stop processes this script started itself (by PID): the real
# desktop runs the same programs (and its own lock screen greeter!).
shot() { spectacle -b -n -f -o "$SHOTS/$1.png" >/dev/null 2>&1; }
qd() { qdbus-qt6 "$@" >/dev/null 2>&1; }
stop() { for p in "$@"; do [ -n "$p" ] && kill "$p" 2>/dev/null; done; }
lookandfeeltool -a "$LNF" --resetLayout >/dev/null 2>&1
if [ "$OUTSCALE" != 1 ]; then
    kscreen-doctor output.1.scale."$OUTSCALE" > "$SANDBOX/kscreen.log" 2>&1
    sleep 2
fi
plasmashell --no-respawn >"$SANDBOX/plasmashell.log" 2>&1 &
SHELLPID=$!
sleep 9
shot desktop
if [ "$LIVE" = 1 ]; then
    qd org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript \
        'var d = desktops(); for (var i = 0; i < d.length; i++) { d[i].wallpaperPlugin = "org.borealis.aurora"; }'
    sleep 6
    shot live1
    sleep 4
    shot live2
    # pause test: a see-through maximized window must freeze the aurora
    dolphin --new-window "$HOME" >/dev/null 2>&1 &
    MPID=$!
    sleep 3
    qd org.kde.KWin /Scripting org.kde.kwin.Scripting.loadScript "$SANDBOX/maximize.js" borealis-max
    qd org.kde.KWin /Scripting org.kde.kwin.Scripting.start
    sleep 3
    shot paused1
    sleep 3
    shot paused2
    qd org.kde.KWin /Scripting org.kde.kwin.Scripting.loadScript "$SANDBOX/restore.js" borealis-restore
    qd org.kde.KWin /Scripting org.kde.kwin.Scripting.start
    sleep 3
    shot resumed1
    sleep 3
    shot resumed2
    stop "$MPID"
    sleep 1
    qd org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript \
        'desktops()[0].showConfigurationInterface()'
    sleep 5
    shot live-config
fi
if [ "$APPS" = 1 ]; then
    dolphin --new-window "$HOME" >/dev/null 2>&1 &
    DPID=$!
    sleep 4
    shot dolphin
    konsole --profile "$PROFILE" --workdir "$HOME/Projects/borealis" \
        -e bash --rcfile "$SANDBOX/demorc" >/dev/null 2>&1 &
    KPID=$!
    sleep 3
    qd org.kde.KWin /Scripting org.kde.kwin.Scripting.loadScript "$SANDBOX/arrange.js" borealis-arrange
    qd org.kde.KWin /Scripting org.kde.kwin.Scripting.start
    sleep 2
    shot windows
    qd org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.activateLauncherMenu
    sleep 2
    shot kickoff
    qd org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.activateLauncherMenu
    sleep 1
    systemsettings kcm_colors >/dev/null 2>&1 &
    SPID=$!
    sleep 5
    shot settings
    stop "$DPID" "$KPID" "$SPID"
    sleep 1
    kwrite "$HOME/Projects/borealis/src/aurora.py" >/dev/null 2>&1 &
    WPID=$!
    sleep 4
    shot editor
    stop "$WPID"
    sleep 1
fi
if [ "$SWITCHER" = 1 ]; then
    # Alt+Tab can't be opened without a held modifier (the virtual backend has no
    # keyboard), so use KWin's own preview helper: same QML, sample windows
    QT_WAYLAND_DISABLE_FIXED_POSITIONS=1 /usr/libexec/kwin-tabbox-preview \
        "$XDG_DATA_HOME/plasma/look-and-feel/$LNF/contents/windowswitcher/WindowSwitcher.qml" \
        --show-desktop > "$SANDBOX/switcher.log" 2>&1 &
    TPID=$!
    sleep 4
    shot switcher
    stop "$TPID"
    sleep 1
    # the real thing: hold Alt + tap Tab through the nested Xwayland (XTest is
    # forwarded to the nested KWin as input). Never against the real display.
    if [ -n "$DISPLAY" ] && [ "$DISPLAY" != "$REAL_DISPLAY" ]; then
        dolphin --new-window "$HOME" >/dev/null 2>&1 &
        A1=$!
        konsole --profile "$PROFILE" --workdir "$HOME/Projects/borealis" \
            -e bash --rcfile "$SANDBOX/demorc" >/dev/null 2>&1 &
        A2=$!
        kwrite "$HOME/Projects/borealis/src/aurora.py" >/dev/null 2>&1 &
        A3=$!
        sleep 5
        python3 "$SANDBOX/hold_alt_tab.py" 4 > "$SANDBOX/xtest.log" 2>&1 &
        HPID=$!
        sleep 2
        shot switcher-live
        wait "$HPID"
        stop "$A1" "$A2" "$A3"
        sleep 1
    else
        echo "no nested DISPLAY ('$DISPLAY'), skipped the live switcher" > "$SANDBOX/xtest.log"
    fi
fi
if [ "$DOCK" = 1 ]; then
    dolphin --new-window "$HOME" >/dev/null 2>&1 &
    D1=$!
    konsole --profile "$PROFILE" -e bash --rcfile "$SANDBOX/demorc" >/dev/null 2>&1 &
    D2=$!
    sleep 5
    qd org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript \
        "$(cat "$SANDBOX/swapdock.js")"
    sleep 5
    shot dock-plain
    if [ -n "$DISPLAY" ] && [ "$DISPLAY" != "$REAL_DISPLAY" ]; then
        python3 "$SANDBOX/tap_key.py" "move:900,1168" > "$SANDBOX/dock.log" 2>&1
        sleep 2
        shot dock-zoom
    fi
    stop "$D1" "$D2"
    sleep 1
fi
if [ "$QUICK" = 1 ]; then
    plasmawindowed "$QUICK_ID" > "$SANDBOX/quick.log" 2>&1 &
    QPID=$!
    sleep 8
    shot quicksettings
    stop "$QPID"
    sleep 1
fi
if [ "$TWEAKS" = 1 ]; then
    "$XDG_DATA_HOME"/*-tweaks/main.py > "$SANDBOX/tweaks.log" 2>&1 &
    APPID=$!
    sleep 6
    shot tweaks
    stop "$APPID"
    sleep 1
fi
if [ "$REMIX" != "" ]; then
    # the app's own backend, driven headlessly: rebuild on a new accent and apply
    python3 "$SANDBOX/remix_test.py" "$REMIX" > "$SANDBOX/remix.log" 2>&1
    sleep 6
    shot remixed
    dolphin --new-window "$HOME" >/dev/null 2>&1 &
    RPID=$!
    sleep 5
    shot remixed-window
    stop "$RPID"
    sleep 1
fi
if [ "$FIREFOX" = 1 ]; then
    FFP="$SANDBOX/ffprofile"
    mkdir -p "$FFP/chrome"
    cp "$XDG_DATA_HOME"/firefox/*/*.css "$FFP/chrome/"
    for part in userChrome userContent; do
        printf '@import "%s";\n' "$(basename "$(ls "$FFP/chrome"/*-$part.css)")" > "$FFP/chrome/$part.css"
    done
    {
        echo 'user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);'
        echo 'user_pref("browser.shell.checkDefaultBrowser", false);'
        echo 'user_pref("browser.startup.homepage_override.mstone", "ignore");'
        echo 'user_pref("browser.aboutwelcome.enabled", false);'
        echo 'user_pref("datareporting.policy.dataSubmissionEnabled", false);'
        echo 'user_pref("browser.startup.page", 0);'
        [ "$VARIANT" = dark ] && echo 'user_pref("ui.systemUsesDarkTheme", 1);'
    } > "$FFP/user.js"
    firefox --no-remote --profile "$FFP" about:blank > "$SANDBOX/firefox.log" 2>&1 &
    FXPID=$!
    sleep 16
    shot firefox
    stop "$FXPID"
    sleep 2
fi
if [ "$GTK" = 1 ]; then
    # the sandbox's portal starts mid theme switch and can report the wrong
    # light/dark preference, so tell libadwaita directly
    ADW_DEBUG_COLOR_SCHEME="prefer-$VARIANT" zenity --list --title="Borealis for GTK" --text="libadwaita app, Borealis colors" \
        --column=Component --column=State "Colors" "Done" "Icons" "Done" "Sounds" "Done" \
        --width=520 --height=380 >/dev/null 2>&1 &
    ZPID=$!
    sleep 4
    shot gtk
    stop "$ZPID"
    sleep 1
fi
if [ "$EXTRAS" = 1 ]; then
    /usr/libexec/kscreenlocker_greet --testing >/dev/null 2>&1 &
    LPID=$!
    sleep 5
    shot lockscreen
    if [ -n "$DISPLAY" ] && [ "$DISPLAY" != "$REAL_DISPLAY" ]; then
        # wake the prompt so the password field and action buttons show
        python3 "$SANDBOX/tap_key.py" "click:960,600" > "$SANDBOX/tap.log" 2>&1
        sleep 2
        python3 "$SANDBOX/tap_key.py" 0061 >> "$SANDBOX/tap.log" 2>&1
        sleep 3
        shot lockscreen-prompt
    fi
    stop "$LPID"
    ksplashqml "$LNF" --test >/dev/null 2>&1 &
    KSPID=$!
    sleep 4
    shot splash
    stop "$KSPID"
    sleep 1
fi
if [ "$SDOCK" = 1 ]; then
    # the standalone dock; its KWin bridge is enabled in this sandbox's kwinrc
    sd() { qdbus-qt6 "$SDOCK_BUS" /Dock "${SDOCK_BUS}1.$1" "${@:2}" 2>&1; }
    layout() { sd Layout > "$SANDBOX/sdock-$1.json"; }
    # resting centre of a row along the dock: at_of <layout> <screen length> <app id or kind>
    at_of() {
        python3 -c 'import json, sys
d = json.load(open(sys.argv[1])); start = (int(sys.argv[2]) - d["length"]) / 2
rows = [i for i, r in enumerate(d["rows"]) if sys.argv[3] in (r["appId"], r["kind"])]
print(int(start + d["offsets"][rows[0]] + d["iconSize"] / 2) if rows else -1)' "$SANDBOX/sdock-$1.json" "$2" "$3"
    }
    settle() {      # change the dock's settings file; the dock follows it live
        python3 -c 'import json, os, sys
p = os.path.join(os.environ["XDG_CONFIG_HOME"], sys.argv[1], "dock.json")
d = json.load(open(p)) if os.path.exists(p) else {}
d.update(json.loads(sys.argv[2]))
os.makedirs(os.path.dirname(p), exist_ok=True)
json.dump(d, open(p + ".tmp", "w")); os.replace(p + ".tmp", p)' "$SDOCK_SLUG" "$1"
    }
    tap() { python3 "$SANDBOX/tap_key.py" "$1" >> "$SANDBOX/sdock-input.log" 2>&1; }
    dolphin --new-window "$HOME" >/dev/null 2>&1 &
    S1=$!
    konsole --profile "$PROFILE" -e bash --rcfile "$SANDBOX/demorc" >/dev/null 2>&1 &
    S2=$!
    sleep 4
    "$XDG_DATA_HOME"/*-dock/main.py > "$SANDBOX/sdock.log" 2>&1 &
    SDPID=$!
    sleep 7
    layout rest
    shot sdock-rest
    Y=$(( SCREEN_H - 40 ))
    if [ -n "$DISPLAY" ] && [ "$DISPLAY" != "$REAL_DISPLAY" ]; then
        # hover and click the front app (minimises it)
        DX=$(at_of rest "$SCREEN_W" org.kde.dolphin)
        tap "move:$(( DX - 40 )),$Y"; sleep 0.3
        tap "move:$DX,$Y"; sleep 1
        shot sdock-hover
        tap "click:$DX,$Y"; sleep 2
        layout clicked
        shot sdock-clicked
        tap "move:$(( SCREEN_W / 2 )),300"; sleep 1
        sd OpenMenu 0 >/dev/null; sleep 2
        shot sdock-menu
        tap "click:300,400"; sleep 1
        # launch a pinned app: it bounces until its window shows up
        KX=$(at_of rest "$SCREEN_W" org.kde.kwrite)
        tap "click:$KX,$Y"; sleep 0.5
        layout launching
        tap "move:$(( SCREEN_W / 2 )),300"; sleep 0.3
        shot sdock-launching
        sleep 5
        layout launched
        # drag the second pinned app past the third
        tap "move:$(( SCREEN_W / 2 )),300"; sleep 0.5
        layout before-drag
        FX=$(at_of before-drag "$SCREEN_W" org.mozilla.firefox)
        CX=$(at_of before-drag "$SCREEN_W" org.kde.konsole)
        tap "down:$FX,$Y"; sleep 0.1
        for step in 12 30 60; do tap "move:$(( FX + step )),$Y"; sleep 0.08; done
        tap "move:$CX,$Y"; sleep 0.3
        tap "move:$(( CX + 10 )),$Y"; sleep 0.3
        tap "up:$(( CX + 10 )),$Y"; sleep 1
        layout reordered
        # drag one off the dock: it unpins (and stays as an open app while it has a window)
        tap "move:$(( SCREEN_W / 2 )),300"; sleep 0.5
        layout before-unpin
        WX=$(at_of before-unpin "$SCREEN_W" org.kde.kwrite)
        tap "down:$WX,$Y"; sleep 0.1
        for up in 15 40 90 160 230; do tap "move:$WX,$(( Y - up ))"; sleep 0.08; done
        sleep 0.4
        shot sdock-removing
        tap "up:$WX,$(( Y - 230 ))"; sleep 1.5
        layout unpinned
        shot sdock-unpinned
        # auto-hide: gone when the pointer leaves, back at the screen edge
        settle '{"hide": "auto", "hideDelay": 300}'
        tap "move:$(( SCREEN_W / 2 )),300"; sleep 2
        shot sdock-autohidden
        tap "move:$(( SCREEN_W / 2 )),$(( SCREEN_H - 1 ))"; sleep 1.2
        shot sdock-revealed
        # the left edge
        tap "move:$(( SCREEN_W / 2 )),300"; sleep 0.3
        settle '{"hide": "always", "position": "left"}'
        sleep 3
        layout left
        shot sdock-left
        LY=$(at_of left "$SCREEN_H" org.kde.dolphin)
        tap "move:40,$(( LY - 40 ))"; sleep 0.3
        tap "move:40,$LY"; sleep 1
        shot sdock-left-hover
        tap "move:$(( SCREEN_W / 2 )),300"; sleep 0.5

        # ---- badges, Exposé, Meta+N, Stacks --------------------------------
        settle '{"position": "bottom", "hide": "always"}'
        sleep 3
        # an app publishing a count and progress; it stays on the bus, as apps do
        # (the dock forgets what a sender published once it leaves)
        python3 -c 'import time
from PySide6.QtCore import QCoreApplication
from PySide6.QtDBus import QDBusConnection, QDBusMessage
app = QCoreApplication([])
msg = QDBusMessage.createSignal("/com/canonical/unity/launcherentry/1", "com.canonical.Unity.LauncherEntry", "Update")
msg.setArguments(["application://org.kde.dolphin.desktop",
                  {"count": 3, "count-visible": True, "progress": 0.6, "progress-visible": True}])
print("emitted:", QDBusConnection.sessionBus().send(msg), flush=True)
time.sleep(60)' >> "$SANDBOX/sdock-input.log" 2>&1 &
        EMITTER=$!
        sleep 2
        layout badges
        shot sdock-badges
        # a second Dolphin window comes to the front; clicking Dolphin spreads both
        dolphin --new-window "$HOME/Documents" >/dev/null 2>&1 &
        S3=$!
        sleep 5
        layout two-windows
        DX=$(at_of two-windows "$SCREEN_W" org.kde.dolphin)
        tap "click:$DX,$Y"; sleep 2
        shot sdock-expose
        tap ff1b; sleep 1.5
        # Meta+2: the second app in the dock
        SECOND=$(python3 -c 'import json, sys
rows = [r["appId"] for r in json.load(open(sys.argv[1]))["rows"] if r["kind"] == "app"]
print(rows[1] if len(rows) > 1 else "")' "$SANDBOX/sdock-two-windows.json")
        echo "second app: $SECOND" >> "$SANDBOX/sdock-input.log"
        grep "activate task manager entry 2=" "$XDG_CONFIG_HOME/kglobalshortcutsrc" >> "$SANDBOX/sdock-input.log" 2>&1
        tap "chord:ffeb+0032"; sleep 3
        layout meta2
        # Stacks: the Downloads folder, fanned out, then as a grid
        mkdir -p "$HOME/Downloads"
        for i in 1 2 3 4 5; do
            python3 -c "from PIL import Image; Image.new('RGB', (96, 64), ($(( 40 * i )), 150, 220)).save('$HOME/Downloads/photo-$i.png')"
            sleep 0.1
        done
        echo "notes" > "$HOME/Downloads/notes.txt"
        sleep 2
        layout stacks
        SX=$(at_of stacks "$SCREEN_W" stack)
        tap "move:$(( SX - 30 )),$Y"; sleep 0.3
        tap "click:$SX,$Y"; sleep 2
        shot sdock-stack-fan
        tap "click:200,300"; sleep 1
        for i in 1 2 3 4 5 6 7 8 9 10; do echo x > "$HOME/Downloads/file-$i.txt"; done
        sleep 2
        tap "move:$(( SX - 30 )),$Y"; sleep 0.3
        tap "click:$SX,$Y"; sleep 2
        shot sdock-stack-grid
        tap "click:200,300"; sleep 1
        stop "$S3" "$EMITTER"

        # ---- previews, Launchpad, widgets, presets -------------------------
        dolphin --new-window "$HOME/Music" >/dev/null 2>&1 &
        S4=$!
        sleep 4
        tap "move:$(( SCREEN_W / 2 )),300"; sleep 0.5
        layout previews
        DX=$(at_of previews "$SCREEN_W" org.kde.dolphin)
        # rest on Dolphin (two windows): live previews above it
        tap "move:$(( DX - 30 )),$Y"; sleep 0.2
        tap "move:$DX,$Y"; sleep 1.8
        sd State > "$SANDBOX/sdock-state-preview.json"
        shot sdock-preview
        # up into them: they stay, and a click switches to that window
        tap "move:$DX,$(( Y - 90 ))"; sleep 0.25
        tap "move:$(( DX - 60 )),$(( Y - 170 ))"; sleep 1
        sd State > "$SANDBOX/sdock-state-preview-hover.json"
        shot sdock-preview-hover
        tap "click:$(( DX - 110 )),$(( Y - 170 ))"; sleep 1.5
        sd State > "$SANDBOX/sdock-state-preview-click.json"
        tap "move:$(( SCREEN_W / 2 )),300"; sleep 1
        shot sdock-preview-clicked
        # Launchpad: its dock icon, then typing and Return
        LX=$(at_of previews "$SCREEN_W" launchpad)
        tap "move:$(( LX + 30 )),$Y"; sleep 0.2
        tap "click:$LX,$Y"; sleep 1.5
        shot sdock-launchpad
        for k in 006b 0063 0061 006c; do tap "$k"; sleep 0.15; done
        sleep 1.5
        sd State > "$SANDBOX/sdock-state-launchpad.json"
        shot sdock-launchpad-search
        tap ff0d; sleep 3
        layout launchpad-launched
        sd State > "$SANDBOX/sdock-state-launchpad-closed.json"
        # Meta+Space opens it anywhere; Escape leaves
        tap "chord:ffeb+0020"; sleep 1.5
        sd State > "$SANDBOX/sdock-state-launchpad-key.json"
        tap ff1b; sleep 1
        # a lone Meta works too, once given to Launchpad in the shortcut settings
        # (here: taken from Plasma's launcher, which holds it by default)
        busctl --user call org.kde.kglobalaccel /kglobalaccel org.kde.KGlobalAccel setForeignShortcutKeys 'asa(ai)' \
            4 plasmashell "activate application launcher" plasmashell "Activate Application Launcher" \
            1 1 $(( 0x08000000 | 0x01000030 )) >> "$SANDBOX/sdock-input.log" 2>&1
        busctl --user call org.kde.kglobalaccel /kglobalaccel org.kde.KGlobalAccel setForeignShortcutKeys 'asa(ai)' \
            4 kwin "$SDOCK_LAUNCHPAD" KWin "$SDOCK_LAUNCHPAD" \
            2 1 $(( 0x10000000 | 0x20 )) 1 $(( 0x01000022 )) >> "$SANDBOX/sdock-input.log" 2>&1
        sleep 1
        tap ffeb; sleep 1.5
        sd State > "$SANDBOX/sdock-state-meta.json"
        tap ff1b; sleep 1
        # widgets: a clock, the battery, and a player saying what's playing
        python3 "$SANDBOX/mpris_fake.py" "file://$XDG_DATA_HOME/wallpapers/Borealis/contents/images/1280x1024.jpg" \
            >> "$SANDBOX/sdock-input.log" 2>&1 &
        PLAYER=$!
        settle '{"widgets": [{"type": "clock", "style": "analog"}, {"type": "battery"}, {"type": "media"}]}'
        sleep 3
        layout widgets
        sd State > "$SANDBOX/sdock-state-widgets.json"
        shot sdock-widgets
        MX=$(at_of widgets "$SCREEN_W" media)
        if [ "$MX" -ge 0 ]; then
            tap "move:$(( MX - 30 )),$Y"; sleep 0.2
            tap "move:$MX,$Y"; sleep 1
            shot sdock-widget-label
            tap "click:$MX,$Y"; sleep 1.5
            sd State > "$SANDBOX/sdock-state-paused.json"
        fi
        CX=$(at_of widgets "$SCREEN_W" clock)
        tap "click:$CX,$Y"; sleep 1.5
        shot sdock-calendar
        tap ff1b; sleep 1
        BX=$(at_of widgets "$SCREEN_W" battery)
        if [ "$BX" -ge 0 ]; then
            # look only: its menu switches the machine's real power mode
            tap "click:$BX,$Y"; sleep 1.5
            shot sdock-battery-menu
            tap ff1b; sleep 1
        fi
        tap "move:$(( SCREEN_W / 2 )),300"; sleep 0.5
        # presets from the command line: the dock follows its settings file
        DOCKCMD=$(ls "$XDG_DATA_HOME"/*-dock/main.py)
        "$DOCKCMD" --preset macos >> "$SANDBOX/sdock-input.log" 2>&1; sleep 3
        tap "move:$(( SCREEN_W / 2 - 80 )),$Y"; sleep 0.3
        tap "move:$(( SCREEN_W / 2 )),$Y"; sleep 1
        shot sdock-preset-macos
        tap "move:$(( SCREEN_W / 2 )),300"; sleep 0.5
        "$DOCKCMD" --preset minimal >> "$SANDBOX/sdock-input.log" 2>&1; sleep 2
        tap "move:$(( SCREEN_W / 2 )),$(( SCREEN_H - 1 ))"; sleep 1.5
        shot sdock-preset-minimal
        "$DOCKCMD" --list-presets >> "$SANDBOX/sdock-input.log" 2>&1
        "$DOCKCMD" --export-preset "$SANDBOX/shared-preset.json" >> "$SANDBOX/sdock-input.log" 2>&1
        "$DOCKCMD" --preset borealis >> "$SANDBOX/sdock-input.log" 2>&1
        tap "move:$(( SCREEN_W / 2 )),300"; sleep 2
        stop "$PLAYER" "$S4"
        # the dock's page in Borealis Tweaks
        "$XDG_DATA_HOME"/*-tweaks/main.py --page dock > "$SANDBOX/sdock-tweaks.log" 2>&1 &
        TW=$!
        sleep 7
        shot sdock-tweaks
        stop "$TW"
        sleep 1
    fi
    sd Quit >/dev/null
    sleep 1
    stop "$SDPID" "$S1" "$S2"
    sleep 1
fi
stop "$SHELLPID"
sleep 1
"""


DEMORC = r"""PS1='\[\e[1;36m\]aurora\[\e[0m\] \[\e[1;34m\]\w\[\e[0m\] \[\e[35m\]❯\[\e[0m\] '
P='\e[1;36maurora\e[0m \e[1;34m~/Projects/borealis\e[0m \e[35m❯\e[0m'
clear
printf '\e[1;34m ╭─────────────────────────────╮\e[0m\n'
printf '\e[1;34m │\e[0m   \e[1;36mBorealis\e[0m \e[2mfor KDE Plasma\e[0m   \e[1;34m│\e[0m\n'
printf '\e[1;34m ╰─────────────────────────────╯\e[0m\n\n'
printf "$P ls\n"
ls --color=always -F
printf "\n$P git log --oneline -4\n"
printf '\e[33ma91f3c2\e[0m \e[36m(\e[1;36mHEAD -> \e[1;32mmain\e[0;36m)\e[0m Pill buttons for the titlebar\n'
printf '\e[33m7c2e8d1\e[0m Frosted Plasma style with 12px corners\n'
printf '\e[33m3b4f0a9\e[0m Aurora wallpapers: night and dawn\n'
printf '\e[33me5d1c77\e[0m The Borealis palette\n\n'
for i in 0 1 2 3 4 5 6 7; do printf '\e[4%sm    \e[0m' $i; done; echo
for i in 0 1 2 3 4 5 6 7; do printf '\e[10%sm    \e[0m' $i; done; echo; echo
"""

SAMPLE_PY = '''"""Aurora ribbons for the Borealis wallpaper."""
import math
from dataclasses import dataclass

TEAL, PERIWINKLE = "#5fe0c8", "#8b9cff"


@dataclass
class Ribbon:
    y0: float          # base height (0..1)
    amplitude: float = 0.05
    strength: float = 1.0

    def base(self, t: float) -> float:
        # a gentle S-curve across the sky
        return self.y0 - 0.3 * t + self.amplitude * math.sin(t * 4.4)


def render(ribbons: list[Ribbon], width: int = 3840) -> int:
    drawn = 0
    for rb in ribbons:
        for x in range(0, width, 2):
            if rb.strength * 0.42 < 0.003:
                continue
            drawn += 1
    return drawn


if __name__ == "__main__":
    print(f"rays drawn: {render([Ribbon(0.64), Ribbon(0.42, strength=0.5)])}")
'''

ARRANGE_JS = r"""
const wins = workspace.windowList();
for (let i = 0; i < wins.length; i++) {
    const w = wins[i];
    if (!w.normalWindow) continue;
    const rc = String(w.resourceClass);
    if (rc.indexOf("dolphin") >= 0)
        w.frameGeometry = {x: 250, y: 150, width: 1000, height: 660};
    else if (rc.indexOf("konsole") >= 0)
        w.frameGeometry = {x: 880, y: 430, width: 800, height: 500};
}
"""

HOLD_ALT_TAB = r"""import ctypes, os, sys, time
# Refuse to talk to anything but the nested session's own Xwayland.
disp = os.environ.get("DISPLAY", "")
if not disp or disp == os.environ.get("REAL_DISPLAY", ""):
    sys.exit("refusing: DISPLAY is not the nested one")
x = ctypes.CDLL("libX11.so.6")
t = ctypes.CDLL("libXtst.so.6")
x.XOpenDisplay.restype = ctypes.c_void_p
x.XOpenDisplay.argtypes = [ctypes.c_char_p]
x.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
x.XFlush.argtypes = [ctypes.c_void_p]
t.XTestFakeKeyEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]
d = x.XOpenDisplay(disp.encode())
if not d:
    sys.exit("cannot open " + disp)
ALT, TAB = x.XKeysymToKeycode(d, 0xffe9), x.XKeysymToKeycode(d, 0xff09)
def key(code, down):
    t.XTestFakeKeyEvent(d, code, down, 0)
    x.XFlush(d)
key(ALT, 1); time.sleep(0.1); key(TAB, 1); time.sleep(0.05); key(TAB, 0)
time.sleep(float(sys.argv[1]) if len(sys.argv) > 1 else 4)
key(ALT, 0)
print("ok", disp)
"""


REMIX_TEST = r"""#!/usr/bin/env python3
# Drives Borealis Tweaks' backend inside the nested session: build a remix on
# the given accent and apply it here.
import glob
import sys

from PySide6.QtCore import QCoreApplication, QTimer

sys.path.insert(0, glob.glob(__import__("os").environ["XDG_DATA_HOME"] + "/*-tweaks")[0])
from backend import Backend  # noqa: E402

app = QCoreApplication([])
b = Backend()
b.logged.connect(lambda line: print(line, flush=True))
b.finished.connect(lambda ok, msg: (print(f"FINISHED ok={ok} {msg}", flush=True), app.quit()))
QTimer.singleShot(0, lambda: b.remix(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "Borealis Moss",
                                     False, False))
app.exec()
"""

SWAP_DOCK = """
var ps = panels();
for (var i = 0; i < ps.length; i++) {
    if (String(ps[i].location) !== "bottom") { continue; }
    var ids = ps[i].widgetIds;
    for (var j = 0; j < ids.length; j++) {
        var w = ps[i].widgetById(ids[j]);
        if (w && String(w.type).indexOf("icontasks") >= 0) { w.remove(); }
    }
    var dock = ps[i].addWidget("@DOCK_ID@");
    print("added " + dock.type);
}
"""

TAP_KEY = r"""import ctypes, os, sys, time
disp = os.environ.get("DISPLAY", "")
if not disp or disp == os.environ.get("REAL_DISPLAY", ""):
    sys.exit("refusing: DISPLAY is not the nested one")
x = ctypes.CDLL("libX11.so.6")
t = ctypes.CDLL("libXtst.so.6")
x.XOpenDisplay.restype = ctypes.c_void_p
x.XOpenDisplay.argtypes = [ctypes.c_char_p]
x.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
x.XFlush.argtypes = [ctypes.c_void_p]
t.XTestFakeKeyEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]
t.XTestFakeMotionEvent.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_ulong]
t.XTestFakeButtonEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]
d = x.XOpenDisplay(disp.encode())
arg = sys.argv[1] if len(sys.argv) > 1 else "ff1b"
if arg.startswith("move:"):                  # move:X,Y — hover, no click
    cx, cy = (int(v) for v in arg.split(":")[1].split(","))
    t.XTestFakeMotionEvent(d, 0, cx, cy, 0); x.XFlush(d)
    print("moved to", cx, cy, "on", disp)
elif arg.startswith(("down:", "up:")):          # down:X,Y / up:X,Y — press or release there (drags)
    cx, cy = (int(v) for v in arg.split(":")[1].split(","))
    t.XTestFakeMotionEvent(d, 0, cx, cy, 0); x.XFlush(d)
    time.sleep(0.05)
    t.XTestFakeButtonEvent(d, 1, 1 if arg.startswith("down:") else 0, 0); x.XFlush(d)
    print(arg.split(":")[0], cx, cy, "on", disp)
elif arg.startswith("chord:"):                 # chord:ffeb+0032 — hold the first keys, tap the last
    codes = [x.XKeysymToKeycode(d, int(k, 16)) for k in arg.split(":")[1].split("+")]
    for code in codes:
        t.XTestFakeKeyEvent(d, code, 1, 0); x.XFlush(d)
        time.sleep(0.06)
    for code in reversed(codes):
        t.XTestFakeKeyEvent(d, code, 0, 0); x.XFlush(d)
        time.sleep(0.06)
    print("chord", arg.split(":")[1], "on", disp)
elif arg.startswith("click:"):                 # click:X,Y — focus a window, then wake it
    cx, cy = (int(v) for v in arg.split(":")[1].split(","))
    t.XTestFakeMotionEvent(d, 0, cx, cy, 0); x.XFlush(d)
    time.sleep(0.3)
    t.XTestFakeButtonEvent(d, 1, 1, 0); x.XFlush(d)
    time.sleep(0.05)
    t.XTestFakeButtonEvent(d, 1, 0, 0); x.XFlush(d)
    print("clicked", cx, cy, "on", disp)
else:
    code = x.XKeysymToKeycode(d, int(arg, 16))
    t.XTestFakeKeyEvent(d, code, 1, 0); x.XFlush(d)
    time.sleep(0.05)
    t.XTestFakeKeyEvent(d, code, 0, 0); x.XFlush(d)
    print("tapped", hex(code), "on", disp)
"""

MPRIS_FAKE = r"""import sys
from PySide6.QtCore import ClassInfo, Property, QCoreApplication, QObject, QTimer, Slot
from PySide6.QtDBus import QDBusAbstractAdaptor, QDBusConnection, QDBusMessage

# a media player as the dock sees one: MPRIS on the session bus
ART = sys.argv[1] if len(sys.argv) > 1 else ""


@ClassInfo({"D-Bus Interface": "org.mpris.MediaPlayer2"})
class Root(QDBusAbstractAdaptor):
    @Property(str)
    def Identity(self):
        return "Elisa"

    @Property(str)
    def DesktopEntry(self):
        return "org.kde.elisa"

    @Property(bool)
    def CanRaise(self):
        return True

    @Slot()
    def Raise(self):
        print("player: raise", flush=True)


@ClassInfo({"D-Bus Interface": "org.mpris.MediaPlayer2.Player"})
class Player(QDBusAbstractAdaptor):
    status = "Playing"

    @Property(str)
    def PlaybackStatus(self):
        return Player.status

    @Property("QVariantMap")
    def Metadata(self):
        return {"xesam:title": "Northern Lights", "xesam:artist": ["Aurora Band"], "mpris:artUrl": ART}

    @Property(bool)
    def CanGoNext(self):
        return True

    @Property(bool)
    def CanGoPrevious(self):
        return True

    @Property(bool)
    def CanPause(self):
        return True

    @Property(bool)
    def CanPlay(self):
        return True

    @Slot()
    def PlayPause(self):
        Player.status = "Paused" if Player.status == "Playing" else "Playing"
        print("player:", Player.status, flush=True)
        msg = QDBusMessage.createSignal("/org/mpris/MediaPlayer2", "org.freedesktop.DBus.Properties",
                                        "PropertiesChanged")
        msg.setArguments(["org.mpris.MediaPlayer2.Player", {"PlaybackStatus": Player.status}, []])
        QDBusConnection.sessionBus().send(msg)

    @Slot()
    def Next(self):
        print("player: next", flush=True)


app = QCoreApplication(sys.argv)
holder = QObject()
Root(holder)
Player(holder)
bus = QDBusConnection.sessionBus()
print("player registered:", bus.registerObject("/org/mpris/MediaPlayer2", holder),
      bus.registerService("org.mpris.MediaPlayer2.elisa"), flush=True)
QTimer.singleShot(180000, app.quit)
app.exec()
"""

MAXIMIZE_JS = r"""
const wins = workspace.windowList();
for (let i = 0; i < wins.length; i++) {
    const w = wins[i];
    if (w.normalWindow && String(w.resourceClass).indexOf("dolphin") >= 0) {
        w.opacity = 0.35;
        w.setMaximize(true, true);
    }
}
"""

RESTORE_JS = r"""
const wins = workspace.windowList();
for (let i = 0; i < wins.length; i++) {
    const w = wins[i];
    if (w.normalWindow && String(w.resourceClass).indexOf("dolphin") >= 0) {
        w.setMaximize(false, false);
        w.frameGeometry = {x: 1100, y: 700, width: 700, height: 400};
    }
}
"""


def reap(sandbox):
    """Stop anything the nested session left behind (bus-activated daemons)."""
    import signal
    import time
    for attempt in range(2):
        for pid in os.listdir("/proc"):
            if not pid.isdigit():
                continue
            try:
                env = open(f"/proc/{pid}/environ", "rb").read().split(b"\0")
            except OSError:
                continue
            if any(e.startswith(b"XDG_DATA_HOME=") and sandbox.encode() in e for e in env):
                try:
                    os.kill(int(pid), signal.SIGTERM if attempt == 0 else signal.SIGKILL)
                except OSError:
                    pass
        time.sleep(1.5)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("variant", choices=("dark", "light"))
    ap.add_argument("--keep", action="store_true", help="keep the sandbox directory")
    ap.add_argument("--no-apps", action="store_true")
    ap.add_argument("--no-extras", action="store_true")
    ap.add_argument("--size", default="1920x1200")
    ap.add_argument("--scale", default="1", help="output scale, e.g. 1.5 or 2")
    ap.add_argument("--live", action="store_true", help="also test the animated wallpaper")
    ap.add_argument("--switcher", action="store_true", help="also show the Alt+Tab switcher (preview helper)")
    ap.add_argument("--gtk", action="store_true", help="also show a GTK4/libadwaita dialog")
    ap.add_argument("--tweaks", action="store_true", help="also open the Borealis Tweaks app")
    ap.add_argument("--firefox", action="store_true", help="also open Firefox with the Borealis chrome")
    ap.add_argument("--dock", action="store_true", help="swap the panel's task manager for the Borealis dock")
    ap.add_argument("--quicksettings", action="store_true", help="open the Quick Settings widget in a window")
    ap.add_argument("--standalone-dock", action="store_true",
                    help="run the standalone dock with its KWin bridge (hover, click, menu)")
    ap.add_argument("--remix", metavar="HEX", default="",
                    help="also remix onto this accent through the app's backend, e.g. '#4fbf6a'")
    args = ap.parse_args()
    if not os.path.isdir(SHARE):
        sys.exit("build/share missing: run ./build.py first")

    shots = os.path.join(HERE, "build", "shots", args.variant)
    # keep what earlier runs captured: the look-and-feel previews are built
    # from them, and one run rarely takes every screenshot
    os.makedirs(shots, exist_ok=True)
    sandbox = tempfile.mkdtemp(prefix="borealis-test-")
    for d in ("config", "config/kdedefaults", "cache", "state"):
        os.makedirs(os.path.join(sandbox, d))
    data = os.path.join(sandbox, "data")
    shutil.copytree(SHARE, data, symlinks=True)
    user_icons = os.path.expanduser("~/.local/share/icons")
    for name in ("Tela", "Tela-dark", "Tela-light"):
        src = os.path.join(user_icons, name)
        if os.path.isdir(src) and not os.path.exists(os.path.join(data, "icons", name)):
            os.symlink(src, os.path.join(data, "icons", name))
    # keep the nested session self-contained: no podman probing (Konsole),
    # no first-run welcome window
    fakebin = os.path.join(sandbox, "bin")
    os.makedirs(fakebin)
    with open(os.path.join(fakebin, "podman"), "w") as f:
        f.write("#!/bin/sh\nexit 127\n")
    os.chmod(os.path.join(fakebin, "podman"), 0o755)
    os.makedirs(os.path.join(sandbox, "config", "autostart"))
    for app in ("org.kde.plasma-welcome", "org.kde.kdeconnect.daemon"):
        with open(os.path.join(sandbox, "config", "autostart", app + ".desktop"), "w") as f:
            f.write("[Desktop Entry]\nType=Application\nHidden=true\n")
    if args.gtk:
        import glob
        css = glob.glob(os.path.join(SHARE, "gtk", "*", "*-libadwaita.css"))[0]
        name = os.path.basename(css)
        os.makedirs(os.path.join(sandbox, "config", "gtk-4.0"), exist_ok=True)
        shutil.copy(css, os.path.join(sandbox, "config", "gtk-4.0", name))
        with open(os.path.join(sandbox, "config", "gtk-4.0", "gtk.css"), "w") as f:
            f.write(f"@import 'colors.css';\n@import '{name}';\n")
    kwinrc = ""
    if args.switcher or args.standalone_dock:
        # sandbox only: let the nested Xwayland's XTest input through unprompted
        kwinrc += "[Xwayland]\nXwaylandEisNoPrompt=true\n\n"
    sdock_bus = sdock_slug = sdock_launchpad = ""
    if args.standalone_dock:
        import glob
        import re
        bridge = next(iter(glob.glob(os.path.join(SHARE, "kwin", "scripts", "*-dockbridge"))), "")
        app = next(iter(glob.glob(os.path.join(data, "*-dock"))), "")
        if not (bridge and app):
            sys.exit("the standalone dock isn't built: ./build.py dock")
        kwinrc += f"[Plugins]\n{os.path.basename(bridge)}Enabled=true\n"
        ids_text = open(os.path.join(app, "ids.py")).read()
        sdock_bus = re.search(r"^BUS = ['\"](.+)['\"]$", ids_text, re.M).group(1)
        sdock_slug = re.search(r"^SLUG = ['\"](.+)['\"]$", ids_text, re.M).group(1)
        sdock_launchpad = re.search(r"^LAUNCHPAD_SHORTCUT = ['\"](.+)['\"]$", ids_text, re.M).group(1)
        # the layout script asks applicationExists() for the dock's command
        os.symlink(os.path.join(app, "main.py"), os.path.join(fakebin, os.path.basename(app)))
        # apps launched with files go through systemd-run: run them directly here
        with open(os.path.join(fakebin, "systemd-run"), "w") as f:
            f.write('#!/bin/sh\nwhile [ $# -gt 0 ] && [ "$1" != "--" ]; do shift; done\nshift\nexec "$@"\n')
        os.chmod(os.path.join(fakebin, "systemd-run"), 0o755)
    if kwinrc:
        with open(os.path.join(sandbox, "config", "kwinrc"), "w") as f:
            f.write(kwinrc)
    if args.live:
        with open(os.path.join(sandbox, "config", "kscreenlockerrc"), "w") as f:
            f.write("[Greeter]\nWallpaperPlugin=org.borealis.aurora\n")
    with open(os.path.join(sandbox, "config", "plasma-welcomerc"), "w") as f:
        f.write("[General]\nLastSeenVersion=99.0.0\nShowUpdatePage=false\n")
    home = os.path.join(sandbox, "home")
    for d in ("Desktop", "Documents", "Downloads", "Music", "Pictures", "Projects",
              "Public", "Templates", "Videos"):
        os.makedirs(os.path.join(home, d))
    for fn in ("notes.md", "aurora.png", "report.pdf"):
        open(os.path.join(home, "Documents", fn), "w").close()
    proj = os.path.join(home, "Projects", "borealis")
    for d in ("src", "build", "assets"):
        os.makedirs(os.path.join(proj, d))
    for fn in ("README.md", "build.py", "install.sh", "LICENSE"):
        open(os.path.join(proj, fn), "w").close()
    os.chmod(os.path.join(proj, "install.sh"), 0o755)
    os.chmod(os.path.join(proj, "build.py"), 0o755)
    with open(os.path.join(proj, "src", "aurora.py"), "w") as f:
        f.write(SAMPLE_PY)
    theme = "Borealis Dark" if args.variant == "dark" else "Borealis Light"
    with open(os.path.join(sandbox, "config", "kwriterc"), "w") as f:
        f.write("[KTextEditor Renderer]\nAuto Color Theme Selection=false\n"
                f"Color Theme={theme}\n")
    with open(os.path.join(sandbox, "demorc"), "w") as f:
        f.write(DEMORC)
    with open(os.path.join(sandbox, "arrange.js"), "w") as f:
        f.write(ARRANGE_JS)
    with open(os.path.join(sandbox, "hold_alt_tab.py"), "w") as f:
        f.write(HOLD_ALT_TAB)
    with open(os.path.join(sandbox, "tap_key.py"), "w") as f:
        f.write(TAP_KEY)
    with open(os.path.join(sandbox, "mpris_fake.py"), "w") as f:
        f.write(MPRIS_FAKE)
    import glob as _glob
    dock_id = os.path.basename(next(iter(_glob.glob(os.path.join(SHARE, "plasma", "plasmoids", "*.dock"))), "org.borealis.dock"))
    with open(os.path.join(sandbox, "swapdock.js"), "w") as f:
        f.write(SWAP_DOCK.replace("@DOCK_ID@", dock_id))
    with open(os.path.join(sandbox, "remix_test.py"), "w") as f:
        f.write(REMIX_TEST)
    for name, js in (("maximize.js", MAXIMIZE_JS), ("restore.js", RESTORE_JS)):
        with open(os.path.join(sandbox, name), "w") as f:
            f.write(js)
    script = os.path.join(sandbox, "session.sh")
    with open(script, "w") as f:
        f.write(SESSION)
    os.chmod(script, 0o755)

    w, h = args.size.split("x")
    env = {
        "HOME": home, "USER": os.environ.get("USER", ""),
        "PATH": fakebin + ":/usr/bin:/bin", "SHELL": "/bin/bash", "LANG": os.environ.get("LANG", "en_US.UTF-8"),
        "XDG_RUNTIME_DIR": os.environ["XDG_RUNTIME_DIR"],
        "XDG_CONFIG_HOME": os.path.join(sandbox, "config"),
        "XDG_DATA_HOME": data,
        "XDG_CACHE_HOME": os.path.join(sandbox, "cache"),
        "XDG_STATE_HOME": os.path.join(sandbox, "state"),
        "XDG_DATA_DIRS": "/usr/local/share:/usr/share",
        "XDG_CONFIG_DIRS": os.path.join(sandbox, "config", "kdedefaults") + ":/etc/xdg",
        "XDG_SESSION_TYPE": "wayland", "XDG_CURRENT_DESKTOP": "KDE",
        "KDE_FULL_SESSION": "true", "KDE_SESSION_VERSION": "6",
        "QT_QPA_PLATFORM": "wayland",
        "SANDBOX": sandbox, "SHOTS": shots,
        "LNF": "Borealis-Dark" if args.variant == "dark" else "Borealis-Light",
        "PROFILE": "Borealis Dark" if args.variant == "dark" else "Borealis Light",
        "APPS": "0" if args.no_apps else "1",
        "EXTRAS": "0" if args.no_extras else "1",
        "LIVE": "1" if args.live else "0",
        "SWITCHER": "1" if args.switcher else "0",
        "OUTSCALE": args.scale,
        "GTK": "1" if args.gtk else "0",
        "TWEAKS": "1" if args.tweaks else "0",
        "FIREFOX": "1" if args.firefox else "0",
        "DOCK": "1" if args.dock else "0",
        "QUICK": "1" if args.quicksettings else "0",
        "QUICK_ID": os.path.basename(next(iter(__import__("glob").glob(
            os.path.join(SHARE, "plasma", "plasmoids", "*.quicksettings"))), "org.borealis.quicksettings")),
        "REMIX": args.remix,
        "BOREALIS_PROJECT": HERE,
        "VARIANT": args.variant,
        "REAL_DISPLAY": os.environ.get("DISPLAY", ":0"),
        "SDOCK": "1" if args.standalone_dock else "0", "SDOCK_BUS": sdock_bus, "SDOCK_SLUG": sdock_slug,
        "SDOCK_LAUNCHPAD": sdock_launchpad,
        "SCREEN_W": w, "SCREEN_H": h,
    }
    # the standalone dock's run walks through every feature, and takes a while
    cmd = ["timeout", "330" if args.standalone_dock else "120", "dbus-run-session", "--",
           "kwin_wayland", "--virtual", "--no-lockscreen",
           "--width", w, "--height", h,
           "--socket", f"wayland-borealis-{os.getpid()}"]
    if args.switcher or args.dock or args.standalone_dock or not args.no_extras:
        cmd.append("--xwayland")      # only so XTest can reach the nested KWin
    cmd += ["--exit-with-session", script]
    with open(os.path.join(sandbox, "kwin.log"), "w") as log:
        subprocess.run(cmd, env=env, stdout=log, stderr=subprocess.STDOUT)
    reap(sandbox)
    print("screenshots:", ", ".join(sorted(os.listdir(shots))) or "none")
    if args.keep:
        print("sandbox kept at", sandbox)
    else:
        shutil.rmtree(sandbox, ignore_errors=True)


if __name__ == "__main__":
    main()
