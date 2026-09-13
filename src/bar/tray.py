"""The tray: a StatusNotifierHost showing the icons apps put there. kded keeps
the list of items (org.kde.StatusNotifierWatcher); each item describes itself
through its properties and offers its menu over DBusMenu."""
import os

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot, SLOT
from PySide6.QtDBus import QDBusConnection, QDBusMessage, QDBusServiceWatcher
from PySide6.QtGui import QImage
from PySide6.QtQuick import QQuickImageProvider

from busctl import busctl
from dbusmenu import DBusMenu

WATCHER = ("org.kde.StatusNotifierWatcher", "/StatusNotifierWatcher", "org.kde.StatusNotifierWatcher")
ITEM = "org.kde.StatusNotifierItem"
ITEM_SIGNALS = ("NewIcon", "NewAttentionIcon", "NewOverlayIcon", "NewToolTip", "NewTitle", "NewStatus", "NewMenu")


def pixmap_image(pixmaps, size=32):
    """An item's IconPixmap (width, height, ARGB32 in network byte order) the
    closest to `size`, as a QImage."""
    best = None
    for entry in pixmaps or []:
        if not isinstance(entry, list) or len(entry) < 3:
            continue
        w, h, data = int(entry[0]), int(entry[1]), bytes(entry[2])
        if w <= 0 or h <= 0 or len(data) < w * h * 4:
            continue
        if best is None or abs(w - size) < abs(best[0] - size):
            best = (w, h, data)
    if best is None:
        return None
    w, h, data = best
    native = bytearray(w * h * 4)
    native[0::4], native[1::4], native[2::4], native[3::4] = data[3::4], data[2::4], data[1::4], data[0::4]
    return QImage(bytes(native), w, h, QImage.Format.Format_ARGB32).copy()


def theme_icon(theme_path, name):
    """An icon an app ships in its own folder (IconThemePath)."""
    if not theme_path or not name:
        return ""
    for root, _dirs, files in os.walk(theme_path):
        for ext in (".svg", ".png"):
            if name + ext in files:
                return "file://" + os.path.join(root, name + ext)
    return ""


class TrayImages(QQuickImageProvider):
    """image://tray/<slot>/<revision>: pixmaps apps send instead of icon names."""

    def __init__(self):
        super().__init__(QQuickImageProvider.ImageType.Image)
        self.images = {}

    def requestImage(self, ident, size, requested):
        image = self.images.get(ident.split("/", 1)[0])
        return image if image is not None else QImage(1, 1, QImage.Format.Format_ARGB32)


