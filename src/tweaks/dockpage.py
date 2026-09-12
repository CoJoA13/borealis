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
except ImportError:         # the source tree: use the dock's own modules
    import sys
    sys.path.insert(1, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "dock"))
    import ids
    import settings as docksettings
    import stacks as dockstacks

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
        # which key KWin gave Meta+1: asked in the background, never blocking the page
        self._shortcut_key = ""
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
        key = ""
        try:
            infos = json.loads(bytes(self._probe.readAllStandardOutput()).decode())["data"][0]
            for info in infos:
                if info[4] == f"{ids.NAME} Dock: activate app 1" and info[6]:
                    key = QKeySequence(info[6][0]).toString()
        except (ValueError, KeyError, IndexError, TypeError):
            pass
        if key != self._shortcut_key:
            self._shortcut_key = key
            self.stateChanged.emit()

    @Property(str, notify=stateChanged)
    def shortcutKey(self):
        """The key KWin gave "activate app 1": empty when something else holds it."""
        return self._shortcut_key

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
