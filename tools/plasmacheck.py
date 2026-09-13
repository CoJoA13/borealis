#!/usr/bin/env python3
"""Put the Borealis Tweaks Plasma pages' backends through their changes without
touching the session.

    python3 tools/plasmacheck.py

Each change is written into a throwaway config folder (kwriteconfig6 runs
for real, minus --notify) and read back the way Plasma reads it; the D-Bus
calls and signals a page would send (busctl, dbus-send) and the pointer
theme tool are written down instead of run, and what the pages would ask
KWin and kglobalaccel for comes from stand-ins. No session bus is reachable
from here at all.
"""
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TWEAKS = os.path.join(HERE, "src", "tweaks")
home = tempfile.mkdtemp(prefix="plasmacheck-")
# like a Plasma session, the Global Theme's defaults are a system config folder,
# which is what makes kwriteconfig6 --delete hide them
os.environ.update(QT_QPA_PLATFORM="offscreen", XDG_CONFIG_HOME=os.path.join(home, "config"),
                  XDG_DATA_HOME=os.path.join(home, "data"), XDG_STATE_HOME=os.path.join(home, "state"),
                  XDG_CACHE_HOME=os.path.join(home, "cache"),
                  XDG_CONFIG_DIRS=os.path.join(home, "config", "kdedefaults") + ":" + os.path.join(home, "etc"))
os.environ.pop("DBUS_SESSION_BUS_ADDRESS", None)     # so nothing can slip through to the real session
sys.path.insert(0, TWEAKS)

FONTS_CONF = """<?xml version='1.0'?>
<!DOCTYPE fontconfig SYSTEM 'urn:fontconfig:fonts.dtd'>
<fontconfig>
 <!-- synthetic emboldening, which must survive -->
 <match target="font">
  <test compare="more_eq" name="weight" target="pattern"><const>bold</const></test>
  <edit mode="assign" name="embolden"><bool>true</bool></edit>
 </match>
 <match target="font">
  <edit mode="assign" name="hintstyle"><const>hintslight</const></edit>
 </match>
</fontconfig>
"""

failures = 0


def check(what, good, detail=""):
    global failures
    print(("ok: " if good else "FAIL: ") + what + ("" if good or detail == "" else f" ({detail})"))
    failures += not good


def setup():
    """The Borealis defaults a real install leaves, and a Borealis decoration built with 8 px corners."""
    conf = os.environ["XDG_CONFIG_HOME"]
    os.makedirs(os.path.join(conf, "kdedefaults"), exist_ok=True)
    with open(os.path.join(conf, "kdedefaults", "kwinrc"), "w") as f:
        f.write("[org.kde.kdecoration2]\nButtonsOnLeft=M\nButtonsOnRight=IAX\n"
                "library=org.kde.kwin.aurorae.v2\ntheme=__aurorae__svg__Borealis-Dark\n")
    with open(os.path.join(conf, "kdedefaults", "kcminputrc"), "w") as f:
        f.write("[Mouse]\ncursorTheme=Borealis-Snow-Cursors\n")
    os.makedirs(os.path.join(conf, "fontconfig"), exist_ok=True)
    with open(os.path.join(conf, "fontconfig", "fonts.conf"), "w") as f:
        f.write(FONTS_CONF)
    built = os.path.join(home, "built")
    for radius in (0, 24, 8):
        r = subprocess.run([sys.executable, os.path.join(HERE, "build.py"), "aurorae", "--out", built,
                            "--window-radius", str(radius)], capture_output=True, text=True)
        theme = os.path.join(built, "aurorae", "themes", "Borealis-Dark")
        try:
            ET.parse(os.path.join(theme, "decoration.svg"))
            parsed = True
        except (ET.ParseError, OSError):
            parsed = False
        rc = open(os.path.join(theme, "Borealis-Darkrc")).read() if os.path.exists(theme) else ""
        check(f"the decoration builds with {radius} px corners", r.returncode == 0 and parsed
              and f"CornerRadius={radius}" in rc, r.stderr[-300:])
    shutil.copytree(os.path.join(built, "aurorae"), os.path.join(os.environ["XDG_DATA_HOME"], "aurorae"))


setup()

from PySide6.QtGui import QGuiApplication, QKeySequence  # noqa: E402
app = QGuiApplication(["plasmacheck"])

import backend as tweaks_backend  # noqa: E402
import dockpage  # noqa: E402,F401  (finds the dock's names, as main.py does)
import plasmasettings as ps  # noqa: E402

