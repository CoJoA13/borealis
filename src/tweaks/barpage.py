"""Borealis Tweaks, the Bar page: the bar's settings file, and the bar itself.

The bar watches its settings file, so changes here show up at once. Switching
to the bar (or back to a Plasma panel) goes through install.sh, like the
dock's switch.
"""
import json
import os
import subprocess

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot
from PySide6.QtDBus import QDBusConnection, QDBusInterface, QDBusServiceWatcher

HERE = os.path.dirname(os.path.abspath(__file__))
try:                        # installed: a copy made by gen_tweaks.py
    import barsettings
except ImportError:         # the source tree: the bar's own module
    import importlib.util
    import sys
    sys.path.insert(1, os.path.join(HERE, "..", "shellkit"))
    _spec = importlib.util.spec_from_file_location("barsettings", os.path.join(HERE, "..", "bar", "settings.py"))
    barsettings = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(barsettings)

import ids  # noqa: E402  (the dock's names; the bar shares its SLUG)
from backend import PROJECT  # noqa: E402

BUS = f"org.{ids.SLUG}.Bar"
SERVICE = f"{ids.SLUG}-bar.service"
ZONES = ("left", "center", "right")


class BarBackend(QObject):
    changed = Signal()
    stateChanged = Signal()

    def __init__(self, backend, parent=None):
        super().__init__(parent)
        self.backend = backend
        self.settings = barsettings.Settings(parent=self)
        self.settings.changed.connect(self.changed)
        self._pending = {}
        self._flush = QTimer(self, singleShot=True, interval=150)
        self._flush.timeout.connect(self._write)
        self._tray = []
        self._watcher = QDBusServiceWatcher(BUS, QDBusConnection.sessionBus(),
                                            QDBusServiceWatcher.WatchModeFlag.WatchForOwnerChange, self)
        self._watcher.serviceOwnerChanged.connect(lambda *_: self._state_changed())
        backend.finished.connect(lambda *_: self._state_changed())
        self._state_changed()

    def _state_changed(self):
        self._read_tray()
        self.stateChanged.emit()

    # ---------------------------------------------------------------- state --
    @Property("QVariantMap", notify=changed)
    def values(self):
        return {**self.settings.values, **self._pending}

    @Property(bool, notify=stateChanged)
    def running(self):
        reply = QDBusConnection.sessionBus().interface().isServiceRegistered(BUS)
        return bool(reply.value() if hasattr(reply, "value") else reply)

    @Property(bool, notify=stateChanged)
    def installed(self):
        return os.path.islink(os.path.expanduser(f"~/.local/bin/{ids.SLUG}-bar"))

    @Property(bool, constant=True)
    def canSwitch(self):
        return os.path.exists(os.path.join(PROJECT, "install.sh"))

    @Property(str, constant=True)
    def configPath(self):
        return self.settings.path

    @Property("QVariantList", constant=True)
    def items(self):
        return list(barsettings.ITEMS)

    @Property("QVariantList", constant=True)
    def pills(self):
        return list(barsettings.PILLS)

    def _read_tray(self):
        """The tray icons the running bar shows, so they can be hidden from here."""
        tray = []
        if self.running:
            reply = QDBusInterface(BUS, "/Bar", BUS + "1", QDBusConnection.sessionBus()).call("State")
            try:
                state = json.loads(reply.arguments()[0]) if reply.arguments() else {}
                tray = [{"id": t.get("id", ""), "title": t.get("title", ""), "icon": t.get("iconName", "")}
                        for t in state.get("tray", []) if t.get("id")]
            except (ValueError, TypeError, IndexError):
                pass
        if tray != self._tray:
            self._tray = tray

    @Property("QVariantList", notify=stateChanged)
    def trayItems(self):
        hidden = [{"id": h, "title": h, "icon": ""} for h in self.values.get("trayHidden", [])
                  if all(t["id"] != h for t in self._tray)]
        return self._tray + hidden

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

    def _zones(self):
        values = self.values
        return {zone: list(values.get(zone, [])) for zone in ZONES}

    @Slot(str, result=str)
    def zoneOf(self, item):
        return next((zone for zone, items in self._zones().items() if item in items), "")

    @Slot(str, str)
    def placeItem(self, item, zone):
        """Moves an item to the end of a zone; an empty zone hides it."""
        zones = self._zones()
        for items in zones.values():
            if item in items:
                items.remove(item)
        if zone in zones:
            zones[zone].append(item)
        for name, items in zones.items():
            self.set(name, items)

    @Slot(str, int)
    def moveItem(self, item, step):
        zones = self._zones()
        for name, items in zones.items():
            if item in items:
                i = items.index(item)
                j = max(0, min(len(items) - 1, i + step))
                items.insert(j, items.pop(i))
                self.set(name, items)
                return

    @Slot(str, bool)
    def setPill(self, name, on):
        pills = [p for p in self.values.get("pills", []) if p != name]
        if on:
            pills.append(name)
        self.set("pills", pills)

    @Slot(str, int)
    def movePill(self, name, step):
        pills = list(self.values.get("pills", []))
        if name in pills:
            i = pills.index(name)
            j = max(0, min(len(pills) - 1, i + step))
            pills.insert(j, pills.pop(i))
            self.set("pills", pills)

    @Slot(str, bool)
    def setTrayShown(self, item_id, shown):
        hidden = [h for h in self.values.get("trayHidden", []) if h != item_id]
        if not shown:
            hidden.append(item_id)
        self.set("trayHidden", hidden)

    @Slot()
    def resetLook(self):
        self._write()
        self.settings.update({k: v for k, v in barsettings.DEFAULTS.items() if k != "trayHidden"})

    # ---------------------------------------------------------- the bar itself --
    @Slot()
    def enable(self):
        self.backend.runInstaller(["--bar"], "The Borealis Bar is on.")

    @Slot()
    def disable(self):
        self.backend.runInstaller(["--bar-revert"], "Back to a Plasma top panel.")

    @Slot()
    def restart(self):
        subprocess.Popen(["systemctl", "--user", "restart", SERVICE], start_new_session=True)
        QTimer.singleShot(2000, self._state_changed)

    @Slot(str)
    def openKcm(self, module):
        subprocess.Popen(["systemsettings", module], start_new_session=True)
