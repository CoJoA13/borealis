#!/usr/bin/env python3
"""Borealis Bar: the top bar of the Borealis desktop, for KDE Plasma on Wayland.

    borealis-bar              run the bar (normally started by systemd)
    borealis-bar --settings   open its page in Borealis Tweaks

The app in front and its menus come from KWin's window list, which KWin only
shares with the private interpreter copy named in the bar's .desktop entry
(install.sh sets both up). Started any other way, the bar works without them.
"""
import os
import signal
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)
# what the bar shares with the dock lives in src/shellkit; a built copy has
# those files right here instead
if os.path.isdir(os.path.join(HERE, "..", "shellkit")):
    sys.path.insert(1, os.path.join(HERE, "..", "shellkit"))

import ids  # noqa: E402


def main():
    import argparse
    ap = argparse.ArgumentParser(prog=f"{ids.SLUG}-bar", description=f"{ids.NAME} Bar")
    ap.add_argument("--settings", action="store_true", help="open the bar's settings")
    ap.add_argument("--version", action="store_true")
    args = ap.parse_args()
    if args.version:
        print(ids.VERSION)
        return 0

    # exactly what LayerShellQt::Shell::useLayerShell() does, before any window exists
    os.environ["QT_WAYLAND_SHELL_INTEGRATION"] = "layer-shell"
    try:
        from PySide6.QtCore import QTimer, QUrl
        from PySide6.QtDBus import QDBusConnection
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtQml import QQmlApplicationEngine
    except ImportError:
        sys.exit(f"{ids.NAME} Bar needs PySide6:  sudo dnf install python3-pyside6")
    from appmenu import AppMenu
    from controller import Controller
    from drives import Drives
    from service import BarService
    from settings import Settings
    from tray import Tray
    from widgets import Battery, Media
    from windows import Windows

    app = QGuiApplication(sys.argv)
    # apps started from the bar must not inherit the shell integration
    os.environ.pop("QT_WAYLAND_SHELL_INTEGRATION", None)
    app.setApplicationName(f"{ids.NAME} Bar")
    app.setDesktopFileName(ids.APP_ID)
    app.setQuitOnLastWindowClosed(False)
    # Plasma's notification library only serves notifications from the process
    # marked as the desktop's "D-Bus master" (normally plasmashell)
    app.setProperty("_plasma_dbus_master", True)
    if app.platformName() != "wayland":
        sys.exit(f"{ids.NAME} Bar needs a Plasma Wayland session (running on '{app.platformName()}')")

    bus = QDBusConnection.sessionBus()
    if not bus.registerService(ids.BUS):
        print(f"{ids.NAME} Bar is already running", file=sys.stderr)
        return 0
    # kded's appmenu module runs the global-menu registrar (which apps look for
    # before they share their menus) only while a menu view owns this name.
    # Queued: if Plasma's own global menu still holds it, the bar takes over
    # the moment that widget goes
    from PySide6.QtDBus import QDBusConnectionInterface
    bus.interface().registerService("org.kde.kappmenuview", QDBusConnectionInterface.ServiceQueueOptions.QueueService,
                                    QDBusConnectionInterface.ServiceReplacementOptions.AllowReplacement)

    engine = QQmlApplicationEngine()
    settings = Settings(parent=app)
    windows = Windows(engine, parent=app)
    if not windows.available:
        print("bar: no window list (not started through its interpreter copy?):", windows.error, file=sys.stderr)
    appmenu = AppMenu(windows, parent=app)
    tray = Tray(parent=app)
    engine.addImageProvider("tray", tray.images)
    drives = Drives(parent=app)
    battery = Battery(parent=app)
    media = Media(parent=app)
    controller = Controller(app, settings, windows, appmenu, tray, drives, battery, media, parent=app)
    service = BarService(controller, app, parent=app)
    if not bus.registerObject(ids.PATH, ids.INTERFACE, service, QDBusConnection.RegisterOption.ExportAllSlots):
        print("bar: couldn't export the D-Bus interface:", bus.lastError().message(), file=sys.stderr)

    engine.rootContext().setContextProperty("bar", controller)
    engine.load(QUrl.fromLocalFile(os.path.join(HERE, "ui", "Main.qml")))
    if not engine.rootObjects():
        sys.exit("bar: the interface didn't load (is layer-shell-qt installed?)")

    # let Python see SIGTERM from systemd between Qt events
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: app.quit())
    tick = QTimer(app, interval=300)
    tick.timeout.connect(lambda: None)
    tick.start()

    code = app.exec()
    del engine                     # the QML goes before the objects it binds to
    return code


if __name__ == "__main__":
    if "--settings" in sys.argv[1:]:
        # Tweaks, on the bar's page (no need to start the bar for that)
        sys.path.insert(0, HERE)
        import ids as _ids
        from controller import desktop_file  # noqa: F401  (PySide6 only needed for the class)
        path = desktop_file(_ids.TWEAKS_ID)
        if not path:
            sys.exit(f"{_ids.NAME} Tweaks isn't installed")
        exec_line = next((line[5:].strip() for line in open(path) if line.startswith("Exec=")), "")
        import shlex
        argv = shlex.split(exec_line.replace("%U", "").replace("%u", "")) + ["--page", "bar"]
        os.execvp(argv[0], argv)
    sys.exit(main())