sent = []
_real_run = subprocess.run


def fake_run(argv):
    if argv and argv[0] == "kwriteconfig6":
        _real_run([a for a in argv if a != "--notify"], capture_output=True, text=True)
    else:
        sent.append([str(a) for a in argv])


def fake_detached(argv):
    sent.append([str(a) for a in argv])


LAUNCHPAD_KEYS = [150994992, 268435488, 16777250]       # Alt+F1, Meta+Space, Meta
TOUCHPAD = {"name": ("s", "Test Touchpad"), "touchpad": ("b", True), "tapToClick": ("b", True),
            "tapToClickEnabledByDefault": ("b", True), "tapAndDrag": ("b", True), "tapFingerCount": ("i", 3),
            "tapDragLock": ("b", False), "lmrTapButtonMap": ("b", False), "supportsLmrTapButtonMap": ("b", True),
            "clickMethodAreas": ("b", True), "clickMethodClickfinger": ("b", False),
            "supportsClickMethodAreas": ("b", True), "supportsClickMethodClickfinger": ("b", True),
            "scrollTwoFinger": ("b", True), "scrollEdge": ("b", False), "supportsScrollTwoFinger": ("b", True),
            "supportsScrollEdge": ("b", True), "scrollFactor": ("d", 1.0), "pointerAcceleration": ("d", 0.2),
            "pointerAccelerationProfileFlat": ("b", False), "supportsPointerAcceleration": ("b", True),
            "naturalScroll": ("b", False), "supportsNaturalScroll": ("b", True),
            "disableWhileTyping": ("b", True), "supportsDisableWhileTyping": ("b", True)}


def fake_ask(argv):
    text = " ".join(str(a) for a in argv)
    reply = None
    if "devicesSysNames" in text:
        reply = {"type": "as", "data": ["event2", "event6"]}
    elif text.endswith("event2 org.kde.KWin.InputDevice touchpad"):
        reply = {"type": "b", "data": False}
    elif text.endswith("event6 org.kde.KWin.InputDevice touchpad"):
        reply = {"type": "b", "data": True}
    elif "event6 org.freedesktop.DBus.Properties GetAll" in text:
        reply = {"type": "a{sv}", "data": [{k: {"type": t, "data": v} for k, (t, v) in TOUCHPAD.items()}]}
    elif text.endswith("VirtualDesktopManager desktops"):
        reply = {"type": "a(iss)", "data": [[0, "desk-1", "Desktop 1"]]}
    elif text.endswith("VirtualDesktopManager rows"):
        reply = {"type": "u", "data": 1}
    elif "/component/kwin " in text and "allShortcutInfos" in text:
        reply = {"type": "a(ssssssaiai)", "data": [[
            ["Overview", "Toggle Overview", "kwin", "KWin", "default", "Default Context", [268435543], [268435543]],
            [dockpage.ids.LAUNCHPAD_SHORTCUT if hasattr(dockpage.ids, "LAUNCHPAD_SHORTCUT") else "Borealis Dock: Launchpad",
             "Launchpad", "kwin", "KWin", "default", "Default Context", LAUNCHPAD_KEYS, LAUNCHPAD_KEYS]]]}
    return json.dumps(reply) if reply is not None else ""


ps.run, ps.run_detached, ps.ask = fake_run, fake_detached, fake_ask

from desktoppage import DesktopBackend  # noqa: E402
from inputpage import InputBackend, LAUNCHPAD  # noqa: E402
from textpage import TextBackend  # noqa: E402
from windowspage import WindowsBackend  # noqa: E402


def conf(file, group, key):
    return ps.Config().get(file, group, key)


def did(*prefix):
    """Whether a command starting with these words was sent (or began with them after busctl's options)."""
    return any(cmd[:len(prefix)] == list(prefix) for cmd in sent)


def apply(page, **changes):
    for key, value in changes.items():
        page.set(key, value)
    page._apply_pending()


backend = tweaks_backend.Backend(app)

# --------------------------------------------------------------- windows ---
w = WindowsBackend(backend, app)
v = w.values
check("the title bar is read from the theme's defaults",
      v["buttonsSide"] == "right" and v["minimize"] and v["maximize"] and v["close"] and v["appIcon"]
      and not v["keepAbove"], str(v))
check("the Borealis decoration and its corners are found", v["decoration"] == "Borealis-Dark"
      and v["cornerRadius"] == 8, f"{v['decoration']!r} {v['cornerRadius']}")
