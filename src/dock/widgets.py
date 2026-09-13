"""What the dock's widgets show: the battery (UPower) and what's playing (MPRIS).

Both are read through busctl's JSON output, which copes with the nested
variants these D-Bus APIs are full of; their change signals only say when to
read again. Nothing is watched while its widget isn't in the dock.
"""
import json
import time

from PySide6.QtCore import Property, QObject, QProcess, QTimer, Signal, Slot, SLOT
from PySide6.QtDBus import QDBusConnection, QDBusMessage

PROPERTIES = "org.freedesktop.DBus.Properties"


def unwrap(node):
    """busctl's {"type": …, "data": …} -> plain values."""
    if isinstance(node, dict):
        if set(node) == {"type", "data"}:
            return unwrap(node["data"])
        return {k: unwrap(v) for k, v in node.items()}
    if isinstance(node, list):
        return [unwrap(v) for v in node]
    return node


def busctl(parent, args, done=None):
    """Runs busctl in the background; `done` gets one value per JSON line."""
    proc = QProcess(parent)

    def finished(*_):
        out = bytes(proc.readAllStandardOutput()).decode(errors="replace")
        proc.deleteLater()
        values = []
        for line in out.splitlines():
            try:
                values.append(unwrap(json.loads(line)))
            except ValueError:
                pass
        if done:
            done(values)

    proc.finished.connect(finished)
    proc.start("busctl", args)
    return proc


def duration(seconds):
    minutes = max(1, int(round(seconds / 60)))
    hours, minutes = divmod(minutes, 60)
    return f"{hours} h {minutes} min" if hours else f"{minutes} min"


# --------------------------------------------------------------------- battery --
UPOWER = ("org.freedesktop.UPower", "/org/freedesktop/UPower/devices/DisplayDevice", "org.freedesktop.UPower.Device")
PROFILES = ("org.freedesktop.UPower.PowerProfiles", "/org/freedesktop/UPower/PowerProfiles",
            "org.freedesktop.UPower.PowerProfiles")
CHARGING, DISCHARGING, EMPTY, FULL, PENDING_CHARGE = 1, 2, 3, 4, 5


class Battery(QObject):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active = False
        self._device = {}
        self._profile, self._profiles = "", []
        self._again = QTimer(self, singleShot=True, interval=250)
        self._again.timeout.connect(self.read)
        self._poll = QTimer(self, interval=60000)       # UPower's time estimates drift quietly
        self._poll.timeout.connect(self.read)
        bus = QDBusConnection.systemBus()
        for service, path, _iface in (UPOWER, PROFILES):
            bus.connect(service, path, PROPERTIES, "PropertiesChanged", self, SLOT("onChanged(QDBusMessage)"))

    def set_active(self, active):
        if active != self._active:
            self._active = active
            if active:
                self._poll.start()
                self.read()
            else:
                self._poll.stop()

    @Slot(QDBusMessage)
    def onChanged(self, _message):
        if self._active:
            self._again.start()

    def read(self):
        busctl(self, ["--system", "--json=short", "call", UPOWER[0], UPOWER[1], PROPERTIES, "GetAll", "s",
                      UPOWER[2]], self._got_device)
        busctl(self, ["--system", "--json=short", "get-property", PROFILES[0], PROFILES[1], PROFILES[2],
                      "ActiveProfile", "Profiles"], self._got_profiles)

    def _got_device(self, values):
        device = values[0] if values and isinstance(values[0], list) and values[0] else {}
        device = device[0] if isinstance(device, list) else device
        if isinstance(device, dict) and device != self._device:
            self._device = device
            self.changed.emit()

    def _got_profiles(self, values):
        profile = values[0] if values and isinstance(values[0], str) else ""
        profiles = [p.get("Profile", "") for p in values[1]] if len(values) > 1 and isinstance(values[1], list) else []
        profiles = [p for p in profiles if p]
        if (profile, profiles) != (self._profile, self._profiles):
            self._profile, self._profiles = profile, profiles
            self.changed.emit()

    @Property(bool, notify=changed)
    def present(self):
        return bool(self._device.get("IsPresent")) and self._device.get("Type") == 2

    @Property(int, notify=changed)
    def percent(self):
        return int(round(float(self._device.get("Percentage") or 0)))

    @Property(bool, notify=changed)
    def pluggedIn(self):
        return self._device.get("State") in (CHARGING, FULL, PENDING_CHARGE)

    @Property(bool, notify=changed)
    def charging(self):
        return self._device.get("State") == CHARGING

    @Property(str, notify=changed)
    def status(self):
        state = self._device.get("State")
        if state == FULL:
            return "Fully charged"
        if state == CHARGING:
            left = int(self._device.get("TimeToFull") or 0)
            return f"{duration(left)} until full" if left > 0 else "Charging"
        if state == PENDING_CHARGE:
            return "Plugged in, not charging"
        left = int(self._device.get("TimeToEmpty") or 0)
        return f"{duration(left)} left" if left > 0 else "On battery"

    @Property(str, notify=changed)
    def profile(self):
        return self._profile

    @Property("QVariantList", notify=changed)
    def profiles(self):
        return self._profiles

    @Slot(str)
    def setProfile(self, name):
        if name in self._profiles and name != self._profile:
            busctl(self, ["--system", "set-property", PROFILES[0], PROFILES[1], PROFILES[2], "ActiveProfile", "s", name],
                   lambda _v: self.read())


