"""What the bar's QML sees as `bar`: the settings, the windows, the menus, and
every action the bar can take."""
import os
import re
import shlex
import signal
import sys

from PySide6.QtCore import Property, QObject, QProcess, QRectF, QStandardPaths, QTimer, Signal, Slot
from PySide6.QtDBus import QDBus, QDBusConnection, QDBusMessage

import ids
import lookandfeel
from settings import PILLS
from surfaces import Surfaces

# one read of everything the Control Center's own toggles show
PROBE = "; ".join([
    'printf "night=%s\\n" "$(kreadconfig6 --file kwinrc --group NightColor --key Active 2>/dev/null)"',
    'printf "theme=%s\\n" "$(kreadconfig6 --file kdeglobals --group KDE --key LookAndFeelPackage 2>/dev/null)"',
    'printf "wallpaper=%s\\n" "$(qdbus-qt6 org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript '
    '\'print(desktops().map(function (d) { return d.wallpaperPlugin; }).join(","));\' 2>/dev/null)"',
])

# screenshots and recordings: Spectacle's global shortcut for each, and its
# command line for when there's no shortcut service to ask
SPECTACLE = "/component/org_kde_spectacle_desktop"
CAPTURES = {
    "region": ("RectangularRegionScreenShot", ["--region"]),
    "window": ("ActiveWindowScreenShot", ["--activewindow"]),
    "screen": ("CurrentMonitorScreenShot", ["--current"]),
    "all": ("FullScreenScreenShot", ["--fullscreen"]),
    "record-region": ("RecordRegion", ["--record", "region"]),
    "record-window": ("RecordWindow", ["--record", "window"]),
    "record-screen": ("RecordScreen", ["--record", "screen"]),
    "open": ("_launch", []),
}


