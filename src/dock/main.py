#!/usr/bin/env python3
"""Borealis Dock: a standalone, macOS-style dock for KDE Plasma on Wayland.

    borealis-dock                      run the dock (normally started by systemd)
    borealis-dock --settings           open its settings in Borealis Tweaks
    borealis-dock --launchpad          open or close Launchpad
    borealis-dock --list-presets       the looks to choose from
    borealis-dock --preset macos       switch to one (or to a preset file someone shared)
    borealis-dock --export-preset F    save the current look to share [--with-apps]

A layer-shell surface per screen draws the dock; the KWin script next to it
reports the open windows over D-Bus and carries out window commands.
"""
import os
import signal
import subprocess
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


def preset_command(args):
    """Presets from the command line edit the settings file; a running dock follows it."""
    import presets
    import settings
    path = settings.config_path()
    values = settings.load_values(path)
    if args.list_presets:
        current = presets.current_id(values)
        for p in presets.all_presets():
            mark = "*" if p["id"] == current else " "
            print(f"{mark} {p['id']:<22} {p['name']}" + (f"  ({p['description']})" if p["description"] else ""))
        return 0
    if args.export_preset:
        name = os.path.splitext(os.path.basename(args.export_preset))[0]
        print(presets.write(args.export_preset, name, values, args.with_apps))
        return 0
    if os.path.isfile(os.path.expanduser(args.preset)):
        try:
            preset = presets.read(args.preset)
        except ValueError as e:
            sys.exit(f"{args.preset}: {e}")
    else:
        preset = presets.find(args.preset)
        if preset is None:
            sys.exit(f"there's no preset called {args.preset!r} (see --list-presets)")
    settings.write_values(path, presets.apply(values, preset, args.with_apps))
    print(f"{ids.NAME} Dock: {preset['name']}")
    return 0


def main():
    import argparse
    ap = argparse.ArgumentParser(prog=f"{ids.SLUG}-dock", description=f"{ids.NAME} Dock")
    ap.add_argument("--settings", action="store_true", help="open the dock settings")
    ap.add_argument("--launchpad", action="store_true", help="open or close Launchpad in the running dock")
    ap.add_argument("--list-presets", action="store_true", help="the presets there are (* is the one in use)")
    ap.add_argument("--preset", metavar="NAME|FILE",
                    help="switch to a preset (borealis, macos, minimal, one you saved) or a preset file")
    ap.add_argument("--export-preset", metavar="FILE", help="save the current look as a preset file")
    ap.add_argument("--with-apps", action="store_true",
                    help="with --preset or --export-preset: the pinned apps and Stacks as well")
    ap.add_argument("--version", action="store_true")
    args = ap.parse_args()
    if args.version:
        print(ids.VERSION)
        return 0
    if args.settings:
        return open_settings()
    if args.launchpad:
        return subprocess.call(["busctl", "--user", "call", ids.BUS, ids.PATH, ids.INTERFACE, "ToggleLaunchpad"])
    if args.list_presets or args.preset or args.export_preset:
        return preset_command(args)

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
    from launchpad import AppGrid
    from model import DockModel
    from settings import Settings
    from stacks import StackIndex
    from widgets import Battery, Media

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
    battery = Battery(parent=app)
    media = Media(apps, parent=app)
    grid = AppGrid(apps, parent=app)
    model = DockModel(settings, apps, bridge, badges=badges, stacks=stacks, battery=battery, media=media,
                      parent=app)
    controller = Controller(app, settings, apps, bridge, model, stacks=stacks, battery=battery, media=media,
                            launchpad=grid, parent=app)
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
