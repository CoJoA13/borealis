#!/usr/bin/env python3
"""Render the Borealis Bar's Control Center offscreen with stand-in backends,
walk its pages and edit mode, and check what each click asks for; then click
the bar's own buttons and check they ask for their popups.

    python3 tools/barcheck.py            screenshots in build/shots/bar/
    python3 tools/barcheck.py --app DIR  check a built or installed copy instead

Nothing here reaches NetworkManager, BlueZ, PipeWire, UPower or Spectacle:
every backend is a stand-in that writes down what it was asked to do, and the
bar's settings file lives in a throwaway folder.
"""
import glob
import json
import os
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BAR = (os.path.abspath(sys.argv[sys.argv.index("--app") + 1]) if "--app" in sys.argv[:-1]
       else os.path.join(HERE, "src", "bar"))
SHOTS = os.path.join(HERE, "build", "shots", "bar")

config = tempfile.mkdtemp(prefix="barcheck-")
os.environ.update(QT_QPA_PLATFORM="offscreen", XDG_CONFIG_HOME=config)
os.environ.setdefault("QT_QPA_PLATFORMTHEME", "kde")
# Borealis Dark's colours when the theme is built, so the screenshots look like the desktop
_schemes = sorted(glob.glob(os.path.join(HERE, "build", "share", "color-schemes", "*Dark*.colors")))
if _schemes:
    shutil.copy(_schemes[0], os.path.join(config, "kdeglobals"))
sys.path.insert(0, BAR)
if os.path.isdir(os.path.join(BAR, "..", "shellkit")):
    sys.path.insert(1, os.path.join(BAR, "..", "shellkit"))

from PySide6.QtCore import (Property, QAbstractListModel, QByteArray, QDateTime, QEvent, QModelIndex,  # noqa: E402
                            QObject, QPointF, QRect, QRectF, Qt, QUrl, Signal, Slot, qInstallMessageHandler)
from PySide6.QtGui import QColor, QGuiApplication, QImage, QKeyEvent, QMouseEvent, QPainter  # noqa: E402
from PySide6.QtQml import QQmlComponent, QQmlEngine  # noqa: E402
from PySide6.QtQuick import QQuickItem, QQuickWindow  # noqa: E402
import shiboken6  # noqa: E402

messages = []
qInstallMessageHandler(lambda kind, context, text: messages.append(text))
app = QGuiApplication(["barcheck"])

import settings as bar_settings  # noqa: E402  (the bar's own)

NORMAL = 65536
ROLE = 257
calls = []          # what the Control Center asked the stand-ins for, in order


def record(*what):
    calls.append(what)


# ------------------------------------------------------------- stand-ins ---
class Rows(QAbstractListModel):
    """A list model with named roles, like the ones Plasma's modules hand over.
    A value may be a function, read each time (for live volumes)."""

    def __init__(self, rows, parent=None):
        super().__init__(parent)
        self.rows = rows
        self.names = list(dict.fromkeys(key for row in rows for key in row))

    def roleNames(self):
        return {ROLE + i: QByteArray(name.encode()) for i, name in enumerate(self.names)}

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def data(self, index, role=0):
        i = int(role) - ROLE
        if not index.isValid() or not 0 <= index.row() < len(self.rows) or not 0 <= i < len(self.names):
            return None
        value = self.rows[index.row()].get(self.names[i])
        return value() if callable(value) and not isinstance(value, QObject) else value

    def refresh(self):
        if self.rows:
            self.dataChanged.emit(self.index(0, 0), self.index(len(self.rows) - 1, 0), [])


class Thing(QObject):
    """An object with a name and whatever a QML page reads off it."""
    changed = Signal()

    def __init__(self, name, **values):
        super().__init__()
        self._name = name
        self.values = values

    name = Property(str, lambda self: self._name, constant=True)
    percentage = Property(int, lambda self: self.values.get("percentage", 0), constant=True)


class Pulse(QObject):
    """A sound device or an app's stream."""
    changed = Signal()

    def __init__(self, name, volume, muted=False, default=False):
        super().__init__()
        self.label = name
        self._volume, self._muted, self._default = int(volume * NORMAL), muted, default
        self.peers = []

    def _get_volume(self):
        return self._volume

    def _set_volume(self, value):
        self._volume = int(value)
        self.changed.emit()

    def _get_muted(self):
        return self._muted

    def _set_muted(self, value):
        self._muted = bool(value)
        self.changed.emit()

    def _get_default(self):
        return self._default

    def _set_default(self, value):
        for peer in self.peers:
            peer._default = peer is self and bool(value)
            peer.changed.emit()

    volume = Property(int, _get_volume, _set_volume, notify=changed)
    muted = Property(bool, _get_muted, _set_muted, notify=changed)
    default = Property(bool, _get_default, _set_default, notify=changed)
    description = Property(str, lambda self: self.label, constant=True)