def desktop_file(entry_id):
    """Where an app's .desktop entry is, by its id (org.kde.kinfocenter)."""
    homes = [os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")]
    homes += (os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share").split(":")
    for base in homes:
        path = os.path.join(base, "applications", entry_id + ".desktop")
        if os.path.isfile(path):
            return path
    return ""


class Controller(QObject):
    screensChanged = Signal()
    popupChanged = Signal()
    togglesChanged = Signal()
    # entries, source ("system", "app", "tray:<key>"), screen, x, y, w, h
    menuRequested = Signal("QVariantList", str, QObject, float, float, float, float)
    # source, parent key, entries
    submenuReady = Signal(str, str, "QVariantList")
    # "clock" | "controls" | "drives", screen, x, y, w, h
    panelRequested = Signal(str, QObject, float, float, float, float)
    # title, text, confirm label, action
    confirmRequested = Signal(str, str, str, str)
    sessionRequested = Signal(str)
    closeRequested = Signal()
    # a Control Center page to show ("" for its front, "edit" for edit mode)
    controlsPageRequested = Signal(str)

    def __init__(self, app, settings, windows, appmenu, tray, drives, battery, media, parent=None):
        super().__init__(parent)
        self.app = app
        self._settings, self._windows, self._appmenu, self._tray, self._drives = \
            settings, windows, appmenu, tray, drives
        self._battery, self._media = battery, media
        battery.set_active(True)
        media.set_active(True)
        self._surfaces = Surfaces(self)
        self._popup = ""
        self._buttons = {}                  # name -> (screen name, QRectF), reported by the QML
        self._tray_anchor = None
        self._toggles = {"night": False, "dark": True, "aurora": False, "known": False}
        self._controls = {"page": "", "editing": False}
        self._screen_key = settings.get("screen")
        settings.changed.connect(self._settings_changed)
        for sig in (app.screenAdded, app.screenRemoved, app.primaryScreenChanged):
            sig.connect(lambda *_: self.screensChanged.emit())
        tray.menuReady.connect(self._tray_menu_ready)
        self._probe = QProcess(self)
        self._probe.finished.connect(self._probed)
        self._reprobe = QTimer(self, singleShot=True, interval=700)
        self._reprobe.timeout.connect(self.refreshToggles)

    # --- objects for QML -----------------------------------------------------
    settings = Property(QObject, lambda self: self._settings, constant=True)
    windows = Property(QObject, lambda self: self._windows, constant=True)
    appmenu = Property(QObject, lambda self: self._appmenu, constant=True)
    tray = Property(QObject, lambda self: self._tray, constant=True)
    drives = Property(QObject, lambda self: self._drives, constant=True)
    battery = Property(QObject, lambda self: self._battery, constant=True)
    media = Property(QObject, lambda self: self._media, constant=True)

    @Slot(str, result="QVariantList")
    def menuTitleRects(self, screen):
        """The app's menu titles on one screen, for moving between open menus by hovering."""
        out = []
        for name, (on, rect) in self._buttons.items():
            if name.startswith("app:") and on == screen:
                out.append({"key": name[4:], "x": rect.x(), "y": rect.y(), "width": rect.width(),
                            "height": rect.height()})
        return out

    @Property(str, constant=True)
    def name(self):
        return ids.NAME

    @Property(str, constant=True)
    def logo(self):
        return ids.SLUG

    def _settings_changed(self):
        if self._settings.get("screen") != self._screen_key:
            self._screen_key = self._settings.get("screen")
            self.screensChanged.emit()

    @Property("QVariantList", notify=screensChanged)
    def screens(self):
        if self._settings.get("screen") == "all":
            return list(self.app.screens())
        primary = self.app.primaryScreen()
        return [primary] if primary else []

    # --- surfaces ------------------------------------------------------------
    @Slot(QObject, "QVariantList", QRectF, float)
    def updateSurface(self, window, rects, blur, radius):
        self._surfaces.update(window, rects, blur, radius)

    @Slot(str, str, QRectF)
    def placeButton(self, name, screen, rect):
        """Where each bar button is: for switching between open menus, and for tests."""
        self._buttons[name] = (screen, rect)

    def button(self, name):
        return self._buttons.get(name)

    def buttons(self):
        return dict(self._buttons)

    # --- popups --------------------------------------------------------------
    @Property(str, notify=popupChanged)
    def popup(self):
        """What's open: "" | "system" | "app:<key>" | "tray:<key>" | "clock" | "controls" | "drives"."""
        return self._popup

    @Slot(str)
    def setPopup(self, name):
        if name != self._popup:
            self._popup = name
            self._windows.freeze(bool(name))
            self.popupChanged.emit()

    def _screen(self, screen):
        return screen if screen is not None else self.app.primaryScreen()

    @Slot(QObject, float, float, float, float)
    def openSystemMenu(self, screen, x, y, w, h):
        front = self._windows.active
        caps = self._sessions
        entries = [
            {"type": "command", "key": "about", "text": "About This Computer", "icon": "help-about"},
            {"type": "separator"},
            {"type": "command", "key": "settings", "text": "System Settings…", "icon": "preferences-system"},
            {"type": "command", "key": "tweaks", "text": f"{ids.NAME} Tweaks…", "icon": ids.SLUG},
            {"type": "separator"},
            {"type": "command", "key": "forcequit",
             "text": f"Force Quit {front['name']}…" if front.get("name") else "Force Quit…",
             "icon": "process-stop", "enabled": bool(front.get("pid"))},
            {"type": "separator"},
            {"type": "command", "key": "sleep", "text": "Sleep", "icon": "system-suspend",
             "enabled": caps.get("suspend", True)},
            {"type": "command", "key": "restart", "text": "Restart…", "icon": "system-reboot",
             "enabled": caps.get("reboot", True)},
            {"type": "command", "key": "shutdown", "text": "Shut Down…", "icon": "system-shutdown",
             "enabled": caps.get("shutdown", True)},
            {"type": "separator"},
            {"type": "command", "key": "lock", "text": "Lock Screen", "icon": "system-lock-screen",
             "shortcut": "Meta+L", "enabled": caps.get("lock", True)},
            {"type": "command", "key": "logout", "text": "Log Out…", "icon": "system-log-out",
             "enabled": caps.get("logout", True)},
        ]
        self.menuRequested.emit(entries, "system", self._screen(screen), x, y, w, h)

    _sessions = {}

    @Slot("QVariantMap")
    def setSessionCapabilities(self, caps):
        self._sessions = dict(caps)

    @Slot(str, QObject, float, float, float, float)
    def openAppMenu(self, key, screen, x, y, w, h):
        screen = self._screen(screen)
        self._appmenu.open(key, lambda entries: self.menuRequested.emit(entries, "app:" + key, screen, x, y, w, h))

    @Slot(str, QObject, float, float, float, float)
    def openTrayMenu(self, key, screen, x, y, w, h):
        self._tray_anchor = (key, self._screen(screen), x, y, w, h)
        self._tray.requestMenu(key)

    def _tray_menu_ready(self, key, entries):
        anchor = self._tray_anchor
        if anchor and anchor[0] == key and entries:
            self.menuRequested.emit(entries, "tray:" + key, *anchor[1:])

    @Slot(str, str)
    def openSubmenu(self, source, key):
        if source.startswith("app:"):
            self._appmenu.open(key, lambda entries: self.submenuReady.emit(source, key, entries))
        elif source.startswith("tray:"):
            self._tray.open_submenu(source[5:], key, lambda entries: self.submenuReady.emit(source, key, entries))

    @Slot(str, str)
    def triggerMenu(self, source, key):
        if source.startswith("app:"):
            self._appmenu.activate(key)
        elif source.startswith("tray:"):
            self._tray.activateEntry(source[5:], key)
        elif source == "system":
            self._system(key)

    @Slot(str, QObject, float, float, float, float)
    def openPanel(self, kind, screen, x, y, w, h):
        if kind == "controls":
            self.refreshToggles()
        self.panelRequested.emit(kind, self._screen(screen), x, y, w, h)

    @Slot()
    def closePopups(self):
        self.closeRequested.emit()

    # --- the Borealis menu ---------------------------------------------------
    def _system(self, key):
        if key == "about":
            self.launch("org.kde.kinfocenter")
        elif key == "settings":
            self.launch("systemsettings")
        elif key == "tweaks":
            self.launch(ids.TWEAKS_ID)
        elif key == "forcequit":
            front = self._windows.active
            if front.get("pid"):
                name = front.get("name") or "this app"
                self.confirmRequested.emit(f"Force Quit {name}?", "Anything it hasn't saved will be lost.",
                                           "Force Quit", f"kill:{front['pid']}")
        elif key in ("sleep", "restart", "shutdown", "lock", "logout"):
            self.sessionRequested.emit(key)

    @Slot(str)
    def confirmed(self, action):
        if action.startswith("kill:"):
            try:
                pid = int(action[5:])
                if pid > 1 and pid != os.getpid():
                    os.kill(pid, signal.SIGKILL)
            except (ValueError, OSError):
                pass

    @Slot(str)
    def launch(self, entry_id):
        path = desktop_file(entry_id)
        if path:
            QProcess.startDetached("kioclient", ["exec", path])

    @Slot(str, str)
    def launchWith(self, entry_id, args):
        """An app with extra arguments (Tweaks on one page): its Exec line, run directly."""
        path = desktop_file(entry_id)
        if not path:
            return
        exec_line = ""
        for line in open(path, encoding="utf-8", errors="replace"):
            if line.startswith("Exec="):
                exec_line = line[5:].strip()
                break
        argv = [a for a in shlex.split(re.sub(r"%[a-zA-Z]", "", exec_line)) if a]
        if argv:
            QProcess.startDetached(argv[0], argv[1:] + shlex.split(args))

    @Slot(str)
    def openKcm(self, module):
        QProcess.startDetached("systemsettings", [module])

    @Slot(str)
    def openTweaks(self, page):
        self.launchWith(ids.TWEAKS_ID, f"--page {page}" if page else "")

    # --- the Control Center -------------------------------------------------
    allPills = Property("QVariantList", lambda self: list(PILLS), constant=True)

    @Property(bool, constant=True)
    def canCapture(self):
        return bool(QStandardPaths.findExecutable("spectacle"))

    @Slot(str, bool)
    def reportControls(self, page, editing):
        """Which page the Control Center shows, and whether it's in edit mode."""
        self._controls = {"page": page, "editing": bool(editing)}

    def controls_state(self):
        return dict(self._controls)

    def show_controls_page(self, page):
        self.controlsPageRequested.emit(page)

    @Slot(str)
    def capture(self, kind):
        """A screenshot or screen recording through Spectacle, once the popup is off the screen."""
        shortcut, args = CAPTURES.get(kind, CAPTURES["region"])
        self.closeRequested.emit()
        QTimer.singleShot(350, lambda: self._capture(shortcut, args))

    def _capture(self, shortcut, args):
        bus = QDBusConnection.sessionBus()
        names = QDBusMessage.createMethodCall("org.kde.kglobalaccel", SPECTACLE, "org.kde.kglobalaccel.Component",
                                              "shortcutNames")
        reply = bus.call(names, QDBus.CallMode.Block, 1500)
        known = reply.arguments()[0] if reply.type() == QDBusMessage.MessageType.ReplyMessage and reply.arguments() else []
        if shortcut in known:
            call = QDBusMessage.createMethodCall("org.kde.kglobalaccel", SPECTACLE, "org.kde.kglobalaccel.Component",
                                                 "invokeShortcut")
            call.setArguments([shortcut])
            bus.send(call)
        else:
            QProcess.startDetached("spectacle", args)

    # --- the Control Center's own toggles -----------------------------------
    @Slot()
    def refreshToggles(self):
        if self._probe.state() == QProcess.ProcessState.NotRunning:
            self._probe.start("sh", ["-c", PROBE])

    def _probed(self, *_):
        text = bytes(self._probe.readAllStandardOutput()).decode(errors="replace")
        values = dict(line.split("=", 1) for line in text.splitlines() if "=" in line)
        wallpapers = [w for w in values.get("wallpaper", "").split(",") if w]
        toggles = {
            "night": values.get("night", "").strip().lower() == "true",
            "dark": not values.get("theme", "").strip().endswith("-Light"),
            "aurora": any(w.endswith(".aurora") for w in wallpapers),
            "known": True,
        }
        if toggles != self._toggles:
            self._toggles = toggles
            self.togglesChanged.emit()

    @Property("QVariantMap", notify=togglesChanged)
    def toggles(self):
        return self._toggles

    def _run(self, program, args):
        QProcess.startDetached(program, args)
        self._reprobe.start()

    @Slot()
    def toggleNightLight(self):
        self._toggles["night"] = not self._toggles["night"]
        self.togglesChanged.emit()
        self._run("kwriteconfig6", ["--notify", "--file", "kwinrc", "--group", "NightColor", "--key", "Active",
                                    "true" if self._toggles["night"] else "false"])

    @Slot()
    def toggleDarkStyle(self):
        self._toggles["dark"] = not self._toggles["dark"]
        self.togglesChanged.emit()
        # shellkit's lookandfeel.py applies the Global Theme and keeps your own fonts and pointer
        self._run(sys.executable, [lookandfeel.__file__, ids.LNF_DARK if self._toggles["dark"] else ids.LNF_LIGHT])

    @Slot()
    def toggleAurora(self):
        self._toggles["aurora"] = not self._toggles["aurora"]
        self.togglesChanged.emit()
        plugin = ids.AURORA if self._toggles["aurora"] else "org.kde.image"
        self._run("qdbus-qt6", ["org.kde.plasmashell", "/PlasmaShell", "org.kde.PlasmaShell.evaluateScript",
                                "desktops().forEach(function (d) { d.wallpaperPlugin = '%s'; });" % plugin])
