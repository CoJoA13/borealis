"""Borealis design tokens — single source of truth for every generator.

A different accent can be passed in (`build.py --accent '#ff8a5b' --name
"Borealis Ember"`, which sets BOREALIS_ACCENT / BOREALIS_NAME): every colour
below, and the scene and glyph colours in the other generators, are rotated
around the colour wheel by the same angle, so a remix stays coherent. With no
accent given nothing is transformed and the output is the original Borealis.
"""
import os

NAME = os.environ.get("BOREALIS_NAME", "Borealis").strip() or "Borealis"
SLUG = "".join(NAME.split())
VERSION = "1.0"
AUTHOR = "cjones"
EMAIL = "CoJoA13@users.noreply.github.com"
LICENSE = "GPL-3.0-or-later"

RADIUS = 12          # windows, panels, popups
RADIUS_CTRL = 8      # buttons, fields, list highlights
RADIUS_SMALL = 6     # tooltips, small chips
FROST_OPACITY = 0.80 # panels / popups (blur behind)

# Package ids and display names (a remix ships alongside the original)
TITLES = {"dark": f"{NAME} Dark", "light": f"{NAME} Light"}
IDS = {
    "lnf_dark": f"{SLUG}-Dark", "lnf_light": f"{SLUG}-Light",
    "colors_dark": f"{SLUG}Dark", "colors_light": f"{SLUG}Light",
    "icons_dark": f"{SLUG}-Dark", "icons_light": f"{SLUG}-Light",
    "aurorae_dark": f"{SLUG}-Dark", "aurorae_light": f"{SLUG}-Light",
    "cursors_dark": f"{SLUG}-Snow-Cursors", "cursors_light": f"{SLUG}-Ink-Cursors",
    "cursors_dark_name": f"{NAME} Snow", "cursors_light_name": f"{NAME} Ink",
    "style": SLUG, "wallpaper": SLUG, "wallpaper_lock": f"{SLUG}-Lock",
    "sounds": SLUG, "live": f"org.{SLUG.lower()}.aurora", "plymouth": SLUG.lower(),
    "kate_dark": f"{SLUG.lower()}dark", "kate_light": f"{SLUG.lower()}light",
    "dock": f"org.{SLUG.lower()}.dock", "quicksettings": f"org.{SLUG.lower()}.quicksettings",
    "logo": SLUG.lower(),
}


# --------------------------------------------------------------- remix ----
def _hue_of(hex_color):
    import colorsys
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return colorsys.rgb_to_hls(r, g, b)[0]


ACCENT = (os.environ.get("BOREALIS_ACCENT") or "").strip()
SATURATION = float(os.environ.get("BOREALIS_SATURATION", "1") or 1)
# every colour is rotated by the angle between the requested accent and ours
HUE_SHIFT = (_hue_of(ACCENT) - _hue_of("#8b9cff")) % 1.0 if ACCENT else 0.0
REMIX = bool(ACCENT) or SATURATION != 1.0


def remix(hex_color):
    """Rotate one colour into the remixed palette (identity by default)."""
    if not REMIX:
        return hex_color
    import colorsys
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return hex_color
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    hue, lig, sat = colorsys.rgb_to_hls(r, g, b)
    hue = (hue + HUE_SHIFT) % 1.0
    sat = min(1.0, sat * SATURATION)
    r, g, b = colorsys.hls_to_rgb(hue, lig, sat)
    return "#%02x%02x%02x" % tuple(round(c * 255) for c in (r, g, b))


def remix_text(text):
    """Rotate every #rrggbb and 0xrrggbb in generated markup (SVG, CSS, ...)."""
    if not REMIX:
        return text
    import re
    return re.sub(r"(#|0x)([0-9a-fA-F]{6})\b",
                  lambda m: m.group(1) + remix("#" + m.group(2)).lstrip("#"), text)


# Brand hues (shared by both variants; each variant picks tints of these)
AURORA_TEAL = "#5fe0c8"
PERIWINKLE = "#8b9cff"
VIOLET = "#b18cff"
ROSE = "#ff6b81"
AMBER = "#ffc46b"

DARK = {
    "id": "dark",
    "title": TITLES["dark"],
    # surfaces, deepest -> highest
    "base": "#0e121b",       # deepest (complementary, splash, lock)
    "view": "#11151f",       # content areas: lists, editors
    "window": "#161b27",     # chrome: toolbars, dialogs
    "header": "#1a2030",     # headers / titlebars
    "header_inactive": "#151a26",
    "button": "#222a3b",
    "button_alt": "#1c2333",
    "tooltip": "#1c2231",
    "border": "#2a3246",     # hairlines on surfaces
    "border_strong": "#3a4258",
    # text
    "text": "#e6e9f2",
    "text_inactive": "#8f97ab",
    "text_disabled": "#5a6278",
    # accents
    "accent": "#8b9cff",
    "accent_hover": "#a3b1ff",
    "accent_pressed": "#7383f0",
    "on_accent": "#0b0f19",
    "secondary": "#5fe0c8",
    "link": "#8b9cff",
    "visited": "#b18cff",
    "positive": "#5fe0c8",
    "neutral": "#ffc46b",
    "negative": "#ff6b81",
    # titlebar pills (minimize, maximize, close)
    "pill_min": "#5fe0c8",
    "pill_max": "#8b9cff",
    "pill_close": "#ff6b81",
    "pill_other": "#3a4258",
    "pill_inactive": "#2e3548",
    "pill_glyph": "#0b0f19",
    "shadow": "#000000",
    "is_dark": True,
}