class Net(QObject):
    changed = Signal()

    def __init__(self):
        super().__init__()
        self._on, self._airplane, self._networks = True, False, None
        self.rows = [
            {"ItemUniqueName": "Aurora Home", "ConnectionIcon": "network-wireless-100-locked", "ConnectionState": 2,
             "SecurityType": 6, "Uuid": "aa11", "ConnectionPath": "/c/1", "DevicePath": "/d/1", "SpecificPath": "/ap/1"},
            {"ItemUniqueName": "Café Polaris", "ConnectionIcon": "network-wireless-60-locked", "ConnectionState": 4,
             "SecurityType": 6, "Uuid": "", "ConnectionPath": "", "DevicePath": "/d/1", "SpecificPath": "/ap/2"},
            {"ItemUniqueName": "Library Guest", "ConnectionIcon": "network-wireless-40", "ConnectionState": 4,
             "SecurityType": 0, "Uuid": "", "ConnectionPath": "", "DevicePath": "/d/1", "SpecificPath": "/ap/3"},
            {"ItemUniqueName": "Northern Lights 5G", "ConnectionIcon": "network-wireless-80-locked", "ConnectionState": 4,
             "SecurityType": 8, "Uuid": "bb22", "ConnectionPath": "/c/2", "DevicePath": "/d/1", "SpecificPath": "/ap/4"},
        ]

    wifiAvailable = Property(bool, lambda self: True, constant=True)
    available = Property(bool, lambda self: True, constant=True)
    airplaneAvailable = Property(bool, lambda self: True, constant=True)
    on = Property(bool, lambda self: self._on, notify=changed)
    airplane = Property(bool, lambda self: self._airplane, notify=changed)
    label = Property(str, lambda self: "Airplane Mode" if self._airplane else "Aurora Home" if self._on else "Off",
                     notify=changed)
    iconName = Property(str, lambda self: "network-wireless-100-locked", constant=True)
    scanning = Property(bool, lambda self: False, constant=True)
    hotspotSupported = Property(bool, lambda self: False, constant=True)
    hotspotActive = Property(bool, lambda self: False, constant=True)
    hotspotName = Property(str, lambda self: "borealis-laptop", constant=True)
    hotspotPassword = Property(str, lambda self: "", constant=True)
    activating = Property(int, lambda self: 1, constant=True)
    activated = Property(int, lambda self: 2, constant=True)
    deactivating = Property(int, lambda self: 3, constant=True)
    networks = Property(QObject, lambda self: self._networks, notify=changed)

    @Slot()
    def toggle(self):
        record("net.toggle")
        self._on = not self._on
        self.changed.emit()

    @Slot(bool)
    def setAirplane(self, enable):
        record("net.setAirplane", enable)
        self._airplane = enable
        self.changed.emit()

    @Slot()
    def scan(self):
        record("net.scan")

    @Slot()
    def readHotspot(self):
        record("net.readHotspot")

    @Slot(int, str, result=bool)
    def asksForPassword(self, security, uuid):
        return not uuid and security in (1, 4, 6, 8)

    @Slot(int, result=int)
    def shortestPassword(self, security):
        return 5 if security == 1 else 8

    @Slot("QVariantMap", str)
    def connectTo(self, row, password):
        record("net.connectTo", row.get("specificPath"), password)

    @Slot("QVariantMap")
    def disconnectFrom(self, row):
        record("net.disconnectFrom", row.get("connectionPath"))

    @Slot(str, str)
    def startHotspot(self, name, password):
        record("net.startHotspot", name)

    @Slot()
    def stopHotspot(self):
        record("net.stopHotspot")

    @Slot(bool)
    def watchNetworks(self, watch):
        record("net.watchNetworks", watch)
        self._networks = Rows(self.rows, self) if watch else None
        self.changed.emit()

    @Slot(int, bool)
    def holdRow(self, row, hold):
        record("net.holdRow", row, hold)


class Bluetooth(QObject):
    changed = Signal()

    def __init__(self):
        super().__init__()
        self._list = None
        self.buds, self.keys = Thing("Aurora Buds"), Thing("Polar Keyboard")
        self.rows = [
            {"DeviceFullName": "Aurora Buds", "Icon": "audio-headphones", "Connected": True, "Connecting": False,
             "Disconnecting": False, "ConnectionFailed": False, "Paired": True, "Battery": Thing("b", percentage=80),
             "Device": self.buds, "Ubi": "/org/bluez/hci0/dev_1"},
            {"DeviceFullName": "Polar Keyboard", "Icon": "input-keyboard", "Connected": False, "Connecting": False,
             "Disconnecting": False, "ConnectionFailed": False, "Paired": True, "Battery": None,
             "Device": self.keys, "Ubi": "/org/bluez/hci0/dev_2"},
        ]

    available = Property(bool, lambda self: True, constant=True)
    on = Property(bool, lambda self: True, constant=True)
    label = Property(str, lambda self: "Aurora Buds", constant=True)
    deviceList = Property(QObject, lambda self: self._list, notify=changed)

    @Slot()
    def toggle(self):
        record("bt.toggle")

    @Slot(bool)
    def watchDevices(self, watch):
        record("bt.watchDevices", watch)
        self._list = Rows(self.rows, self) if watch else None
        self.changed.emit()

    @Slot(QObject, str, bool)
    def toggleDevice(self, device, ubi, connected):
        record("bt.toggleDevice", device.property("name") if device else None, connected)

    @Slot()
    def pairDevice(self):
        record("bt.pairDevice")


