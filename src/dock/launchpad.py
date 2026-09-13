"""Launchpad's apps: every app you can start, alphabetically, or the best
matches for what has been typed."""
from PySide6.QtCore import Property, QObject, Signal, Slot

from apps import FALLBACK_ICON, exec_binary


def score(entry, words):
    """How well an app matches every typed word; 0 when one of them misses."""
    name = entry.name.casefold()
    generic = (entry.generic or "").casefold()
    keywords = [k.casefold() for k in entry.keywords or []]
    binary = exec_binary(entry.exec).casefold()
    total = 0
    for w in words:
        if name.startswith(w):
            total += 100
        elif any(part.startswith(w) for part in name.split()):
            total += 80
        elif w in name:
            total += 60
        elif generic.startswith(w) or any(part.startswith(w) for part in generic.split()):
            total += 40
        elif any(k.startswith(w) for k in keywords):
            total += 30
        elif binary.startswith(w):
            total += 25
        elif w in (entry.comment or "").casefold():
            total += 10
        else:
            return 0
    return total


class AppGrid(QObject):
    changed = Signal()

    def __init__(self, apps, parent=None):
        super().__init__(parent)
        self.apps = apps
        self._query = ""
        self._items = []
        apps.changed.connect(self.refresh)
        self.refresh()

    @Property(str, notify=changed)
    def query(self):
        return self._query

    @Slot(str)
    def setQuery(self, text):
        text = " ".join(str(text).split())
        if text != self._query:
            self._query = text
            self.refresh()

    @Property("QVariantList", notify=changed)
    def items(self):
        return self._items

    @Property(int, notify=changed)
    def count(self):
        return len(self._items)

    def refresh(self):
        entries = [e for e in self.apps.by_id.values() if e.listed]
        words = self._query.casefold().split()
        if words:
            scored = sorted(((score(e, words), e) for e in entries), key=lambda t: (-t[0], t[1].name.casefold()))
            entries = [e for s, e in scored if s > 0]
        else:
            entries.sort(key=lambda e: e.name.casefold())
        self._items = [{"appId": e.id, "name": e.name, "icon": e.icon or FALLBACK_ICON,
                        "generic": e.generic or ""} for e in entries]
        self.changed.emit()
