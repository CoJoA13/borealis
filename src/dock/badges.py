"""Counts, progress bars and urgency that apps publish for their launcher icon.

This is the Unity LauncherEntry D-Bus API: apps emit
com.canonical.Unity.LauncherEntry.Update(app_uri, properties) with any of
count, count-visible, progress, progress-visible and urgent. Values persist
until the app changes them or leaves the bus.
"""
import os
from urllib.parse import unquote

from PySide6.QtCore import QObject, Signal, Slot, SLOT
from PySide6.QtDBus import QDBusConnection, QDBusMessage

INTERFACE = "com.canonical.Unity.LauncherEntry"
PROPERTIES = {"count": ("count", int), "count-visible": ("countVisible", bool),
              "progress": ("progress", float), "progress-visible": ("progressVisible", bool),
              "urgent": ("urgent", bool)}


def entry_id_from_uri(uri):
    """application://org.kde.dolphin.desktop (or a file:// path) -> org.kde.dolphin"""
    uri = str(uri)
    if uri.startswith("application://"):
        name = uri[len("application://"):]
    elif uri.startswith("file://"):
        name = os.path.basename(unquote(uri[len("file://"):]))
    else:
        name = uri
    return name[:-8] if name.endswith(".desktop") else name


class Badges(QObject):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries = {}          # entry id -> latest properties
        self._senders = {}          # entry id -> the bus name that sent them
        bus = QDBusConnection.sessionBus()
        # some apps only publish while a launcher is known to listen
        bus.registerService("com.canonical.Unity")
        bus.connect("", "", INTERFACE, "Update", self, SLOT("onSender(QDBusMessage)"))
        bus.connect("", "", INTERFACE, "Update", "sa{sv}", self, SLOT("onUpdate(QString,QVariantMap)"))
        bus.connect("org.freedesktop.DBus", "/org/freedesktop/DBus", "org.freedesktop.DBus",
                    "NameOwnerChanged", "sss", self, SLOT("onOwnerChanged(QString,QString,QString)"))

    @Slot(QDBusMessage)
    def onSender(self, message):
        args = message.arguments()
        if args and isinstance(args[0], str):
            self._senders[entry_id_from_uri(args[0])] = message.service()

    @Slot(str, "QVariantMap")
    def onUpdate(self, uri, properties):
        entry = self._entries.setdefault(entry_id_from_uri(uri), {
            "count": 0, "countVisible": False, "progress": 0.0, "progressVisible": False, "urgent": False})
        for key, value in dict(properties).items():
            if key in PROPERTIES:
                name, cast = PROPERTIES[key]
                try:
                    entry[name] = cast(value)
                except (TypeError, ValueError):
                    pass
        self.changed.emit()

    @Slot(str, str, str)
    def onOwnerChanged(self, name, _old, new):
        if new or not name.startswith(":"):
            return
        gone = [k for k, sender in self._senders.items() if sender == name]
        for key in gone:
            self._entries.pop(key, None)
            self._senders.pop(key, None)
        if gone:
            self.changed.emit()

    def get(self, entry_id):
        """(count, progress, urgent) for an app; 0 / -1 mean nothing to show."""
        entry = self._entries.get(entry_id)
        if entry is None:
            lower = entry_id.lower()
            entry = next((v for k, v in self._entries.items() if k.lower() == lower), None)
        if entry is None:
            return 0, -1.0, False
        count = entry["count"] if entry["countVisible"] else 0
        progress = min(1.0, max(0.0, entry["progress"])) if entry["progressVisible"] else -1.0
        return max(0, count), progress, entry["urgent"]