class Sound(QObject):
    changed = Signal()

    def __init__(self):
        super().__init__()
        self.speakers = Pulse("Speakers", 0.62, default=True)
        self.headphones = Pulse("Aurora Buds", 0.45)
        self.speakers.peers = self.headphones.peers = [self.speakers, self.headphones]
        self.mic = Pulse("Built-in Microphone", 0.8, default=True)
        self.mic.peers = [self.mic]
        self.music = Pulse("Music", 0.7)
        self.browser = Pulse("Firefox", 0.35, muted=True)
        self._models = None
        for obj in (self.speakers, self.headphones, self.mic, self.music, self.browser):
            obj.changed.connect(self._changed)

    def _changed(self):
        self.changed.emit()
        for model in (self._models or ()):
            model.refresh()

    def _device(self, pulse, icon):
        return {"Description": pulse.label, "IconName": icon, "Default": lambda: pulse.default,
                "PulseObject": pulse, "Volume": lambda: pulse.volume, "Muted": lambda: pulse.muted}

    def _stream(self, pulse, icon, client, media):
        return {"Client": client, "Name": "", "IconName": icon, "Volume": lambda: pulse.volume,
                "Muted": lambda: pulse.muted, "HasVolume": True, "PulseObject": pulse,
                "Properties": {"media.name": media}}

    normalVolume = Property(float, lambda self: float(NORMAL), constant=True)
    sink = Property(QObject, lambda self: self.speakers, constant=True)
    available = Property(bool, lambda self: True, constant=True)
    volume = Property(float, lambda self: self.speakers.volume / NORMAL, notify=changed)
    muted = Property(bool, lambda self: self.speakers.muted, notify=changed)
    deviceName = Property(str, lambda self: "Speakers", constant=True)
    iconName = Property(str, lambda self: "audio-volume-medium", notify=changed)
    micAvailable = Property(bool, lambda self: True, constant=True)
    micVolume = Property(float, lambda self: self.mic.volume / NORMAL, notify=changed)
    micMuted = Property(bool, lambda self: self.mic.muted, notify=changed)
    micName = Property(str, lambda self: "Built-in Microphone", constant=True)
    micIconName = Property(str, lambda self: "microphone-sensitivity-high", notify=changed)
    outputs = Property(QObject, lambda self: self._models[0] if self._models else None, notify=changed)
    inputs = Property(QObject, lambda self: self._models[1] if self._models else None, notify=changed)
    streams = Property(QObject, lambda self: self._models[2] if self._models else None, notify=changed)

    @Slot(float, bool, str, result=str)
    def iconFor(self, level, mute, stem):
        return f"{stem}-muted" if mute or level <= 0.001 else f"{stem}-low" if level < 0.34 \
            else f"{stem}-medium" if level < 0.67 else f"{stem}-high"

    @Slot(float)
    def setVolume(self, fraction):
        record("sound.setVolume", round(fraction, 2))

    @Slot()
    def toggleMute(self):
        record("sound.toggleMute")

    @Slot(float)
    def setMicVolume(self, fraction):
        record("sound.setMicVolume", round(fraction, 2))

    @Slot()
    def toggleMicMute(self):
        record("sound.toggleMicMute")

    @Slot(QObject, float)
    def setObjectVolume(self, obj, fraction):
        record("sound.setObjectVolume", obj.label if obj else None, round(fraction, 2))
        if obj:
            obj.volume = int(fraction * NORMAL)

    @Slot(QObject)
    def toggleObjectMute(self, obj):
        record("sound.toggleObjectMute", obj.label if obj else None)

    @Slot(QObject)
    def makeDefault(self, obj):
        record("sound.makeDefault", obj.label if obj else None)
        if obj:
            obj.default = True

    @Slot(bool)
    def watchDevices(self, watch):
        record("sound.watchDevices", watch)
        if watch:
            self._models = (
                Rows([self._device(self.speakers, "audio-speakers"), self._device(self.headphones, "audio-headphones")], self),
                Rows([self._device(self.mic, "audio-input-microphone")], self),
                Rows([self._stream(self.music, "multimedia-player", Thing("Elisa"), "Northern Lights"),
                      self._stream(self.browser, "firefox", Thing("Firefox"), "Aurora timelapse — YouTube")], self),
            )
        else:
            self._models = None
        self.changed.emit()


