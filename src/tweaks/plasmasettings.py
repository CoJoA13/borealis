"""Borealis Tweaks, what the Plasma pages share.

Plasma's settings are read the way Plasma reads them: your own file first,
then the Global Theme's defaults (~/.config/kdedefaults), then the system's.
Changes go through kwriteconfig6 --notify, and a D-Bus nudge gets the programs
that care to apply them at once, as Plasma's own settings pages do.

Every command that changes something goes through `run` (or `run_detached`),
and every one that only looks goes through `ask`, so a test can swap them out
and see what a page would have done without touching the session.
"""
import json
import os
import re
import shutil
import subprocess
import time

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

# KGlobalSettings' notifyChange(type, category): SettingsChanged, CursorChanged,
# and the categories used here
SETTINGS_CHANGED = 3
CURSOR_CHANGED = 5
SETTINGS_MOUSE = 0
SETTINGS_STYLE = 7


def config_home():
    return os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")


def state_home():
    return os.environ.get("XDG_STATE_HOME") or os.path.expanduser("~/.local/state")


def read_text(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def plain(value):
    """What QML hands over, as plain Python (a JavaScript array can arrive wrapped)."""
    if hasattr(value, "toVariant"):
        value = value.toVariant()
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    return value


# ------------------------------------------------------------- commands ---
def run(argv):
    """Changes something (a config write, a D-Bus call or signal), and waits for it."""
    try:
        subprocess.run(argv, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        pass


def run_detached(argv):
    """Changes something that takes a moment, without waiting."""
    try:
        subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    except OSError:
        pass


def ask(argv):
    """Only looks: what the command printed, or "" if it failed."""
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=4)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return r.stdout if r.returncode == 0 else ""


def ask_json(argv):
    try:
        return json.loads(ask(argv) or "null")
    except ValueError:
        return None


def _group_args(group):
    return [arg for name in group.split("/") for arg in ("--group", name)]


def text_of(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def kwrite(file, group, key, value):
    run(["kwriteconfig6", "--notify", "--file", file, *_group_args(group), "--key", key, text_of(value)])


def kdelete(file, group, key):
    """Takes a key out of your own file, so the Global Theme's default (or Plasma's
    own) applies again. Not kwriteconfig6 --delete: that writes key[$d], which
    hides the defaults as well."""
    path = os.path.join(config_home(), file)
    text = read_text(path)
    names = group.split("/")
    current, kept = None, []
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        if stripped.startswith("["):
            current = [n for n in re.findall(r"\[([^\]]*)\]", stripped) if not n.startswith("$")]
        elif current == names and stripped and stripped[0] not in "#;":
            head = stripped.split("=", 1)[0]
            if re.split(r"\[", head, maxsplit=1)[0].strip() == key \
                    and all(s.startswith("$") for s in re.findall(r"\[([^\]]*)\]", head)):
                continue                # the key itself, or its [$d] marker; translations stay
        kept.append(line)
    if len(kept) != len(text.splitlines()):
        with open(path + ".tmp", "w", encoding="utf-8") as f:
            f.write("".join(kept))
        os.replace(path + ".tmp", path)
    # tell the programs watching the file, as kwriteconfig6 --notify would
    data = key.encode()
    run(["busctl", "--user", "emit", "/" + re.sub(r"[^A-Za-z0-9_]", "_", file), "org.kde.kconfig.notify",
         "ConfigChanged", "a{saay}", "1", "\x1d".join(names), "1", str(len(data)), *[str(b) for b in data]])


def signal(path, interface, name, *args):
    """A D-Bus signal on the session bus; args the way dbus-send takes them ("int32:3")."""
    run(["dbus-send", "--session", "--type=signal", path, f"{interface}.{name}", *args])


def call(service, path, interface, method, signature="", *args):
    run(["busctl", "--user", "call", service, path, interface, method]
        + ([signature, *[text_of(a) for a in args]] if signature else []))


def set_property(service, path, interface, prop, signature, value):
    run(["busctl", "--user", "set-property", service, path, interface, prop, signature, text_of(value)])


def get_property(service, path, interface, prop):
    reply = ask_json(["busctl", "--user", "--json=short", "get-property", service, path, interface, prop])
    return reply.get("data") if isinstance(reply, dict) else None


def reload_kwin():
    signal("/KWin", "org.kde.KWin", "reloadConfig")


def reconfigure_effect(name):
    call("org.kde.KWin", "/Effects", "org.kde.kwin.Effects", "reconfigureEffect", "s", name)


def notify_settings(category, change=SETTINGS_CHANGED):
    signal("/KGlobalSettings", "org.kde.KGlobalSettings", "notifyChange", f"int32:{change}", f"int32:{category}")


_backed_up = set()


def backup(path, label):
    """A copy of a file this app is about to change (once a run), beside install.sh's backups."""
    if path in _backed_up or not os.path.exists(path):
        return
    folder = os.path.join(state_home(), "borealis-backup", time.strftime("%Y%m%d-%H%M%S") + "-" + label)
    os.makedirs(folder, exist_ok=True)
    shutil.copy2(path, folder)
    _backed_up.add(path)


# --------------------------------------------------------------- config ---
_UNESCAPE = {"s": " ", "t": "\t", "n": "\n", "r": "\r", "\\": "\\"}
DELETED = "\0deleted"    # a key[$d] line: gone, defaults and all


def parse(text):
    """{"Group" or "Outer/Inner": {key: value}} from a KConfig file; the last word wins."""
    groups, current = {}, None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line[0] in "#;":
            continue
        if line.startswith("["):
            names = [n for n in re.findall(r"\[([^\]]*)\]", line) if not n.startswith("$")]
            current = groups.setdefault("/".join(names), {})
            continue
        if current is None:
            continue
        if "=" not in line:
            marker = re.match(r"^(.+?)\[\$d\]$", line)
            if marker:
                current[marker.group(1).strip()] = DELETED
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        suffixes = re.findall(r"\[([^\]]*)\]", key)
        if any(not s.startswith("$") for s in suffixes):
            continue                    # a translation (Name[de]=…)
        key = re.sub(r"\[[^\]]*\]", "", key).strip()
        current[key] = re.sub(r"\\(.)", lambda m: _UNESCAPE.get(m.group(1), m.group(1)), value.strip())
    return groups


class Config:
    """Plasma's cascade: the first file with the key has the say."""

    def __init__(self):
        self._files = {}

    @staticmethod
    def paths(name):
        home = config_home()
        dirs = [home, os.path.join(home, "kdedefaults")]
        dirs += [d for d in (os.environ.get("XDG_CONFIG_DIRS") or "/etc/xdg").split(":") if d]
        return [os.path.join(d, name) for d in dirs]

    def _groups(self, path):
        try:
            stamp = os.stat(path).st_mtime_ns
        except OSError:
            return {}
        cached = self._files.get(path)
        if cached and cached[0] == stamp:
            return cached[1]
        groups = parse(read_text(path))
        self._files[path] = (stamp, groups)
        return groups

    def get(self, name, group, key, default=None):
        for path in self.paths(name):
            value = self._groups(path).get(group, {}).get(key)
            if value == DELETED:
                return default
            if value is not None:
                return value
        return default

    def own(self, name, group, key):
        """Whether your own file sets this (rather than a default)."""
        return self._groups(self.paths(name)[0]).get(group, {}).get(key) not in (None, DELETED)

    def get_bool(self, name, group, key, default=False):
        value = self.get(name, group, key)
        return default if value is None else value.strip().lower() in ("true", "1", "yes", "on")

    def get_int(self, name, group, key, default=0):
        try:
            return int(float(self.get(name, group, key, default)))
        except (TypeError, ValueError):
            return default

    def get_float(self, name, group, key, default=0.0):
        try:
            return float(self.get(name, group, key, default))
        except (TypeError, ValueError):
            return default

    def get_ints(self, name, group, key, default=()):
        value = self.get(name, group, key)
        if value is None:
            return list(default)
        return [int(v) for v in re.findall(r"-?\d+", value)]


# ----------------------------------------------------------------- page ---
class PlasmaPage(QObject):
    """One page's share of Plasma's settings: `values` for its controls, and
    `set(key, value)`, which applies a change after a short pause (so a slider
    being dragged doesn't write a hundred times)."""
    changed = Signal()

    def __init__(self, backend=None, parent=None):
        super().__init__(parent)
        self.backend = backend
        self.config = Config()
        self._values = {}
        self._pending = {}
        self._flush = QTimer(self, singleShot=True, interval=180)
        self._flush.timeout.connect(self._apply_pending)
        # some programs take a moment to act on a change: look again then
        self._reread = QTimer(self, singleShot=True, interval=700)
        self._reread.timeout.connect(self.refresh)

    @Property("QVariantMap", notify=changed)
    def values(self):
        return {**self._values, **self._pending}

    @Slot()
    def refresh(self):
        values = self.read()
        if values != self._values:
            self._values = values
            self.changed.emit()

    def read(self):
        return {}

    @Slot(str, "QVariant")
    def set(self, key, value):
        self._pending[key] = plain(value)
        self.changed.emit()
        self._flush.start()

    def _apply_pending(self):
        changes, self._pending = self._pending, {}
        if changes:
            self.apply_changes(changes, {**self._values, **changes})
            self._values = {**self._values, **changes}
            self.refresh()
            self._reread.start()

    def apply_changes(self, changes, merged):
        raise NotImplementedError


if __name__ == "__main__":
    # plasmasettings.py revert FILE GROUP KEY: for steps that run as commands
    import sys
    if len(sys.argv) == 5 and sys.argv[1] == "revert":
        kdelete(*sys.argv[2:])
    else:
        sys.exit("usage: plasmasettings.py revert FILE GROUP KEY")
