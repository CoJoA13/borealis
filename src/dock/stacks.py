"""Folders kept in the dock (Stacks): their newest files, watched for changes."""
import os

from PySide6.QtCore import QFileSystemWatcher, QMimeDatabase, QObject, QStandardPaths, QTimer, QUrl, Signal

MAX_ITEMS = 60
SPECIAL = {
    "xdg:download": QStandardPaths.StandardLocation.DownloadLocation,
    "xdg:documents": QStandardPaths.StandardLocation.DocumentsLocation,
    "xdg:pictures": QStandardPaths.StandardLocation.PicturesLocation,
    "xdg:desktop": QStandardPaths.StandardLocation.DesktopLocation,
    "xdg:music": QStandardPaths.StandardLocation.MusicLocation,
    "xdg:videos": QStandardPaths.StandardLocation.MoviesLocation,
}
FOLDER_ICONS = {"xdg:download": "folder-downloads", "xdg:documents": "folder-documents",
                "xdg:pictures": "folder-pictures", "xdg:desktop": "user-desktop",
                "xdg:music": "folder-music", "xdg:videos": "folder-videos"}


def resolve(path):
    """A stack's folder as saved (xdg:download, ~/Stuff, /abs) -> absolute path."""
    path = str(path)
    if path in SPECIAL:
        return QStandardPaths.writableLocation(SPECIAL[path])
    return os.path.abspath(os.path.expanduser(path))


def folder_icon(path):
    if path in FOLDER_ICONS:
        return FOLDER_ICONS[path]
    real = resolve(path)
    for key, location in SPECIAL.items():
        if QStandardPaths.writableLocation(location) == real:
            return FOLDER_ICONS[key]
    return "folder"


class StackIndex(QObject):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mime = QMimeDatabase()
        self._watcher = QFileSystemWatcher(self)
        self._cache = {}
        self._dirty = QTimer(self, singleShot=True, interval=400)
        self._dirty.timeout.connect(self._rescan)
        self._watcher.directoryChanged.connect(lambda *_: self._dirty.start())

    def watch(self, paths):
        wanted = {resolve(p) for p in paths}
        wanted = {p for p in wanted if os.path.isdir(p)}
        current = set(self._watcher.directories())
        if current - wanted:
            self._watcher.removePaths(list(current - wanted))
        if wanted - current:
            self._watcher.addPaths(list(wanted - current))
        for key in [k for k in self._cache if k[0] not in wanted]:
            del self._cache[key]

    def _rescan(self):
        self._cache.clear()
        self.changed.emit()

    def entries(self, path, sort="added"):
        real = resolve(path)
        key = (real, sort)
        if key not in self._cache:
            self._cache[key] = self._scan(real, sort)
        return self._cache[key]

    def _scan(self, real, sort):
        items = []
        try:
            listing = list(os.scandir(real))
        except OSError:
            return items
        for entry in listing:
            if entry.name.startswith("."):
                continue
            try:
                st = entry.stat()
                is_dir = entry.is_dir()
            except OSError:
                continue                  # a dangling link
            mime = (self._mime.mimeTypeForName("inode/directory") if is_dir
                    else self._mime.mimeTypeForFile(entry.path, QMimeDatabase.MatchMode.MatchExtension))
            icon = mime.iconName() if mime.isValid() else ""
            items.append({
                "name": entry.name,
                "path": entry.path,
                "url": QUrl.fromLocalFile(entry.path).toString(),
                "icon": icon or ("folder" if is_dir else "text-x-generic"),
                "image": mime.name().startswith("image/") and st.st_size < 40 * 1024 * 1024,
                "dir": is_dir,
                "modified": st.st_mtime,
                "added": getattr(st, "st_birthtime", None) or st.st_ctime,
            })
        if sort == "name":
            items.sort(key=lambda it: (not it["dir"], it["name"].casefold()))
        else:
            items.sort(key=lambda it: it["modified" if sort == "modified" else "added"], reverse=True)
        return items[:MAX_ITEMS]