class Brightness(QObject):
    available = Property(bool, lambda self: True, constant=True)
    fraction = Property(float, lambda self: 0.7, constant=True)

    @Slot(float)
    def setFraction(self, fraction):
        record("brightness.setFraction", round(fraction, 2))


class Keyboard(QObject):
    changed = Signal()
    available = Property(bool, lambda self: True, constant=True)
    maximum = Property(int, lambda self: 3, constant=True)
    level = Property(int, lambda self: 1, constant=True)
    fraction = Property(float, lambda self: 1 / 3, constant=True)
    label = Property(str, lambda self: "Low", constant=True)

    @Slot(float)
    def setFraction(self, fraction):
        record("keyboard.setFraction", round(fraction, 2))

    @Slot()
    def cycle(self):
        record("keyboard.cycle")


class Power(QObject):
    changed = Signal()

    def __init__(self):
        super().__init__()
        self._profile, self._awake = "balanced", False

    profiles = Property("QVariantList", lambda self: ["power-saver", "balanced", "performance"], constant=True)
    profilesAvailable = Property(bool, lambda self: True, constant=True)
    profile = Property(str, lambda self: self._profile, notify=changed)
    performanceBlocked = Property(str, lambda self: "", constant=True)
    performanceDegraded = Property(str, lambda self: "", constant=True)
    holds = Property("QVariantList", lambda self: [], constant=True)
    awake = Property(bool, lambda self: self._awake, notify=changed)

    @Slot(str)
    def setProfile(self, name):
        record("power.setProfile", name)
        self._profile = name
        self.changed.emit()

    @Slot(bool)
    def setAwake(self, on):
        record("power.setAwake", on)
        self._awake = on
        self.changed.emit()


class Status(QObject):
    def __init__(self):
        super().__init__()
        self._parts = {"net": Net(), "bt": Bluetooth(), "sound": Sound(), "brightness": Brightness(),
                       "keyboard": Keyboard(), "power": Power()}
        for part in self._parts.values():
            part.setParent(self)

    net = Property(QObject, lambda self: self._parts["net"], constant=True)
    bt = Property(QObject, lambda self: self._parts["bt"], constant=True)
    sound = Property(QObject, lambda self: self._parts["sound"], constant=True)
    brightness = Property(QObject, lambda self: self._parts["brightness"], constant=True)
    keyboard = Property(QObject, lambda self: self._parts["keyboard"], constant=True)
    power = Property(QObject, lambda self: self._parts["power"], constant=True)


class Notices(QObject):
    changed = Signal()

    def __init__(self):
        super().__init__()
        self._until = QDateTime()

    doNotDisturb = Property(bool, lambda self: self._until.isValid() and self._until > QDateTime.currentDateTime(),
                            notify=changed)
    doNotDisturbUntil = Property(QDateTime, lambda self: self._until, notify=changed)
    doNotDisturbByApp = Property(bool, lambda self: False, constant=True)
    unread = Property(int, lambda self: 0, constant=True)

    @Slot(int)
    def setDoNotDisturb(self, minutes):
        record("notices.setDoNotDisturb", minutes)
        self._until = QDateTime.currentDateTime().addSecs(minutes * 60) if minutes > 0 else QDateTime()
        self.changed.emit()

    @Slot(QDateTime)
    def setDoNotDisturbUntil(self, until):
        minutes = round(QDateTime.currentDateTime().secsTo(until) / 60)
        record("notices.setDoNotDisturbUntil", minutes)
        self._until = until
        self.changed.emit()


class Battery(QObject):
    present = Property(bool, lambda self: True, constant=True)
    percent = Property(int, lambda self: 76, constant=True)
    charging = Property(bool, lambda self: False, constant=True)
    pluggedIn = Property(bool, lambda self: False, constant=True)
    status = Property(str, lambda self: "3 h 20 min left", constant=True)
    profile = Property(str, lambda self: "balanced", constant=True)
    profiles = Property("QVariantList", lambda self: ["power-saver", "balanced", "performance"], constant=True)

    @Slot(str)
    def setProfile(self, name):
        record("battery.setProfile", name)


class Media(QObject):
    available = Property(bool, lambda self: True, constant=True)
    playing = Property(bool, lambda self: True, constant=True)
    title = Property(str, lambda self: "Northern Lights", constant=True)
    artist = Property(str, lambda self: "Aurora Ensemble", constant=True)
    artUrl = Property(str, lambda self: "", constant=True)
    identity = Property(str, lambda self: "Elisa", constant=True)
    icon = Property(str, lambda self: "multimedia-player", constant=True)
    canNext = Property(bool, lambda self: True, constant=True)
    canPrevious = Property(bool, lambda self: True, constant=True)

    @Slot()
    def previous(self):
        record("media.previous")

    @Slot()
    def next(self):
        record("media.next")

    @Slot()
    def playPause(self):
        record("media.playPause")


class Windows(QObject):
    active = Property("QVariantMap", lambda self: {"name": "Kate"}, constant=True)


