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
    stop "$LPID"
    ksplashqml "$LNF" --test >/dev/null 2>&1 &
    KSPID=$!
    sleep 4
    shot splash
    stop "$KSPID"
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
    args = ap.parse_args()
    if not os.path.isdir(SHARE):
        sys.exit("build/share missing: run ./build.py first")

    shots = os.path.join(HERE, "build", "shots", args.variant)
    shutil.rmtree(shots, ignore_errors=True)
    os.makedirs(shots)
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
        name = "borealis-libadwaita.css"
        os.makedirs(os.path.join(sandbox, "config", "gtk-4.0"), exist_ok=True)
        shutil.copy(os.path.join(SHARE, "gtk", "borealis", name),
                    os.path.join(sandbox, "config", "gtk-4.0", name))
        with open(os.path.join(sandbox, "config", "gtk-4.0", "gtk.css"), "w") as f:
            f.write(f"@import 'colors.css';\n@import '{name}';\n")
    if args.switcher:
        # sandbox only: let the nested Xwayland's XTest input through unprompted
        with open(os.path.join(sandbox, "config", "kwinrc"), "w") as f:
            f.write("[Xwayland]\nXwaylandEisNoPrompt=true\n")
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
        "VARIANT": args.variant,
        "REAL_DISPLAY": os.environ.get("DISPLAY", ":0"),
    }
    cmd = ["timeout", "120", "dbus-run-session", "--",
           "kwin_wayland", "--virtual", "--no-lockscreen",
           "--width", w, "--height", h,
           "--socket", f"wayland-borealis-{os.getpid()}"]
    if args.switcher:
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
