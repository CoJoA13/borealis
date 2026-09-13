"""Borealis Tweaks, the Desktop page: virtual desktops, hot corners and screen
edges, night light, and whether one click opens files."""
import re

from PySide6.QtCore import Slot

import plasmasettings as ps

KWIN = "org.kde.KWin"
DESKTOPS = "/VirtualDesktopManager"
DESKTOPS_IFACE = "org.kde.KWin.VirtualDesktopManager"
# page key: (kwinrc [ElectricBorders] key, KWin's number for that corner)
CORNERS = {"topLeft": ("TopLeft", 7), "topRight": ("TopRight", 1),
           "bottomLeft": ("BottomLeft", 5), "bottomRight": ("BottomRight", 3)}
# what a corner can do: KWin's own actions...
ACTIONS = {"desktop": "ShowDesktop", "lock": "LockScreen", "search": "KRunner"}
# ...and effects, by (group, key, KWin's default corners)
EFFECTS = {
    "overview": ("Effect-overview", "BorderActivate", (7,)),
    "grid": ("Effect-overview", "GridBorderActivate", ()),
    "windows": ("Effect-windowview", "BorderActivateAll", ()),
}
NIGHT_DAY_TEMPERATURE = 6500


def clock(value, default):
    """A time of day as "06:30", from "06:30", "06:30:00" or "0630"."""
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) in (3, 4):
        digits = digits.zfill(4)
        if int(digits[:2]) < 24 and int(digits[2:]) < 60:
            return f"{digits[:2]}:{digits[2:]}"
    return default


