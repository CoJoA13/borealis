"""The KWin half of the dock (a declarative KWin script) talks to this: window
snapshots arrive over D-Bus; commands wait in a queue until the script is poked
through a KWin shortcut and collects them."""
import json
import os

DEBUG = os.environ.get("BOREALIS_DOCK_DEBUG") == "1"

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot
from PySide6.QtDBus import QDBusConnection, QDBusMessage, QDBusPendingCallWatcher
from PySide6.QtGui import QGuiApplication

import ids


class Bridge(QObject):
    windowsChanged = Signal()
    aliveChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.windows = []
        self._queue = []
        self._alive = False
        self._watchers = set()
        self._kick = QTimer(self, singleShot=True, interval=0)
        self._kick.timeout.connect(self._poke)

    @Property(bool, notify=aliveChanged)
    def alive(self):
        return self._alive

    def _set_alive(self, alive):
        if alive != self._alive:
            self._alive = alive
            self.aliveChanged.emit()

    def send(self, op, **args):
        self._queue.append({"op": op, **args})
        del self._queue[:-64]                 # a stalled bridge mustn't pile up work
        self._kick.start()

    def _poke(self):
        msg = QDBusMessage.createMethodCall("org.kde.kglobalaccel", "/component/kwin",
                                            "org.kde.kglobalaccel.Component", "invokeShortcut")
        msg.setArguments([ids.SHORTCUT])
        watcher = QDBusPendingCallWatcher(QDBusConnection.sessionBus().asyncCall(msg), self)
        self._watchers.add(watcher)
        watcher.finished.connect(self._poked)

    def _poked(self, watcher):
        self._watchers.discard(watcher)
        if watcher.isError():
            print("dock: couldn't reach the KWin bridge:", watcher.error().message(), flush=True)
            self._set_alive(False)
        watcher.deleteLater()

    def take(self):
        out, self._queue = self._queue, []
        return json.dumps(out)

    def receive(self, payload):
        try:
            data = json.loads(payload)
        except ValueError:
            return
        windows = data.get("windows") if isinstance(data, dict) else None
        if not isinstance(windows, list):
            return
        self.windows = [w for w in windows if isinstance(w, dict) and w.get("id")]
        if DEBUG:
            print("dock: snapshot", [(w.get("app") or w.get("cls"), w.get("caption", "")[:24],
                                     "A" if w.get("active") else "") for w in self.windows], flush=True)
        self._set_alive(True)
        self.windowsChanged.emit()


class DockService(QObject):
    """Exported at ids.PATH on ids.BUS as ids.INTERFACE."""

    def __init__(self, bridge, controller, parent=None):
        super().__init__(parent)
        self.bridge = bridge
        self.controller = controller

    @Slot(str)
    def WindowsChanged(self, payload):
        self.bridge.receive(payload)

    @Slot(result=str)
    def TakeCommands(self):
        return self.bridge.take()

    @Slot(str)
    def Hello(self, version):
        # a bridge (re)loaded after the dock started missed what the dock told
        # the previous one: say it again
        print("dock: KWin bridge", version, "is up", flush=True)
        self.controller.push_config()
        self.bridge.send("resync")

    @Slot(str)
    def Log(self, text):
        print("bridge:", text, flush=True)

    @Slot(int)
    def ActivateSlot(self, number):
        self.controller.activateSlot(number)

    @Slot()
    def Reload(self):
        self.controller.settings.load()

    @Slot(int)
    def OpenMenu(self, row):
        self.controller.testMenuRequested.emit(row)

    @Slot(result=str)
    def Layout(self):
        """The resting layout, for tests: where each row sits along the dock."""
        model, settings = self.controller.model, self.controller.settings
        rows = [{"kind": it["kind"], "appId": it.get("appId", ""), "windows": it.get("windowCount", 0),
                 "active": it.get("active", False), "launching": it.get("launching", False),
                 "badge": it.get("badge", 0), "progress": it.get("progress", -1.0)}
                for it in model.items]
        return json.dumps({"offsets": model.restOffsets, "length": model.restLength,
                           "iconSize": settings.get("iconSize"), "margin": settings.get("margin"),
                           "padding": settings.get("padding"), "rows": rows,
                           "bridge": self.bridge.alive})

    @Slot(str)
    def SendBridge(self, command):
        """For tests and debugging: queue a raw bridge command (JSON object)."""
        try:
            data = json.loads(command)
        except ValueError:
            return
        if isinstance(data, dict) and data.get("op"):
            self.bridge.send(**data)

    @Slot(result=str)
    def Version(self):
        return ids.VERSION

    @Slot()
    def Quit(self):
        QGuiApplication.quit()
