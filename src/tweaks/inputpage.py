"""Borealis Tweaks, the Touchpad & Keys page: the touchpad as KWin drives it
(KWin keeps what's set here), and the shortcuts people most often change."""
from PySide6.QtCore import Property, Signal, Slot
from PySide6.QtGui import QKeySequence

import ids
import plasmasettings as ps

KWIN = "org.kde.KWin"
DEVICES = "/org/kde/KWin/InputDevice"
DEVICE = "org.kde.KWin.InputDevice"
# Plasma's own scroll speed steps
SCROLL_FACTORS = (0.1, 0.3, 0.5, 0.75, 1, 1.5, 2, 3, 4, 5, 7, 9, 12, 15, 20)
# page key: (KWin's property, the property saying the touchpad can, the one with its default)
TOGGLES = {
    "tapToClick": ("tapToClick", None, "tapToClickEnabledByDefault"),
    "tapAndDrag": ("tapAndDrag", None, "tapAndDragEnabledByDefault"),
    "tapDragLock": ("tapDragLock", None, "tapDragLockEnabledByDefault"),
    "naturalScroll": ("naturalScroll", "supportsNaturalScroll", "naturalScrollEnabledByDefault"),
    "disableWhileTyping": ("disableWhileTyping", "supportsDisableWhileTyping", "disableWhileTypingEnabledByDefault"),
    "disableWithMouse": ("disableEventsOnExternalMouse", "supportsDisableEventsOnExternalMouse",
                         "disableEventsOnExternalMouseEnabledByDefault"),
    "leftHanded": ("leftHanded", "supportsLeftHanded", "leftHandedEnabledByDefault"),
    "middleEmulation": ("middleEmulation", "supportsMiddleEmulation", "middleEmulationEnabledByDefault"),
}
LAUNCHPAD = getattr(ids, "LAUNCHPAD_SHORTCUT", f"{ids.NAME} Dock: Launchpad")
META = 0x01000022                       # a lone Meta, as kglobalaccel stores it
# (component, action, what the page calls it)
SHORTCUTS = (
    ("kwin", LAUNCHPAD, "Launchpad"),
    ("kwin", "Overview", "Overview"),
    ("kwin", "Grid View", "All desktops at a glance"),
    ("kwin", "Expose", "Windows on this desktop"),
    ("kwin", "Show Desktop", "Peek at the desktop"),
    ("org_kde_krunner_desktop", "_launch", "Search"),
    ("ksmserver", "Lock Session", "Lock the screen"),
    ("org_kde_spectacle_desktop", "RectangularRegionScreenShot", "Screenshot of a region"),
    ("org_kde_spectacle_desktop", "FullScreenScreenShot", "Screenshot of the whole screen"),
    ("org_kde_spectacle_desktop", "RecordRegion", "Record a region"),
    ("kwin", "Switch One Desktop to the Left", "Desktop to the left"),
    ("kwin", "Switch One Desktop to the Right", "Desktop to the right"),
)


def key_text(combined):
    return QKeySequence(combined).toString(QKeySequence.SequenceFormat.PortableText)