class DesktopBackend(ps.PlasmaPage):
    def __init__(self, backend, parent=None):
        super().__init__(backend, parent)
        self.refresh()

    # ----------------------------------------------------------------- read --
    def _desktops(self):
        raw = ps.get_property(KWIN, DESKTOPS, DESKTOPS_IFACE, "desktops") or []
        desktops = [{"index": int(d[0]), "id": str(d[1]), "name": str(d[2])} for d in raw
                    if isinstance(d, list) and len(d) >= 3]
        return sorted(desktops, key=lambda d: d["index"])

    def read(self):
        c = self.config
        desktops = self._desktops()
        values = {"desktops": desktops, "desktopCount": max(1, len(desktops)),
                  "rows": int(ps.get_property(KWIN, DESKTOPS, DESKTOPS_IFACE, "rows") or 1),
                  "wrapAround": c.get_bool("kwinrc", "Windows", "RollOverDesktops", False)}
        lists = {name: c.get_ints("kwinrc", group, key, default) for name, (group, key, default) in EFFECTS.items()}
        for page_key, (name, border) in CORNERS.items():
            choice = next((effect for effect, borders in lists.items() if border in borders), None)
            if choice is None:
                action = c.get("kwinrc", "ElectricBorders", name, "None")
                choice = next((k for k, v in ACTIONS.items() if v == action), "none" if action == "None" else "other")
            values[page_key] = choice
        values["edgeSwitch"] = c.get_int("kwinrc", "Windows", "ElectricBorders", 0)
        active = c.get_bool("kwinrc", "NightColor", "Active", False)
        mode = c.get("kwinrc", "NightColor", "Mode", "DarkLight")
        values["nightLight"] = "off" if not active else "always" if mode == "Constant" else "sunset"
        values["nightTemperature"] = c.get_int("kwinrc", "NightColor", "NightTemperature", 4500)
        values["nightSchedule"] = "times" if c.get("knighttimerc", "General", "Source", "") == "Times" else "location"
        values["sunrise"] = clock(c.get("knighttimerc", "Times", "SunriseStart"), "06:00")
        values["sunset"] = clock(c.get("knighttimerc", "Times", "SunsetStart"), "18:00")
        values["singleClick"] = c.get_bool("kdeglobals", "KDE", "SingleClick", False)
        return values

    # ---------------------------------------------------------------- write --
    def apply_changes(self, changes, merged):
        if "desktopCount" in changes:
            self._set_count(max(1, min(20, int(changes["desktopCount"]))))
        if "rows" in changes:
            ps.set_property(KWIN, DESKTOPS, DESKTOPS_IFACE, "rows", "u", max(1, min(8, int(changes["rows"]))))
        kwin = False
        if "wrapAround" in changes:
            ps.kwrite("kwinrc", "Windows", "RollOverDesktops", bool(changes["wrapAround"]))
            kwin = True
        if set(changes) & set(CORNERS):
            self._set_corners(changes)
            kwin = True
        if "edgeSwitch" in changes:
            ps.kwrite("kwinrc", "Windows", "ElectricBorders", max(0, min(2, int(changes["edgeSwitch"]))))
            kwin = True
        if kwin:
            ps.reload_kwin()
        if "nightLight" in changes:
            mode = changes["nightLight"]
            ps.kwrite("kwinrc", "NightColor", "Active", mode != "off")
            if mode != "off":
                ps.kwrite("kwinrc", "NightColor", "Mode", "Constant" if mode == "always" else "DarkLight")
        if "nightTemperature" in changes:
            ps.kwrite("kwinrc", "NightColor", "NightTemperature",
                      max(1000, min(NIGHT_DAY_TEMPERATURE, round(changes["nightTemperature"] / 100) * 100)))
        if set(changes) & {"nightSchedule", "sunrise", "sunset"}:
            if merged.get("nightSchedule") == "times":
                # knighttimed reads set times from their own group, as 19:30
                ps.kwrite("knighttimerc", "General", "Source", "Times")
                for key, name in (("sunrise", "SunriseStart"), ("sunset", "SunsetStart")):
                    text = clock(merged.get(key), "")
                    if text:
                        ps.kwrite("knighttimerc", "Times", name, text)
            else:
                ps.kdelete("knighttimerc", "General", "Source")
        if "singleClick" in changes:
            ps.kwrite("kdeglobals", "KDE", "SingleClick", bool(changes["singleClick"]))
            ps.notify_settings(ps.SETTINGS_MOUSE)

    def _set_count(self, count):
        desktops = self._desktops()
        for position in range(len(desktops), count):
            ps.call(KWIN, DESKTOPS, DESKTOPS_IFACE, "createDesktop", "us", position, f"Desktop {position + 1}")
        for desktop in desktops[count:][::-1]:
            ps.call(KWIN, DESKTOPS, DESKTOPS_IFACE, "removeDesktop", "s", desktop["id"])

    def _set_corners(self, changes):
        c = self.config
        lists = {name: c.get_ints("kwinrc", group, key, default) for name, (group, key, default) in EFFECTS.items()}
        for page_key, choice in changes.items():
            if page_key not in CORNERS:
                continue
            name, border = CORNERS[page_key]
            for borders in lists.values():
                while border in borders:
                    borders.remove(border)
            if choice in EFFECTS:
                lists[choice].append(border)
            ps.kwrite("kwinrc", "ElectricBorders", name, ACTIONS.get(choice, "None"))
        for effect, (group, key, _default) in EFFECTS.items():
            ps.kwrite("kwinrc", group, key, ",".join(str(b) for b in sorted(lists[effect])))
        for effect in dict.fromkeys(group for group, _k, _d in EFFECTS.values()):
            ps.reconfigure_effect(effect.split("-", 1)[1])

    @Slot(str, str)
    def renameDesktop(self, desktop_id, name):
        name = name.strip()
        if desktop_id and name:
            ps.call(KWIN, DESKTOPS, DESKTOPS_IFACE, "setDesktopName", "ss", desktop_id, name)
            self._reread.start()

    @Slot()
    def resetCorners(self):
        for name, _border in CORNERS.values():
            ps.kdelete("kwinrc", "ElectricBorders", name)
        for group, key, _default in EFFECTS.values():
            ps.kdelete("kwinrc", group, key)
        ps.kdelete("kwinrc", "Windows", "ElectricBorders")
        ps.reload_kwin()
        ps.reconfigure_effect("overview")
        ps.reconfigure_effect("windowview")
        self.refresh()

    @Slot()
    def resetNightLight(self):
        for key in ("Active", "Mode", "NightTemperature"):
            ps.kdelete("kwinrc", "NightColor", key)
        ps.kdelete("knighttimerc", "General", "Source")
        for key in ("SunriseStart", "SunsetStart"):
            ps.kdelete("knighttimerc", "Times", key)
        self.refresh()
