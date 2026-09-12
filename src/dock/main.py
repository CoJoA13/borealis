#!/usr/bin/env python3
"""Borealis Dock: a standalone, macOS-style dock for KDE Plasma on Wayland.

    borealis-dock              run the dock (normally started by systemd)
    borealis-dock --settings   open its settings in Borealis Tweaks

A layer-shell surface per screen draws the dock; the KWin script next to it
reports the open windows over D-Bus and carries out window commands.
"""
import os
import signal
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)

import ids  # noqa: E402


def open_settings():
    from apps import find_entry_path
    path = find_entry_path(ids.TWEAKS_ID)
    if not path:
        sys.exit(f"{ids.NAME} Tweaks isn't installed")
    os.execvp("kioclient", ["kioclient", "exec", path])


def main():
    import argparse
    ap = argparse.ArgumentParser(prog=f"{ids.SLUG}-dock", description=f"{ids.NAME} Dock")
    ap.add_argument("--settings", action="store_true", help="open the dock settings")
    ap.add_argument("--version", action="store_true")
    args = ap.parse_args()
    if args.version:
        print(ids.VERSION)
        return 0
    if args.settings:
        return open_settings()

    # exactly what LayerShellQt::Shell::useLayerShell() does, before any window exists
    os.environ["QT_WAYLAND_SHELL_INTEGRATION"] = "layer-shell"
    try:
        from PySide6.QtCore import QTimer, QUrl
        from PySide6.QtDBus import QDBusConnection
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtQml import QQmlApplicationEngine
    except ImportError:
        sys.exit(f"{ids.NAME} Dock needs PySide6:  sudo dnf install python3-pyside6")
    from apps import AppIndex
    from badges import Badges
    from bridge import Bridge, DockService
    from controller import Controller
    from model import DockModel
    from settings import Settings
    from stacks import StackIndex

    app = QGuiApplication(sys.argv)
    # Qt picked its shell integration while starting up; apps launched from the
    # dock must not inherit it, or their windows become layer surfaces too
    # (full screen, undecorated, no title, missing from the dock)
    os.environ.pop("QT_WAYLAND_SHELL_INTEGRATION", None)
    app.setApplicationName(f"{ids.NAME} Dock")
    app.setDesktopFileName(ids.APP_ID)
    app.setQuitOnLastWindowClosed(False)
    if app.platformName() != "wayland":
        sys.exit(f"{ids.NAME} Dock needs a Plasma Wayland session (running on '{app.platformName()}')")

    bus = QDBusConnection.sessionBus()
    if not bus.registerService(ids.BUS):
        print(f"{ids.NAME} Dock is already running", file=sys.stderr)
        return 0

    settings = Settings(parent=app)
    apps = AppIndex(parent=app)
    bridge = Bridge(parent=app)
    badges = Badges(parent=app)
    stacks = StackIndex(parent=app)
    model = DockModel(settings, apps, bridge, badges=badges, stacks=stacks, parent=app)
    controller = Controller(app, settings, apps, bridge, model, stacks=stacks, parent=app)
    service = DockService(bridge, controller, parent=app)
    if not bus.registerObject(ids.PATH, ids.INTERFACE, service,
                              QDBusConnection.RegisterOption.ExportAllSlots):
        print("dock: couldn't export the D-Bus interface:", bus.lastError().message(), file=sys.stderr)

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("dock", controller)
    engine.load(QUrl.fromLocalFile(os.path.join(HERE, "ui", "Main.qml")))
    if not engine.rootObjects():
        sys.exit("dock: the interface didn't load (is layer-shell-qt installed?)")

    # let Python see SIGTERM from systemd between Qt events
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: app.quit())
    tick = QTimer(app, interval=300)
    tick.timeout.connect(lambda: None)
    tick.start()

    if os.environ.get("BOREALIS_DOCK_DEBUG") == "1":
        bridge.send("debug", on=True)
    controller.push_config()
    bridge.send("resync")          # a bridge that loaded before us reports in
    code = app.exec()
    del engine                     # the QML goes before the objects it binds to
    return code


if __name__ == "__main__":
    sys.exit(main())
