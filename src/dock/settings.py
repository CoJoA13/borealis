"""Dock settings: one JSON file, watched, so Borealis Tweaks (or a text editor)
changes the dock while it runs."""
import json
import os

from PySide6.QtCore import Property, QFileSystemWatcher, QObject, QTimer, Signal, Slot

import ids

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
    # folders shown as Stacks, before the trash
    "stacks": [{"path": "xdg:download", "view": "auto", "sort": "added", "display": "stack"}],
}
STACK_CHOICES = {"view": ("auto", "fan", "grid"), "sort": ("added", "modified", "name"),
                 "display": ("stack", "folder")}
RANGES = {
    "iconSize": (16, 256), "zoom": (1.0, 3.0), "zoomLast": (1.05, 3.0), "reach": (1.0, 8.0),
    "spacing": (0, 48), "padding": (4, 32), "margin": (0, 64), "radius": (0, 64),
    "opacity": (0.0, 1.0), "hideDelay": (0, 5000), "animation": (0.0, 3.0),
}
CHOICES = {
    "position": ("bottom", "left", "right"), "screen": ("primary", "all", "follow"),
    "hide": ("always", "dodge", "auto"), "indicator": ("dot", "line", "none"),
    "clickAction": ("expose", "cycle", "minimize"),
}


def config_path():
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, ids.SLUG, "dock.json")


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
    pinned = out["pinned"] if isinstance(out["pinned"], list) else DEFAULTS["pinned"]
    out["pinned"] = [p for p in pinned if isinstance(p, str) and p]
    out["schema"] = SCHEMA
    return out


class Settings(QObject):
    changed = Signal()

    def __init__(self, path=None, parent=None):
        super().__init__(parent)
        self.path = path or config_path()
        self._values = sanitize({})
        self._raw = None
        self._watcher = QFileSystemWatcher(self)
        self._reload = QTimer(self, singleShot=True, interval=150)
        self._reload.timeout.connect(self.load)
        self._watcher.fileChanged.connect(lambda *_: self._reload.start())
        self._watcher.directoryChanged.connect(lambda *_: self._reload.start())
        self.load()

    def _watch(self):
        # the nearest folder that exists: a settings folder created later (by
        # Tweaks, or by hand) still announces itself through its parent
        folder = os.path.dirname(self.path)
        while folder and not os.path.isdir(folder) and os.path.dirname(folder) != folder:
            folder = os.path.dirname(folder)
        if folder and folder not in self._watcher.directories():
            self._watcher.addPath(folder)
        if os.path.exists(self.path) and self.path not in self._watcher.files():
            self._watcher.addPath(self.path)

    @Slot()
    def load(self):
        try:
            with open(self.path) as f:
                raw = f.read()
        except OSError:
            raw = None
        self._watch()
        if raw is not None and raw == self._raw:
            return
        self._raw = raw
        try:
            data = json.loads(raw) if raw else {}
        except ValueError:
            return          # caught mid-write: the next change event brings the whole file
        values = sanitize(data)
        if values != self._values:
            self._values = values
            self.changed.emit()

    def _save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        text = json.dumps(self._values, indent=2) + "\n"
        tmp = self.path + ".tmp"
        with open(tmp, "w") as f:
            f.write(text)
        os.replace(tmp, self.path)
        self._raw = text
        self._watch()

    @Property("QVariantMap", notify=changed)
    def values(self):
        return self._values

    def get(self, key):
        return self._values.get(key, DEFAULTS.get(key))

    @Slot(str, "QVariant")
    def set(self, key, value):
        self.update({key: value})

    @Slot("QVariantMap")
    def update(self, changes):
        values = sanitize({**self._values, **dict(changes)})
        if values != self._values:
            self._values = values
            self._save()
            self.changed.emit()
