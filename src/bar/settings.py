"""Bar settings: one JSON file, watched, so Borealis Tweaks (or a text editor)
changes the bar while it runs."""
import os

import ids
import settingsfile

SCHEMA = 1
# what can sit in the bar, by name
ITEMS = ("menu", "app", "appmenu", "clock", "tray", "drives", "controls")
# the Control Center's round toggles, in the order its edit mode offers them
PILLS = ("wifi", "bluetooth", "night", "power", "dark", "dnd", "aurora", "awake",
         "airplane", "hotspot", "mic", "keyboard", "screenshot", "record")
# the Control Center's sliders, shown in this order
SLIDERS = ("brightness", "volume", "microphone", "keyboard")
# what the Control Center's button in the bar shows, in this order
GLYPHS = ("network", "bluetooth", "sound", "battery")
DEFAULTS = {
    "schema": SCHEMA,
    "screen": "all",             # all | primary
    "height": 30,                # the bar itself, without the gap around it
    "floating": True,
    "gap": 6,                    # around a floating bar
    "radius": 12,
    "opacity": 0.72,
    "blur": True,
    "border": True,
    "flush": True,               # a maximized window turns a floating bar flush and solid
    "left": ["menu", "app", "appmenu"],
    "center": ["clock"],
    "right": ["tray", "drives", "controls"],
    "clockDate": True,
    "clockWeekday": True,
    "clockSeconds": False,
    "clockHours": "auto",        # auto | 12 | 24
    "banners": True,             # notifications pop up under the bar
    "bannerPosition": "right",   # right | center
    "pills": ["wifi", "bluetooth", "night", "power", "dark", "dnd", "aurora", "awake"],
    "sliders": ["brightness", "volume"],
    "media": True,
    "glyphs": list(GLYPHS),
    "batteryPercent": True,      # the percentage beside the battery glyph
    "trayHidden": [],            # tray items (by their id) left out of the bar
}
# the Control Center's share of the file, which Tweaks resets on its own
CONTROLS = ("pills", "sliders", "media", "glyphs", "batteryPercent")
RANGES = {"height": (22, 48), "gap": (0, 24), "radius": (0, 24), "opacity": (0.0, 1.0)}
CHOICES = {"screen": ("all", "primary"), "clockHours": ("auto", "12", "24"),
           "bannerPosition": ("right", "center")}

read_text = settingsfile.read_text
write_values = settingsfile.write_values


def config_path():
    return os.path.join(settingsfile.config_home(), ids.SLUG, "bar.json")


def load_values(path=None):
    return settingsfile.load_values(path or config_path(), sanitize)


def sanitize(data):
    """Defaults for anything missing or out of range; unknown keys survive."""
    out = dict(DEFAULTS)
    if isinstance(data, dict):
        out.update(data)
    for key, (lo, hi) in RANGES.items():
        try:
            value = min(hi, max(lo, float(out[key])))
        except (TypeError, ValueError):
            value = float(DEFAULTS[key])
        out[key] = int(round(value)) if type(DEFAULTS[key]) is int else value
    for key, allowed in CHOICES.items():
        if out[key] not in allowed:
            out[key] = DEFAULTS[key]
    for key, default in DEFAULTS.items():
        if type(default) is bool:
            out[key] = bool(out[key])
    # each item sits in one zone at most, in the order given
    seen = set()
    for zone in ("left", "center", "right"):
        items = out[zone] if isinstance(out[zone], list) else DEFAULTS[zone]
        clean = []
        for item in items:
            if item in ITEMS and item not in seen:
                seen.add(item)
                clean.append(item)
        out[zone] = clean
    # toggles keep the order given; sliders and glyphs have their own
    pills = out["pills"] if isinstance(out["pills"], list) else DEFAULTS["pills"]
    out["pills"] = list(dict.fromkeys(p for p in pills if p in PILLS))
    for key, known in (("sliders", SLIDERS), ("glyphs", GLYPHS)):
        chosen = out[key] if isinstance(out[key], list) else DEFAULTS[key]
        out[key] = [name for name in known if name in chosen]
    hidden = out["trayHidden"] if isinstance(out["trayHidden"], list) else []
    out["trayHidden"] = [h for h in hidden if isinstance(h, str) and h]
    out["schema"] = SCHEMA
    return out


class Settings(settingsfile.SettingsFile):
    def __init__(self, path=None, parent=None):
        super().__init__(path or config_path(), sanitize, parent)

    def get(self, key):
        return self._values.get(key, DEFAULTS.get(key))
