"""Desktop presets: the whole Borealis desktop in one go, and files to share it.

A preset has a section for each part of the desktop it sets:

    theme      Dark, Light or day and night, the palette (accent and name), the animated aurora
    dock       the dock's look and behaviour; dockApps holds its apps, Stacks and widgets
    bar        the bar's look and what sits where
    controls   the Control Center's toggles, sliders and glyphs
    windows    the title bar's buttons, window corners, blur and animation speed
    desktop    hot corners, screen edges, and opening files with one click or two

A section a preset leaves out stays as it is. Within a section, what a preset
doesn't say gets the Borealis default, except in `theme`, where only what's
given changes. What's personal is never part of a preset: fonts, the pointer,
the touchpad, shortcuts, night light, virtual desktops, which screens the bar
and the dock use, and the tray. The built-in presets ship with Borealis Tweaks;
saved and imported ones live in ~/.config/borealis/desktop-presets, one JSON
file each.
"""
import json
import os
import re

from barpage import barsettings
from desktoppage import ACTIONS, EFFECTS
from dockpage import dockpresets, ids
from windowspage import BLUR_STRENGTH, NOISE_STRENGTH, SPEEDS

FORMAT = f"{ids.SLUG}-desktop-preset"
VERSION = 1
MAX_BYTES = 512 * 1024
SECTIONS = ("theme", "dock", "bar", "controls", "windows", "desktop")
VARIANTS = ("dark", "light", "auto")
# the bar's settings about this machine, or the Control Center's, rather than its look
BAR_PERSONAL = ("schema", "screen", "trayHidden") + tuple(barsettings.CONTROLS)
WINDOWS_DEFAULTS = {"buttonsSide": "right", "appIcon": True, "minimize": True, "maximize": True, "close": True,
                    "keepAbove": False, "allDesktops": False, "blurStrength": BLUR_STRENGTH,
                    "noiseStrength": NOISE_STRENGTH, "animationSpeed": SPEEDS.index(1), "cornerRadius": 12}
DESKTOP_DEFAULTS = {"topLeft": "overview", "topRight": "none", "bottomLeft": "none", "bottomRight": "none",
                    "edgeSwitch": 0, "singleClick": False}
CORNER_CHOICES = ("none",) + tuple(EFFECTS) + tuple(ACTIONS)
RANGES = {"blurStrength": (1, 15), "noiseStrength": (0, 14), "animationSpeed": (0, len(SPEEDS) - 1),
          "cornerRadius": (0, 24), "edgeSwitch": (0, 2)}
CHOICES = {"buttonsSide": ("right", "left"), "topLeft": CORNER_CHOICES, "topRight": CORNER_CHOICES,
           "bottomLeft": CORNER_CHOICES, "bottomRight": CORNER_CHOICES}
ACCENT = re.compile(r"^#[0-9a-fA-F]{6}$")
_USER_ID = re.compile(r"^user:([a-z0-9][a-z0-9-]{0,63})$")


def _dock_look(preset_id):
    return next(p["settings"] for p in dockpresets.BUILTIN if p["id"] == preset_id)


BUILTIN = [
    {"id": "borealis", "name": ids.NAME,
     "description": "A floating frosted bar, a gently swelling dock, buttons at the right",
     "sections": {"dock": {}, "bar": {}, "controls": {}, "windows": {}, "desktop": {}}},
    {"id": "maclike", "name": "Mac-like",
     "description": "A flush menu bar, a big magnifying dock, close at the left",
     "sections": {
         "dock": _dock_look("macos"),
         "bar": {"floating": False, "height": 28, "opacity": 0.6, "border": False,
                 "left": ["menu", "app", "appmenu"], "center": [], "right": ["tray", "drives", "controls", "clock"]},
         "controls": {"pills": ["wifi", "bluetooth", "dnd", "dark", "night", "awake"], "batteryPercent": False},
         "windows": {"buttonsSide": "left", "appIcon": False},
         "desktop": {"topLeft": "none"}}},
    {"id": "minimal", "name": "Minimal",
     "description": "A slim bar, a dock that hides, one close button, quick animations",
     "sections": {
         "dock": _dock_look("minimal"),
         "bar": {"height": 26, "gap": 4, "radius": 10, "opacity": 0.55, "border": False,
                 "left": ["menu", "appmenu"], "center": ["clock"], "right": ["tray", "drives", "controls"],
                 "clockDate": False, "clockWeekday": False},
         "controls": {"pills": ["wifi", "bluetooth", "dnd", "dark"], "sliders": ["volume"], "media": False,
                      "glyphs": ["network", "battery"], "batteryPercent": False},
         "windows": {"appIcon": False, "minimize": False, "maximize": False, "animationSpeed": SPEEDS.index(0.5)},
         "desktop": {}}},
]