class AppMenu(QObject):
    titles = Property("QVariantList", lambda self: [{"key": "7", "text": "File"}], constant=True)


def screen_name(screen):
    return screen.property("name") if screen is not None else None


class Bar(QObject):
    """What the Control Center and the bar's buttons see as `bar`, minus the bar."""
    changed = Signal()
    sessionRequested = Signal(str)
    controlsPageRequested = Signal(str)

    def __init__(self):
        super().__init__()
        self._settings = bar_settings.Settings(parent=self)
        self._battery, self._media = Battery(self), Media(self)
        self._windows, self._appmenu = Windows(self), AppMenu(self)
        self._toggles = {"night": False, "dark": True, "aurora": True, "known": True}
        self._sessions = {"lock": True, "suspend": True, "reboot": True, "shutdown": True, "logout": True}
        self.controls = {}
        self.placed = {}
        self.sessionRequested.connect(lambda action: record("bar.session", action))

    logo = Property(str, lambda self: "start-here-kde-symbolic", constant=True)
    windows = Property(QObject, lambda self: self._windows, constant=True)
    appmenu = Property(QObject, lambda self: self._appmenu, constant=True)

    @Slot(str, str, QRectF)
    def placeButton(self, name, screen, rect):
        self.placed[name] = screen

    @Slot(str, QObject, float, float, float, float)
    def openPanel(self, kind, screen, x, y, w, h):
        record("bar.openPanel", kind, screen_name(screen))

    @Slot(QObject, float, float, float, float)
    def openSystemMenu(self, screen, x, y, w, h):
        record("bar.openSystemMenu", screen_name(screen))

    @Slot(str, QObject, float, float, float, float)
    def openAppMenu(self, key, screen, x, y, w, h):
        record("bar.openAppMenu", key, screen_name(screen))

    settings = Property(QObject, lambda self: self._settings, constant=True)
    battery = Property(QObject, lambda self: self._battery, constant=True)
    media = Property(QObject, lambda self: self._media, constant=True)
    toggles = Property("QVariantMap", lambda self: self._toggles, notify=changed)
    sessionCapabilities = Property("QVariantMap", lambda self: self._sessions, notify=changed)
    allPills = Property("QVariantList", lambda self: list(bar_settings.PILLS), constant=True)
    canCapture = Property(bool, lambda self: True, constant=True)
    name = Property(str, lambda self: "Borealis", constant=True)
    popup = Property(str, lambda self: "controls", constant=True)

    @Slot(str)
    def launch(self, entry):
        record("bar.launch", entry)

    @Slot(str)
    def openKcm(self, module):
        record("bar.openKcm", module)

    @Slot(str)
    def openTweaks(self, page):
        record("bar.openTweaks", page)

    @Slot(str)
    def capture(self, kind):
        record("bar.capture", kind)

    @Slot()
    def toggleNightLight(self):
        record("bar.toggleNightLight")

    @Slot()
    def toggleDarkStyle(self):
        record("bar.toggleDarkStyle")

    @Slot()
    def toggleAurora(self):
        record("bar.toggleAurora")

    @Slot(str, bool)
    def reportControls(self, page, editing):
        self.controls = {"page": page, "editing": editing}


class Harness(QObject):
    @Slot()
    def dismissed(self):
        record("dismissed")


# ----------------------------------------------------------------- driving --
def spin(ms):
    end = time.monotonic() + ms / 1000
    while time.monotonic() < end:
        app.processEvents()
        time.sleep(0.005)


def descendants(item):
    todo = [item]
    while todo:
        current = todo.pop()
        yield current
        todo.extend(current.childItems())


