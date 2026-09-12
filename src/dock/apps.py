"""Desktop entries: names, icons, jump lists, launching, and which app a window
belongs to (KWin reports app ids and window classes, not desktop entries)."""
import configparser
import os
import shlex
import subprocess
import uuid
from urllib.parse import unquote

from PySide6.QtCore import QFileSystemWatcher, QObject, QProcess, QTimer, QUrl, Signal

import ids

FALLBACK_ICON = "application-x-executable"
PREFERRED_MIME = {"browser": "x-scheme-handler/https", "mail": "x-scheme-handler/mailto",
                  "filemanager": "inode/directory"}


def application_dirs():
    home = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    rest = os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share"
    out = []
    for base in [home] + rest.split(":"):
        path = os.path.join(base, "applications")
        if base and path not in out:
            out.append(path)
    return out


def _languages():
    lang = os.environ.get("LC_ALL") or os.environ.get("LC_MESSAGES") or os.environ.get("LANG") or ""
    lang = lang.split(".")[0].split("@")[0]
    if not lang or lang in ("C", "POSIX"):
        return []
    return [lang, lang.split("_")[0]] if "_" in lang else [lang]


LANGS = _languages()


def _localized(section, key):
    for lang in LANGS:
        value = section.get(f"{key}[{lang}]")
        if value:
            return value
    return section.get(key, "")


def _true(value):
    return str(value).strip().lower() == "true"


def exec_binary(line):
    try:
        words = shlex.split(line or "")
    except ValueError:
        return ""
    while words and (words[0] == "env" or ("=" in words[0] and not words[0].startswith("/"))):
        words.pop(0)
    return os.path.basename(words[0]) if words else ""


class Entry:
    __slots__ = ("id", "path", "name", "icon", "exec", "terminal", "wmclass", "actions", "listed")

    def __init__(self, **kw):
        for key in self.__slots__:
            setattr(self, key, kw.get(key))


def parse_entry(path, entry_id):
    parser = configparser.RawConfigParser(strict=False, interpolation=None, delimiters=("=",),
                                          comment_prefixes=("#",))
    parser.optionxform = str
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            parser.read_file(f)
    except configparser.MissingSectionHeaderError:
        return None
    except configparser.ParsingError:
        pass                            # keep what parsed before the odd line
    except (configparser.Error, OSError):
        return None
    if not parser.has_section("Desktop Entry"):
        return None
    main = parser["Desktop Entry"]
    if main.get("Type", "Application") != "Application":
        return None
    if _true(main.get("Hidden", "")):
        return False                    # deliberately removed: shadows other copies
    actions = []
    for action in filter(None, (a.strip() for a in main.get("Actions", "").split(";"))):
        section = f"Desktop Action {action}"
        if parser.has_section(section):
            sec = parser[section]
            name = _localized(sec, "Name")
            if name and sec.get("Exec"):
                actions.append({"id": action, "name": name, "icon": sec.get("Icon", ""),
                                "exec": sec.get("Exec")})
    only = [d for d in main.get("OnlyShowIn", "").split(";") if d]
    never = [d for d in main.get("NotShowIn", "").split(";") if d]
    return Entry(id=entry_id, path=path, name=_localized(main, "Name") or entry_id,
                 icon=main.get("Icon", ""), exec=main.get("Exec", ""),
                 terminal=_true(main.get("Terminal", "")),
                 wmclass=main.get("StartupWMClass", ""), actions=actions,
                 listed=not _true(main.get("NoDisplay", "")) and (not only or "KDE" in only)
                 and "KDE" not in never)


def find_entry_path(entry_id):
    """Without an index (and without Qt): where a desktop entry lives."""
    for folder in application_dirs():
        path = os.path.join(folder, entry_id + ".desktop")
        if os.path.exists(path):
            return path
    return ""


def expand_exec(line, urls, entry):
    """A desktop entry's Exec line as argv, field codes filled in."""
    try:
        words = shlex.split(line or "")
    except ValueError:
        return []
    urls = [str(u) for u in urls]
    files = [QUrl(u).toLocalFile() or u for u in urls]
    out = []
    for word in words:
        if word == "%f":
            out += files[:1]
        elif word == "%F":
            out += files
        elif word == "%u":
            out += urls[:1]
        elif word == "%U":
            out += urls
        elif word == "%i":
            out += ["--icon", entry.icon] if entry.icon else []
        elif word == "%c":
            out.append(entry.name)
        elif word == "%k":
            out.append(entry.path)
        elif word in ("%d", "%D", "%n", "%N", "%v", "%m"):
            continue
        else:
            for code in ("%f", "%F", "%u", "%U", "%i", "%c", "%k"):
                word = word.replace(code, "")
            out.append(word.replace("%%", "%"))
    return out


