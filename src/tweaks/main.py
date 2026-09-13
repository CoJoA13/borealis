#!/usr/bin/env python3
"""Borealis Tweaks: a small desktop app for the Borealis theme.

    borealis-tweaks                 open the window (on the welcome tour the first time)
    borealis-tweaks --page presets  open it on a page (or welcome, theme, bar, controls, dock,
                                    windows, text, input, desktop, system)
    borealis-tweaks --welcome       open it on the welcome tour
    BOREALIS_PROJECT=~/src/Borealis borealis-tweaks     use another checkout
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QGuiApplication, QIcon
    from PySide6.QtQml import QQmlApplicationEngine
except ImportError:
    sys.exit("Borealis Tweaks needs PySide6:  sudo dnf install python3-pyside6")

from backend import Backend  # noqa: E402
from dockpage import DockBackend  # noqa: E402
from barpage import BarBackend  # noqa: E402
from desktoppage import DesktopBackend  # noqa: E402
from inputpage import InputBackend  # noqa: E402
from presetspage import PresetsBackend  # noqa: E402
from textpage import TextBackend  # noqa: E402
from windowspage import WindowsBackend  # noqa: E402

# the pages in ui/main.qml's sidebar, by name
PAGES = ("welcome", "presets", "theme", "bar", "controls", "dock", "windows", "text", "input", "desktop", "system")


def plasma_pages(backend, app):
    """The Plasma settings pages' backends, by the names their pages use."""
    return {"windowsSettings": WindowsBackend(backend, app), "textSettings": TextBackend(backend, app),
            "inputSettings": InputBackend(backend, app), "desktopSettings": DesktopBackend(backend, app)}


def context(app):
    """Everything the pages use, by the names they use it by; all owned by the
    app, so QML never sees any of it vanish."""
    backend = Backend(app)
    dock, bar = DockBackend(backend, app), BarBackend(backend, app)
    objects = {"backend": backend, "dockSettings": dock, "barSettings": bar, **plasma_pages(backend, app)}
    objects["presetsSettings"] = PresetsBackend(backend, dock, bar, objects["windowsSettings"],
                                                objects["desktopSettings"], app)
    return objects


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Borealis Tweaks")
    ap.add_argument("--page", choices=PAGES)
    ap.add_argument("--welcome", action="store_true", help="open on the welcome tour")
    args, qt_args = ap.parse_known_args()
    app = QGuiApplication([sys.argv[0]] + qt_args)
    app.setApplicationName("Borealis Tweaks")
    app.setDesktopFileName("org.borealis.tweaks")
    app.setWindowIcon(QIcon.fromTheme("borealis"))
    engine = QQmlApplicationEngine()
    objects = context(app)
    for name, obj in objects.items():
        engine.rootContext().setContextProperty(name, obj)
    # the tour, the first time Tweaks opens
    start = "welcome" if args.welcome else args.page or ("theme" if objects["backend"].welcomed else "welcome")
    engine.rootContext().setContextProperty("startPage", start)
    engine.load(QUrl.fromLocalFile(os.path.join(HERE, "ui", "main.qml")))
    if not engine.rootObjects():
        sys.exit("could not load the interface (is org.kde.kirigami installed?)")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
