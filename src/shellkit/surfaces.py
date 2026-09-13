"""Input regions and blur for layer-shell surfaces, applied at most once a frame.

Both are double-buffered Wayland state: they only take effect with the
surface's next commit, so after changing them the window's `commitTick` goes
up, which repaints a 1 px rectangle and makes that commit happen."""
from PySide6.QtCore import QObject, QRectF, QTimer
from PySide6.QtGui import QRegion

import effects


class Surfaces(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pending = {}
        self._regions = {}
        self._flush = QTimer(self, singleShot=True, interval=16)
        self._flush.timeout.connect(self._apply)

    def update(self, window, rects, blur, radius):
        """`rects` take input (none at all: the whole surface does); the blur
        goes behind `blur` with corners of `radius` (negative: no blur)."""
        self._pending[id(window)] = (window, rects, blur, radius)
        if not self._flush.isActive():
            self._flush.start()

    def _apply(self):
        pending, self._pending = self._pending, {}
        for key, (window, rects, blur, radius) in pending.items():
            mask = QRegion()
            for r in rects:
                rect = r if isinstance(r, QRectF) else QRectF(r)
                if rect.width() > 0 and rect.height() > 0:
                    mask = mask.united(QRegion(rect.toAlignedRect()))
            if mask != window.mask():
                window.setMask(mask)           # empty: the whole surface takes input
            region = (effects.rounded_region(blur.x(), blur.y(), blur.width(), blur.height(), radius)
                      if radius >= 0 and blur.width() > 0 and blur.height() > 0 else QRegion())
            if region != self._regions.get(key):
                self._regions[key] = effects.set_blur(window, region) or region
            # both only apply with a commit: make sure a frame follows
            window.setProperty("commitTick", int(window.property("commitTick") or 0) + 1)
