"""A Borealis app's settings: one JSON file, watched, so Borealis Tweaks (or a
text editor) changes the app while it runs. Each app brings its own defaults
and `sanitize`; this keeps the file, the watching and the atomic writes."""
import json
import os

from PySide6.QtCore import Property, QFileSystemWatcher, QObject, QTimer, Signal, Slot


def config_home():
    return os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")


def read_text(path):
    try:
        with open(path) as f:
            return f.read()
    except OSError:
        return None


def load_values(path, sanitize):
    """The settings as the app would see them, without watching anything."""
    raw = read_text(path)
    try:
        return sanitize(json.loads(raw) if raw else {})
    except ValueError:
        return sanitize({})


def plain(value):
    """What QML hands over, as plain Python: a JavaScript array or object can
    arrive wrapped (a QJSValue) rather than as a list or dict."""
    if hasattr(value, "toVariant"):
        value = value.toVariant()
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    return value


def write_values(path, values):
    """Atomically, so a watcher never reads half a file; returns the text."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    text = json.dumps(values, indent=2) + "\n"
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        f.write(text)
    os.replace(tmp, path)
    return text


class SettingsFile(QObject):
    changed = Signal()

    def __init__(self, path, sanitize, parent=None):
        super().__init__(parent)
        self.path = path
        self._sanitize = sanitize
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
        raw = read_text(self.path)
        self._watch()
        if raw is not None and raw == self._raw:
            return
        self._raw = raw
        try:
            data = json.loads(raw) if raw else {}
        except ValueError:
            return          # caught mid-write: the next change event brings the whole file
        values = self._sanitize(data)
        if values != self._values:
            self._values = values
            self.changed.emit()

    def _save(self):
        self._raw = write_values(self.path, self._values)
        self._watch()

    @Property("QVariantMap", notify=changed)
    def values(self):
        return self._values

    def get(self, key):
        return self._values.get(key)

    @Slot(str, "QVariant")
    def set(self, key, value):
        self.update({key: value})

    @Slot("QVariantMap")
    def update(self, changes):
        values = self._sanitize({**self._values, **plain(dict(changes))})
        if values != self._values:
            self._values = values
            self._save()
            self.changed.emit()
