"""The menus of the app in front: their titles for the bar, and each menu's
entries, fetched as it opens so the app can fill it in first."""
from PySide6.QtCore import Property, QObject, QTimer, Signal

from dbusmenu import DBusMenu


class AppMenu(QObject):
    changed = Signal()

    def __init__(self, windows, parent=None):
        super().__init__(parent)
        self.windows = windows
        self._menu = None
        self._key = ("", "")
        self._top = []
        self._again = QTimer(self, singleShot=True, interval=150)
        self._again.timeout.connect(self._fetch_titles)
        windows.changed.connect(self._follow)
        self._follow()

    def _follow(self):
        active = self.windows.active
        key = (active.get("menuService", ""), active.get("menuPath", ""))
        if key == self._key:
            return
        self._key = key
        if self._menu is not None:
            self._menu.close()
            self._menu = None
        if all(key):
            self._menu = DBusMenu(*key, parent=self)
            self._menu.updated.connect(self._again.start)
            self._fetch_titles()
        elif self._top:
            self._top = []
            self.changed.emit()

    def _fetch_titles(self):
        menu = self._menu
        if menu is None:
            return

        def done(entries):
            if menu is not self._menu:
                return                       # another app came to the front meanwhile
            top = [{"key": e["key"], "text": e["text"], "enabled": e["enabled"]}
                   for e in entries if e["type"] != "separator" and e["text"]]
            if top != self._top:
                self._top = top
                self.changed.emit()
        menu.fetch(0, done, depth=1)

    @Property("QVariantList", notify=changed)
    def titles(self):
        return self._top

    def open(self, key, done):
        if self._menu is not None:
            self._menu.fetch(int(key), done)

    def activate(self, key):
        if self._menu is not None:
            self._menu.activate(int(key))
