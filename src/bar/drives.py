"""Removable drives for the bar: the USB sticks, SD cards and external disks
UDisks2 knows about, and mounting, opening and safely removing them. The system
asks for a password itself (polkit) when a drive needs one."""
import os

from PySide6.QtCore import Property, QObject, QProcess, QTimer, QUrl, Signal, Slot, SLOT
from PySide6.QtDBus import QDBusConnection, QDBusMessage

from busctl import busctl

UDISKS = "org.freedesktop.UDisks2"
ROOT = "/org/freedesktop/UDisks2"
MANAGER = "org.freedesktop.DBus.ObjectManager"
BLOCK = "org.freedesktop.UDisks2.Block"
FILESYSTEM = "org.freedesktop.UDisks2.Filesystem"
DRIVE = "org.freedesktop.UDisks2.Drive"
# tests run a stand-in UDisks2 on the session bus
ON_SESSION = os.environ.get("BOREALIS_BAR_UDISKS") == "session"


def _text(value):
    """UDisks2 byte strings ("ay", NUL-terminated) -> str."""
    if isinstance(value, list):
        return bytes(value).rstrip(b"\0").decode(errors="replace")
    return str(value or "")


def removable(objects):
    """GetManagedObjects -> the filesystems on removable drives, as the bar shows them."""
    drives = {path: ifaces[DRIVE] for path, ifaces in objects.items() if DRIVE in ifaces}
    out = []
    for path, ifaces in sorted(objects.items()):
        block, fs = ifaces.get(BLOCK), ifaces.get(FILESYSTEM)
        if not block or fs is None or block.get("HintIgnore") or block.get("HintSystem"):
            continue
        drive = drives.get(block.get("Drive"), {})
        if not (drive.get("Removable") or drive.get("MediaRemovable") or drive.get("Ejectable")
                or drive.get("ConnectionBus") == "usb"):
            continue
        mounts = [_text(m) for m in fs.get("MountPoints") or []]
        device = _text(block.get("PreferredDevice") or block.get("Device"))
        out.append({
            "path": path,
            "drive": block.get("Drive") or "",
            "label": block.get("IdLabel") or drive.get("Model") or os.path.basename(device) or "Drive",
            "device": device,
            "size": int(block.get("Size") or 0),
            "mounted": bool(mounts),
            "mountPoint": mounts[0] if mounts else "",
            "canPowerOff": bool(drive.get("CanPowerOff")),
            "ejectable": bool(drive.get("Ejectable")),
        })
    return out


class Drives(QObject):
    changed = Signal()
    failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._drives = []
        self._flag = "--user" if ON_SESSION else "--system"
        self._later = QTimer(self, singleShot=True, interval=300)
        self._later.timeout.connect(self.refresh)
        bus = QDBusConnection.sessionBus() if ON_SESSION else QDBusConnection.systemBus()
        for signal in ("InterfacesAdded", "InterfacesRemoved"):
            bus.connect(UDISKS, ROOT, MANAGER, signal, self, SLOT("onChanged(QDBusMessage)"))
        bus.connect(UDISKS, "", "org.freedesktop.DBus.Properties", "PropertiesChanged", self,
                    SLOT("onChanged(QDBusMessage)"))
        self.refresh()

    @Slot(QDBusMessage)
    def onChanged(self, _message):
        self._later.start()

    @Slot()
    def refresh(self):
        def done(values):
            objects = values[0] if values else {}
            if isinstance(objects, list):
                objects = objects[0] if objects else {}
            drives = removable(objects if isinstance(objects, dict) else {})
            if drives != self._drives:
                self._drives = drives
                self.changed.emit()
        busctl(self, [self._flag, "--json=short", "call", UDISKS, ROOT, MANAGER, "GetManagedObjects"], done,
               failed=lambda _err: None)

    @Property("QVariantList", notify=changed)
    def drives(self):
        return self._drives

    def _find(self, path):
        return next((d for d in self._drives if d["path"] == path), None)

    def _call(self, path, iface, method, then=None):
        busctl(self, [self._flag, "call", UDISKS, path, iface, method, "a{sv}", "0"],
               lambda _values: (self._later.start(), then and then()),
               failed=lambda err: self.failed.emit(err))

    @Slot(str)
    def open(self, path):
        drive = self._find(path)
        if drive is None:
            return
        if drive["mounted"]:
            QProcess.startDetached("kioclient", ["exec", QUrl.fromLocalFile(drive["mountPoint"]).toString()])
            return

        def opened(values):
            mount_point = values[0] if values and isinstance(values[0], str) else ""
            self._later.start()
            if mount_point:
                QProcess.startDetached("kioclient", ["exec", QUrl.fromLocalFile(mount_point).toString()])
        busctl(self, [self._flag, "--json=short", "call", UDISKS, path, FILESYSTEM, "Mount", "a{sv}", "0"], opened,
               failed=lambda err: self.failed.emit(err))

    @Slot(str)
    def remove(self, path):
        """Unmount, then power the drive off (or eject it) so it can be pulled out."""
        drive = self._find(path)
        if drive is None:
            return

        def power_off():
            if drive["canPowerOff"]:
                self._call(drive["drive"], DRIVE, "PowerOff")
            elif drive["ejectable"]:
                self._call(drive["drive"], DRIVE, "Eject")
        if drive["mounted"]:
            self._call(path, FILESYSTEM, "Unmount", then=power_off)
        else:
            power_off()