class AppIndex(QObject):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._preferred = {}
        self._watcher = QFileSystemWatcher(self)
        self._rescan = QTimer(self, singleShot=True, interval=1500)
        self._rescan.timeout.connect(self.scan)
        self._watcher.directoryChanged.connect(lambda *_: self._rescan.start())
        self.scan(emit=False)

    def scan(self, emit=True):
        found = {}
        for folder in application_dirs():
            if not os.path.isdir(folder):
                continue
            if folder not in self._watcher.directories():
                self._watcher.addPath(folder)
            for root, _dirs, files in os.walk(folder):
                for fn in files:
                    if not fn.endswith(".desktop"):
                        continue
                    path = os.path.join(root, fn)
                    entry_id = os.path.relpath(path, folder)[:-8].replace(os.sep, "-")
                    if entry_id not in found:           # earlier directories win
                        found[entry_id] = parse_entry(path, entry_id)
        self.by_id = {k: v for k, v in found.items() if v}
        self.by_lower = {k.lower(): v for k, v in self.by_id.items()}
        self.by_wmclass, tails, binaries = {}, {}, {}
        for e in self.by_id.values():
            if e.wmclass:
                self.by_wmclass.setdefault(e.wmclass.lower(), e)
            tails.setdefault(e.id.rsplit(".", 1)[-1].lower(), []).append(e)
            binary = exec_binary(e.exec)
            if binary:
                binaries.setdefault(binary.lower(), []).append(e)
        # only unambiguous guesses: two "calculator"s match neither
        self.by_tail = {k: v[0] for k, v in tails.items() if len(v) == 1}
        self.by_binary = {k: v[0] for k, v in binaries.items() if len(v) == 1}
        self._preferred.clear()
        if emit:
            self.changed.emit()

    def get(self, entry_id):
        return self.by_id.get(entry_id)

    def match(self, app_id="", wm_class="", res_name=""):
        """The desktop entry a window belongs to, or None."""
        for cand in (app_id, wm_class, res_name):
            if cand:
                c = cand[:-8] if cand.endswith(".desktop") else cand
                e = self.by_id.get(c) or self.by_lower.get(c.lower())
                if e:
                    return e
        for cand in (wm_class, res_name, app_id):
            if cand:
                low = cand.lower()
                e = self.by_wmclass.get(low) or self.by_tail.get(low) or self.by_binary.get(low)
                if e:
                    return e
        return None

    def preferred(self, kind):
        if kind not in self._preferred:
            found = ""
            mime = PREFERRED_MIME.get(kind)
            if mime:
                try:
                    out = subprocess.run(["xdg-mime", "query", "default", mime], capture_output=True,
                                         text=True, timeout=3).stdout.strip()
                    found = out[:-8] if out.endswith(".desktop") else out
                except (OSError, subprocess.SubprocessError):
                    pass
            self._preferred[kind] = found
        return self._preferred[kind]

    def resolve(self, spec):
        """A pinned item as written in the settings -> desktop entry id."""
        spec = str(spec).strip()
        if spec.startswith("preferred://"):
            return self.preferred(spec[len("preferred://"):]) or ""
        if spec.startswith("applications:"):
            spec = spec[len("applications:"):]
        if spec.startswith("file://"):
            spec = unquote(spec[len("file://"):])
        if spec.startswith("/"):
            for e in self.by_id.values():
                if e.path == spec:
                    return e.id
            spec = os.path.basename(spec)
        return spec[:-8] if spec.endswith(".desktop") else spec

    def launch(self, entry_id, urls=(), action=None):
        e = self.get(entry_id)
        if e is None:
            return False
        if not urls and not action:
            # KIO gives the app its own systemd scope, startup feedback and focus
            return QProcess.startDetached("kioclient", ["exec", e.path])[0]
        line = e.exec
        if action:
            line = next((a["exec"] for a in e.actions if a["id"] == action), "")
        argv = expand_exec(line, urls, e)
        if not argv:
            return False
        if e.terminal:
            argv = ["konsole", "-e"] + argv
        # never inside the dock's own service cgroup: restarting the dock
        # would take the app down with it
        safe = "".join(c if c.isalnum() else "_" for c in e.id)
        unit = f"app-{ids.SLUG}dock-{safe}-{uuid.uuid4().hex[:8]}.scope"
        ok = QProcess.startDetached("systemd-run", ["--user", "--scope", "--quiet", "--slice=app.slice",
                                                    f"--unit={unit}", "--"] + argv)[0]
        return ok or QProcess.startDetached(argv[0], argv[1:])[0]