class Driver:
    def __init__(self, window, center):
        self.window, self.center = window, center
        self.stamp = 1000
        self.failures = 0
        self.shots = []

    def find(self, name, within=None):
        for item in descendants(within or self.window.contentItem()):
            if item.objectName() == name and item.isVisible():
                return item
        return None

    def point(self, item, fx=0.5, fy=0.5):
        return item.mapToScene(QPointF(item.width() * fx, item.height() * fy))

    def _mouse(self, kind, point, button, buttons):
        self.stamp += 20
        event = QMouseEvent(kind, point, point, button, buttons, Qt.KeyboardModifier.NoModifier)
        event.setTimestamp(self.stamp)
        QGuiApplication.sendEvent(self.window, event)

    def click(self, item, fx=0.5, fy=0.5):
        if item is None:
            return False
        p = self.point(item, fx, fy)
        left = Qt.MouseButton.LeftButton
        self._mouse(QEvent.Type.MouseButtonPress, p, left, left)
        spin(30)
        self._mouse(QEvent.Type.MouseButtonRelease, p, left, Qt.MouseButton.NoButton)
        spin(350)
        return True

    def drag(self, start, end, steps=16):
        left = Qt.MouseButton.LeftButton
        self._mouse(QEvent.Type.MouseButtonPress, start, left, left)
        spin(40)
        for i in range(1, steps + 1):
            p = QPointF(start.x() + (end.x() - start.x()) * i / steps, start.y() + (end.y() - start.y()) * i / steps)
            self._mouse(QEvent.Type.MouseMove, p, Qt.MouseButton.NoButton, left)
            spin(25)
        spin(200)
        self._mouse(QEvent.Type.MouseButtonRelease, end, left, Qt.MouseButton.NoButton)
        spin(400)

    def type(self, text):
        for ch in text:
            for kind in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease):
                QGuiApplication.sendEvent(self.window, QKeyEvent(kind, 0, Qt.KeyboardModifier.NoModifier, ch))
            spin(10)

    def key(self, key, text=""):
        for kind in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease):
            QGuiApplication.sendEvent(self.window, QKeyEvent(kind, key, Qt.KeyboardModifier.NoModifier, text))
        spin(300)

    def page(self):
        return self.center.property("page")

    def show(self, name):
        bar.controlsPageRequested.emit(name)
        spin(500)

    def check(self, what, good, detail=""):
        print(("ok: " if good else "FAIL: ") + what + ("" if good or not detail else f" ({detail})"))
        self.failures += not good

    def called(self, *what):
        return any(c[:len(what)] == what for c in calls)

    def texts_inside(self, label):
        """Every visible text lies across the card, not past its sides."""
        left = self.center.mapToScene(QPointF(0, 0)).x()
        right = left + self.center.width()
        bad = []
        for item in descendants(self.center):
            if not item.isVisible() or item.metaObject().className() != "QQuickText" or not item.property("text"):
                continue
            a = item.mapToScene(QPointF(0, 0)).x()
            b = item.mapToScene(QPointF(item.width(), 0)).x()
            if a < left - 0.5 or b > right + 0.5:
                bad.append(f"{item.property('text')!r} at {a:.0f}–{b:.0f}")
        self.check(f"{label}: every text stays on the card", not bad, "; ".join(bad[:4]))

    def shot(self, name):
        image = self.window.grabWindow()
        top_left = self.center.mapToScene(QPointF(0, 0))
        rect = QRect(int(top_left.x()) - 14, int(top_left.y()) - 14, int(self.center.width()) + 28,
                     int(self.center.height()) + 28)
        crop = image.copy(rect)
        crop.save(os.path.join(SHOTS, f"{name}.png"))
        self.shots.append((name, crop))

    def sheet(self, names, path):
        chosen = [(n, img) for n, img in self.shots if n in names]
        if not chosen:
            return
        gap, label = 18, 26
        width = sum(img.width() for _, img in chosen) + gap * (len(chosen) + 1)
        height = max(img.height() for _, img in chosen) + gap * 2 + label
        out = QImage(width, height, QImage.Format.Format_ARGB32)
        out.fill(QColor("#11141b"))
        painter = QPainter(out)
        painter.setPen(QColor("#c8cde0"))
        x = gap
        for name, img in chosen:
            painter.drawText(x + 14, gap + 16, name)
            painter.drawImage(x, gap + label, img)
            x += img.width() + gap
        painter.end()
        out.save(path)


HARNESS = """import QtQuick
import "%s" as Bar

Window {
    width: 490
    height: 1000
    visible: true
    color: "#1b2030"

    Bar.ControlCenter {
        objectName: "center"
        x: 35
        y: 30
        status: fakeStatus
        notices: fakeNotices
        maxHeight: 940
        onDismissed: harness.dismissed()
    }
}
"""


# the bar's own buttons, the way BarWindow.qml lays them out
BUTTONS_HARNESS = """import QtQuick
import QtQuick.Layouts
import "%s" as Bar

Window {
    id: win
    width: 700
    height: 40
    visible: true
    color: "#1b2030"

    property var targetScreen: Qt.application.screens[0]
    property var status: fakeStatus
    property var notices: fakeNotices
    signal layoutChanged()

    RowLayout {
        height: 30
        spacing: 4
        Bar.BarItem {
            objectName: "item-menu"
            name: "menu"
            window: win
        }
        Bar.BarItem {
            objectName: "item-app"
            name: "app"
            window: win
        }
        Bar.BarItem {
            objectName: "item-clock"
            name: "clock"
            window: win
        }
        Bar.BarItem {
            objectName: "item-controls"
            name: "controls"
            window: win
        }
    }
}
"""