class InputBackend(ps.PlasmaPage):
    notice = Signal(str)

    def __init__(self, backend, parent=None):
        super().__init__(backend, parent)
        self._device = ""
        self._props = {}
        self._shortcuts = {}
        self.refresh()

    # ------------------------------------------------------------- touchpad --
    def _find_touchpad(self):
        names = ps.get_property(KWIN, DEVICES, "org.kde.KWin.InputDeviceManager", "devicesSysNames") or []
        for name in names:
            if ps.get_property(KWIN, f"{DEVICES}/{name}", DEVICE, "touchpad") is True:
                return name
        return ""

    def _read_touchpad(self):
        if not self._device:
            self._device = self._find_touchpad()
        if not self._device:
            return {}
        reply = ps.ask_json(["busctl", "--user", "--json=short", "call", KWIN, f"{DEVICES}/{self._device}",
                             "org.freedesktop.DBus.Properties", "GetAll", "s", DEVICE])
        try:
            raw = reply["data"][0]
        except (TypeError, KeyError, IndexError):
            self._device = ""               # unplugged, or KWin restarted: look again next time
            return {}
        return {k: v.get("data") for k, v in raw.items() if isinstance(v, dict)}

    def _set(self, prop, signature, value):
        ps.set_property(KWIN, f"{DEVICES}/{self._device}", DEVICE, prop, signature, value)

    # ------------------------------------------------------------ shortcuts --
    def _read_shortcuts(self):
        found = {}
        for component in dict.fromkeys(c for c, _a, _l in SHORTCUTS):
            reply = ps.ask_json(["busctl", "--user", "--json=short", "call", "org.kde.kglobalaccel",
                                 f"/component/{component}", "org.kde.kglobalaccel.Component", "allShortcutInfos"])
            try:
                infos = reply["data"][0]
            except (TypeError, KeyError, IndexError):
                continue
            for info in infos:
                # (action, action's name, component, component's name, context, context's name, keys, defaults)
                found[(component, info[0])] = {"friendly": info[1], "componentFriendly": info[3],
                                               "keys": [k for k in info[6] if k], "defaults": [k for k in info[7] if k]}
        return found

    def _write_keys(self, component, action, keys):
        info = self._shortcuts.get((component, action))
        if info is None:
            return
        argv = ["busctl", "--user", "call", "org.kde.kglobalaccel", "/kglobalaccel", "org.kde.KGlobalAccel",
                "setForeignShortcutKeys", "asa(ai)", "4", component, action, info["componentFriendly"],
                info["friendly"], str(len(keys))]
        for key in keys:
            argv += ["1", str(key)]
        ps.run(argv)

    # ----------------------------------------------------------------- read --
    def read(self):
        props = self._read_touchpad()
        self._props = props
        values = {"touchpad": str(props.get("name", "")) if props else ""}
        if props:
            for key, (prop, supports, _default) in TOGGLES.items():
                values[key] = props.get(prop) is True
                values["can_" + key] = supports is None or props.get(supports) is True
            values["canTap"] = int(props.get("tapFingerCount") or 0) > 0
            values["twoFingerTap"] = "middle" if props.get("lmrTapButtonMap") else "right"
            values["canTwoFingerTap"] = props.get("supportsLmrTapButtonMap") is True
            values["rightClick"] = "twoFingers" if props.get("clickMethodClickfinger") else "corner"
            values["canRightClick"] = props.get("supportsClickMethodAreas") is True \
                and props.get("supportsClickMethodClickfinger") is True
            values["scrollMethod"] = "edge" if props.get("scrollEdge") else "twoFingers"
            values["canScrollMethod"] = props.get("supportsScrollEdge") is True \
                and props.get("supportsScrollTwoFinger") is True
            factor = float(props.get("scrollFactor") or 1)
            values["scrollSpeed"] = min(range(len(SCROLL_FACTORS)), key=lambda i: abs(SCROLL_FACTORS[i] - factor))
            values["pointerSpeed"] = int(round(float(props.get("pointerAcceleration") or 0) * 100))
            values["acceleration"] = props.get("pointerAccelerationProfileFlat") is not True
            values["canAccelerate"] = props.get("supportsPointerAcceleration") is True
        self._shortcuts = self._read_shortcuts()
        rows = []
        for component, action, label in SHORTCUTS:
            info = self._shortcuts.get((component, action))
            if info is None:
                continue
            keys = [k for k in info["keys"] if k != META]
            rows.append({"id": f"{component}\t{action}", "label": label,
                         "key": key_text(keys[0]) if keys else "",
                         "others": ", ".join(key_text(k) for k in keys[1:]),
                         "isDefault": sorted(info["keys"]) == sorted(info["defaults"])})
        values["shortcuts"] = rows
        launchpad = self._shortcuts.get(("kwin", LAUNCHPAD))
        values["hasLaunchpad"] = launchpad is not None
        values["launchpadMeta"] = bool(launchpad) and META in launchpad["keys"]
        return values

    # ---------------------------------------------------------------- write --
    def apply_changes(self, changes, merged):
        if self._device:
            for key, value in changes.items():
                if key in TOGGLES:
                    self._set(TOGGLES[key][0], "b", bool(value))
                elif key == "twoFingerTap":
                    self._set("lmrTapButtonMap", "b", value == "middle")
                elif key == "rightClick":
                    # as Plasma's page does it: one method on, the other off
                    self._set("clickMethodAreas", "b", value == "corner")
                    self._set("clickMethodClickfinger", "b", value == "twoFingers")
                elif key == "scrollMethod":
                    self._set("scrollTwoFinger", "b", value == "twoFingers")
                    self._set("scrollEdge", "b", value == "edge")
                elif key == "scrollSpeed":
                    index = max(0, min(len(SCROLL_FACTORS) - 1, round(value)))
                    self._set("scrollFactor", "d", float(SCROLL_FACTORS[index]))
                elif key == "pointerSpeed":
                    self._set("pointerAcceleration", "d", max(-1.0, min(1.0, round(value) / 100)))
                elif key == "acceleration":
                    self._set("pointerAccelerationProfileFlat", "b", not value)
                    self._set("pointerAccelerationProfileAdaptive", "b", bool(value))
        if "launchpadMeta" in changes:
            info = self._shortcuts.get(("kwin", LAUNCHPAD))
            if info is not None:
                keys = [k for k in info["keys"] if k != META] + ([META] if changes["launchpadMeta"] else [])
                self._write_keys("kwin", LAUNCHPAD, keys)

    @Slot()
    def resetTouchpad(self):
        props = self._props
        if not self._device or not props:
            return
        for prop, _supports, default in TOGGLES.values():
            if default in props:
                self._set(prop, "b", props[default] is True)
        if "lmrTapButtonMapEnabledByDefault" in props:
            self._set("lmrTapButtonMap", "b", props["lmrTapButtonMapEnabledByDefault"] is True)
        if "defaultClickMethodAreas" in props:
            self._set("clickMethodAreas", "b", props["defaultClickMethodAreas"] is True)
            self._set("clickMethodClickfinger", "b", props.get("defaultClickMethodClickfinger") is True)
        if "scrollTwoFingerEnabledByDefault" in props:
            self._set("scrollTwoFinger", "b", props["scrollTwoFingerEnabledByDefault"] is True)
            self._set("scrollEdge", "b", props.get("scrollEdgeEnabledByDefault") is True)
        self._set("scrollFactor", "d", 1.0)
        if "defaultPointerAcceleration" in props:
            self._set("pointerAcceleration", "d", float(props["defaultPointerAcceleration"]))
        if "defaultPointerAccelerationProfileFlat" in props:
            self._set("pointerAccelerationProfileFlat", "b", props["defaultPointerAccelerationProfileFlat"] is True)
            self._set("pointerAccelerationProfileAdaptive", "b",
                      props.get("defaultPointerAccelerationProfileAdaptive") is True)
        self.refresh()

    @Slot(str, "QVariant")
    def setShortcut(self, row_id, sequence):
        """The shortcut's main key; an empty sequence takes it away. Its other keys stay."""
        component, _, action = row_id.partition("\t")
        info = self._shortcuts.get((component, action))
        if info is None:
            return
        if not isinstance(sequence, QKeySequence):
            sequence = QKeySequence(str(sequence or ""))
        new = sequence[0].toCombined() if sequence.count() > 0 else 0
        rest = [k for k in info["keys"] if k != META][1:]
        keys = ([new] if new else []) + [k for k in rest if k != new]
        if META in info["keys"] and component == "kwin" and action == LAUNCHPAD:
            keys.append(META)
        self._write_keys(component, action, keys)
        self.refresh()
        if new and new not in self._shortcuts.get((component, action), {}).get("keys", []):
            self.notice.emit(f"{key_text(new)} is taken by another shortcut; pick another key, or free it "
                             "in System Settings › Shortcuts.")

    @Slot(str)
    def resetShortcut(self, row_id):
        component, _, action = row_id.partition("\t")
        info = self._shortcuts.get((component, action))
        if info is not None:
            self._write_keys(component, action, info["defaults"])
            self.refresh()