# -------------------------------------------------------------- cleaning ---
def _number(value, lo, hi, default):
    if isinstance(value, bool):
        return default
    try:
        return max(lo, min(hi, int(round(float(value)))))
    except (TypeError, ValueError):
        return default


def _plain_section(data, defaults):
    data = data if isinstance(data, dict) else {}
    out = {}
    for key, default in defaults.items():
        value = data.get(key, default)
        if isinstance(default, bool):
            out[key] = value if isinstance(value, bool) else default
        elif key in RANGES:
            out[key] = _number(value, *RANGES[key], default)
        else:
            out[key] = value if value in CHOICES.get(key, ()) else default
    return out


def palette_name(name):
    """A palette's name, safe to build packages from: letters, digits and
    spaces, and starting with Borealis, so a shared file can't make a theme
    that stands in for another one."""
    text = " ".join(re.sub(r"[^A-Za-z0-9 ]+", " ", str(name or "")).split())
    if not text.startswith(ids.NAME):
        text = f"{ids.NAME} {text}".strip()
    return text[:40].strip()


def clean_theme(data):
    data = data if isinstance(data, dict) else {}
    out = {}
    if data.get("variant") in VARIANTS:
        out["variant"] = data["variant"]
    if isinstance(data.get("accent"), str) and ACCENT.match(data["accent"]):
        out["accent"] = data["accent"].lower()
        out["name"] = palette_name(data.get("name"))
    if isinstance(data.get("liveWallpaper"), bool):
        out["liveWallpaper"] = data["liveWallpaper"]
    return out


def bar_look(values):
    values = values if isinstance(values, dict) else {}
    full = barsettings.sanitize({k: v for k, v in values.items() if k not in BAR_PERSONAL})
    return {k: full[k] for k in barsettings.DEFAULTS if k not in BAR_PERSONAL}


def bar_controls(values):
    values = values if isinstance(values, dict) else {}
    full = barsettings.sanitize({k: v for k, v in values.items() if k in barsettings.CONTROLS})
    return {k: full[k] for k in barsettings.CONTROLS}


def clean_section(section, data):
    """One section, every value valid (the theme: only what's valid of what's given)."""
    if section == "theme":
        return clean_theme(data)
    if section == "dock":
        return dockpresets.clean_look(data if isinstance(data, dict) else {})
    if section == "bar":
        return bar_look(data)
    if section == "controls":
        return bar_controls(data)
    if section == "windows":
        return _plain_section(data, WINDOWS_DEFAULTS)
    if section == "desktop":
        return _plain_section(data, DESKTOP_DEFAULTS)
    raise KeyError(section)


# ----------------------------------------------------------------- files ---
def presets_dir():
    return os.path.join(os.path.dirname(dockpresets.presets_dir()), "desktop-presets")


def parse(text, fallback_name=""):
    """A preset file's text -> preset; ValueError says what's wrong with it."""
    if len(text) > MAX_BYTES:
        raise ValueError("too big to be a desktop preset")
    try:
        data = json.loads(text)
    except ValueError:
        raise ValueError("not a JSON file") from None
    if not isinstance(data, dict) or not str(data.get("format", "")).endswith("-desktop-preset"):
        raise ValueError("not a desktop preset")
    sections = {}
    for section in SECTIONS:
        if isinstance(data.get(section), dict):
            cleaned = clean_section(section, data[section])
            if cleaned:
                sections[section] = cleaned
    apps = dockpresets.clean_apps(data.get("dockApps"))
    if not sections and not apps:
        raise ValueError("the preset doesn't set anything")
    name = " ".join(str(data.get("name") or fallback_name or "Preset").split())[:60]
    return {"name": name, "description": " ".join(str(data.get("description") or "").split())[:200],
            "sections": sections, "dockApps": apps}


def payload(name, sections, apps=None, description=""):
    out = {"format": FORMAT, "version": VERSION, "name": name, "description": description}
    for section in SECTIONS:
        if section in sections:
            cleaned = clean_section(section, sections[section])
            if cleaned:
                out[section] = cleaned
    apps = dockpresets.clean_apps(apps) if apps else None
    if apps:
        out["dockApps"] = apps
    return out


def write(path, name, sections, apps=None, description=""):
    path = os.path.abspath(os.path.expanduser(path))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(payload(name, sections, apps, description), f, indent=2)
        f.write("\n")
    os.replace(tmp, path)
    return path