def check_buttons(engine, d):
    """Clicks on the bar's buttons reach the bar, each with its screen."""
    component = QQmlComponent(engine)
    component.setData((BUTTONS_HARNESS % QUrl.fromLocalFile(os.path.join(BAR, "ui")).toString()).encode(),
                      QUrl.fromLocalFile(os.path.join(config, "buttons.qml")))
    root = component.create()
    if root is None:
        d.check("the bar's buttons load", False, "; ".join(e.toString() for e in component.errors()[:3]))
        return
    window = shiboken6.wrapInstance(shiboken6.getCppPointer(root)[0], QQuickWindow)
    buttons = Driver(window, window.contentItem())
    spin(600)
    screen = window.screen().name()
    for item, expected in (("item-menu", ("bar.openSystemMenu", screen)),
                           ("item-app", ("bar.openAppMenu", "7", screen)),
                           ("item-clock", ("bar.openPanel", "clock", screen)),
                           ("item-controls", ("bar.openPanel", "controls", screen))):
        found = buttons.find(item)
        buttons.click(found)
        d.check(f"a click on the bar's {item[5:]} button opens its popup", d.called(*expected),
                f"asked for {[c for c in calls if c[0].startswith('bar.open')][-1:]}" if found else "no button")
    d.check("the buttons tell the bar where they are", {"system", "clock", "controls"} <= set(bar.placed),
            str(sorted(bar.placed)))
    root.deleteLater()
    spin(100)


