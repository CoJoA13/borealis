#!/usr/bin/env python3
"""Borealis Tweaks: a small desktop app for the Borealis theme.

    borealis-tweaks           open the window
    borealis-tweaks --page dock   open it on the Dock page
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


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Borealis Tweaks")
    ap.add_argument("--page", choices=("theme", "dock"), default="theme")
    args, qt_args = ap.parse_known_args()
    app = QGuiApplication([sys.argv[0]] + qt_args)
    app.setApplicationName("Borealis Tweaks")
    app.setDesktopFileName("org.borealis.tweaks")
    app.setWindowIcon(QIcon.fromTheme("borealis"))
    engine = QQmlApplicationEngine()
    backend = Backend(app)   # owned by the app, so QML never sees it vanish
    dock = DockBackend(backend, app)
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("dockSettings", dock)
    engine.rootContext().setContextProperty("startPage", args.page)
    engine.load(QUrl.fromLocalFile(os.path.join(HERE, "ui", "main.qml")))
    if not engine.rootObjects():
        sys.exit("could not load the interface (is org.kde.kirigami installed?)")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
