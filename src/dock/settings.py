"""Dock settings: one JSON file, watched, so Borealis Tweaks (or a text editor)
changes the dock while it runs."""
import os

import ids
import settingsfile

SCHEMA = 1
DEFAULTS = {
    "schema": SCHEMA,
    "pinned": ["org.kde.dolphin", "preferred://browser", "org.kde.konsole",
               "org.kde.kwrite", "org.kde.discover", "systemsettings"],
    "position": "bottom",        # bottom | left | right
    "screen": "primary",         # primary | all | follow (the screen with the pointer)
    "iconSize": 48,
    "zoom": 1.7,                 # 1 turns magnification off
    "zoomLast": 1.7,             # what "Turn Magnification On" goes back to
    "reach": 3.0,                # how many icons either side the swell reaches
    "spacing": 6,
    "padding": 8,
    "margin": 8,                 # gap between the shelf and the screen edge
    "radius": 18,
    "opacity": 0.72,
    "blur": True,
    "border": True,
    "hide": "dodge",             # always | dodge | auto
    "hideDelay": 400,
    "indicator": "dot",          # dot | line | none
    "labels": True,
    "bounce": True,
    "divider": True,
    "showTrash": True,
    "animation": 1.0,            # speed factor; 0 = no animation
    "clickAction": "expose",     # the front app, clicked: expose (its windows) | cycle | minimize
    "badges": True,              # counts and progress apps publish for their icon
    "shortcuts": True,           # Meta+1…9 open the dock's first nine apps
    "previews": True,            # live window previews when the pointer rests on an open app
    "previewDelay": 450,         # ms before they show
    "launchpad": True,           # the Launchpad icon at the start of the dock
    # small live tiles before the Stacks: clock, battery, now playing
    "widgets": [{"type": "media"}],
    # folders shown as Stacks, before the trash
    "stacks": [{"path": "xdg:download", "view": "auto", "sort": "added", "display": "stack"}],
}
STACK_CHOICES = {"view": ("auto", "fan", "grid"), "sort": ("added", "modified", "name"),
                 "display": ("stack", "folder")}
# each widget's own options; the first choice is its default
WIDGET_CHOICES = {"clock": {"style": ("analog", "digital")}, "battery": {}, "media": {}}
RANGES = {
    "iconSize": (16, 256), "zoom": (1.0, 3.0), "zoomLast": (1.05, 3.0), "reach": (1.0, 8.0),
    "spacing": (0, 48), "padding": (4, 32), "margin": (0, 64), "radius": (0, 64),
    "opacity": (0.0, 1.0), "hideDelay": (0, 5000), "animation": (0.0, 3.0),
    "previewDelay": (0, 3000),
}
CHOICES = {
    "position": ("bottom", "left", "right"), "screen": ("primary", "all", "follow"),
    "hide": ("always", "dodge", "auto"), "indicator": ("dot", "line", "none"),
    "clickAction": ("expose", "cycle", "minimize"),
}

read_text = settingsfile.read_text
write_values = settingsfile.write_values


def config_path():
    return os.path.join(settingsfile.config_home(), ids.SLUG, "dock.json")


def load_values(path=None):
    """The settings as the dock would see them, without watching anything."""
    return settingsfile.load_values(path or config_path(), sanitize)


def sanitize(data):
    """Defaults for anything missing or out of range; unknown keys survive, so
    a newer dock's settings aren't lost by an older one."""
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
    stacks, seen = [], set()
    for stack in out["stacks"] if isinstance(out["stacks"], list) else DEFAULTS["stacks"]:
        if not isinstance(stack, dict) or not isinstance(stack.get("path"), str) or not stack["path"]:
            continue
        if stack["path"] in seen:
            continue
        seen.add(stack["path"])
        clean = {"path": stack["path"]}
        for key, allowed in STACK_CHOICES.items():
            clean[key] = stack.get(key) if stack.get(key) in allowed else allowed[0]
        stacks.append(clean)
    out["stacks"] = stacks
    widgets, seen = [], set()
    for widget in out["widgets"] if isinstance(out["widgets"], list) else DEFAULTS["widgets"]:
        kind = widget.get("type") if isinstance(widget, dict) else None
        if kind not in WIDGET_CHOICES or kind in seen:
            continue
        seen.add(kind)
        clean = {"type": kind}
        for key, allowed in WIDGET_CHOICES[kind].items():
            clean[key] = widget.get(key) if widget.get(key) in allowed else allowed[0]
        widgets.append(clean)
    out["widgets"] = widgets
    pinned = out["pinned"] if isinstance(out["pinned"], list) else DEFAULTS["pinned"]
    out["pinned"] = [p for p in pinned if isinstance(p, str) and p]
    out["schema"] = SCHEMA
    return out


class Settings(settingsfile.SettingsFile):
    def __init__(self, path=None, parent=None):
        super().__init__(path or config_path(), sanitize, parent)

    def get(self, key):
        return self._values.get(key, DEFAULTS.get(key))
