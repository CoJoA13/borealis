"""The row of icons: pinned apps, a divider, apps that are open but not pinned,
another divider, the trash. One row per app, its windows attached."""
import itertools
import os
import time

from PySide6.QtCore import Property, QAbstractListModel, QByteArray, QModelIndex, QTimer, Qt, Signal
from PySide6.QtGui import QIcon

from apps import FALLBACK_ICON
from stacks import folder_icon, resolve as resolve_stack

ROLES = ("kind", "key", "appId", "name", "icon", "pinned", "windows", "windowCount",
         "active", "attention", "launching", "hasEntry", "badge", "progress",
         "stackPath", "stackCount", "preview", "display")
DEFAULTS = {"kind": "", "key": "", "appId": "", "name": "", "icon": "", "pinned": False,
            "windows": [], "windowCount": 0, "active": False, "attention": False,
            "launching": False, "hasEntry": False, "badge": 0, "progress": -1.0,
            "stackPath": "", "stackCount": 0, "preview": [], "display": ""}
LAUNCH_TIMEOUT = 12.0


class DockModel(QAbstractListModel):
    offsetsChanged = Signal()
    countChanged = Signal()

    def __init__(self, settings, apps, bridge, badges=None, stacks=None, parent=None):
        super().__init__(parent)
        self.settings, self.apps, self.bridge = settings, apps, bridge
        self.badges, self.stacks = badges, stacks
        self.items = []
        self.pins = []                 # [(spec as saved, resolved entry id)]
        self._preview = None           # pinned order while an icon is being dragged
        self._launching = {}           # entry id -> (deadline, windows it had)
        self._first_seen = {}
        self._counter = itertools.count()
        self._offsets, self._length = [], 0.0
        self._expiry = QTimer(self, singleShot=True)
        self._expiry.setTimerType(Qt.TimerType.PreciseTimer)
        self._expiry.timeout.connect(self.rebuild)
        settings.changed.connect(self.rebuild)
        apps.changed.connect(self.rebuild)
        bridge.windowsChanged.connect(self.rebuild)
        if badges is not None:
            badges.changed.connect(self.rebuild)
        if stacks is not None:
            stacks.changed.connect(self.rebuild)
        self.rebuild()

    # --- Qt model ---------------------------------------------------------
    def roleNames(self):
        base = int(Qt.ItemDataRole.UserRole)
        return {base + i: QByteArray(name.encode()) for i, name in enumerate(ROLES)}

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.items)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self.items):
            return None
        i = int(role) - int(Qt.ItemDataRole.UserRole)
        if not 0 <= i < len(ROLES):
            return None
        return self.items[index.row()].get(ROLES[i], DEFAULTS[ROLES[i]])

    @Property(int, notify=countChanged)
    def count(self):
        return len(self.items)

    @Property("QVariantList", notify=offsetsChanged)
    def restOffsets(self):
        return self._offsets

    @Property(float, notify=offsetsChanged)
    def restLength(self):
        return self._length

    @Property(int, notify=offsetsChanged)
    def dividerSpan(self):
        return max(2, int(self.settings.get("spacing")))

    def item(self, row):
        return self.items[row] if 0 <= row < len(self.items) else None

    # --- building ---------------------------------------------------------
    def windows_of(self, entry_id):
        return next((it["windows"] for it in self.items if it.get("appId") == entry_id), [])

    def set_launching(self, entry_id):
        if os.environ.get("BOREALIS_DOCK_DEBUG") == "1":
            print("dock: launching", entry_id, flush=True)
        self._launching[entry_id] = (time.monotonic() + LAUNCH_TIMEOUT, len(self.windows_of(entry_id)))
        self.rebuild()

    def preview_order(self, ids_in_order):
        self._preview = list(ids_in_order)
        self.rebuild()

    def end_preview(self):
        order, self._preview = self._preview, None
        return order

    def _resolve_pins(self):
        pins, seen = [], set()
        for spec in self.settings.get("pinned"):
            entry_id = self.apps.resolve(spec)
            if entry_id and entry_id not in seen:
                seen.add(entry_id)
                pins.append((spec, entry_id))
        return pins

    def _icon_for(self, entry, windows):
        if entry and entry.icon:
            return entry.icon
        for w in windows:
            for name in (w.get("cls", ""), w.get("app", "")):
                if name and QIcon.hasThemeIcon(name.lower()):
                    return name.lower()
        return FALLBACK_ICON

    def _app(self, entry_id, pinned, windows):
        entry = self.apps.get(entry_id)
        windows = sorted(windows, key=lambda w: w.get("stack", 0))
        launching = False
        if entry_id in self._launching:
            deadline, had = self._launching[entry_id]
            if time.monotonic() > deadline or len(windows) > had:
                del self._launching[entry_id]
            else:
                launching = True
        name = entry.name if entry else (windows[-1].get("caption") if windows else entry_id)
        count, progress, urgent = (self.badges.get(entry_id)
                                   if self.badges is not None and self.settings.get("badges")
                                   else (0, -1.0, False))
        return {"kind": "app", "key": "app:" + entry_id, "appId": entry_id, "name": name or entry_id,
                "icon": self._icon_for(entry, windows), "pinned": pinned, "windows": windows,
                "windowCount": len(windows), "active": any(w.get("active") for w in windows),
                "attention": any(w.get("attention") for w in windows) or urgent, "launching": launching,
                "hasEntry": entry is not None, "badge": count, "progress": progress}

    def _expire_launches(self):
        """Check again when the soonest launch runs out (a precise timer: coarse
        ones may fire early, and then nothing would ever stop the bounce)."""
        if self._launching:
            wait = min(deadline for deadline, _had in self._launching.values()) - time.monotonic()
            self._expiry.start(max(0, int(wait * 1000)) + 50)

    def rebuild(self):
        self.pins = self._resolve_pins()
        order = self._preview if self._preview is not None else [i for _s, i in self.pins]
        groups = {}
        for w in self.bridge.windows:
            entry = self.apps.match(w.get("app", ""), w.get("cls", ""), w.get("name", ""))
            key = entry.id if entry else "window:" + (w.get("cls") or w.get("app") or w["id"])
            groups.setdefault(key, []).append(w)
        items = [self._app(entry_id, True, groups.pop(entry_id, [])) for entry_id in order]
        for key in groups:
            self._first_seen.setdefault(key, next(self._counter))
        for key in [k for k in self._first_seen if k not in groups]:
            del self._first_seen[key]
        opened = [self._app(key, False, groups[key]) for key in sorted(groups, key=self._first_seen.get)]
        divider = self.settings.get("divider")
        if opened:
            if divider:
                items.append({"kind": "divider", "key": "divider:open"})
            items += opened
        end = []
        stacks = self.settings.get("stacks") if self.stacks is not None else []
        if self.stacks is not None:
            self.stacks.watch([st["path"] for st in stacks])
        for st in stacks:
            entries = self.stacks.entries(st["path"], st["sort"])
            real = resolve_stack(st["path"])
            end.append({"kind": "stack", "key": "stack:" + st["path"],
                        "name": os.path.basename(real.rstrip("/")) or real, "icon": folder_icon(st["path"]),
                        "stackPath": st["path"], "stackCount": len(entries), "display": st["display"],
                        "preview": [{"icon": e["icon"], "url": e["url"], "image": e["image"]}
                                    for e in entries[:3]]})
        if self.settings.get("showTrash"):
            end.append({"kind": "trash", "key": "trash", "name": "Trash", "icon": "user-trash"})
        if end:
            if divider:
                items.append({"kind": "divider", "key": "divider:end"})
            items += end
        self._offsets_for(items)
        self._apply(items)
        self._expire_launches()

    def _offsets_for(self, items):
        size, gap = int(self.settings.get("iconSize")), int(self.settings.get("spacing"))
        span = max(2, gap)
        offsets, pos = [], 0.0
        for it in items:
            offsets.append(pos)
            pos += (span if it["kind"] == "divider" else size) + gap
        length = max(0.0, pos - gap) if items else 0.0
        if offsets != self._offsets or length != self._length:
            self._offsets, self._length = offsets, length
            self.offsetsChanged.emit()

    def _apply(self, new):
        """Turn the current rows into `new` with removes, moves and inserts, so
        QML keeps (and animates) the delegates of rows that merely moved."""
        before = len(self.items)
        keep = {it["key"] for it in new}
        for row in range(len(self.items) - 1, -1, -1):
            if self.items[row]["key"] not in keep:
                self.beginRemoveRows(QModelIndex(), row, row)
                del self.items[row]
                self.endRemoveRows()
        for i, it in enumerate(new):
            if i < len(self.items) and self.items[i]["key"] == it["key"]:
                if self.items[i] != it:
                    self.items[i] = it
                    self.dataChanged.emit(self.index(i), self.index(i))
                continue
            j = next((k for k in range(i + 1, len(self.items)) if self.items[k]["key"] == it["key"]), -1)
            if j >= 0:
                self.beginMoveRows(QModelIndex(), j, j, QModelIndex(), i)
                self.items.insert(i, self.items.pop(j))
                self.endMoveRows()
                if self.items[i] != it:
                    self.items[i] = it
                    self.dataChanged.emit(self.index(i), self.index(i))
            else:
                self.beginInsertRows(QModelIndex(), i, i)
                self.items.insert(i, it)
                self.endInsertRows()
        if len(self.items) != before:
            self.countChanged.emit()
