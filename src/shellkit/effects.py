"""Blur behind a surface. Like the input region, it is double-buffered Wayland
state: it takes effect with the surface's next commit, so callers repaint."""
import ctypes

from PySide6.QtGui import QRegion

try:
    import shiboken6
except ImportError:          # pragma: no cover - PySide6 always ships it
    shiboken6 = None

_blur = None


def _blur_function():
    global _blur
    if _blur is None:
        _blur = False
        if shiboken6 is not None:
            try:
                lib = ctypes.CDLL("libKF6WindowSystem.so.6")
                fn = lib._ZN14KWindowEffects16enableBlurBehindEP7QWindowbRK7QRegion
                fn.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_void_p]
                fn.restype = None
                _blur = fn
            except (OSError, AttributeError):
                pass
    return _blur or None


def rounded_region(x, y, w, h, radius):
    """A rounded rectangle as a region: whole rows, stepped in the corners."""
    x, y, w, h = int(round(x)), int(round(y)), int(round(w)), int(round(h))
    r = max(0, min(int(radius), w // 2, h // 2))
    region = QRegion(x, y + r, w, h - 2 * r)
    for i in range(r):
        dy = r - i - 0.5
        inset = r - int(round((r * r - dy * dy) ** 0.5))
        region = region.united(QRegion(x + inset, y + i, w - 2 * inset, 1))
        region = region.united(QRegion(x + inset, y + h - 1 - i, w - 2 * inset, 1))
    return region


def set_blur(window, region):
    """Blur behind `region` (window coordinates); None or empty turns it off.
    Returns the QRegion so the caller can keep it alive until the commit."""
    fn = _blur_function()
    if fn is None:
        return None
    region = region if region is not None else QRegion()
    fn(shiboken6.getCppPointer(window)[0], not region.isEmpty(), shiboken6.getCppPointer(region)[0])
    return region
