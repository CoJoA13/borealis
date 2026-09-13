"""What the QML sees as `dock`: the model, the settings, and every action."""
import os
import shutil

from PySide6.QtCore import (Property, QFileSystemWatcher, QObject, QProcess, QRectF, QTimer,
                            QUrl, Signal, Slot)
from PySide6.QtDBus import QDBusConnection, QDBusMessage
from PySide6.QtGui import QRegion

import effects
import ids
import presets as dockpresets
import stacks as stackfolders

PROFILE_NAMES = {"power-saver": "Power Save", "balanced": "Balanced", "performance": "Performance"}


def _data_home():
    return os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")


class Controller(QObject):
    screensChanged = Signal()
    trashChanged = Signal()
    windowsRevisionChanged = Signal()
    menuOpenChanged = Signal()
    bridgeAliveChanged = Signal()
    launchpadChanged = Signal()
    launchpadDragChanged = Signal()
    previewChanged = Signal()
    menuRequested = Signal("QVariantList", int, QObject, float, float, float, float, str)
    # entries, title, folder, view, row, screen, x, y, w, h, edge
    stackRequested = Signal("QVariantList", str, str, str, int, QObject, float, float, float, float, str)
    # screen, x, y, w, h, edge
    calendarRequested = Signal(QObject, float, float, float, float, str)
    testMenuRequested = Signal(int)

    def __init__(self, app, settings, apps, bridge, model, stacks=None, battery=None, media=None,
                 launchpad=None, parent=None):
        super().__init__(parent)
        self.app, self.apps, self.bridge, self.stacks = app, apps, bridge, stacks
        self._shortcuts = None
        self._settings_obj, self._model_obj = settings, model
        self._battery_obj, self._media_obj, self._grid_obj = battery, media, launchpad
        self._revision = 0
        self._menu_open = False
        self._last_menu = None
        self._launchpad_open = False
        self._launchpad_dragging = False
        self._launchpad_screen = None
        self._preview_visible = False
        self._preview_hovered = False
        self._preview_row = -1
        self._window_order = {}             # window id -> when the dock first saw it
        self._window_counter = 0
        bridge.windowsChanged.connect(self._windows_changed)
        bridge.aliveChanged.connect(self.bridgeAliveChanged)
        settings.changed.connect(self._settings_changed)
        for sig in (app.screenAdded, app.screenRemoved, app.primaryScreenChanged):
            sig.connect(lambda *_: self.screensChanged.emit())
        self._layout = self._layout_key()
        try:
            self._pointer = float(os.environ.get("BOREALIS_DOCK_POINTER", "-1"))
        except ValueError:
            self._pointer = -1.0
        # trash
        self._trash_full = False
        self._trash_watch = QFileSystemWatcher(self)
        self._trash_watch.directoryChanged.connect(lambda *_: self._check_trash())
        self._check_trash()
        # surfaces: masks and blur, coalesced to one update per frame
        self._pending = {}
        self._regions = {}
        self._flush = QTimer(self, singleShot=True, interval=16)
        self._flush.timeout.connect(self._apply_surfaces)
        self._activate_widgets()

    # --- state for QML ------------------------------------------------------
    def _get_model(self):
        return self._model_obj

    def _get_settings(self):
        return self._settings_obj

    def _get_battery(self):
        return self._battery_obj

    def _get_media(self):
        return self._media_obj

    def _get_grid(self):
        return self._grid_obj

    model = Property(QObject, _get_model, constant=True)
    settings = Property(QObject, _get_settings, constant=True)
    battery = Property(QObject, _get_battery, constant=True)
    media = Property(QObject, _get_media, constant=True)
    launchpadApps = Property(QObject, _get_grid, constant=True)

    def _layout_key(self):
        return (self.settings.get("position"), self.settings.get("screen"))

    def push_config(self):
        """What the KWin bridge needs to know: whether to hold Meta+1…9."""
        self._shortcuts = bool(self.settings.get("shortcuts"))
        self.claim_task_manager_keys(self._shortcuts)
        self.bridge.send("config", shortcuts=self._shortcuts)

    @staticmethod
    def claim_task_manager_keys(claim):
        """plasmashell registers Meta+1…9 for a task manager whether or not one
        exists, and a key held twice goes to the first owner. Setting those to
        "none" is a user choice Plasma keeps across restarts; turning the dock's
        shortcuts off hands the keys back."""
        for n in range(1, 11):
            action = [f"activate task manager entry {n}", f"Activate Task Manager Entry {n}"]
            keys = ["0"] if claim or n == 10 else ["1", "1", str(0x10000000 | (0x30 + n))]
            QProcess.startDetached("busctl", ["--user", "call", "org.kde.kglobalaccel", "/kglobalaccel",
                                              "org.kde.KGlobalAccel", "setForeignShortcutKeys", "asa(ai)",
                                              "4", "plasmashell", action[0], "plasmashell", action[1]] + keys)

    def _activate_widgets(self):
        kinds = {w["type"] for w in self.settings.get("widgets")}
        if self._battery_obj is not None:
            self._battery_obj.set_active("battery" in kinds)
        if self._media_obj is not None:
            self._media_obj.set_active("media" in kinds)

    def _settings_changed(self):
        if bool(self.settings.get("shortcuts")) != self._shortcuts:
            self.push_config()
        self._activate_widgets()
        if not self.settings.get("previews"):
            self.previewHide()
        key = self._layout_key()
        if key != self._layout:
            self._layout = key
            self.screensChanged.emit()          # new surfaces for a new edge or screen

    @Property("QVariantList", notify=screensChanged)
    def screens(self):
        if self.settings.get("screen") == "all":
            return list(self.app.screens())
        primary = self.app.primaryScreen()
        return [primary] if primary else []

    @Property(bool, notify=bridgeAliveChanged)
    def bridgeAlive(self):
        return self.bridge.alive

    @Property(int, notify=windowsRevisionChanged)
    def windowsRevision(self):
        return self._revision

    def _windows_changed(self):
        present = [w["id"] for w in self.bridge.windows]
        for wid in present:
            if wid not in self._window_order:
                self._window_counter += 1
                self._window_order[wid] = self._window_counter
        keep = set(present)
        for wid in [k for k in self._window_order if k not in keep]:
            del self._window_order[wid]
        self._revision += 1
        self.windowsRevisionChanged.emit()

    @Property(float, constant=True)
    def pointerOverride(self):
        return self._pointer

    def _get_menu_open(self):
        return self._menu_open

    def _set_menu_open(self, value):
        if bool(value) != self._menu_open:
            self._menu_open = bool(value)
            self.menuOpenChanged.emit()

    menuOpen = Property(bool, _get_menu_open, _set_menu_open, notify=menuOpenChanged)

    # --- Launchpad ----------------------------------------------------------
    @Property(bool, notify=launchpadChanged)
    def launchpadOpen(self):
        return self._launchpad_open

    @Property(QObject, notify=launchpadChanged)
    def launchpadScreen(self):
        return self._launchpad_screen or self.app.primaryScreen()

    def _get_launchpad_dragging(self):
        return self._launchpad_dragging

    def _set_launchpad_dragging(self, value):
        if bool(value) != self._launchpad_dragging:
            self._launchpad_dragging = bool(value)
            self.launchpadDragChanged.emit()

    # an app is being carried from Launchpad: the dock shows itself to catch it
    launchpadDragging = Property(bool, _get_launchpad_dragging, _set_launchpad_dragging,
                                 notify=launchpadDragChanged)

    def set_launchpad(self, value, screen=None):
        value = bool(value)
        if value == self._launchpad_open:
            return
        self._launchpad_open = value
        if value:
            self._launchpad_screen = screen or self.app.primaryScreen()
            self.previewHide()
            if self._grid_obj is not None:
                self._grid_obj.setQuery("")
        self.launchpadChanged.emit()

    @Slot()
    def toggleLaunchpad(self):
        self.set_launchpad(not self._launchpad_open)

    @Slot(bool)
    def setLaunchpadOpen(self, value):
        self.set_launchpad(value)

    @Slot(QObject)
    def toggleLaunchpadFrom(self, window):
        """The dock's own icon: Launchpad opens on that dock's screen."""
        self.set_launchpad(not self._launchpad_open, window.screen() if hasattr(window, "screen") else None)

    def toggle_launchpad_on(self, screen_name):
        screen = next((s for s in self.app.screens() if s.name() == screen_name), None)
        self.set_launchpad(not self._launchpad_open, screen)

    @Slot(str)
    def launchApp(self, entry_id):
        """From Launchpad: start the app (it bounces in the dock when it's there)."""
        if self.apps.launch(entry_id):
            self.model.set_launching(entry_id)
        self.set_launchpad(False)

    @Slot(str, result="QVariantList")
    def launchpadMenu(self, entry_id):
        entry = self.apps.get(entry_id)
        if entry is None:
            return []
        pinned = entry_id in [i for _s, i in self.model.pins]
        out = [{"type": "command", "key": "open", "icon": entry.icon or "", "text": "Open"}]
        if entry.actions:
            out.append({"type": "separator"})
            out += [{"type": "command", "key": "action:" + a["id"], "text": a["name"], "icon": a["icon"]}
                    for a in entry.actions]
        out += [{"type": "separator"},
                {"type": "command", "key": "unpin" if pinned else "pin",
                 "icon": "window-unpin" if pinned else "window-pin",
                 "text": "Remove from Dock" if pinned else "Keep in Dock"}]
        return out

    @Slot(str, str)
    def launchpadMenuTriggered(self, entry_id, key):
        if key == "open":
            self.launchApp(entry_id)
        elif key.startswith("action:"):
            self.apps.launch(entry_id, action=key[len("action:"):])
            self.set_launchpad(False)
        elif key == "pin":
            self.pin_app(entry_id)
        elif key == "unpin":
            self._save_pins([i for _s, i in self.model.pins if i != entry_id])

    # --- window previews (drawn by the KWin bridge) --------------------------
    @Property(bool, notify=previewChanged)
    def previewVisible(self):
        return self._preview_visible

    @Property(bool, notify=previewChanged)
    def previewHovered(self):
        return self._preview_hovered

    @Property(int, notify=previewChanged)
    def previewRow(self):
        return self._preview_row

    def preview_state(self, visible, hovered):
        visible = bool(visible)
        hovered = bool(hovered) and visible
        if (visible, hovered) == (self._preview_visible, self._preview_hovered):
            return
        self._preview_visible, self._preview_hovered = visible, hovered
        if not visible:
            self._preview_row = -1
        self.previewChanged.emit()

    @Slot(int, QObject, float, float, float, float, str, result=bool)
    def requestPreview(self, row, window, x, y, w, h, edge):
        """x, y, w, h: the icon on the desktop, in logical pixels."""
        it = self.model.item(row)
        if (not self.settings.get("previews") or self._launchpad_open or self._menu_open
                or not it or it["kind"] != "app" or not it["windows"] or not self.bridge.alive):
            return False
        screen = window.screen() if hasattr(window, "screen") else None
        # in the order they were opened, so the previews don't reshuffle
        windows = sorted(it["windows"], key=lambda win: self._window_order.get(win["id"], 0))
        if row != self._preview_row:
            self._preview_row = row
            self.previewChanged.emit()
        self.bridge.send("preview", ids=[win["id"] for win in windows], x=x, y=y, w=w, h=h, edge=edge,
                         output=screen.name() if screen else "")
        return True

    @Slot()
    def previewLeave(self):
        if self._preview_visible or self._preview_row >= 0:
            self.bridge.send("previewLeave")

    @Slot()
    def previewHide(self):
        if self._preview_visible or self._preview_row >= 0:
            self._preview_row = -1
            self.bridge.send("previewHide")
            self.previewChanged.emit()

    # --- trash --------------------------------------------------------------
    def _check_trash(self):
        files = os.path.join(_data_home(), "Trash", "files")
        for path in (files, os.path.dirname(files), _data_home()):
            if os.path.isdir(path) and path not in self._trash_watch.directories():
                self._trash_watch.addPath(path)
        try:
            full = any(True for _ in os.scandir(files))
        except OSError:
            full = False
        if full != self._trash_full:
            self._trash_full = full
            self.trashChanged.emit()

    @Property(bool, notify=trashChanged)
    def trashFull(self):
        return self._trash_full

    # --- clicks -------------------------------------------------------------
    def _launch(self, item, urls=()):
        if item and item.get("hasEntry") and self.apps.launch(item["appId"], urls=urls):
            self.model.set_launching(item["appId"])

    @Slot(int)
    def click(self, row):
        it = self.model.item(row)
        if not it:
            return
        self.previewHide()
        if it["kind"] == "trash":
            return self.openTrash()
        if it["kind"] == "launchpad":
            return self.toggleLaunchpad()
        if it["kind"] == "widget":
            if it["widget"] == "media" and self._media_obj is not None:
                self._media_obj.playPause()
            return
        if it["kind"] != "app":
            return
        windows = it["windows"]
        if not windows:
            return self._launch(it)
        active = [w for w in windows if w.get("active")]
        if not active:
            # bring the app forward: its most recently used window
            return self.bridge.send("activate", id=windows[-1]["id"])
        action = self.settings.get("clickAction")
        if len(windows) > 1 and action == "expose":
            return self.expose([w["id"] for w in windows])
        if len(windows) == 1 or action == "minimize":
            for w in windows:
                if not w.get("minimized"):
                    self.bridge.send("minimize", id=w["id"])
            return
        # several windows and one in front: step to the one used longest ago
        self.bridge.send("activate", id=windows[0]["id"])

    def expose(self, window_ids):
        """App Exposé: KWin's Window View with just these windows."""
        msg = QDBusMessage.createMethodCall("org.kde.KWin.Effect.WindowView1", "/org/kde/KWin/Effect/WindowView1",
                                            "org.kde.KWin.Effect.WindowView1", "activate")
        msg.setArguments([list(window_ids)])
        QDBusConnection.sessionBus().asyncCall(msg)

    @Slot(int)
    def activateSlot(self, number):
        """Meta+1…9: the dock's apps in order, dividers and folders skipped."""
        if not self.settings.get("shortcuts"):
            return
        rows = [row for row, it in enumerate(self.model.items) if it["kind"] == "app"]
        if 1 <= number <= len(rows):
            self.click(rows[number - 1])

    @Slot(str)
    def openUrl(self, url):
        QProcess.startDetached("kioclient", ["exec", url])

    @Slot(str)
    def openStackFolder(self, path):
        QProcess.startDetached("kioclient", ["exec", QUrl.fromLocalFile(stackfolders.resolve(path)).toString()])

    def _stack_settings(self, path):
        return next((st for st in self.settings.get("stacks") if st["path"] == path),
                    {"path": path, "view": "auto", "sort": "added", "display": "stack"})

    def _edit_stacks(self, change):
        self.settings.set("stacks", change([dict(st) for st in self.settings.get("stacks")]))

    @Slot(int, QObject, float, float, float, float, str)
    def requestStack(self, row, window, x, y, w, h, edge):
        it = self.model.item(row)
        if not it or it["kind"] != "stack" or self.stacks is None:
            return
        self.previewHide()
        cfg = self._stack_settings(it["stackPath"])
        entries = self.stacks.entries(it["stackPath"], cfg["sort"])
        screen = window.screen() if hasattr(window, "screen") else self.app.primaryScreen()
        self._last_menu = (row, screen, x, y, w, h, edge)
        self.stackRequested.emit(entries, it["name"], it["stackPath"], cfg["view"], row, screen, x, y, w, h, edge)

    @Slot(int, QObject, float, float, float, float, str)
    def requestCalendar(self, row, window, x, y, w, h, edge):
        screen = window.screen() if hasattr(window, "screen") else self.app.primaryScreen()
        self._last_menu = (row, screen, x, y, w, h, edge)
        self.calendarRequested.emit(screen, x, y, w, h, edge)

    @Slot(int)
    def middleClick(self, row):
        it = self.model.item(row)
        if it and it["kind"] == "app":
            self._launch(it)

    @Slot(int, int)
    def scroll(self, row, direction):
        it = self.model.item(row)
        if not it or it["kind"] != "app" or not it["windows"]:
            return
        windows = it["windows"]
        pick = windows[0] if direction > 0 else windows[-2 if len(windows) > 1 else -1]
        self.bridge.send("activate", id=pick["id"])

    # --- pinning and dragging -----------------------------------------------
    def _save_pins(self, entry_ids):
        specs = dict((i, s) for s, i in self.model.pins)
        self.settings.set("pinned", [specs.get(i, i) for i in entry_ids])

    def pin_app(self, entry_id, at=None):
        order = [i for _s, i in self.model.pins if i != entry_id]
        order.insert(len(order) if at is None else max(0, min(at, len(order))), entry_id)
        self._save_pins(order)

    @Slot(int, int, result=int)
    def moveItem(self, from_row, to_row):
        """Live reordering while an icon is dragged; returns its new row."""
        it = self.model.item(from_row)
        if not it or it["kind"] != "app" or not it["hasEntry"]:
            return from_row
        order = list(self.model._preview if self.model._preview is not None
                     else [i for _s, i in self.model.pins])
        if it["appId"] in order:
            order.remove(it["appId"])
        order.insert(max(0, min(to_row - self.model.pin_offset, len(order))), it["appId"])
        self.model.preview_order(order)
        return next((r for r, x in enumerate(self.model.items) if x.get("appId") == it["appId"]), from_row)

    @Slot()
    def commitOrder(self):
        order = self.model.end_preview()
        if order is not None:
            self._save_pins(order)
        else:
            self.model.rebuild()

    @Slot(int)
    def unpin(self, row):
        it = self.model.item(row)
        self.model.end_preview()
        if it and it["kind"] == "app":
            self._save_pins([i for _s, i in self.model.pins if i != it["appId"]])

    @Slot(int, "QVariantList")
    def dropUrls(self, row, urls):
        urls = [u.toString() if isinstance(u, QUrl) else str(u) for u in urls]
        entries = [u for u in urls if u.endswith(".desktop") or u.startswith("applications:")]
        it = self.model.item(row)
        folders = [QUrl(u).toLocalFile() for u in urls
                   if QUrl(u).isLocalFile() and os.path.isdir(QUrl(u).toLocalFile())]
        if it and it["kind"] == "trash":
            self.trashUrls(urls)
        elif it and it["kind"] == "app" and not entries:
            self._launch(it, urls)
        elif folders and not entries:
            # a folder dropped on the dock becomes a Stack
            known = {stackfolders.resolve(st["path"]) for st in self.settings.get("stacks")}
            added = [{"path": f} for f in folders if os.path.abspath(f) not in known]
            if added:
                self.settings.set("stacks", self.settings.get("stacks") + added)
        else:
            pinned_rows = sum(1 for x in self.model.items if x.get("pinned"))
            offset = self.model.pin_offset
            for u in entries:
                entry_id = self.apps.resolve(u)
                if self.apps.get(entry_id):
                    self.pin_app(entry_id, at=max(0, min(row - offset, pinned_rows)) if row >= 0 else None)

    # --- menus --------------------------------------------------------------
    @Slot(QObject, result=QRectF)
    def screenRect(self, window):
        screen = window.screen() if hasattr(window, "screen") else None
        return QRectF(screen.geometry()) if screen else QRectF()

    @Slot(int, QObject, float, float, float, float, str)
    def requestMenu(self, row, window, x, y, w, h, edge):
        self.previewHide()
        screen = window.screen() if hasattr(window, "screen") else self.app.primaryScreen()
        self._last_menu = (row, screen, x, y, w, h, edge)
        self.menuRequested.emit(self._menu_for(row), row, screen, x, y, w, h, edge)

    def _menu_for(self, row):
        it = self.model.item(row)
        if it is None or it["kind"] == "divider":
            zoom = self.settings.get("zoom")
            current = dockpresets.current_id(self.settings.values)
            entries = [
                {"type": "command", "key": "launchpad", "icon": "view-app-grid", "text": "Show Launchpad"},
                {"type": "separator"},
                {"type": "command", "key": "hide-toggle", "icon": "view-visible",
                 "text": "Turn Hiding On" if self.settings.get("hide") == "always" else "Turn Hiding Off"},
                {"type": "command", "key": "magnify-toggle", "icon": "zoom-in",
                 "text": "Turn Magnification Off" if zoom > 1 else "Turn Magnification On"},
                {"type": "separator"},
                {"type": "header", "text": "Presets"},
            ]
            entries += [{"type": "command", "key": "preset:" + p["id"], "text": p["name"], "check": p["id"] == current}
                        for p in dockpresets.all_presets()]
            entries += [{"type": "separator"},
                        {"type": "command", "key": "settings", "icon": "configure", "text": "Dock Settings…"}]
            return entries
        if it["kind"] == "launchpad":
            return [{"type": "command", "key": "launchpad", "icon": "view-app-grid", "text": "Show Launchpad"},
                    {"type": "separator"},
                    {"type": "command", "key": "launchpad-remove", "icon": "list-remove", "text": "Remove from Dock"}]
        if it["kind"] == "widget":
            return self._widget_menu(it) + [
                {"type": "separator"},
                {"type": "command", "key": "widget-remove", "icon": "list-remove", "text": "Remove from Dock"}]
        if it["kind"] == "stack":
            cfg = self._stack_settings(it["stackPath"])

            def choice(field, value, text):
                return {"type": "command", "key": f"stack-{field}:{value}", "text": text, "check": cfg[field] == value}
            return [
                {"type": "command", "key": "stack-open", "icon": "document-open-folder", "text": f"Open “{it['name']}”"},
                {"type": "separator"},
                {"type": "header", "text": "Sort by"},
                choice("sort", "added", "Date Added"), choice("sort", "modified", "Date Modified"),
                choice("sort", "name", "Name"),
                {"type": "separator"},
                {"type": "header", "text": "View as"},
                choice("view", "auto", "Automatic"), choice("view", "fan", "Fan"), choice("view", "grid", "Grid"),
                {"type": "separator"},
                {"type": "header", "text": "Display as"},
                choice("display", "stack", "Stack"), choice("display", "folder", "Folder"),
                {"type": "separator"},
                {"type": "command", "key": "stack-remove", "icon": "list-remove", "text": "Remove from Dock"},
            ]
        if it["kind"] == "trash":
            return [
                {"type": "command", "key": "trash-open", "icon": "document-open-folder", "text": "Open"},
                {"type": "separator"},
                {"type": "command", "key": "trash-empty", "icon": "trash-empty", "text": "Empty Trash…",
                 "enabled": self._trash_full},
            ]
        entries = []
        if it["windows"]:
            for w in reversed(it["windows"]):
                entries.append({"type": "window", "key": "window:" + w["id"],
                                "text": w.get("caption") or it["name"], "check": bool(w.get("active")),
                                "dim": bool(w.get("minimized"))})
            if len(it["windows"]) > 1:
                entries.append({"type": "command", "key": "expose", "icon": "window-duplicate",
                                "text": "Show All Windows"})
            entries.append({"type": "separator"})
        entry = self.apps.get(it["appId"])
        if entry and entry.actions:
            for a in entry.actions:
                entries.append({"type": "command", "key": "action:" + a["id"], "text": a["name"],
                                "icon": a["icon"]})
            entries.append({"type": "separator"})
        if entry:
            entries.append({"type": "command", "key": "new", "icon": "window-new", "text": "New Window"})
            entries.append({"type": "command", "key": "unpin" if it["pinned"] else "pin",
                            "icon": "window-unpin" if it["pinned"] else "window-pin",
                            "text": "Remove from Dock" if it["pinned"] else "Keep in Dock"})
        if it["windows"]:
            entries.append({"type": "command", "key": "quit", "icon": "application-exit",
                            "text": "Quit" if entry else "Close"})
        return entries

    def _widget_menu(self, it):
        kind = it["widget"]
        if kind == "clock":
            style = it.get("widgetStyle") or "analog"
            return [{"type": "header", "text": "Clock"},
                    {"type": "command", "key": "clock-style:analog", "text": "Analog", "check": style == "analog"},
                    {"type": "command", "key": "clock-style:digital", "text": "Digital", "check": style == "digital"},
                    {"type": "separator"},
                    {"type": "command", "key": "clock-settings", "icon": "preferences-system-time",
                     "text": "Date & Time Settings…"}]
        battery = self._battery_obj
        if kind == "battery" and battery is not None:
            out = [{"type": "header", "text": f"Battery {battery.percent}% · {battery.status}"}]
            if battery.profiles:
                out += [{"type": "separator"}, {"type": "header", "text": "Power Mode"}]
                out += [{"type": "command", "key": "power:" + p, "check": p == battery.profile,
                         "text": PROFILE_NAMES.get(p, p.replace("-", " ").title())} for p in battery.profiles]
            out += [{"type": "separator"},
                    {"type": "command", "key": "power-settings", "icon": "preferences-system-power-management",
                     "text": "Power Settings…"}]
            return out
        media = self._media_obj
        if kind == "media" and media is not None:
            out = [{"type": "header", "text": " — ".join(x for x in (media.title, media.artist) if x) or media.identity},
                   {"type": "command", "key": "media-previous", "icon": "media-skip-backward", "text": "Previous",
                    "enabled": media.canPrevious},
                   {"type": "command", "key": "media-playpause",
                    "icon": "media-playback-pause" if media.playing else "media-playback-start",
                    "text": "Pause" if media.playing else "Play"},
                   {"type": "command", "key": "media-next", "icon": "media-skip-forward", "text": "Next",
                    "enabled": media.canNext}]
            players = media.players()
            if len(players) > 1:
                current = media.current_name()
                out += [{"type": "separator"}, {"type": "header", "text": "Players"}]
                out += [{"type": "command", "key": "media-player:" + name, "text": label, "check": name == current}
                        for name, label in players]
            if media.canRaise:
                out += [{"type": "separator"},
                        {"type": "command", "key": "media-raise", "icon": media.icon, "text": f"Show {media.identity}"}]
            return out
        return []

    def _widget_triggered(self, it, key):
        kind, battery, media = it["widget"], self._battery_obj, self._media_obj
        if key == "widget-remove":
            self.settings.set("widgets", [w for w in self.settings.get("widgets") if w["type"] != kind])
        elif key.startswith("clock-style:"):
            style = key.split(":", 1)[1]
            self.settings.set("widgets", [dict(w, style=style) if w["type"] == "clock" else w
                                          for w in self.settings.get("widgets")])
        elif key == "clock-settings":
            QProcess.startDetached("systemsettings", ["kcm_clock"])
        elif key == "power-settings":
            QProcess.startDetached("systemsettings", ["kcm_powerdevilprofilesconfig"])
        elif key.startswith("power:") and battery is not None:
            battery.setProfile(key.split(":", 1)[1])
        elif media is not None:
            if key == "media-previous":
                media.previous()
            elif key == "media-playpause":
                media.playPause()
            elif key == "media-next":
                media.next()
            elif key == "media-raise":
                media.raisePlayer()
            elif key.startswith("media-player:"):
                media.choose(key.split(":", 1)[1])

    @Slot(int, str)
    def menuTriggered(self, row, key):
        it = self.model.item(row)
        if key == "settings":
            self.openSettings()
        elif key == "launchpad":
            self.set_launchpad(True, self._last_menu[1] if self._last_menu else None)
        elif key == "launchpad-remove":
            self.settings.set("launchpad", False)
        elif key.startswith("preset:"):
            preset = dockpresets.find(key[len("preset:"):])
            if preset:
                self.settings.update(dockpresets.apply(self.settings.values, preset))
        elif key == "hide-toggle":
            self.settings.set("hide", "dodge" if self.settings.get("hide") == "always" else "always")
        elif key == "magnify-toggle":
            zoom = self.settings.get("zoom")
            self.settings.update({"zoom": 1.0, "zoomLast": zoom} if zoom > 1
                                 else {"zoom": self.settings.get("zoomLast")})
        elif key == "trash-open":
            self.openTrash()
        elif key == "trash-empty" and self._last_menu:
            _row, screen, x, y, w, h, edge = self._last_menu
            confirm = [{"type": "header", "text": "Erase the items in the Trash for good?"},
                       {"type": "command", "key": "trash-empty-confirm", "icon": "trash-empty",
                        "text": "Empty Trash"},
                       {"type": "command", "key": "cancel", "text": "Cancel"}]
            QTimer.singleShot(0, lambda: self.menuRequested.emit(confirm, row, screen, x, y, w, h, edge))
        elif key == "trash-empty-confirm":
            self.emptyTrash()
        elif it and it["kind"] == "widget":
            self._widget_triggered(it, key)
        elif it and it["kind"] == "stack" and key.startswith("stack-"):
            path = it["stackPath"]
            if key == "stack-open":
                self.openStackFolder(path)
            elif key == "stack-remove":
                self._edit_stacks(lambda sts: [st for st in sts if st["path"] != path])
            elif ":" in key:
                field, value = key[len("stack-"):].split(":", 1)
                self._edit_stacks(lambda sts: [dict(st, **{field: value}) if st["path"] == path else st
                                               for st in sts])
        elif it and it["kind"] == "app":
            if key.startswith("window:"):
                self.bridge.send("activate", id=key[len("window:"):])
            elif key.startswith("action:"):
                self.apps.launch(it["appId"], action=key[len("action:"):])
            elif key == "new":
                self._launch(it)
            elif key == "pin":
                self.pin_app(it["appId"])
            elif key == "unpin":
                self._save_pins([i for _s, i in self.model.pins if i != it["appId"]])
            elif key == "quit":
                for w in it["windows"]:
                    self.bridge.send("close", id=w["id"])
            elif key == "expose":
                self.expose([w["id"] for w in it["windows"]])

    # --- trash and settings actions -----------------------------------------
    @Slot()
    def openTrash(self):
        QProcess.startDetached("kioclient", ["exec", "trash:/"])

    def emptyTrash(self):
        if shutil.which("ktrash6"):
            QProcess.startDetached("ktrash6", ["--empty"])
        else:
            QProcess.startDetached("gio", ["trash", "--empty"])

    def trashUrls(self, urls):
        if urls:
            QProcess.startDetached("kioclient", ["move"] + list(urls) + ["trash:/"])

    @Slot()
    def openSettings(self):
        # straight to the Dock page (a desktop action of Tweaks' entry), else Tweaks as is
        if not (self.apps.launch(ids.TWEAKS_ID, action="dock") or self.apps.launch(ids.TWEAKS_ID)):
            print("dock: Borealis Tweaks isn't installed", flush=True)

    # --- where windows are (for hiding) --------------------------------------
    @Slot(str, float, float, float, float, result=bool)
    def overlaps(self, screen, x, y, w, h):
        for win in self.bridge.windows:
            if win.get("minimized") or not win.get("here", True):
                continue
            if screen and win.get("output") and win["output"] != screen:
                continue
            gx, gy, gw, gh = (list(win.get("geometry") or []) + [0, 0, 0, 0])[:4]
            if gx < x + w and x < gx + gw and gy < y + h and y < gy + gh:
                return True
        return False

    @Slot(str, result=bool)
    def fullscreenOn(self, screen):
        return any(w.get("fullScreen") and w.get("active") and not w.get("minimized")
                   and (not screen or w.get("output") in ("", screen)) for w in self.bridge.windows)

    # --- input region and blur ----------------------------------------------
    @Slot(QObject, "QVariantList", QRectF, float)
    def updateSurface(self, window, rects, blur, radius):
        self._pending[id(window)] = (window, rects, blur, radius)
        if not self._flush.isActive():
            self._flush.start()

    def _apply_surfaces(self):
        pending, self._pending = self._pending, {}
        for key, (window, rects, blur, radius) in pending.items():
            mask = QRegion()
            for r in rects:
                rect = r if isinstance(r, QRectF) else QRectF(r)
                if rect.width() > 0 and rect.height() > 0:
                    mask = mask.united(QRegion(rect.toAlignedRect()))
            if mask != window.mask():
                window.setMask(mask)           # empty: the whole surface takes input
            region = (effects.rounded_region(blur.x(), blur.y(), blur.width(), blur.height(), radius)
                      if radius >= 0 and blur.width() > 0 and blur.height() > 0 else QRegion())
            if region != self._regions.get(key):
                self._regions[key] = effects.set_blur(window, region) or region
            # both only apply with a commit: make sure a frame follows
            window.setProperty("commitTick", int(window.property("commitTick") or 0) + 1)