LIGHT = {
    "id": "light",
    "title": TITLES["light"],
    "base": "#e4e8f2",
    "view": "#fbfcfe",
    "window": "#eef1f7",
    "header": "#e6eaf3",
    "header_inactive": "#edf0f6",
    "button": "#f8f9fc",
    "button_alt": "#eceff6",
    "tooltip": "#f8f9fc",
    "border": "#d5dbe8",
    "border_strong": "#bcc4d6",
    "text": "#1b2130",
    "text_inactive": "#5d6680",
    "text_disabled": "#a2aabd",
    "accent": "#5566e0",
    "accent_hover": "#6b7bea",
    "accent_pressed": "#4757cf",
    "on_accent": "#ffffff",
    "secondary": "#139c86",
    "link": "#4c5ed8",
    "visited": "#8a55d9",
    "positive": "#12957f",
    "neutral": "#c7831a",
    "negative": "#d93f5a",
    "pill_min": "#2fc4a9",
    "pill_max": "#6f80f0",
    "pill_close": "#ef5b73",
    "pill_other": "#c3cadb",
    "pill_inactive": "#d3d9e6",
    "pill_glyph": "#10141f",
    "shadow": "#1b2130",
    "is_dark": False,
}

VARIANTS = (DARK, LIGHT)

TEXT_TARGET = 4.6   # WCAG AA (4.5) plus a little headroom


def rgb(hex_color):
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgbf(hex_color):
    return tuple(c / 255 for c in rgb(hex_color))


def to_hex(r, g, b):
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(c))) for c in (r, g, b))


def mix(a, b, t):
    """Linear mix of two hex colors, t=0 -> a, t=1 -> b."""
    ra, rb = rgb(a), rgb(b)
    return to_hex(*(x + (y - x) * t for x, y in zip(ra, rb)))


def kde(hex_color):
    """Hex -> 'r,g,b' as used in KDE .colors files."""
    return ",".join(str(c) for c in rgb(hex_color))


# ------------------------------------------------------------- contrast ---
def luminance(hex_color):
    def ch(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(c) for c in rgb(hex_color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(fg, bg):
    a, b = luminance(fg), luminance(bg)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


def ensure_contrast(fg, bg, target=TEXT_TARGET):
    """Keep fg's hue and saturation but darken (light bg) or lighten (dark
    bg) it just enough to reach the target contrast ratio."""
    import colorsys
    if contrast(fg, bg) >= target:
        return fg
    h, lig, s = colorsys.rgb_to_hls(*rgbf(fg))
    step = -0.005 if luminance(bg) > 0.18 else 0.005
    out = fg
    for _ in range(200):
        lig = min(1.0, max(0.0, lig + step))
        out = to_hex(*(c * 255 for c in colorsys.hls_to_rgb(h, lig, s)))
        if contrast(out, bg) >= target:
            break
    return out


# Everything but the semantic colours follows the requested accent
# semantics beat brand: red still means close/danger in every remix
_KEEP = ("id", "title", "is_dark", "positive", "neutral", "negative", "pill_close")
if REMIX:
    for _p in VARIANTS:
        for _k, _v in _p.items():
            if _k not in _KEEP and isinstance(_v, str) and _v.startswith("#"):
                _p[_k] = remix(_v)
    AURORA_TEAL, PERIWINKLE, VIOLET = remix(AURORA_TEAL), remix(PERIWINKLE), remix(VIOLET)
    ROSE, AMBER = remix(ROSE), remix(AMBER)

def _hls(hex_color):
    import colorsys
    return colorsys.rgb_to_hls(*rgbf(hex_color))


def _from_hls(h, lig, sat):
    import colorsys
    return to_hex(*(c * 255 for c in colorsys.hls_to_rgb(h, max(0.0, min(1.0, lig)), sat)))


# The requested accent should appear as asked in the dark variant; the light
# variant keeps its own (darker) lightness so it still reads on white.
if ACCENT:
    _ah, _al, _as = _hls(ACCENT)
    for _p in VARIANTS:
        _lig = _al if _p["is_dark"] else _hls(_p["accent"])[1]
        _p["accent"] = ensure_contrast(_from_hls(_ah, _lig, _as), _p["window"], 3.0)
        _h, _l, _s = _hls(_p["accent"])
        _p["accent_hover"] = _from_hls(_h, _l + (0.06 if _p["is_dark"] else 0.05), _s)
        _p["accent_pressed"] = _from_hls(_h, _l - 0.07, _s)
        _p["on_accent"] = max(("#ffffff", "#0b0f19"), key=lambda c: contrast(c, _p["accent"]))
        _p["link"] = _p["accent"]
        _p["pill_max"] = _p["accent"]

# Semantic text colours must stay readable on both window and view surfaces
for _p in VARIANTS:
    _bg = min((_p["window"], _p["view"]), key=lambda c: contrast(_p["text"], c))
    for _k in ("text_inactive", "link", "visited", "positive", "neutral", "negative", "secondary"):
        _p[_k] = ensure_contrast(_p[_k], _bg)