apply(w, buttonsSide="left", keepAbove=True)
check("buttons move left with close first", conf("kwinrc", "org.kde.kdecoration2", "ButtonsOnLeft") == "XIAF"
      and conf("kwinrc", "org.kde.kdecoration2", "ButtonsOnRight") == "M")
check("KWin is told to reload", did("dbus-send", "--session", "--type=signal", "/KWin", "org.kde.KWin.reloadConfig"))
check("the page reads its change back", w.values["buttonsSide"] == "left" and w.values["keepAbove"] is True)
apply(w, blurStrength=6.6, animationSpeed=5)
check("blur strength is written and the blur effect reconfigured",
      conf("kwinrc", "Effect-blur", "BlurStrength") == "7"
      and did("busctl", "--user", "call", "org.kde.KWin", "/Effects", "org.kde.kwin.Effects", "reconfigureEffect", "s", "blur"))
check("animation speed is written and announced", conf("kdeglobals", "KDE", "AnimationDurationFactor") == "0.5"
      and did("dbus-send", "--session", "--type=signal", "/KGlobalSettings", "org.kde.KGlobalSettings.notifyChange",
              "int32:3", "int32:7"))
w.resetTitleBar()
check("resetting the title bar goes back to the theme's", w.values["buttonsSide"] == "right"
      and conf("kwinrc", "org.kde.kdecoration2", "ButtonsOnLeft") == "M")
user_kwinrc = os.path.join(os.environ["XDG_CONFIG_HOME"], "kwinrc")
check("a reset takes the key out instead of hiding the defaults",
      "[$d]" not in ps.read_text(user_kwinrc) and "ButtonsOn" not in ps.read_text(user_kwinrc))
check("the change is announced to programs watching kwinrc",
      did("busctl", "--user", "emit", "/kwinrc", "org.kde.kconfig.notify", "ConfigChanged", "a{saay}", "1",
          "org.kde.kdecoration2", "1", "13"))
with open(user_kwinrc, "a") as f:
    f.write("\n[org.kde.kdecoration2]\nButtonsOnRight[$d]\n")
check("a key[$d] left by other tools reads as unset, defaults and all",
      ps.Config().get("kwinrc", "org.kde.kdecoration2", "ButtonsOnRight", "none") == "none")
ps.kdelete("kwinrc", "org.kde.kdecoration2", "ButtonsOnRight")
check("and a reset clears it", "[$d]" not in ps.read_text(user_kwinrc)
      and conf("kwinrc", "org.kde.kdecoration2", "ButtonsOnRight") == "IAX")
check("the corner rebuild keeps a remix's colours", backend.build_flags() == [])

# ------------------------------------------------------------------ text ---
sent.clear()
t = TextBackend(backend, app)
apply(t, font={"family": "DejaVu Sans", "size": 11})
check("a font change is written as Qt's font string",
      (conf("kdeglobals", "General", "font") or "").startswith("DejaVu Sans,11"), conf("kdeglobals", "General", "font"))
check("apps are told to refresh their fonts",
      did("dbus-send", "--session", "--type=signal", "/KDEPlatformTheme", "org.kde.KDEPlatformTheme.refreshFonts"))
apply(t, hinting="full", subpixel="rgb")
fonts = open(os.path.join(os.environ["XDG_CONFIG_HOME"], "fontconfig", "fonts.conf")).read()
check("fonts.conf gets the new hinting and sub-pixel order",
      "<const>hintfull</const>" in fonts and "<const>rgb</const>" in fonts and "<const>lcddefault</const>" in fonts)
check("the rest of fonts.conf survives", "embolden" in fonts and "synthetic emboldening" in fonts
      and fonts.count('name="hintstyle"') == 1)
check("fonts.conf is backed up first",
      bool(glob.glob(os.path.join(os.environ["XDG_STATE_HOME"], "borealis-backup", "*-fonts", "fonts.conf"))))
check("Plasma's own copy of the rendering settings follows",
      conf("kdeglobals", "General", "XftHintStyle") == "hintfull" and conf("kdeglobals", "General", "XftSubPixel") == "rgb")
apply(t, cursorSize=36)
check("the pointer size is applied with the theme's tool",
      conf("kcminputrc", "Mouse", "cursorSize") == "36"
      and did("plasma-apply-cursortheme", "Borealis-Snow-Cursors", "--size", "36"))
apply(t, toolbarIcons=32)
check("toolbar icon size is written and announced", conf("kdeglobals", "ToolbarIcons", "Size") == "32"
      and did("dbus-send", "--session", "--type=signal", "/KIconLoader", "org.kde.KIconLoader.iconChanged", "int32:1"))
