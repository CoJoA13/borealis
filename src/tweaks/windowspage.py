"""Borealis Tweaks, the Windows page: the title bar's buttons, window corners,
blur and how fast things animate."""
import os
import sys

from PySide6.QtCore import Slot

import plasmasettings as ps
from backend import DATA, PROJECT

DECORATION = "org.kde.kdecoration2"
AURORAE = "__aurorae__svg__"
# the buttons offered, by KDecoration's letters
BUTTONS = {"keepAbove": "F", "allDesktops": "S", "minimize": "I", "maximize": "A", "close": "X"}
RIGHT_ORDER = "FSIAX"   # at the right, close goes in the corner
LEFT_ORDER = "XIASF"    # at the left, the macOS way: close first
# Plasma's own animation speed steps, slowest to instant
SPEEDS = (4, 2, 1.5, 1, 0.75, 0.5, 0)
# KWin's blur when nothing sets it
BLUR_STRENGTH, NOISE_STRENGTH = 15, 0


def layout(values):
    """ButtonsOnLeft and ButtonsOnRight for the page's choices."""
    left_side = values.get("buttonsSide") == "left"
    chosen = {letter for key, letter in BUTTONS.items() if values.get(key)}
    main = "".join(letter for letter in (LEFT_ORDER if left_side else RIGHT_ORDER) if letter in chosen)
    other = "M" if values.get("appIcon") else ""
    return (main, other) if left_side else (other, main)


class WindowsBackend(ps.PlasmaPage):
    def __init__(self, backend, parent=None):
        super().__init__(backend, parent)
        backend.finished.connect(self._job_finished)
        self.refresh()

    # ----------------------------------------------------------------- read --
    def _decoration(self):
        """The Borealis decoration in use (its folder name), or "" for any other."""
        theme = self.config.get("kwinrc", DECORATION, "theme", "")
        if not theme.startswith(AURORAE):
            return ""
        name = theme[len(AURORAE):]
        folder = os.path.join(DATA, "aurorae", "themes", name)
        meta = ps.read_text(os.path.join(folder, "metadata.json"))
        return name if os.path.exists(os.path.join(folder, f"{name}rc")) and "aurora pill buttons" in meta else ""

    @staticmethod
    def _radius(name):
        if not name:
            return 12
        rc = ps.parse(ps.read_text(os.path.join(DATA, "aurorae", "themes", name, f"{name}rc")))
        try:
            return int(rc.get("Borealis", {}).get("CornerRadius", 12))
        except ValueError:
            return 12

    def read(self):
        c = self.config
        left = c.get("kwinrc", DECORATION, "ButtonsOnLeft", "MSE")
        right = c.get("kwinrc", DECORATION, "ButtonsOnRight", "HIAX")
        side = "left" if "X" in left and "X" not in right else "right"
        main, other = (left, right) if side == "left" else (right, left)
        values = {"buttonsSide": side, "appIcon": "M" in other}
        values.update({key: letter in main for key, letter in BUTTONS.items()})
        factor = c.get_float("kdeglobals", "KDE", "AnimationDurationFactor", 1.0)
        values["animationSpeed"] = next((i for i, s in enumerate(SPEEDS) if s <= factor), len(SPEEDS) - 1)
        values["blurStrength"] = c.get_int("kwinrc", "Effect-blur", "BlurStrength", BLUR_STRENGTH)
        values["noiseStrength"] = c.get_int("kwinrc", "Effect-blur", "NoiseStrength", NOISE_STRENGTH)
        name = self._decoration()
        values["decoration"] = name
        values["cornerRadius"] = self._radius(name)
        return values

    # ---------------------------------------------------------------- write --
    def apply_changes(self, changes, merged):
        if set(changes) & (set(BUTTONS) | {"buttonsSide", "appIcon"}):
            left, right = layout(merged)
            ps.kwrite("kwinrc", DECORATION, "ButtonsOnLeft", left)
            ps.kwrite("kwinrc", DECORATION, "ButtonsOnRight", right)
            ps.reload_kwin()
        if "blurStrength" in changes or "noiseStrength" in changes:
            if "blurStrength" in changes:
                ps.kwrite("kwinrc", "Effect-blur", "BlurStrength", max(1, min(15, round(changes["blurStrength"]))))
            if "noiseStrength" in changes:
                ps.kwrite("kwinrc", "Effect-blur", "NoiseStrength", max(0, min(14, round(changes["noiseStrength"]))))
            ps.reconfigure_effect("blur")
        if "animationSpeed" in changes:
            index = max(0, min(len(SPEEDS) - 1, round(changes["animationSpeed"])))
            ps.kwrite("kdeglobals", "KDE", "AnimationDurationFactor", float(SPEEDS[index]))
            ps.notify_settings(ps.SETTINGS_STYLE)

    @Slot()
    def resetTitleBar(self):
        for key in ("ButtonsOnLeft", "ButtonsOnRight"):
            ps.kdelete("kwinrc", DECORATION, key)
        ps.reload_kwin()
        self.refresh()

    @Slot()
    def resetEffects(self):
        for key in ("BlurStrength", "NoiseStrength"):
            ps.kdelete("kwinrc", "Effect-blur", key)
        ps.reconfigure_effect("blur")
        ps.kdelete("kdeglobals", "KDE", "AnimationDurationFactor")
        ps.notify_settings(ps.SETTINGS_STYLE)
        self.refresh()

    # -------------------------------------------------------------- corners --
    @Slot(int)
    def applyCornerRadius(self, radius):
        """Rebuilds just the Borealis window decoration with other corners, and swaps it in."""
        name = self._values.get("decoration", "")
        build = os.path.join(PROJECT, "build.py")
        if not name or not os.path.exists(build) or self.backend.busy:
            return
        radius = max(0, min(24, int(radius)))
        cache = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
        out = os.path.join(cache, "borealis", "corners", "share")
        slug = name.rsplit("-", 1)[0]
        themes = os.path.join(DATA, "aurorae", "themes")
        steps = [(f"building window corners of {radius} px",
                  ["python3", build, "aurorae", "--out", out, "--window-radius", str(radius),
                   *self.backend.build_flags()])]
        for variant in (f"{slug}-Dark", f"{slug}-Light"):
            steps.append((f"installing {variant}",
                          ["cp", "-rT", os.path.join(out, "aurorae", "themes", variant), os.path.join(themes, variant)]))
        # KWin keeps a decoration it already loaded: a moment on the other
        # variant makes it load this one afresh
        other = f"{slug}-Light" if name.endswith("-Dark") else f"{slug}-Dark"
        reload = ["dbus-send", "--session", "--type=signal", "/KWin", "org.kde.KWin.reloadConfig"]
        write_theme = ["kwriteconfig6", "--file", "kwinrc", "--group", DECORATION, "--key", "theme"]
        steps += [("reloading the decoration", write_theme + [AURORAE + other]), ("", reload), ("", ["sleep", "0.8"])]
        if self.config.own("kwinrc", DECORATION, "theme"):
            steps.append(("", write_theme + [AURORAE + name]))
        else:           # it came from the Global Theme's defaults: leave it to them again
            steps.append(("", [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                           "plasmasettings.py"), "revert", "kwinrc", DECORATION, "theme"]))
        steps.append(("asking KWin to redraw the windows", reload))
        self.backend._job(steps, f"Window corners are {radius} px now.")

    @Slot(bool, str)
    def _job_finished(self, ok, message):
        self.refresh()
