"""Borealis Tweaks, the Dock page: the dock's settings file, and the dock itself.

The dock watches its settings file, so every change here shows up on the dock
straight away. Switching the dock on or off goes through install.sh, like the
theme changes on the other page.
"""
import json
import os
import subprocess

from PySide6.QtCore import Property, QObject, QProcess, QTimer, QUrl, Signal, Slot
from PySide6.QtDBus import QDBusConnection, QDBusServiceWatcher
from PySide6.QtGui import QKeySequence

try:                        # installed: copies made by gen_tweaks.py
    import ids
    import docksettings
    import dockstacks
    import dockpresets
except ImportError:         # the source tree: use the dock's own modules
    import sys
    sys.path.insert(1, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "dock"))
    import ids
    import settings as docksettings
    import stacks as dockstacks
    import presets as dockpresets

WIDGET_ORDER = ("clock", "battery", "media")

from backend import PROJECT

SERVICE = f"{ids.SLUG}-dock.service"


class DockBackend(QObject):
    changed = Signal()
    stateChanged = Signal()

    def __init__(self, backend, parent=None):
        super().__init__(parent)
        self.backend = backend
        self.settings = docksettings.Settings(parent=self)
        self.settings.changed.connect(self.changed)
        self._pending = {}
        self._flush = QTimer(self, singleShot=True, interval=150)
        self._flush.timeout.connect(self._write)
        self._watcher = QDBusServiceWatcher(ids.BUS, QDBusConnection.sessionBus(),
                                            QDBusServiceWatcher.WatchModeFlag.WatchForOwnerChange, self)
        self._watcher.serviceOwnerChanged.connect(lambda *_: self.stateChanged.emit())
        backend.finished.connect(lambda *_: self.stateChanged.emit())
        # which keys KWin gave Meta+1 and Launchpad: asked in the background, never blocking the page
        self._shortcut_key = ""
        self._launchpad_key = ""
        self._probe = QProcess(self)
        self._probe.finished.connect(self._probed)
        self._reprobe = QTimer(self, singleShot=True, interval=800)
        self._reprobe.timeout.connect(self._probe_shortcut)
        self.stateChanged.connect(self._reprobe.start)
        self.changed.connect(self._reprobe.start)
        self._probe_shortcut()

    # ---------------------------------------------------------------- state --
    @Property("QVariantMap", notify=changed)
    def values(self):
        return {**self.settings.values, **self._pending}

    @Property(bool, notify=stateChanged)
    def running(self):
        reply = QDBusConnection.sessionBus().interface().isServiceRegistered(ids.BUS)
        return bool(reply.value() if hasattr(reply, "value") else reply)

    @Property(bool, notify=stateChanged)
    def installed(self):
        return os.path.islink(os.path.expanduser(f"~/.local/bin/{ids.SLUG}-dock"))

    @Property(bool, constant=True)
    def canSwitch(self):
        return os.path.exists(os.path.join(PROJECT, "install.sh"))

    @Property(str, constant=True)
    def configPath(self):
        return self.settings.path

    def _probe_shortcut(self):
        if self._probe.state() == QProcess.ProcessState.NotRunning:
            self._probe.start("busctl", ["--user", "--json=short", "call", "org.kde.kglobalaccel",
                                         "/component/kwin", "org.kde.kglobalaccel.Component", "allShortcutInfos"])

    def _probed(self, *_):
        key = launchpad = ""
        launchpad_name = getattr(ids, "LAUNCHPAD_SHORTCUT", f"{ids.NAME} Dock: Launchpad")
        try:
            infos = json.loads(bytes(self._probe.readAllStandardOutput()).decode())["data"][0]
            for info in infos:
                # (unique name, friendly name, component, component name, context, context name, keys, defaults)
                if info[0] == f"{ids.NAME} Dock: activate app 1" and info[6]:
                    key = QKeySequence(info[6][0]).toString()
                elif info[0] == launchpad_name and info[6]:
                    launchpad = ", ".join(QKeySequence(k).toString() for k in sorted(info[6]))
        except (ValueError, KeyError, IndexError, TypeError):
            pass
        if (key, launchpad) != (self._shortcut_key, self._launchpad_key):
            self._shortcut_key, self._launchpad_key = key, launchpad
            self.stateChanged.emit()

    @Property(str, notify=stateChanged)
    def shortcutKey(self):
        """The key KWin gave "activate app 1": empty when something else holds it."""
        return self._shortcut_key

    @Property(str, notify=stateChanged)
    def launchpadKey(self):
        return self._launchpad_key

    # -------------------------------------------------------------- presets --
    @Property("QVariantList", notify=changed)
    def presets(self):
        current = dockpresets.current_id(self.values)
        return [{"id": p["id"], "name": p["name"], "description": p["description"], "builtin": p["builtin"],
                 "current": p["id"] == current, "hasApps": bool(p.get("apps"))}
                for p in dockpresets.all_presets()]

    @Slot(str, bool)
    def applyPreset(self, preset_id, with_apps):
        preset = dockpresets.find(preset_id)
        if preset:
            self._write()
            self.settings.update(dockpresets.apply(self.settings.values, preset, with_apps))

    @Slot(str, bool, result=str)
    def savePreset(self, name, with_apps):
        name = " ".join(str(name).split())
        if not name:
            return ""
        self._write()
        preset_id = dockpresets.save_user(name, self.settings.values, with_apps)
        self.changed.emit()
        return preset_id

    @Slot(str)
    def deletePreset(self, preset_id):
        if dockpresets.delete_user(preset_id):
            self.changed.emit()

    @Slot(str, result=str)
    def importPreset(self, url):
        path = QUrl(url).toLocalFile() if url.startswith("file:") else url
        try:
            preset_id = dockpresets.import_file(path)
        except (ValueError, OSError) as e:
            return f"error:{e}"
        self.changed.emit()
        return preset_id

    @Slot(str, bool, result=str)
    def exportPreset(self, url, with_apps):
        path = QUrl(url).toLocalFile() if url.startswith("file:") else url
        if not path.endswith(".json"):
            path += ".json"
        self._write()
        try:
            return dockpresets.write(path, os.path.splitext(os.path.basename(path))[0], self.settings.values,
                                     with_apps)
        except OSError as e:
            return f"error:{e.strerror or e}"

    # -------------------------------------------------------------- widgets --
    @Slot(str, bool)
    def setWidget(self, kind, on):
        widgets = [dict(w) for w in self.values.get("widgets", [])]
        if on and all(w["type"] != kind for w in widgets):
            widgets.append({"type": kind})
        elif not on:
            widgets = [w for w in widgets if w["type"] != kind]
        widgets.sort(key=lambda w: WIDGET_ORDER.index(w["type"]) if w["type"] in WIDGET_ORDER else 99)
        self.set("widgets", widgets)

    @Slot(str, str, str)
    def setWidgetOption(self, kind, key, value):
        self.set("widgets", [dict(w, **{key: value}) if w["type"] == kind else dict(w)
                             for w in self.values.get("widgets", [])])

    @Slot(result="QVariantList")
    def stackRows(self):
        rows = []
        for st in self.settings.get("stacks"):
            real = dockstacks.resolve(st["path"])
            rows.append({**st, "name": os.path.basename(real.rstrip("/")) or real, "real": real,
                         "icon": dockstacks.folder_icon(st["path"])})
        return rows

    # -------------------------------------------------------------- changes --
    @Slot(str, "QVariant")
    def set(self, key, value):
        self._pending[key] = value           # shown at once, written a moment later
        self.changed.emit()
        self._flush.start()

    def _write(self):
        changes, self._pending = self._pending, {}
        if changes:
            self.settings.update(changes)

    @Slot(int, str, str)
    def setStack(self, index, field, value):
        stacks = [dict(st) for st in self.settings.get("stacks")]
        if 0 <= index < len(stacks):
            stacks[index][field] = value
            self.settings.set("stacks", stacks)

    @Slot(int)
    def removeStack(self, index):
        stacks = [dict(st) for st in self.settings.get("stacks")]
        if 0 <= index < len(stacks):
            del stacks[index]
            self.settings.set("stacks", stacks)

    @Slot(str)
    def addStack(self, url):
        path = QUrl(url).toLocalFile() if url.startswith("file:") else url
        if path and os.path.isdir(path):
            stacks = [dict(st) for st in self.settings.get("stacks")]
            if all(dockstacks.resolve(st["path"]) != os.path.abspath(path) for st in stacks):
                self.settings.set("stacks", stacks + [{"path": path}])

    @Slot()
    def resetPins(self):
        self.settings.set("pinned", list(docksettings.DEFAULTS["pinned"]))

    @Slot()
    def resetLook(self):
        """Everything back to the defaults except what's in the dock."""
        keep = ("pinned", "stacks")
        self.settings.update({k: v for k, v in docksettings.DEFAULTS.items() if k not in keep})

    # --------------------------------------------------------- the dock itself --
    @Slot()
    def enable(self):
        self.backend.runInstaller(["--dock"], "The Borealis Dock is on.")

    @Slot()
    def disable(self):
        self.backend.runInstaller(["--dock-revert"], "Back to the panel dock.")

    @Slot()
    def restart(self):
        subprocess.Popen(["systemctl", "--user", "restart", SERVICE], start_new_session=True)
        QTimer.singleShot(1500, self.stateChanged.emit)

    @Slot()
    def openShortcuts(self):
        subprocess.Popen(["systemsettings", "kcm_keys"], start_new_session=True)
