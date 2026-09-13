#!/usr/bin/env python3
"""Render every Borealis Tweaks page offscreen, narrow and wide, and check that
no slider's value ends up outside the window.

    python3 tools/tweakscheck.py            screenshots in build/shots/tweaks/
    python3 tools/tweakscheck.py --keep     leave the throwaway config behind
    python3 tools/tweakscheck.py --app DIR  check a built or installed copy instead

It reads your desktop's state the way the app does (kreadconfig6, fc-list, …)
but writes nothing outside a temporary config folder, and presses nothing.
"""
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TWEAKS = (os.path.abspath(sys.argv[sys.argv.index("--app") + 1]) if "--app" in sys.argv[:-1]
          else os.path.join(HERE, "src", "tweaks"))
SHOTS = os.path.join(HERE, "build", "shots", "tweaks")
WIDTHS = (612, 1100)

config = tempfile.mkdtemp(prefix="tweakscheck-")
os.environ.update(QT_QPA_PLATFORM="offscreen", XDG_CONFIG_HOME=config)
os.environ.setdefault("QT_QPA_PLATFORMTHEME", "kde")
sys.path.insert(0, TWEAKS)

from PySide6.QtCore import QMetaObject, QPointF, QUrl, Q_ARG, qInstallMessageHandler  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine  # noqa: E402
from PySide6.QtQuick import QQuickItem, QQuickWindow  # noqa: E402
import shiboken6  # noqa: E402

messages = []
qInstallMessageHandler(lambda kind, context, text: messages.append(text))
app = QGuiApplication(["tweakscheck"])

from backend import Backend  # noqa: E402
from dockpage import DockBackend  # noqa: E402
from barpage import BarBackend  # noqa: E402
import main as tweaks_main  # noqa: E402


def spin(ms):
    end = time.monotonic() + ms / 1000
    while time.monotonic() < end:
        app.processEvents()
        time.sleep(0.005)


def items(root):
    todo = [root]
    while todo:
        item = todo.pop()
        yield item
        todo.extend(item.childItems())


def check_values(window):
    """Every Amount's value label must be visible inside the window."""
    width = window.width()
    found, bad = 0, []
    for item in items(window.contentItem()):
        if "Amount" not in item.metaObject().className() or not item.isVisible():
            continue
        labels = [c for c in item.childItems() if "Label" in c.metaObject().className()]
        if not labels:
            continue
        found += 1
        label = labels[-1]
        left = label.mapToScene(QPointF(0, 0)).x()
        right = label.mapToScene(QPointF(label.width(), 0)).x()
        if left < 0 or right > width + 0.5 or label.width() < 1:
            bad.append(f"{label.property('text')!r} spans {left:.0f}–{right:.0f} of {width}")
    return found, bad


def main():
    keep = "--keep" in sys.argv
    os.makedirs(SHOTS, exist_ok=True)
    engine = QQmlApplicationEngine()
    backend = Backend(app)
    dock = DockBackend(backend, app)
    bar = BarBackend(backend, app)
    ctx = engine.rootContext()
    ctx.setContextProperty("backend", backend)
    ctx.setContextProperty("dockSettings", dock)
    ctx.setContextProperty("barSettings", bar)
    ctx.setContextProperty("startPage", "theme")
    engine.load(QUrl.fromLocalFile(os.path.join(TWEAKS, "ui", "main.qml")))
    if not engine.rootObjects():
        print("FAIL: the interface didn't load")
        for m in messages[:10]:
            print("  ", m)
        return 1
    root = engine.rootObjects()[0]
    window = shiboken6.wrapInstance(shiboken6.getCppPointer(root)[0], QQuickWindow)
    failures = 0
    for page in tweaks_main.PAGES:
        QMetaObject.invokeMethod(root, "showPage", Q_ARG("QVariant", page))
        for width in WIDTHS:
            root.setProperty("width", width)
            root.setProperty("height", 2400)
            spin(1200)
            found, bad = check_values(window)
            shot = os.path.join(SHOTS, f"{page}-{width}.png")
            window.grabWindow().save(shot)
            status = "ok" if not bad else "FAIL"
            failures += bool(bad)
            print(f"{status}: {page} at {width} px — {found} sliders" + ("" if not bad else ": " + "; ".join(bad)))
    noise = [m for m in dict.fromkeys(messages) if "KLocalized" not in m and "Binding loop" not in m]
    if noise:
        print(f"{len(noise)} QML messages, first ones:")
        for m in noise[:12]:
            print("  ", m[:300])
    del engine
    if not keep:
        import shutil
        shutil.rmtree(config, ignore_errors=True)
    print("screenshots in", SHOTS)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
