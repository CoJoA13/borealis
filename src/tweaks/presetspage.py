"""Borealis Tweaks, the Presets page: the whole desktop in one go.

A preset goes through the other pages' own backends, so it changes exactly
what those pages would. When it changes the theme, that comes first: switching
between Dark and Light, or rebuilding the palette, applies the Global Theme
again, and the rest follows once that's done. The desktop as it was before a
preset is kept as a preset of its own, for Undo (and as a file in
~/.local/state/borealis/presets-undo, should Tweaks be closed in between).
"""
import glob
import os
import time

from PySide6.QtCore import Property, QObject, QTimer, QUrl, Signal, Slot

import desktoppresets as desk
import plasmasettings as ps
from dockpage import dockpresets, ids

UNDO_KEPT = 10


def local_path(url):
    url = str(url)
    return QUrl(url).toLocalFile() if url.startswith("file:") else url


def undo_dir():
    return os.path.join(ps.state_home(), ids.SLUG, "presets-undo")


class PresetsBackend(QObject):
    changed = Signal()
    stateChanged = Signal()

    def __init__(self, backend, dock, bar, windows, desktop, parent=None):
        super().__init__(parent)
        self.backend, self.dock, self.bar, self.windows, self.desktop = backend, dock, bar, windows, desktop
        self._queue = []            # what waits for the theme's job to finish
        self._undo = None
        self._applied = ""
        self._list = None
        # the other pages change often and in bursts: look again once they settle
        self._stale = QTimer(self, singleShot=True, interval=200)
        self._stale.timeout.connect(self._refresh)
        for source in (dock.changed, bar.changed, windows.changed, desktop.changed, backend.changed):
            source.connect(self._soon)
        backend.finished.connect(self._job_finished)

    @Slot()
    def _soon(self):
        self._stale.start()

    def _refresh(self):
        self._list = None
        self.changed.emit()

    # ---------------------------------------------------------------- state --
    def current_state(self):
        """The desktop as it is, a section for each part a preset can set."""
        b = self.backend
        windows = {k: v for k, v in self.windows.values.items() if k in desk.WINDOWS_DEFAULTS}
        if not self.windows.values.get("decoration"):
            windows.pop("cornerRadius", None)
        return {"theme": {"variant": b.variant, "accent": b.accent.lower(), "name": b.paletteName,
                          "liveWallpaper": b.liveWallpaper},
                "dock": desk.clean_section("dock", self.dock.values),
                "dockApps": dockpresets.clean_apps(self.dock.values),
                "bar": desk.bar_look(self.bar.values), "controls": desk.bar_controls(self.bar.values),
                "windows": windows,
                "desktop": {k: v for k, v in self.desktop.values.items() if k in desk.DESKTOP_DEFAULTS}}

    @staticmethod
    def _describe(preset, current):
        theme, now = preset["sections"].get("theme", {}), current["theme"]
        return {"id": preset["id"], "name": preset["name"], "description": preset["description"],
                "builtin": preset["builtin"], "current": desk.matches(current, preset),
                "sections": [s for s in desk.SECTIONS if s in preset["sections"]]
                            + (["dockApps"] if preset.get("dockApps") else []),
                "variant": theme.get("variant", ""),
                "variantChanges": theme.get("variant", now["variant"]) != now["variant"],
                "paletteName": theme.get("name", ""), "accent": theme.get("accent", ""),
                "remix": "accent" in theme and (theme["accent"] != now["accent"] or theme["name"] != now["name"]),
                "liveWallpaper": theme.get("liveWallpaper"),
                "thumb": desk.thumb(preset, current)}

    @Property("QVariantList", notify=changed)
    def presets(self):
        if self._list is None:
            current = self.current_state()
            self._list = [self._describe(p, current) for p in desk.all_presets()]
        return self._list

    @Property(str, notify=stateChanged)
    def lastApplied(self):
        return self._applied

    @Property(bool, notify=stateChanged)
    def canUndo(self):
        return self._undo is not None

    @Property(str, constant=True)
    def folder(self):
        return desk.presets_dir()

    # ------------------------------------------------------------- applying --
    @Slot(str, "QVariant", bool)
    def apply(self, preset_id, sections, remix):
        """The chosen sections of a preset ("dockApps" for its apps); remix: rebuild
        the theme in the preset's colours when they aren't the ones in use."""
        preset = desk.find(preset_id)
        if preset is None or self.backend.busy or self._queue:
            return
        chosen = [s for s in ps.plain(sections) or []
                  if s in preset["sections"] or (s == "dockApps" and preset.get("dockApps"))]
        if not chosen:
            return
        self._undo = self._snapshot()
        self._applied = preset["name"]
        self._run(preset, chosen, remix)
        self.stateChanged.emit()

    @Slot()
    def undo(self):
        if self._undo is None or self.backend.busy or self._queue:
            return
        preset, self._undo, self._applied = self._undo, None, ""
        self._run(preset, list(preset["sections"]) + (["dockApps"] if preset.get("dockApps") else []), True)
        self.stateChanged.emit()

    def _snapshot(self):
        """The desktop as it is, as a preset; also written down, in case Tweaks closes."""
        current = self.current_state()
        preset = {"id": "", "name": "Before", "description": "", "builtin": False,
                  "sections": {s: current[s] for s in desk.SECTIONS if current.get(s)},
                  "dockApps": current["dockApps"]}
        folder = undo_dir()
        try:
            desk.write(os.path.join(folder, time.strftime("%Y%m%d-%H%M%S") + ".json"),
                       "Before " + time.strftime("%Y-%m-%d %H:%M"), preset["sections"], preset["dockApps"])
            for old in sorted(glob.glob(os.path.join(folder, "*.json")))[:-UNDO_KEPT]:
                os.remove(old)
        except OSError:
            pass
        return preset

    def _run(self, preset, chosen, remix):
        sections = preset["sections"]
        if "dock" in chosen or "dockApps" in chosen:
            changes = dict(sections["dock"]) if "dock" in chosen else {}
            if "dockApps" in chosen and preset.get("dockApps"):
                changes.update(preset["dockApps"])
            self.dock._write()
            self.dock.settings.update(changes)
        if "bar" in chosen or "controls" in chosen:
            changes = {**(sections["bar"] if "bar" in chosen else {}),
                       **(sections["controls"] if "controls" in chosen else {})}
            self.bar._write()
            self.bar.settings.update(changes)
        theme = sections.get("theme", {}) if "theme" in chosen else {}
        # a Global Theme applied afresh would take these back: they wait for it,
        # and the corners, a job of their own, go last
        self._queue = ([lambda: self._live(theme["liveWallpaper"])] if "liveWallpaper" in theme else []) \
            + ([lambda: self._desktop(sections["desktop"])] if "desktop" in chosen else []) \
            + ([lambda: self._windows(sections["windows"])] if "windows" in chosen else [])
        if not self._theme(theme, remix):
            self._next()

    def _theme(self, theme, remix):
        """Starts the theme's job when the preset changes the theme; True if one runs."""
        b = self.backend
        variant = theme.get("variant", b.variant)
        if remix and "accent" in theme and b.hasProject \
                and (theme["accent"] != b.accent.lower() or theme["name"] != b.paletteName):
            b.remix_to(theme["accent"], theme["name"], b.gtkColors, b.terminalKit, variant)
            return True
        if variant != b.variant:
            b.setVariant(variant)
            return True
        return False

    def _live(self, on):
        if on != self.backend.liveWallpaper:
            self.backend.setLiveWallpaper(on)

    def _desktop(self, wanted):
        page = self.desktop
        values = page.values
        for key, value in wanted.items():
            if not desk.same(values.get(key), value):
                page.set(key, value)
        page._apply_pending()

    def _windows(self, wanted):
        page = self.windows
        page.refresh()                  # a new palette brings a decoration of its own
        values = page.values
        for key, value in wanted.items():
            if key != "cornerRadius" and not desk.same(values.get(key), value):
                page.set(key, value)
        page._apply_pending()
        radius = wanted.get("cornerRadius")
        if radius is not None and values.get("decoration") and self.backend.hasProject \
                and int(values.get("cornerRadius", 12)) != radius:
            page.applyCornerRadius(radius)

    @Slot(bool, str)
    def _job_finished(self, ok, message):
        self._next()

    def _next(self):
        while self._queue and not self.backend.busy:
            self._queue.pop(0)()
        self._refresh()

    # ---------------------------------------------------------------- files --
    def _current_sections(self, with_apps):
        self.dock._write()
        self.bar._write()
        current = self.current_state()
        return ({s: current[s] for s in desk.SECTIONS if current.get(s)},
                current["dockApps"] if with_apps else None)

    @Slot(str, bool, result=str)
    def savePreset(self, name, with_apps):
        name = " ".join(str(name).split())
        if not name:
            return ""
        sections, apps = self._current_sections(with_apps)
        preset_id = desk.save_user(name, sections, apps)
        self._refresh()
        return preset_id

    @Slot(str)
    def deletePreset(self, preset_id):
        if desk.delete_user(preset_id):
            self._refresh()

    @Slot(str, result=str)
    def importPreset(self, url):
        try:
            preset_id = desk.import_file(local_path(url))
        except (ValueError, OSError) as e:
            return f"error:{e}"
        self._refresh()
        return preset_id

    @Slot(str, bool, result=str)
    def exportPreset(self, url, with_apps):
        path = local_path(url)
        if not path.endswith(".json"):
            path += ".json"
        sections, apps = self._current_sections(with_apps)
        try:
            return desk.write(path, os.path.splitext(os.path.basename(path))[0], sections, apps)
        except OSError as e:
            return f"error:{e.strerror or e}"
