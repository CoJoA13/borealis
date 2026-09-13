"""Borealis Tweaks, the Text & Pointer page: the fonts and how they're drawn,
the pointer, and icon sizes in apps."""
import os
import xml.etree.ElementTree as ET

from PySide6.QtCore import Property, Slot
from PySide6.QtGui import QFont, QFontDatabase

import plasmasettings as ps
from backend import DATA

# page key: (kdeglobals group, key, Plasma's own default)
FONTS = {
    "font": ("General", "font", "Noto Sans,10"),
    "fixed": ("General", "fixed", "Hack,10"),
    "smallestReadableFont": ("General", "smallestReadableFont", "Noto Sans,8"),
    "toolBarFont": ("General", "toolBarFont", "Noto Sans,10"),
    "menuFont": ("General", "menuFont", "Noto Sans,10"),
    "activeFont": ("WM", "activeFont", "Noto Sans,10"),
}
HINTING = {"none": "hintnone", "slight": "hintslight", "medium": "hintmedium", "full": "hintfull"}
SUBPIXEL = ("none", "rgb", "bgr", "vrgb", "vbgr")
# page key: (kdeglobals group, KIconLoader's group number, its default size)
ICONS = {
    "toolbarIcons": ("ToolbarIcons", 1, 22),
    "mainToolbarIcons": ("MainToolbarIcons", 2, 22),
    "smallIcons": ("SmallIcons", 3, 16),
    "dialogIcons": ("DialogIcons", 5, 32),
}
CURSOR_SIZES = (24, 30, 36, 48, 60, 72, 96)
FONTCONFIG_HEADER = '<?xml version="1.0"?>\n<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">\n'


def font_from(text):
    font = QFont()
    if not font.fromString(text):
        font = QFont(text.split(",")[0])
    return font


