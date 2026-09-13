"""The windows as Plasma's task manager sees them: which app is in front, where
its menu lives, and which screens have a maximized window.

KWin only hands its window list to programs it trusts: the bar's .desktop
entry names org_kde_plasma_window_management for the private copy of the
Python interpreter the bar runs under. Without that the list stays empty and
the bar just shows no app name and no menus."""
from PySide6.QtCore import Property, QAbstractItemModel, QObject, QRect, QTimer, QUrl, Signal
from PySide6.QtQml import QQmlComponent, QQmlEngine
import shiboken6

TASKS_QML = b"""import QtQuick
import org.kde.taskmanager as TaskManager
TaskManager.TasksModel {
    groupMode: TaskManager.TasksModel.GroupDisabled
    filterByVirtualDesktop: true
    filterByActivity: true
    filterByScreen: false
    filterHidden: true
}
"""
ROLES = ("AppName", "AppId", "AppPid", "IsActive", "IsWindow", "IsMaximized", "IsMinimized", "IsFullScreen",
         "ScreenGeometry", "ApplicationMenuServiceName", "ApplicationMenuObjectPath")


def _rect(value):
    if isinstance(value, QRect):
        return {"x": value.x(), "y": value.y(), "width": value.width(), "height": value.height()}
    return None


class Windows(QObject):
    changed = Signal()

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._active = {}
        self._covered = []
        self._count = 0
        self._frozen = False
        self._model = None
        self.error = ""
        self._component = QQmlComponent(engine)
        self._component.setData(TASKS_QML, QUrl("file:///borealis-bar/tasks.qml"))
        obj = self._component.create()
        if obj is None:
            self.error = "; ".join(e.toString() for e in self._component.errors())
            return
        QQmlEngine.setObjectOwnership(obj, QQmlEngine.ObjectOwnership.CppOwnership)
        self._object = obj
        self._model = shiboken6.wrapInstance(shiboken6.getCppPointer(obj)[0], QAbstractItemModel)
        self._roles = {bytes(v).decode(): k for k, v in self._model.roleNames().items()}
        self._later = QTimer(self, singleShot=True, interval=40)
        self._later.timeout.connect(self._read)
        for sig in (self._model.rowsInserted, self._model.rowsRemoved, self._model.rowsMoved,
                    self._model.dataChanged, self._model.modelReset, self._model.layoutChanged):
            sig.connect(lambda *_: self._later.start())
        self._read()

    def rows(self):
        if self._model is None:
            return []
        out = []
        for r in range(self._model.rowCount()):
            idx = self._model.index(r, 0)
            out.append({name: self._model.data(idx, self._roles[name]) for name in ROLES if name in self._roles})
        return out

    def _read(self):
        rows = [r for r in self.rows() if r.get("IsWindow")]
        covered = [_rect(r.get("ScreenGeometry")) for r in rows
                   if (r.get("IsMaximized") or r.get("IsFullScreen")) and not r.get("IsMinimized")]
        covered = [c for c in covered if c]
        front = next((r for r in rows if r.get("IsActive")), None)
        active = {}
        if front is not None:
            app_id = str(front.get("AppId") or "")
            active = {
                "name": str(front.get("AppName") or ""),
                "appId": app_id[:-8] if app_id.endswith(".desktop") else app_id,
                "pid": int(front.get("AppPid") or 0),
                "menuService": str(front.get("ApplicationMenuServiceName") or ""),
                "menuPath": str(front.get("ApplicationMenuObjectPath") or ""),
                "screen": _rect(front.get("ScreenGeometry")),
            }
        changed = covered != self._covered or len(rows) != self._count
        self._covered, self._count = covered, len(rows)
        # while one of the bar's own popups has the keyboard, the app it's about stays put
        if not self._frozen and active != self._active:
            self._active = active
            changed = True
        if changed:
            self.changed.emit()

    def freeze(self, frozen):
        """Hold on to the front app while a menu for it is open."""
        self._frozen = bool(frozen)
        if not frozen and self._model is not None:
            self._later.start()

    @Property(bool, constant=True)
    def available(self):
        return self._model is not None

    @Property("QVariantMap", notify=changed)
    def active(self):
        return self._active

    @Property("QVariantList", notify=changed)
    def covered(self):
        """Screen rectangles with a maximized or full-screen window on them."""
        return self._covered

    @Property(int, notify=changed)
    def count(self):
        return self._count
