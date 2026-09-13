"""Dock presets: a whole look in one go, and files to share it.

A preset holds the look and behaviour settings. What's in your dock (pinned
apps, Stacks, widgets) and what belongs to this machine stays yours, unless a
preset file carries its contents and you ask for them too. The built-in presets
ship with the dock; saved and imported ones live beside the settings file, one
JSON file each.
"""
import json
import os
import re

try:
    import docksettings as settings      # Borealis Tweaks' copy
except ImportError:
    import settings                      # the dock's own

import ids

FORMAT = f"{ids.SLUG}-dock-preset"
VERSION = 1
MAX_BYTES = 256 * 1024
# what's in your dock: shared only when asked for
CONTENTS = ("pinned", "stacks", "widgets")
# never part of a look: the contents, and what depends on this machine
PERSONAL = ("schema", "zoomLast", "screen", "shortcuts") + CONTENTS

BUILTIN = [
    {"id": "borealis", "name": ids.NAME,
     "description": "A frosted shelf, a gentle swell, names and dividers",
     "settings": {}},
    {"id": "macos", "name": "macOS",
     "description": "Big magnification, bouncing icons and a glassy shelf",
     "settings": {"iconSize": 54, "zoom": 2.2, "reach": 2.5, "spacing": 4, "padding": 6, "margin": 4,
                  "radius": 16, "opacity": 0.45, "border": True, "indicator": "dot", "labels": True,
                  "bounce": True, "divider": True, "hide": "always", "previews": False,
                  "launchpad": True}},
    {"id": "minimal", "name": "Minimal",
     "description": "Small and flat, no swell, out of the way until you need it",
     "settings": {"iconSize": 40, "zoom": 1.0, "spacing": 4, "padding": 6, "margin": 6, "radius": 12,
                  "opacity": 0.35, "border": False, "indicator": "line", "labels": False,
                  "bounce": False, "divider": False, "showTrash": False, "hide": "auto",
                  "hideDelay": 250, "launchpad": False}},
]
_USER_ID = re.compile(r"^user:([a-z0-9][a-z0-9-]{0,63})$")


def look_keys():
    return [k for k in settings.DEFAULTS if k not in PERSONAL]


def clean_look(values):
    """Only the look, every value valid; anything left out gets its default."""
    full = settings.sanitize({k: v for k, v in dict(values).items() if k not in PERSONAL})
    return {k: full[k] for k in look_keys()}


def clean_apps(apps):
    """A preset's contents: pinned apps, Stacks and widgets (each only if given)."""
    if not isinstance(apps, dict):
        return None
    given = [k for k in CONTENTS if k in apps]
    full = settings.sanitize({k: apps[k] for k in given})
    return {k: full[k] for k in given} or None


def presets_dir():
    return os.path.join(os.path.dirname(settings.config_path()), "dock-presets")


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", str(name).lower()).strip("-")[:48] or "preset"


def parse(text, fallback_name=""):
    """A preset file's text -> preset; ValueError says what's wrong with it."""
    if len(text) > MAX_BYTES:
        raise ValueError("too big to be a dock preset")
    try:
        data = json.loads(text)
    except ValueError:
        raise ValueError("not a JSON file") from None
    if not isinstance(data, dict) or not str(data.get("format", "")).endswith("-dock-preset"):
        raise ValueError("not a dock preset")
    if not isinstance(data.get("settings"), dict):
        raise ValueError("the preset has no settings in it")
    name = " ".join(str(data.get("name") or fallback_name or "Preset").split())[:60]
    return {"name": name, "description": " ".join(str(data.get("description") or "").split())[:200],
            "settings": clean_look(data["settings"]), "apps": clean_apps(data.get("apps"))}


def payload(name, values, with_apps=False, description=""):
    out = {"format": FORMAT, "version": VERSION, "name": name, "description": description,
           "settings": clean_look(values)}
    if with_apps:
        apps = clean_apps(values)
        out["apps"] = apps
    return out


def write(path, name, values, with_apps=False, description=""):
    path = os.path.abspath(os.path.expanduser(path))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(payload(name, values, with_apps, description), f, indent=2)
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
             "settings": clean_look(p["settings"]), "apps": None} for p in BUILTIN]


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
    """By id (macos, user:my-dock) or by name, case aside."""
    everything = all_presets()
    key = str(key)
    return (next((p for p in everything if p["id"] in (key, "user:" + key)), None)
            or next((p for p in everything if p["name"].casefold() == key.casefold()), None))


def apply(values, preset, with_apps=False):
    out = dict(values)
    out.update(preset["settings"])
    if with_apps and preset.get("apps"):
        out.update(preset["apps"])
    return settings.sanitize(out)


def matches(values, preset):
    for key in look_keys():
        a, b = values.get(key), preset["settings"].get(key)
        if isinstance(a, float) or isinstance(b, float):
            try:
                if abs(float(a) - float(b)) > 1e-6:
                    return False
            except (TypeError, ValueError):
                return False
        elif a != b:
            return False
    return True


def current_id(values):
    return next((p["id"] for p in all_presets() if matches(values, p)), "")


def save_user(name, values, with_apps=False):
    """Keeps the current look under a name (replacing one with the same name)."""
    base = slug(name)
    write(os.path.join(presets_dir(), base + ".json"), name, values, with_apps)
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
    base = slug(preset["name"])
    candidate, n = base, 1
    while os.path.exists(os.path.join(folder, candidate + ".json")):
        try:
            same = read(os.path.join(folder, candidate + ".json"))
        except ValueError:
            same = None
        if same and same["settings"] == preset["settings"] and same.get("apps") == preset.get("apps"):
            return "user:" + candidate              # already imported
        n += 1
        candidate = f"{base[:44]}-{n}"
    os.makedirs(folder, exist_ok=True)
    out = payload(preset["name"], {**preset["settings"], **(preset["apps"] or {})},
                  with_apps=bool(preset["apps"]), description=preset["description"])
    tmp = os.path.join(folder, candidate + ".json.tmp")
    with open(tmp, "w") as f:
        json.dump(out, f, indent=2)
        f.write("\n")
    os.replace(tmp, os.path.join(folder, candidate + ".json"))
    return "user:" + candidate