# ----------------------------------------------------------------------- media --
MPRIS_PREFIX = "org.mpris.MediaPlayer2."
MPRIS_PATH = "/org/mpris/MediaPlayer2"
PLAYER = "org.mpris.MediaPlayer2.Player"


class Media(QObject):
    """The player worth showing: the one playing, else the one paused last."""
    changed = Signal()

    def __init__(self, apps=None, parent=None):
        super().__init__(parent)
        self.apps = apps
        self._active = False
        self._players = {}          # bus name -> what we know
        self._owners = {}           # unique name -> bus name
        self._chosen = ""           # picked from the menu; wins while it's around
        self._pending = set()
        self._again = QTimer(self, singleShot=True, interval=120)
        self._again.timeout.connect(self._read_pending)
        bus = QDBusConnection.sessionBus()
        bus.connect("org.freedesktop.DBus", "/org/freedesktop/DBus", "org.freedesktop.DBus", "NameOwnerChanged",
                    "sss", self, SLOT("onOwnerChanged(QString,QString,QString)"))
        bus.connect("", MPRIS_PATH, PROPERTIES, "PropertiesChanged", self, SLOT("onProps(QDBusMessage)"))

    def set_active(self, active):
        if active == self._active:
            return
        self._active = active
        if not active:
            self._players.clear()
            self._owners.clear()
            self.changed.emit()
            return
        reply = QDBusConnection.sessionBus().interface().registeredServiceNames()
        names = reply.value() if hasattr(reply, "value") else reply
        for name in names or []:
            if str(name).startswith(MPRIS_PREFIX):
                self._add(str(name))

    def _add(self, name):
        reply = QDBusConnection.sessionBus().interface().serviceOwner(name)
        owner = reply.value() if hasattr(reply, "value") else reply
        if owner:
            self._owners[str(owner)] = name
        self._players.setdefault(name, {"status": "Stopped", "played": 0.0})
        self._pending.add(name)
        self._again.start()

    @Slot(str, str, str)
    def onOwnerChanged(self, name, _old, new):
        if not self._active or not name.startswith(MPRIS_PREFIX):
            return
        if new:
            self._add(name)
        elif self._players.pop(name, None) is not None:
            self._owners = {k: v for k, v in self._owners.items() if v != name}
            self.changed.emit()

    @Slot(QDBusMessage)
    def onProps(self, message):
        name = self._owners.get(message.service())
        if self._active and name:
            self._pending.add(name)
            self._again.start()

    def _read_pending(self):
        pending, self._pending = self._pending, set()
        for name in pending:
            for iface in (PLAYER, "org.mpris.MediaPlayer2"):
                busctl(self, ["--user", "--json=short", "call", name, MPRIS_PATH, PROPERTIES, "GetAll", "s", iface],
                       lambda values, n=name, i=iface: self._got(n, i, values))

    def _got(self, name, iface, values):
        player = self._players.get(name)
        props = values[0][0] if values and isinstance(values[0], list) and values[0] else None
        if player is None or not isinstance(props, dict):
            return
        before = dict(player)
        if iface == PLAYER:
            meta = props.get("Metadata") or {}
            artist = meta.get("xesam:artist") or ""
            status = str(props.get("PlaybackStatus") or "Stopped")
            if status == "Playing" and player.get("status") != "Playing":
                player["played"] = time.monotonic()
            player.update(status=status, title=str(meta.get("xesam:title") or ""),
                          artist=", ".join(artist) if isinstance(artist, list) else str(artist),
                          art=str(meta.get("mpris:artUrl") or ""),
                          canNext=bool(props.get("CanGoNext")), canPrevious=bool(props.get("CanGoPrevious")),
                          canPlayPause=bool(props.get("CanPause") or props.get("CanPlay")))
        else:
            player.update(identity=str(props.get("Identity") or ""), desktop=str(props.get("DesktopEntry") or ""),
                          canRaise=bool(props.get("CanRaise")))
        if player != before:
            self.changed.emit()

    # --- the player shown ----------------------------------------------------
    def _current(self):
        useful = {n: p for n, p in self._players.items()
                  if p.get("status") in ("Playing", "Paused") or p.get("title")}
        if self._chosen in useful:
            return self._chosen, useful[self._chosen]
        if not useful:
            return "", {}
        name = max(useful, key=lambda n: (useful[n].get("status") == "Playing", useful[n].get("played", 0.0)))
        return name, useful[name]

    def _get(self, key, default=""):
        return self._current()[1].get(key, default)

    @Property(bool, notify=changed)
    def available(self):
        return bool(self._current()[0])

    @Property(bool, notify=changed)
    def playing(self):
        return self._get("status") == "Playing"

    @Property(str, notify=changed)
    def title(self):
        return self._get("title")

    @Property(str, notify=changed)
    def artist(self):
        return self._get("artist")

    @Property(str, notify=changed)
    def artUrl(self):
        return self._get("art")

    @Property(str, notify=changed)
    def identity(self):
        return self._get("identity") or self._current()[0][len(MPRIS_PREFIX):].split(".")[0]

    @Property(str, notify=changed)
    def icon(self):
        desktop = self._get("desktop")
        entry = self.apps.get(desktop) if self.apps is not None and desktop else None
        return (entry.icon if entry and entry.icon else "") or "multimedia-player"

    @Property(bool, notify=changed)
    def canNext(self):
        return bool(self._get("canNext", False))

    @Property(bool, notify=changed)
    def canPrevious(self):
        return bool(self._get("canPrevious", False))

    @Property(bool, notify=changed)
    def canRaise(self):
        return bool(self._get("canRaise", False))

    def players(self):
        """[(bus name, what to call it)] for the menu."""
        return [(n, p.get("identity") or n[len(MPRIS_PREFIX):]) for n, p in sorted(self._players.items())
                if p.get("status") in ("Playing", "Paused") or p.get("title")]

    def current_name(self):
        return self._current()[0]

    def _call(self, method, iface=PLAYER):
        name = self._current()[0]
        if name:
            msg = QDBusMessage.createMethodCall(name, MPRIS_PATH, iface, method)
            QDBusConnection.sessionBus().asyncCall(msg)

    @Slot()
    def playPause(self):
        self._call("PlayPause")

    @Slot()
    def next(self):
        self._call("Next")

    @Slot()
    def previous(self):
        self._call("Previous")

    @Slot()
    def raisePlayer(self):
        self._call("Raise", "org.mpris.MediaPlayer2")

    @Slot(str)
    def choose(self, name):
        if name in self._players:
            self._chosen = name
            self.changed.emit()