t.resetFonts()
check("resetting fonts removes them from your file", conf("kdeglobals", "General", "font") is None)

# --------------------------------------------------------------- touchpad ---
sent.clear()
i = InputBackend(backend, app)
v = i.values
check("the touchpad is found and read", v["touchpad"] == "Test Touchpad" and v["tapToClick"] is True
      and v["rightClick"] == "corner" and v["scrollSpeed"] == 4 and v["pointerSpeed"] == 20, str(v)[:300])
apply(i, tapToClick=False, rightClick="twoFingers", scrollSpeed=7)
device = ["busctl", "--user", "set-property", "org.kde.KWin", "/org/kde/KWin/InputDevice/event6", "org.kde.KWin.InputDevice"]
check("tap to click goes to KWin", did(*device, "tapToClick", "b", "false"))
check("right-click by two fingers switches both click methods",
      did(*device, "clickMethodAreas", "b", "false") and did(*device, "clickMethodClickfinger", "b", "true"))
check("scroll speed goes to KWin as a factor", did(*device, "scrollFactor", "d", "3"))
set_keys = ["busctl", "--user", "call", "org.kde.kglobalaccel", "/kglobalaccel", "org.kde.KGlobalAccel",
            "setForeignShortcutKeys", "asa(ai)", "4", "kwin"]
apply(i, launchpadMeta=False)
check("a lone Meta can be taken from Launchpad", did(*set_keys, LAUNCHPAD, "KWin", "Launchpad", "2",
                                                     "1", str(LAUNCHPAD_KEYS[0]), "1", str(LAUNCHPAD_KEYS[1])))
i.setShortcut("kwin\tOverview", QKeySequence("Meta+O"))
check("a shortcut gets its new key", did(*set_keys, "Overview", "KWin", "Toggle Overview", "1", "1", str(0x10000000 | 0x4F)))

# --------------------------------------------------------------- desktop ---
sent.clear()
d = DesktopBackend(backend, app)
v = d.values
check("desktops, corners and night light are read", v["desktopCount"] == 1 and v["topLeft"] == "overview"
      and v["topRight"] == "none" and v["nightLight"] == "off" and v["singleClick"] is False, str(v)[:300])
apply(d, desktopCount=3)
vdm = ["busctl", "--user", "call", "org.kde.KWin", "/VirtualDesktopManager", "org.kde.KWin.VirtualDesktopManager"]
check("two desktops are added", did(*vdm, "createDesktop", "us", "1", "Desktop 2")
      and did(*vdm, "createDesktop", "us", "2", "Desktop 3"))
apply(d, topRight="grid", topLeft="lock")
check("a corner can open the grid instead", conf("kwinrc", "Effect-overview", "GridBorderActivate") == "1"
      and conf("kwinrc", "Effect-overview", "BorderActivate") == "")
check("a corner can lock the screen", conf("kwinrc", "ElectricBorders", "TopLeft") == "LockScreen")
check("the effects are reconfigured", did("busctl", "--user", "call", "org.kde.KWin", "/Effects",
                                          "org.kde.kwin.Effects", "reconfigureEffect", "s", "overview"))
check("the corners read back", d.values["topLeft"] == "lock" and d.values["topRight"] == "grid")
apply(d, nightLight="always", nightTemperature=3350)
check("night light always on, warmer", conf("kwinrc", "NightColor", "Active") == "true"
      and conf("kwinrc", "NightColor", "Mode") == "Constant" and conf("kwinrc", "NightColor", "NightTemperature") == "3400")
apply(d, nightLight="sunset", nightSchedule="times", sunset="19:30")
check("night light at set times", conf("knighttimerc", "General", "Source") == "Times"
      and conf("knighttimerc", "Times", "SunsetStart") == "19:30" and conf("knighttimerc", "Times", "SunriseStart") == "06:00")
apply(d, singleClick=True)
check("a single click opens files", conf("kdeglobals", "KDE", "SingleClick") == "true"
      and did("dbus-send", "--session", "--type=signal", "/KGlobalSettings", "org.kde.KGlobalSettings.notifyChange",
              "int32:3", "int32:0"))
d.resetCorners()
check("resetting the corners goes back to KWin's", d.values["topLeft"] == "overview" and d.values["topRight"] == "none")

del w, t, i, d
shutil.rmtree(home, ignore_errors=True)
print("all good" if not failures else f"{failures} failed")
sys.exit(1 if failures else 0)