def read(path):
    try:
        with open(os.path.expanduser(path), encoding="utf-8", errors="replace") as f:
            text = f.read(MAX_BYTES + 1)
    except OSError as e:
        raise ValueError(e.strerror or str(e)) from None
    return parse(text, os.path.splitext(os.path.basename(path))[0])


def builtin_presets():
    return [{"id": p["id"], "name": p["name"], "description": p["description"], "builtin": True,
             "sections": {s: clean_section(s, v) for s, v in p["sections"].items()}, "dockApps": None}
            for p in BUILTIN]


def user_presets():
    folder = presets_dir()
    try:
        names = sorted(os.listdir(folder))
    except OSError:
        return []
    out = []
    for fn in names:
        if not fn.endswith(".json") or not _USER_ID.match("user:" + fn[:-5]):
            continue
        try:
            preset = read(os.path.join(folder, fn))
        except ValueError:
            continue
        out.append({"id": "user:" + fn[:-5], "builtin": False, **preset})
    return sorted(out, key=lambda p: p["name"].casefold())


def all_presets():
    return builtin_presets() + user_presets()


def find(key):
    """By id (maclike, user:my-desktop) or by name, case aside."""
    everything = all_presets()
    key = str(key)
    return (next((p for p in everything if p["id"] in (key, "user:" + key)), None)
            or next((p for p in everything if p["name"].casefold() == key.casefold()), None))


def save_user(name, sections, apps=None):
    """Keeps a desktop under a name (replacing one with the same name)."""
    base = dockpresets.slug(name)
    write(os.path.join(presets_dir(), base + ".json"), name, sections, apps)
    return "user:" + base


def delete_user(preset_id):
    m = _USER_ID.match(str(preset_id))
    path = os.path.join(presets_dir(), m.group(1) + ".json") if m else ""
    if path and os.path.isfile(path):
        os.remove(path)
        return True
    return False


def import_file(path):
    """A shared preset file becomes one of yours; returns its id."""
    preset = read(path)
    folder = presets_dir()
    base = dockpresets.slug(preset["name"])
    candidate, n = base, 1
    while os.path.exists(os.path.join(folder, candidate + ".json")):
        try:
            same = read(os.path.join(folder, candidate + ".json"))
        except ValueError:
            same = None
        if same and same["sections"] == preset["sections"] and same.get("dockApps") == preset.get("dockApps"):
            return "user:" + candidate              # already imported
        n += 1
        candidate = f"{base[:44]}-{n}"
    write(os.path.join(folder, candidate + ".json"), preset["name"], preset["sections"], preset["dockApps"],
          preset["description"])
    return "user:" + candidate


# ------------------------------------------------------------- comparing ---
def same(a, b):
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(float(a) - float(b)) < 1e-6
    if isinstance(a, str) and isinstance(b, str) and ACCENT.match(a) and ACCENT.match(b):
        return a.lower() == b.lower()
    return a == b


def section_matches(section, current, wanted):
    have = current.get(section) or {}
    for key, value in wanted.items():
        if key not in have:
            if section == "windows" and key == "cornerRadius":
                continue            # only the Borealis decoration has corners to compare
            return False
        if not same(have[key], value):
            return False
    return True


def matches(current, preset):
    """Whether the desktop is as the preset would leave it (its apps aside).
    `current` has a section for each part, as the Presets page reads them."""
    return all(section_matches(s, current, v) for s, v in preset["sections"].items())


def thumb(preset, current):
    """What a small drawing of the desktop needs, as the preset would leave it."""
    s = preset["sections"]
    theme = {**current.get("theme", {}), **s.get("theme", {})}
    dock = s.get("dock") or current.get("dock") or {}
    bar = s.get("bar") or current.get("bar") or {}
    windows = {**current.get("windows", {}), **s.get("windows", {})}
    return {"variant": theme.get("variant", "dark"), "accent": theme.get("accent", "#8b9cff"),
            "barFloating": bool(bar.get("floating", True)), "barOpacity": float(bar.get("opacity", 0.72)),
            "clock": next((zone for zone in ("left", "center", "right") if "clock" in bar.get(zone, [])), ""),
            "dockSize": int(dock.get("iconSize", 48)), "dockZoom": float(dock.get("zoom", 1.7)),
            "dockPosition": dock.get("position", "bottom"), "dockHidden": dock.get("hide") == "auto",
            "buttonsLeft": windows.get("buttonsSide") == "left",
            "buttons": [b for b in ("minimize", "maximize", "close") if windows.get(b, True)]}