def main():
    global bar
    os.makedirs(SHOTS, exist_ok=True)
    engine = QQmlEngine()
    bar = Bar()
    status, notices, harness = Status(), Notices(), Harness()
    ctx = engine.rootContext()
    ctx.setContextProperty("bar", bar)
    ctx.setContextProperty("fakeStatus", status)
    ctx.setContextProperty("fakeNotices", notices)
    ctx.setContextProperty("harness", harness)
    component = QQmlComponent(engine)
    component.setData((HARNESS % QUrl.fromLocalFile(os.path.join(BAR, "ui")).toString()).encode(),
                      QUrl.fromLocalFile(os.path.join(config, "harness.qml")))
    root = component.create()
    if root is None:
        print("FAIL: the Control Center didn't load")
        for e in component.errors()[:10]:
            print("  ", e.toString())
        return 1
    window = shiboken6.wrapInstance(shiboken6.getCppPointer(root)[0], QQuickWindow)
    window.requestActivate()
    center = next(i for i in descendants(window.contentItem()) if i.objectName() == "center")
    d = Driver(window, center)
    spin(800)

    # the front
    pills = [n for n in bar_settings.PILLS if d.find("pill-" + n)]
    d.check("the front shows the default toggles", pills == [p for p in bar_settings.DEFAULTS["pills"]], str(pills))
    sliders = [n for n in bar_settings.SLIDERS if d.find("slider-" + n)]
    d.check("the front shows brightness and volume", sliders == ["brightness", "volume"], str(sliders))
    d.texts_inside("front")
    d.shot("front")

    d.click(d.find("pill-wifi"), 0.25)
    d.check("a click on Wi-Fi switches it", d.called("net.toggle"))
    d.click(d.find("pill-wifi"), 0.25)
    d.click(d.find("pill-end", d.find("pill-wifi")))
    d.check("Wi-Fi's arrow opens its page", d.page() == "wifi", d.page())
    d.check("the page lists networks", d.called("net.watchNetworks", True) and d.find("network-3") is not None)
    d.texts_inside("Wi-Fi page")
    d.shot("wifi")

    d.click(d.find("network-1"))
    field = d.find("password")
    d.check("a new secured network asks for its password", field is not None)
    d.check("its row keeps still while the password is typed", d.called("net.holdRow", 1, True))
    d.type("polaris-guest")
    d.shot("wifi-password")
    d.key(Qt.Key.Key_Return, "\r")
    d.check("Enter joins with the password", d.called("net.connectTo", "/ap/2", "polaris-guest"))
    d.click(d.find("network-2"))
    d.check("an open network joins at once", d.called("net.connectTo", "/ap/3", ""))
    d.click(d.find("network-3"))
    d.check("a saved network joins at once", d.called("net.connectTo", "/ap/4", ""))
    d.click(d.find("network-0"))
    d.click(d.find("disconnect"))
    d.check("the connected network disconnects", d.called("net.disconnectFrom", "/c/1"))
    d.click(d.find("network-1"))
    d.key(Qt.Key.Key_Escape)
    d.check("Escape in the password field closes just that row", d.find("password") is None and d.page() == "wifi",
            d.page())
    d.key(Qt.Key.Key_Escape)
    d.check("a second Escape goes back to the front", d.page() == "" and d.find("pill-wifi") is not None, d.page())
    d.check("leaving the page lets go of the list", d.called("net.watchNetworks", False))

    d.show("bluetooth")
    d.texts_inside("Bluetooth page")
    d.shot("bluetooth")
    d.click(d.find("page-back"))
    d.check("the back button returns to the front", d.page() == "", d.page())
    d.show("bluetooth")
    d.click(d.find("device-1"))
    d.check("a paired device connects", d.called("bt.toggleDevice", "Polar Keyboard", False))
    d.click(d.find("device-0"))
    d.check("a connected device disconnects", d.called("bt.toggleDevice", "Aurora Buds", True))

    d.show("sound")
    d.texts_inside("Sound page")
    d.shot("sound")
    d.click(d.find("output-1"))
    d.check("an output becomes the default", d.called("sound.makeDefault", "Aurora Buds"))
    d.click(d.find("stream-0"), 0.6)
    d.check("an app's slider sets its volume", d.called("sound.setObjectVolume", "Music"))
    d.click(d.find("stream-1"), 0.04)
    d.check("an app's icon mutes it", d.called("sound.toggleObjectMute", "Firefox"))

    d.show("power")
    d.texts_inside("Power page")
    d.shot("power")
    d.click(d.find("profile-power-saver"))
    d.check("a power mode can be picked", d.called("power.setProfile", "power-saver"))
    d.click(d.find("awake"), 0.3)
    d.check("Stay Awake turns on", d.called("power.setAwake", True))

    d.show("dnd")
    d.texts_inside("Do Not Disturb page")
    d.click(d.find("dnd-hour"))
    d.check("Do Not Disturb for an hour", d.called("notices.setDoNotDisturbUntil", 60))
    spin(300)
    d.shot("dnd")

    d.show("hotspot")
    d.texts_inside("Hotspot page")
    d.shot("hotspot")
    d.click(d.find("hotspot-name"), 0.3)
    d.key(Qt.Key.Key_Escape)
    d.check("Escape in a hotspot field goes back", d.page() == "", d.page())

    d.show("screenshot")
    d.texts_inside("Screenshot page")
    d.shot("screenshot")
    d.click(d.find("capture-region"))
    d.check("a region screenshot goes to Spectacle", d.called("bar.capture", "region"))

    # the power button's page (never the real thing: `bar` only writes it down)
    d.show("")
    d.click(d.find("session"))
    d.check("the power button slides in its page", d.page() == "session", d.page())
    d.texts_inside("Sleep, Restart or Shut Down page")
    d.shot("session")
    d.check("the page offers Sleep, Restart, Shut Down and Log Out",
            all(d.find("session-" + key) for key in ("sleep", "restart", "shutdown", "logout")))
    before = len(calls)
    d.click(d.find("session-restart"))
    d.check("Restart goes to Plasma's own confirmation, with the Control Center out of the way",
            ("dismissed",) in calls[before:] and ("bar.session", "restart") in calls[before:], str(calls[before:]))
    bar._sessions = {**bar._sessions, "suspend": False}
    bar.changed.emit()
    spin(300)
    d.check("what this computer can't do stays out of sight",
            d.find("session-sleep") is None and d.find("session-shutdown") is not None)
    bar._sessions = {**bar._sessions, "suspend": True}
    bar.changed.emit()

    # edit mode
    d.show("")
    d.show("edit")
    d.check("edit mode is on", bar.controls.get("editing") is True, str(bar.controls))
    d.texts_inside("edit mode")
    d.shot("edit")
    wifi, night = d.find("pill-wifi"), d.find("pill-night")
    d.drag(d.point(wifi, 0.3), d.point(night, 0.3))
    saved = json.load(open(bar.settings.path))["pills"]
    d.check("dragging Wi-Fi onto Night Light's place moves it there",
            saved[:4] == ["bluetooth", "night", "wifi", "power"], str(saved))
    d.click(d.find("pill-end", d.find("pill-aurora")))
    saved = json.load(open(bar.settings.path))["pills"]
    d.check("− takes a toggle out", "aurora" not in saved, str(saved))
    d.click(d.find("add-airplane"))
    saved = json.load(open(bar.settings.path))["pills"]
    d.check("a chip adds a toggle at the end", saved[-1:] == ["airplane"], str(saved))
    d.shot("edit-changed")
    d.click(d.find("edit"))
    d.check("Done leaves edit mode", bar.controls.get("editing") is False, str(bar.controls))

    bar.settings.set("sliders", list(bar_settings.SLIDERS))
    spin(500)
    sliders = [n for n in bar_settings.SLIDERS if d.find("slider-" + n)]
    d.check("every slider shows when chosen", sliders == list(bar_settings.SLIDERS), str(sliders))
    d.check("the card fits under its limit", center.height() <= 940, f"{center.height():.0f}")
    d.texts_inside("front with every slider")
    d.shot("front-all")
    d.sheet(["front", "wifi-password", "bluetooth", "sound", "power", "edit-changed"], os.path.join(SHOTS, "sheet.png"))

    check_buttons(engine, d)

    errors = [m for m in dict.fromkeys(messages)
              if any(word in m for word in ("TypeError", "ReferenceError", "Unable to assign", "Cannot assign",
                                            "is not a type", "is not defined", "Error:", "failed"))]
    d.check("no QML errors", not errors, " | ".join(e[:200] for e in errors[:5]))
    del engine
    shutil.rmtree(config, ignore_errors=True)
    print("screenshots in", SHOTS)
    return 1 if d.failures else 0


if __name__ == "__main__":
    sys.exit(main())
