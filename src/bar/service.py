"""org.borealis.Bar1 on the session bus: a peek at the bar's state and a way to
open its menus without a pointer, for tests and for scripts."""
import json

from PySide6.QtCore import QObject, QRectF, Slot


class BarService(QObject):
    def __init__(self, controller, app, parent=None):
        super().__init__(parent)
        self.bar = controller
        self.app = app
        self._last_menu = ("", [])
        controller.menuRequested.connect(lambda entries, source, *_: setattr(self, "_last_menu", (source, entries)))

    @Slot(result=str)
    def State(self):
        bar = self.bar
        return json.dumps({
            "windowTracking": bar.windows.available,
            "active": bar.windows.active,
            "covered": bar.windows.covered,
            "menuTitles": bar.appmenu.titles,
            "tray": [{k: i[k] for k in ("key", "id", "title", "status", "iconName", "iconUrl", "menu")}
                     for i in bar.tray.items],
            "drives": bar.drives.drives,
            "popup": bar.popup,
            "lastMenu": {"source": self._last_menu[0],
                         "entries": [e.get("text", "") for e in self._last_menu[1]]},
            "buttons": {name: [screen, r.x(), r.y(), r.width(), r.height()]
                        for name, (screen, r) in bar.buttons().items()},
            "toggles": bar.toggles,
        }, default=str)

    def _anchor(self, name):
        placed = self.bar.button(name)
        if placed is None:
            return None
        screen = next((s for s in self.app.screens() if s.name() == placed[0]), self.app.primaryScreen())
        rect = placed[1] if isinstance(placed[1], QRectF) else QRectF(placed[1])
        return screen, rect.x(), rect.y(), rect.width(), rect.height()

    @Slot(str, result=bool)
    def Open(self, name):
        """"system", "clock", "controls", "drives", "app:<n>" (the nth menu title)
        or "tray:<n>" (the nth tray icon's menu)."""
        bar = self.bar
        if name.startswith("app:"):
            titles = bar.appmenu.titles
            index = int(name[4:]) if name[4:].isdigit() else -1
            if not 0 <= index < len(titles):
                return False
            key = titles[index]["key"]
            anchor = self._anchor("app:" + key)
            if anchor is None:
                return False
            bar.openAppMenu(key, *anchor)
            return True
        if name.startswith("tray:"):
            items = bar.tray.items
            index = int(name[5:]) if name[5:].isdigit() else -1
            if not 0 <= index < len(items):
                return False
            key = items[index]["key"]
            anchor = self._anchor("tray:" + key)
            if anchor is None:
                return False
            bar.openTrayMenu(key, *anchor)
            return True
        anchor = self._anchor(name)
        if anchor is None:
            return False
        if name == "system":
            bar.openSystemMenu(*anchor)
        else:
            bar.openPanel(name, *anchor)
        return True

    @Slot(str, result=bool)
    def Trigger(self, text):
        """Picks the entry with this text in the menu that opened last."""
        source, entries = self._last_menu
        for entry in entries:
            if entry.get("text") == text and entry.get("type") == "command":
                self.bar.closePopups()
                self.bar.triggerMenu(source, entry["key"])
                return True
        return False

    @Slot()
    def Close(self):
        self.bar.closePopups()

    @Slot()
    def Quit(self):
        self.app.quit()
