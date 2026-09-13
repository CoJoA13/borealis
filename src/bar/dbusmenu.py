"""A DBusMenu client (com.canonical.dbusmenu), for the menus of the app in
front and of tray icons. Layouts are read through busctl, which copes with
their nested variants, and turned into the entries the bar's menus draw:

    {"type": "command" | "submenu" | "separator", "key": "12", "text": "Open…",
     "icon": "document-open", "iconData": "data:…", "check": True, "radio": False,
     "shortcut": "Ctrl+O", "enabled": True, "children": [...]}
"""
import base64

from PySide6.QtCore import QObject, Signal, Slot, SLOT
from PySide6.QtDBus import QDBusConnection, QDBusMessage

from busctl import busctl

IFACE = "com.canonical.dbusmenu"
KEY_NAMES = {"Control": "Ctrl", "Super": "Meta"}


def strip_mnemonic(label):
    """'_File' -> 'File'; a doubled underscore stays as one."""
    return str(label).replace("__", "\0").replace("_", "").replace("\0", "_")


def entries(node):
    """A layout node [id, {properties}, [children]] -> its children as entries."""
    out = []
    children = node[2] if isinstance(node, list) and len(node) > 2 else []
    for child in children:
        if not isinstance(child, list) or len(child) < 3:
            continue
        ident, props = child[0], child[1] if isinstance(child[1], dict) else {}
        if props.get("visible") is False:
            continue
        if props.get("type") == "separator":
            if out and out[-1]["type"] != "separator":
                out.append({"type": "separator"})
            continue
        submenu = props.get("children-display") == "submenu" or bool(child[2])
        entry = {
            "type": "submenu" if submenu else "command",
            "key": str(ident),
            "text": strip_mnemonic(props.get("label", "")),
            "icon": str(props.get("icon-name", "") or ""),
            "enabled": props.get("enabled", True) is not False,
        }
        data = props.get("icon-data")
        if data:
            entry["iconData"] = "data:image/png;base64," + base64.b64encode(bytes(data)).decode()
        if props.get("toggle-type") in ("checkmark", "radio"):
            entry["check"] = props.get("toggle-state", 0) == 1
            entry["radio"] = props.get("toggle-type") == "radio"
        shortcut = props.get("shortcut")
        if shortcut:
            entry["shortcut"] = ", ".join("+".join(KEY_NAMES.get(k, k) for k in keys) for keys in shortcut)
        if submenu:
            entry["children"] = entries(child)
        out.append(entry)
    while out and out[-1]["type"] == "separator":
        out.pop()
    return out


class DBusMenu(QObject):
    updated = Signal()          # the app changed its menu

    def __init__(self, service, path, parent=None):
        super().__init__(parent)
        self.service, self.path = service, path
        bus = QDBusConnection.sessionBus()
        for signal in ("LayoutUpdated", "ItemsPropertiesUpdated"):
            bus.connect(service, path, IFACE, signal, self, SLOT("onUpdated(QDBusMessage)"))

    def close(self):
        bus = QDBusConnection.sessionBus()
        for signal in ("LayoutUpdated", "ItemsPropertiesUpdated"):
            bus.disconnect(self.service, self.path, IFACE, signal, self, SLOT("onUpdated(QDBusMessage)"))
        self.deleteLater()

    @Slot(QDBusMessage)
    def onUpdated(self, _message):
        self.updated.emit()

    def _call(self, args, done=None):
        # "--" so busctl doesn't take a -1 argument for an option
        return busctl(self, ["--user", "--json=short", "call", "--", self.service, self.path, IFACE] + args, done)

    def fetch(self, parent_id, done, depth=-1):
        """Lets the app fill the menu in, then hands `done` its entries."""
        def layout(_values):
            self._call(["GetLayout", "iias", str(parent_id), str(depth), "0"],
                       lambda values: done(entries(values[0][1]) if values and len(values[0]) > 1 else []))
        self._call(["AboutToShow", "i", str(parent_id)], layout)

    def activate(self, ident):
        self._call(["Event", "isvu", str(ident), "clicked", "s", "", "0"])

    def hovered(self, ident):
        self._call(["Event", "isvu", str(ident), "hovered", "s", "", "0"])