def cursor_themes():
    """[{id, name}] for every pointer theme installed, yours before the system's."""
    homes = [os.path.join(DATA, "icons"), os.path.expanduser("~/.icons")]
    homes += [os.path.join(d, "icons") for d in
              (os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share").split(":") if d]
    found = {}
    for home in homes:
        try:
            entries = sorted(os.listdir(home))
        except OSError:
            continue
        for entry in entries:
            if entry not in found and os.path.isdir(os.path.join(home, entry, "cursors")):
                index = ps.parse(ps.read_text(os.path.join(home, entry, "index.theme")))
                found[entry] = index.get("Icon Theme", {}).get("Name", entry)
    return [{"id": k, "name": v} for k, v in sorted(found.items(), key=lambda kv: kv[1].lower())]


def write_rendering(antialias, hintstyle, rgba):
    """Anti-aliasing, hinting and sub-pixel order in ~/.config/fontconfig/fonts.conf,
    where Plasma's own font settings keep them: only those entries change."""
    path = os.path.join(ps.config_home(), "fontconfig", "fonts.conf")
    if os.path.exists(path):
        try:
            root = ET.fromstring(ps.read_text(path), parser=ET.XMLParser(target=ET.TreeBuilder(insert_comments=True)))
        except ET.ParseError:
            return False                # not a file to rewrite blind
        ps.backup(path, "fonts")
    else:
        root = ET.Element("fontconfig")
    wanted = (("antialias", "bool", "true" if antialias else "false"),
              ("hinting", "bool", "false" if hintstyle == "hintnone" else "true"),
              ("hintstyle", "const", hintstyle),
              ("rgba", "const", rgba),
              ("lcdfilter", "const", "lcdnone" if rgba == "none" else "lcddefault"))
    for name, kind, value in wanted:
        edit = None
        for match in root.findall("match"):
            edits = match.findall("edit")
            if match.get("target") == "font" and match.find("test") is None and len(edits) == 1 \
                    and edits[0].get("name") == name:
                edit = edits[0]
                break
        if edit is None:
            edit = ET.SubElement(ET.SubElement(root, "match", target="font"), "edit", mode="assign", name=name)
        for child in list(edit):
            edit.remove(child)
        ET.SubElement(edit, kind).text = value
    ET.indent(root, space=" ")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        f.write(FONTCONFIG_HEADER + ET.tostring(root, encoding="unicode") + "\n")
    os.replace(path + ".tmp", path)
    return True


class TextBackend(ps.PlasmaPage):
    def __init__(self, backend, parent=None):
        super().__init__(backend, parent)
        self._families = sorted(set(QFontDatabase.families()), key=str.lower)
        self._fixed = [f for f in self._families if QFontDatabase.isFixedPitch(f)]
        self._cursors = cursor_themes()
        self.refresh()

    families = Property("QVariantList", lambda self: self._families, constant=True)
    fixedFamilies = Property("QVariantList", lambda self: self._fixed, constant=True)
    cursorThemes = Property("QVariantList", lambda self: self._cursors, constant=True)
    cursorSizes = Property("QVariantList", lambda self: list(CURSOR_SIZES), constant=True)

    # ----------------------------------------------------------------- read --
    def read(self):
        c = self.config
        values = {}
        for key, (group, name, default) in FONTS.items():
            font = font_from(c.get("kdeglobals", group, name, default))
            size = font.pointSizeF() if font.pointSizeF() > 0 else 10
            values[key] = {"family": font.family(), "size": round(size, 1)}
        values["antialias"] = c.get_bool("kdeglobals", "General", "XftAntialias", True)
        hint = c.get("kdeglobals", "General", "XftHintStyle", "hintslight")
        values["hinting"] = next((k for k, v in HINTING.items() if v == hint), "slight")
        subpixel = c.get("kdeglobals", "General", "XftSubPixel", "none")
        values["subpixel"] = subpixel if subpixel in SUBPIXEL else "none"
        values["cursorTheme"] = c.get("kcminputrc", "Mouse", "cursorTheme", "breeze_cursors")
        values["cursorSize"] = c.get_int("kcminputrc", "Mouse", "cursorSize", 24)
        for key, (group, _number, default) in ICONS.items():
            values[key] = c.get_int("kdeglobals", group, "Size", default)
        return values

    # ---------------------------------------------------------------- write --
    def apply_changes(self, changes, merged):
        title_font = False
        for key, value in changes.items():
            if key in FONTS and isinstance(value, dict):
                group, name, default = FONTS[key]
                font = font_from(self.config.get("kdeglobals", group, name, default))
                if value.get("family"):
                    font.setFamily(str(value["family"]))
                if value.get("size"):
                    font.setPointSizeF(max(4.0, min(72.0, float(value["size"]))))
                ps.kwrite("kdeglobals", group, name, font.toString())
                title_font |= group == "WM"
            elif key in ICONS:
                group, number, _default = ICONS[key]
                ps.kwrite("kdeglobals", group, "Size", int(value))
                ps.signal("/KIconLoader", "org.kde.KIconLoader", "iconChanged", f"int32:{number}")
        if set(changes) & set(FONTS):
            ps.signal("/KDEPlatformTheme", "org.kde.KDEPlatformTheme", "refreshFonts")
            if title_font:
                ps.reload_kwin()
        if set(changes) & {"antialias", "hinting", "subpixel"}:
            self._rendering(merged)
        if set(changes) & {"cursorTheme", "cursorSize"}:
            self._pointer(str(merged["cursorTheme"]), int(merged["cursorSize"]))

    def _rendering(self, values):
        hintstyle = HINTING.get(values.get("hinting"), "hintslight")
        subpixel = values.get("subpixel") if values.get("subpixel") in SUBPIXEL else "none"
        ps.kwrite("kdeglobals", "General", "XftAntialias", bool(values.get("antialias", True)))
        ps.kwrite("kdeglobals", "General", "XftHintStyle", hintstyle)
        ps.kwrite("kdeglobals", "General", "XftSubPixel", subpixel)
        write_rendering(bool(values.get("antialias", True)), hintstyle, subpixel)
        ps.signal("/KDEPlatformTheme", "org.kde.KDEPlatformTheme", "refreshFonts")

    @staticmethod
    def _pointer(theme, size):
        ps.kwrite("kcminputrc", "Mouse", "cursorTheme", theme)
        ps.kwrite("kcminputrc", "Mouse", "cursorSize", size)
        ps.notify_settings(0, ps.CURSOR_CHANGED)
        ps.run_detached(["plasma-apply-cursortheme", theme, "--size", str(size)])

    @Slot()
    def resetFonts(self):
        for group, name, _default in FONTS.values():
            ps.kdelete("kdeglobals", group, name)
        ps.signal("/KDEPlatformTheme", "org.kde.KDEPlatformTheme", "refreshFonts")
        ps.reload_kwin()
        self.refresh()

    @Slot()
    def resetRendering(self):
        for name in ("XftAntialias", "XftHintStyle", "XftSubPixel"):
            ps.kdelete("kdeglobals", "General", name)
        write_rendering(True, "hintslight", "none")
        ps.signal("/KDEPlatformTheme", "org.kde.KDEPlatformTheme", "refreshFonts")
        self.refresh()

    @Slot()
    def resetPointer(self):
        for name in ("cursorTheme", "cursorSize"):
            ps.kdelete("kcminputrc", "Mouse", name)
        self.config = ps.Config()
        self._pointer(self.config.get("kcminputrc", "Mouse", "cursorTheme", "breeze_cursors"), 24)
        self.refresh()

    @Slot()
    def resetIcons(self):
        for group, number, _default in ICONS.values():
            ps.kdelete("kdeglobals", group, "Size")
            ps.signal("/KIconLoader", "org.kde.KIconLoader", "iconChanged", f"int32:{number}")
        self.refresh()