class Tray(QObject):
    changed = Signal()
    menuReady = Signal(str, "QVariantList")        # item key, entries

    def __init__(self, parent=None):
        super().__init__(parent)
        self.images = TrayImages()
        self._items = {}
        self._order = []
        self._menus = {}
        self._slots = {}
        self._revision = 0
        self._dirty = set()
        self._reread = QTimer(self, singleShot=True, interval=120)
        self._reread.timeout.connect(self._read_dirty)
        bus = QDBusConnection.sessionBus()
        self._name = f"org.kde.StatusNotifierHost-{os.getpid()}"
        bus.registerService(self._name)
        self._watch = QDBusServiceWatcher(WATCHER[0], bus, QDBusServiceWatcher.WatchModeFlag.WatchForRegistration, self)
        self._watch.serviceRegistered.connect(lambda *_: self._register())
        bus.connect(WATCHER[0], WATCHER[1], WATCHER[2], "StatusNotifierItemRegistered", "s", self,
                    SLOT("onRegistered(QString)"))
        bus.connect(WATCHER[0], WATCHER[1], WATCHER[2], "StatusNotifierItemUnregistered", "s", self,
                    SLOT("onUnregistered(QString)"))
        self._register()

    # --- the list ------------------------------------------------------------
    def _register(self):
        busctl(self, ["--user", "call", *WATCHER, "RegisterStatusNotifierHost", "s", self._name],
               lambda _values: self._list(), failed=lambda _err: None)

    def _list(self):
        busctl(self, ["--user", "--json=short", "get-property", *WATCHER, "RegisteredStatusNotifierItems"],
               lambda values: self._sync(values[0] if values and isinstance(values[0], list) else []))

    def _sync(self, keys):
        for key in keys:
            self._add(key)
        for key in [k for k in self._order if k not in keys]:
            self._remove(key)

    @Slot(str)
    def onRegistered(self, key):
        self._add(key)

    @Slot(str)
    def onUnregistered(self, key):
        self._remove(key)

    @staticmethod
    def _split(key):
        service, sep, path = key.partition("/")
        return service, ("/" + path) if sep else "/StatusNotifierItem"

    def _add(self, key):
        if key in self._items:
            return
        service, path = self._split(key)
        self._slots[key] = f"i{len(self._slots)}"
        self._items[key] = {"key": key, "service": service, "path": path, "id": "", "title": "",
                            "status": "Active", "iconName": "", "iconUrl": "", "overlay": "",
                            "tooltip": "", "tooltipText": "", "itemIsMenu": False, "menu": ""}
        self._order.append(key)
        bus = QDBusConnection.sessionBus()
        for signal in ITEM_SIGNALS:
            bus.connect(service, path, ITEM, signal, self, SLOT("onItemChanged(QDBusMessage)"))
        self._read(key)

    def _remove(self, key):
        item = self._items.pop(key, None)
        if item is None:
            return
        self._order.remove(key)
        bus = QDBusConnection.sessionBus()
        for signal in ITEM_SIGNALS:
            bus.disconnect(item["service"], item["path"], ITEM, signal, self, SLOT("onItemChanged(QDBusMessage)"))
        menu = self._menus.pop(key, None)
        if menu is not None:
            menu.close()
        self.images.images.pop(self._slots.get(key, ""), None)
        self.changed.emit()

    @Slot(QDBusMessage)
    def onItemChanged(self, message):
        # the signal names the sender's unique name, not the name the item
        # registered with: read every item on that path again, soon
        self._dirty.update(k for k, item in self._items.items() if item["path"] == message.path())
        self._reread.start()

    def _read_dirty(self):
        dirty, self._dirty = self._dirty, set()
        for key in dirty:
            self._read(key)

    def _read(self, key):
        item = self._items.get(key)
        if item is None:
            return
        busctl(self, ["--user", "--json=short", "call", item["service"], item["path"],
                      "org.freedesktop.DBus.Properties", "GetAll", "s", ITEM],
               lambda values: self._update(key, values[0][0] if values and values[0] else None),
               failed=lambda _err: None)

    def _update(self, key, props):
        item = self._items.get(key)
        if item is None or not isinstance(props, dict):
            return
        status = str(props.get("Status") or "Active")
        attention = status == "NeedsAttention"
        name = str((attention and props.get("AttentionIconName")) or props.get("IconName") or "")
        pixmaps = (attention and props.get("AttentionIconPixmap")) or props.get("IconPixmap")
        url = theme_icon(str(props.get("IconThemePath") or ""), name)
        if not name and not url:
            image = pixmap_image(pixmaps)
            if image is not None:
                slot = self._slots[key]
                self.images.images[slot] = image
                self._revision += 1
                url = f"image://tray/{slot}/{self._revision}"
        tooltip = props.get("ToolTip")
        tip_title = str(tooltip[2]) if isinstance(tooltip, list) and len(tooltip) > 3 else ""
        tip_text = str(tooltip[3]) if isinstance(tooltip, list) and len(tooltip) > 3 else ""
        item.update({
            "id": str(props.get("Id") or ""), "title": str(props.get("Title") or ""), "status": status,
            "iconName": name, "iconUrl": url, "overlay": str(props.get("OverlayIconName") or ""),
            "tooltip": tip_title or str(props.get("Title") or ""), "tooltipText": tip_text,
            "itemIsMenu": bool(props.get("ItemIsMenu")), "menu": str(props.get("Menu") or ""),
        })
        self.changed.emit()

    @Property("QVariantList", notify=changed)
    def items(self):
        return [dict(self._items[k]) for k in self._order if self._items[k]["status"] != "Passive"]

    # --- what clicks do ------------------------------------------------------
    def _item_call(self, key, method, signature, *args):
        item = self._items.get(key)
        if item is not None:
            busctl(self, ["--user", "call", "--", item["service"], item["path"], ITEM, method, signature]
                   + [str(a) for a in args], failed=lambda _err: None)

    @Slot(str, int, int)
    def activate(self, key, x, y):
        item = self._items.get(key)
        if item is None:
            return
        if item["itemIsMenu"] and item["menu"]:
            self.requestMenu(key)
        else:
            self._item_call(key, "Activate", "ii", x, y)

    @Slot(str, int, int)
    def secondaryActivate(self, key, x, y):
        self._item_call(key, "SecondaryActivate", "ii", x, y)

    @Slot(str, int, str)
    def scroll(self, key, delta, orientation):
        self._item_call(key, "Scroll", "is", delta, orientation)

    @Slot(str)
    def requestMenu(self, key):
        item = self._items.get(key)
        if item is None:
            return
        if not item["menu"]:
            self._item_call(key, "ContextMenu", "ii", 0, 0)
            return
        menu = self._menus.get(key)
        if menu is None or menu.path != item["menu"]:
            if menu is not None:
                menu.close()
            menu = self._menus[key] = DBusMenu(item["service"], item["menu"], parent=self)
        menu.fetch(0, lambda entries: self.menuReady.emit(key, entries))

    def open_submenu(self, key, ident, done):
        menu = self._menus.get(key)
        if menu is not None:
            menu.fetch(int(ident), done)

    @Slot(str, str)
    def activateEntry(self, key, ident):
        menu = self._menus.get(key)
        if menu is not None:
            menu.activate(int(ident))
