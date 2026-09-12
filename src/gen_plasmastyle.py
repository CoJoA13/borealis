"""Borealis Plasma Style: frosted, 12px-rounded, color-scheme adaptive.

No `colors` file: every SVG paints with ColorScheme-* classes, so the same
style follows Borealis Dark and Borealis Light (or any other scheme).
Elements Borealis doesn't ship fall back to Breeze ("default").
"""
import gzip
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(__file__))
from svgkit import Doc, fmt, rounded_piece, shadow_piece  # noqa: E402
from tokens import AUTHOR, EMAIL, LICENSE, VERSION  # noqa: E402

TEXT, BG, HL = "ColorScheme-Text", "ColorScheme-Background", "ColorScheme-Highlight"
VIEWBG, BTNBG, BTNTEXT = "ColorScheme-ViewBackground", "ColorScheme-ButtonBackground", "ColorScheme-ButtonText"
BTNFOCUS, BTNHOVER = "ColorScheme-ButtonFocus", "ColorScheme-ButtonHover"
NEUTRAL, NEGATIVE, POSITIVE = "ColorScheme-NeutralText", "ColorScheme-NegativeText", "ColorScheme-PositiveText"

R = 12          # containers
RC = 8          # list highlights, task buttons
RB = 6          # buttons and fields (also the 16px checkbox box, so it stays square-ish)
EDGE = 0.10     # hairline opacity (Text)


def layered(*layers):
    """painter drawing several rounded-rect layers: (r, fill, stroke, inset)."""
    def painter(piece, w, h):
        return "".join(rounded_piece(piece, w, h, r, fill, stroke, inset)
                       for r, fill, stroke, inset in layers)
    return painter


def blank(piece, w, h):
    return ""


def mask_painter(r):
    """Blur-region mask: same shape as the frame, corners inset by 1px."""
    def painter(piece, w, h):
        if piece in ("topleft", "topright", "bottomleft", "bottomright"):
            return rounded_piece(piece, w, h, r - 1, ("#000000", 1), None, 1)
        return rounded_piece(piece, w, h, r, ("#000000", 1), None, 0)
    return painter


# ------------------------------------------------------------ backgrounds --
def background_svg(r, fill_op, shadow, stroke_op=EDGE, hints=None, extra=None,
                   shadow_strength=0.34, fill_cls=BG):
    """Frame + mask + (optional) shadow, as used by panels, dialogs, tooltips."""
    doc = Doc()
    stroke = (TEXT, stroke_op, 1) if stroke_op else None
    doc.frame("", layered((r, (fill_cls, fill_op), stroke, 0)), r)
    doc.frame("mask", mask_painter(r), r)
    if shadow:
        s = shadow
        doc.frame("shadow", lambda p, w, h: shadow_piece(doc, p, w, h, r, s, strength=shadow_strength),
                  s + r, center=20)
        for side in ("top", "bottom"):
            doc.hint(f"shadow-hint-{side}-margin", 2, s)
            doc.hint(f"shadow-hint-{side}-inset", 2, s)
        for side in ("left", "right"):
            doc.hint(f"shadow-hint-{side}-margin", s, 2)
            doc.hint(f"shadow-hint-{side}-inset", s, 2)
    for name, (w, h) in (hints or {}).items():
        doc.hint(name, w, h)
    if extra:
        extra(doc)
    return doc.svg()


def margins(m_tb, m_lr, prefix="hint"):
    return {f"{prefix}-top-margin": (2, m_tb), f"{prefix}-bottom-margin": (2, m_tb),
            f"{prefix}-left-margin": (m_lr, 2), f"{prefix}-right-margin": (m_lr, 2)}


ZERO_INSETS = {"hint-top-inset": (4, 0), "hint-bottom-inset": (4, 0),
               "hint-left-inset": (0, 4), "hint-right-inset": (0, 4)}


def panel_hints():
    h = margins(4, 6)
    h.update(ZERO_INSETS)
    h["hint-tile-center"] = (5, 5)
    h.update({"thick-hint-top-margin": (4, 8), "thick-hint-bottom-margin": (4, 8),
              "thick-hint-left-margin": (8, 4), "thick-hint-right-margin": (8, 4)})
    return h


def panel_extra(doc):
    # 'thick' panels (docks) reuse the normal centre
    doc.element("thick-center", 32, 32, "")


def dialog_hints():
    h = margins(6, 6)
    h.update(ZERO_INSETS)
    h["hint-tile-center"] = (5, 5)
    return h


# --------------------------------------------------------------- controls --
def button_svg():
    doc = Doc()
    base = (RB, (BTNBG, 1.0), (BTNTEXT, 0.14, 1), 0)
    doc.frame("normal", layered(base), RB)
    doc.frame("mask-normal", layered((RB, ("#000000", 1), None, 0)), RB)
    doc.frame("pressed", layered(base, (RB, (BTNFOCUS, 0.32), (BTNFOCUS, 0.55, 1), 0)), RB)
    doc.frame("hover", layered((RB, (BTNHOVER, 0.10), (BTNHOVER, 0.85, 1), 0)), RB)
    doc.frame("focus", layered((RB + 2, None, (BTNFOCUS, 0.9, 2), 0)), RB + 2)
    doc.frame("toolbutton-hover", layered((RB, (TEXT, 0.10), (TEXT, 0.06, 1), 0)), RB)
    doc.frame("toolbutton-pressed", layered((RB, (HL, 0.28), (HL, 0.45, 1), 0)), RB)
    doc.frame("toolbutton-focus", layered((RB, None, (BTNFOCUS, 0.9, 1.5), 0)), RB)
    doc.frame("shadow", layered((RB + 1, ("#000000", 0.06), None, 0)), RB + 1)
    for n, (w, h) in {**margins(6, 8, "normal-hint"), **margins(6, 8, "pressed-hint"),
                      **margins(0, 0, "hover-hint"), **margins(2, 2, "focus-hint"),
                      **margins(4, 4, "toolbutton-hover-hint"),
                      **margins(4, 4, "toolbutton-pressed-hint"),
                      **margins(2, 2, "toolbutton-focus-hint"),
                      **margins(1, 1, "shadow-hint")}.items():
        doc.hint(n, w, h)
    doc.hint("normal-hint-compose-over-border", 4, 4)
    doc.hint("pressed-hint-compose-over-border", 4, 4)
    return doc.svg()


def lineedit_svg():
    doc = Doc()
    doc.frame("base", layered((RB, (VIEWBG, 1.0), (TEXT, 0.16, 1), 0)), RB)
    doc.frame("hover", layered((RB, None, (HL, 0.6, 1), 0)), RB)
    doc.frame("focus", layered((RB, None, (HL, 1.0, 1.5), 0)), RB)
    doc.frame("focusframe", layered((RB + 2, None, (HL, 0.35, 2), 0)), RB + 2)
    for n, (w, h) in {**margins(6, 8, "base-hint"), **margins(0, 0, "hover-hint"),
                      **margins(0, 0, "focus-hint"), **margins(2, 2, "focusframe-hint")}.items():
        doc.hint(n, w, h)
    doc.hint("hint-focus-over-base", 2, 2)
    return doc.svg()


def checkmarks_svg():
    """'checkbox' fills the whole 16px indicator: an accent rounded square with
    a check (covers the button frame when checked); 'radiobutton' is the dot
    used by the compatibility radio indicator."""
    doc = Doc()
    check = (f'<rect x="0.5" y="0.5" width="14" height="14" rx="{RB - 1}" class="{HL}" fill="currentColor"/>'
             f'<path d="M4 7.8 L6.4 10.2 L11 4.9" fill="none" class="ColorScheme-HighlightedText" '
             f'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>')
    doc.element("checkbox", 15, 15, check)
    doc.element("radiobutton", 15, 15,
                f'<circle cx="7.5" cy="7.5" r="3" class="{HL}" fill="currentColor"/>')
    return doc.svg()


def radiobutton_svg():
    doc = Doc()
    doc.element("normal", 16, 16,
                f'<circle cx="8" cy="8" r="7.5" class="{BTNBG}" fill="currentColor"/>'
                f'<circle cx="8" cy="8" r="7" fill="none" class="{BTNTEXT}" stroke="currentColor" '
                f'stroke-opacity="0.22"/>')
    doc.element("checked", 16, 16, f'<circle cx="8" cy="8" r="7.5" class="{HL}" fill="currentColor"/>')
    doc.element("symbol", 6, 6,
                '<circle cx="3" cy="3" r="3" class="ColorScheme-HighlightedText" fill="currentColor"/>')
    doc.element("hover", 16, 16, f'<circle cx="8" cy="8" r="7" fill="none" class="{HL}" '
                f'stroke="currentColor" stroke-width="1.2"/>')
    doc.element("focus", 20, 20, f'<circle cx="10" cy="10" r="9" fill="none" class="{HL}" '
                f'stroke="currentColor" stroke-opacity="0.55" stroke-width="2"/>')
    doc.element("shadow", 22, 22, '<circle cx="11" cy="11.6" r="8.6" fill="#000" fill-opacity="0.08"/>')
    doc.hint("hint-size", 16, 16)
    return doc.svg()


def bar_meter_svg():
    """Progress bars: 3-slice pills (round caps + stretched middle); the fill
    runs from the positive colour (aurora teal) into the accent."""
    doc = Doc()
    gid = "auroraBar"
    doc.defs.append(f'<linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="0">'
                    f'<stop offset="0" class="{POSITIVE}" style="stop-color:currentColor"/>'
                    f'<stop offset="1" class="{HL}" style="stop-color:currentColor"/></linearGradient>')

    def pill(left_cls, right_cls, op, center_fill):
        def painter(piece, w, h):
            if piece == "left":
                return (f'<path d="M{fmt(w)} 0 A{fmt(w)} {fmt(h / 2)} 0 0 0 {fmt(w)} {fmt(h)} Z" '
                        f'class="{left_cls}" fill="currentColor" fill-opacity="{fmt(op)}"/>')
            if piece == "right":
                return (f'<path d="M0 0 A{fmt(w)} {fmt(h / 2)} 0 0 1 0 {fmt(h)} Z" '
                        f'class="{right_cls}" fill="currentColor" fill-opacity="{fmt(op)}"/>')
            if piece == "center":
                return f'<rect width="{fmt(w)}" height="{fmt(h)}" {center_fill}/>'
            return ""
        return painter

    sizes = {"left": (3, 6), "right": (3, 6), "center": (20, 6)}
    doc.frame("bar-inactive", pill(TEXT, TEXT, 0.14,
                                   f'class="{TEXT}" fill="currentColor" fill-opacity="0.14"'),
              (3, 0, 3, 0), sizes=sizes)
    doc.frame("bar-active", pill(POSITIVE, HL, 1.0, f'fill="url(#{gid})"'), (3, 0, 3, 0), sizes=sizes)
    doc.hint("hint-bar-size", 6, 6)
    doc.hint("hint-stretch-borders", 2, 2)
    return doc.svg()


def busywidget_svg():
    """Spinner: faint track plus an accent arc fading into its tail."""
    import math
    doc = Doc()

    def arc(size, width):
        c, r = size / 2, size / 2 - width / 2 - 0.5
        parts = [f'<circle cx="{fmt(c)}" cy="{fmt(c)}" r="{fmt(r)}" fill="none" class="{TEXT}" '
                 f'stroke="currentColor" stroke-opacity="0.12" stroke-width="{fmt(width)}"/>']
        segs = 18
        for i in range(segs):
            a0 = math.radians(-90 + i * 270 / segs)
            a1 = math.radians(-90 + (i + 1) * 270 / segs + 0.6)
            op = 0.08 + 0.92 * ((i + 1) / segs) ** 1.6
            cap = "round" if i == segs - 1 else "butt"
            parts.append(f'<path d="M{fmt(c + r * math.cos(a0))} {fmt(c + r * math.sin(a0))} '
                         f'A{fmt(r)} {fmt(r)} 0 0 1 {fmt(c + r * math.cos(a1))} {fmt(c + r * math.sin(a1))}" '
                         f'fill="none" class="{HL}" stroke="currentColor" stroke-opacity="{op:.2f}" '
                         f'stroke-width="{fmt(width)}" stroke-linecap="{cap}"/>')
        return "".join(parts)

    doc.element("busywidget", 36, 36, arc(36, 3.4))
    doc.element("22-22-busywidget", 22, 22, arc(22, 2.4))
    doc.element("16-16-busywidget", 16, 16, arc(16, 2))
    doc.element("stopped", 36, 36, f'<circle cx="18" cy="18" r="15.8" fill="none" class="{TEXT}" '
                'stroke="currentColor" stroke-opacity="0.25" stroke-width="3.4"/>')
    return doc.svg()


def listitem_svg():
    doc = Doc()
    doc.frame("normal", blank, RC)
    doc.frame("hover", layered((RC, (HL, 0.12), (HL, 0.25, 1), 0)), RC)
    doc.frame("pressed", layered((RC, (HL, 0.26), (HL, 0.50, 1), 0)), RC)
    doc.frame("section", blank, RC)
    for p in ("normal", "pressed", "section"):
        for n, (w, h) in margins(6, 6, f"{p}-hint").items():
            doc.hint(n, w, h)
    doc.element("separator", 40, 1, f'<rect width="40" height="1" class="{TEXT}" fill="currentColor" '
                'fill-opacity="0.12"/>')
    doc.hint("hint-tile-center", 2, 2)
    return doc.svg()


def line_svg():
    doc = Doc()
    for name in ("horizontal-line", "vertical-line"):
        doc.element(name, 1, 1, f'<rect width="1" height="1" class="{TEXT}" fill="currentColor" '
                    'fill-opacity="0.14"/>')
    return doc.svg()


def viewitem_svg():
    doc = Doc()
    doc.frame("normal", blank, RC)
    doc.frame("hover", layered((RC, (HL, 0.14), (HL, 0.30, 1), 0)), RC)
    doc.frame("selected", layered((RC, (HL, 0.26), (HL, 0.50, 1), 0)), RC)
    doc.frame("selected+hover", layered((RC, (HL, 0.34), (HL, 0.70, 1), 0)), RC)
    doc.hint("hint-tile-center", 40, 40)
    return doc.svg()


def menubaritem_svg():
    doc = Doc()
    doc.frame("normal", blank, 6)
    doc.frame("hover", layered((6, (TEXT, 0.12), None, 0)), 6)
    doc.frame("pressed", layered((6, (HL, 0.30), (HL, 0.45, 1), 0)), 6)
    for p in ("normal", "hover", "pressed"):
        for n, (w, h) in margins(2, 8, f"{p}-hint").items():
            doc.hint(n, w, h)
    return doc.svg()


# ------------------------------------------------------------------ tasks --
def pill_painter(where, color, inset, thick=3, gap=1, bg=None):
    """Task indicator: a rounded bar along one edge, inset from the ends.

    where: 'south' (bar at bottom), 'north', 'west', 'east'.
    The ends' round caps live in the corner pieces; the bar in the edge piece.
    bg: optional (fill, stroke) rounded background behind everything.
    """
    rad = thick / 2

    def painter(piece, w, h):
        out = []
        if bg:
            out.append(rounded_piece(piece, w, h, RC, bg[0], bg[1], 0))
        cls, op = color
        paint = f'class="{cls}" fill="currentColor" fill-opacity="{fmt(op)}"'
        horiz = where in ("south", "north")
        edge_piece = {"south": "bottom", "north": "top", "west": "left", "east": "right"}[where]
        caps = {"south": ("bottomleft", "bottomright"), "north": ("topleft", "topright"),
                "west": ("topleft", "bottomleft"), "east": ("topright", "bottomright")}[where]
        if horiz:
            y0 = (h - gap - thick) if where == "south" else gap
            if piece == edge_piece:
                out.append(f'<rect x="0" y="{fmt(y0)}" width="{fmt(w)}" height="{fmt(thick)}" {paint}/>')
            elif piece == caps[0]:   # left cap: half disc hugging the right side
                cx, cy = w, y0 + rad
                out.append(f'<path d="M{fmt(cx)} {fmt(cy - rad)} A{fmt(rad)} {fmt(rad)} 0 0 0 '
                           f'{fmt(cx)} {fmt(cy + rad)} Z" {paint}/>')
            elif piece == caps[1]:
                cx, cy = 0, y0 + rad
                out.append(f'<path d="M{fmt(cx)} {fmt(cy - rad)} A{fmt(rad)} {fmt(rad)} 0 0 1 '
                           f'{fmt(cx)} {fmt(cy + rad)} Z" {paint}/>')
        else:
            x0 = gap if where == "west" else (w - gap - thick)
            if piece == edge_piece:
                out.append(f'<rect x="{fmt(x0)}" y="0" width="{fmt(thick)}" height="{fmt(h)}" {paint}/>')
            elif piece == caps[0]:   # top cap hugging the bottom side
                cx, cy = x0 + rad, h
                out.append(f'<path d="M{fmt(cx - rad)} {fmt(cy)} A{fmt(rad)} {fmt(rad)} 0 0 1 '
                           f'{fmt(cx + rad)} {fmt(cy)} Z" {paint}/>')
            elif piece == caps[1]:
                cx, cy = x0 + rad, 0
                out.append(f'<path d="M{fmt(cx - rad)} {fmt(cy)} A{fmt(rad)} {fmt(rad)} 0 0 0 '
                           f'{fmt(cx + rad)} {fmt(cy)} Z" {paint}/>')
        return "".join(out)
    return painter


def tasks_svg():
    doc = Doc()
    hover_bg = ((TEXT, 0.10), (TEXT, 0.06, 1))
    focus_bg = ((TEXT, 0.07), None)
    states = {
        # prefix: (pill color or None, inset along the edge, background)
        "normal": ((TEXT, 0.45), 16, None),
        "focus": ((HL, 1.0), 11, focus_bg),
        "attention": ((NEUTRAL, 1.0), 11, ((NEUTRAL, 0.12), None)),
        "minimized": ((TEXT, 0.22), 18, None),
        "hover": (None, 0, hover_bg),
        "launcher-hover": (None, 0, hover_bg),
        "normal-hover": ((TEXT, 0.6), 16, hover_bg),
        "focus-hover": ((HL, 1.0), 11, hover_bg),
        "attention-hover": ((NEUTRAL, 1.0), 11, ((NEUTRAL, 0.18), None)),
        "minimized-hover": ((TEXT, 0.4), 18, hover_bg),
        "progress": (None, 0, ((HL, 0.22), None)),
    }
    for loc, where in (("", "south"), ("north-", "north"), ("west-", "west"),
                       ("east-", "east"), ("south-", "south")):
        for name, (pill, inset, bg) in states.items():
            if pill:
                painter = pill_painter(where, pill, inset, bg=bg)
            else:
                painter = layered((RC, bg[0], bg[1], 0))
            # corner pieces are wide along the indicator edge so the pill is inset
            along = max(inset, RC)
            if where in ("south", "north"):
                corner = (along, RC, along, RC)
            else:
                corner = (RC, along, RC, along)
            doc.frame(f"{loc}{name}", painter, corner)
            for n, (w, h) in margins(4, 4, f"{loc}{name}-hint").items():
                doc.hint(n, w, h)
    for side in ("top", "bottom", "left", "right"):
        doc.element(f"group-expander-{side}", 11, 11,
                    f'<circle cx="5.5" cy="5.5" r="2" class="{TEXT}" fill="currentColor" fill-opacity="0.7"/>')
    return doc.svg()


# --------------------------------------------------------------- tabbar ----
def tabbar_svg():
    doc = Doc()
    for loc in ("north", "south", "west", "east"):
        # the accent bar sits on the named edge (Breeze convention)
        doc.frame(f"{loc}-active-tab",
                  pill_painter(loc, (HL, 1.0), 10, thick=3, gap=0,
                               bg=((TEXT, 0.08), None)), 10)
        for n, (w, h) in margins(5, 6, f"{loc}-active-tab-hint").items():
            doc.hint(n, w, h)
    doc.frame("active-tab", layered((RC, (TEXT, 0.10), None, 0)), RC)
    for n, (w, h) in margins(5, 6, "active-tab-hint").items():
        doc.hint(n, w, h)
    doc.hint("hint-tile-center", 40, 40)
    return doc.svg()


# ------------------------------------------------------------- scrollbar ---
def scrollbar_svg():
    doc = Doc()
    pill = lambda cls, op: layered((3, (cls, op), None, 0))  # noqa: E731
    doc.frame("slider", pill(TEXT, 0.38), 3)
    doc.frame("mouseover-slider", pill(HL, 0.9), 3)
    doc.frame("background-vertical", pill(TEXT, 0.06), 3)
    doc.frame("background-horizontal", pill(TEXT, 0.06), 3)
    for p in ("slider", "mouseover-slider", "background-vertical", "background-horizontal"):
        for side in ("top", "bottom"):
            doc.hint(f"{p}-hint-{side}-inset", 3, 6)
        for side in ("left", "right"):
            doc.hint(f"{p}-hint-{side}-inset", 6, 3)
    doc.hint("hint-scrollbar-size", 6, 6)
    doc.hint("hint-tile-center", 2, 2)
    return doc.svg()


# ---------------------------------------------------------------- slider ---
def slider_svg():
    doc = Doc()
    doc.frame("groove", layered((1.5, (TEXT, 0.22), None, 0)), 3)
    doc.frame("groove-highlight", layered((1.5, (HL, 1.0), None, 0)), 3)
    handle = (f'<circle cx="10" cy="10" r="8.5" class="{BTNBG}" fill="currentColor"/>'
              f'<circle cx="10" cy="10" r="8.5" fill="none" class="{TEXT}" stroke="currentColor" '
              f'stroke-opacity="0.2"/>'
              f'<circle cx="10" cy="10" r="4" class="{HL}" fill="currentColor"/>')
    hover = (f'<circle cx="10" cy="10" r="8.5" fill="none" class="{HL}" stroke="currentColor" '
             f'stroke-width="1.5"/>')
    focus = (f'<circle cx="12" cy="12" r="11" fill="none" class="{HL}" stroke="currentColor" '
             f'stroke-opacity="0.55" stroke-width="2"/>')
    shadow = ('<circle cx="13" cy="13.6" r="10" fill="#000" fill-opacity="0.10"/>'
              '<circle cx="13" cy="13.4" r="9.2" fill="#000" fill-opacity="0.10"/>')
    for o in ("horizontal", "vertical"):
        doc.element(f"{o}-slider-handle", 20, 20, handle)
        doc.element(f"{o}-slider-hover", 20, 20, hover)
        doc.element(f"{o}-slider-focus", 24, 24, focus)
        doc.element(f"{o}-slider-shadow", 26, 26, shadow)
    doc.hint("hint-handle-size", 20, 20)
    doc.hint("hint-tile-center", 2, 2)
    return doc.svg()


# ---------------------------------------------------------------- switch ---
def switch_svg():
    doc = Doc()

    def track(cls, op, piece_w, part):
        r = 8
        if part == "left":
            d = f"M8 0 A8 8 0 0 0 8 16 Z"
        elif part == "right":
            d = f"M0 0 A8 8 0 0 1 0 16 Z"
        else:
            d = f"M0 0 H{piece_w} V16 H0 Z"
        del r
        return f'<path d="{d}" class="{cls}" fill="currentColor" fill-opacity="{fmt(op)}"/>'

    for state, (cls, op) in (("inactive", (TEXT, 0.28)), ("active", (HL, 1.0))):
        doc.element(f"{state}-left", 8, 16, track(cls, op, 8, "left"))
        doc.element(f"{state}-center", 5, 16, track(cls, op, 5, "center"))
        doc.element(f"{state}-right", 8, 16, track(cls, op, 8, "right"))
    knob = ('<circle cx="11" cy="11" r="8" fill="#ffffff"/>'
            f'<circle cx="11" cy="11" r="8" fill="none" class="{TEXT}" stroke="currentColor" '
            'stroke-opacity="0.18"/>')
    doc.element("handle", 22, 22, knob)
    doc.element("handle-hover", 22, 22, knob + f'<circle cx="11" cy="11" r="8" fill="none" class="{HL}" '
                'stroke="currentColor" stroke-width="1.5"/>')
    doc.element("handle-pressed", 22, 22, '<circle cx="11" cy="11" r="8" fill="#e6e9f2"/>'
                f'<circle cx="11" cy="11" r="8" fill="none" class="{HL}" stroke="currentColor" '
                'stroke-width="1.5"/>')
    doc.element("handle-focus", 26, 26, f'<circle cx="13" cy="13" r="11" fill="none" class="{HL}" '
                'stroke="currentColor" stroke-opacity="0.55" stroke-width="2"/>')
    doc.element("handle-shadow", 28, 28, '<circle cx="14" cy="14.8" r="9.5" fill="#000" fill-opacity="0.14"/>')
    doc.hint("hint-bar-size", 38, 16)
    doc.hint("hint-stretch-borders", 4, 4)
    return doc.svg()


# ------------------------------------------------------- plasmoid heading --
def plasmoidheading_svg():
    doc = Doc()

    def header(piece, w, h):
        body = rounded_piece(piece, w, h, R, (TEXT, 0.045), None, 0)
        if piece in ("bottomleft", "bottom", "bottomright"):
            body += (f'<rect x="0" y="{fmt(h - 1)}" width="{fmt(w)}" height="1" '
                     f'class="{TEXT}" fill="currentColor" fill-opacity="0.10"/>')
        return body

    def footer(piece, w, h):
        body = rounded_piece(piece, w, h, R, (TEXT, 0.045), None, 0)
        if piece in ("topleft", "top", "topright"):
            body += (f'<rect x="0" y="0" width="{fmt(w)}" height="1" '
                     f'class="{TEXT}" fill="currentColor" fill-opacity="0.10"/>')
        return body

    doc.frame("header", header, R)
    doc.frame("footer", footer, R)
    for n, (w, h) in margins(6, 6).items():
        doc.hint(n, w, h)
    doc.hint("hint-stretch-borders", 5, 5)
    return doc.svg()


# ----------------------------------------------------------------- pager ---
def pager_svg():
    doc = Doc()
    doc.frame("normal", layered((5, (TEXT, 0.06), (TEXT, 0.14, 1), 0)), 5)
    doc.frame("hover", layered((5, (HL, 0.16), (HL, 0.55, 1), 0)), 5)
    doc.frame("active", layered((5, (HL, 0.30), (HL, 0.9, 1), 0)), 5)
    doc.hint("hint-tile-center", 1, 1)
    return doc.svg()


# ------------------------------------------------------------------ build --
def build(out_root):
    base = os.path.join(out_root, "plasma", "desktoptheme", "Borealis")
    if os.path.exists(base):
        shutil.rmtree(base)

    def write(rel, svg):
        path = os.path.join(base, rel + ".svgz")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with gzip.open(path, "wb") as f:
            f.write(svg.encode())

    # variant opacities: base (compositing, no blur) / translucent (blur) /
    # opaque (no compositing) / solid (opaque panel mode)
    ph = panel_hints()
    dh = dialog_hints()
    th = margins(6, 8)
    th.update(ZERO_INSETS)
    wb = margins(8, 8)
    wb.update(ZERO_INSETS)
    for folder, op, shadow in (("", 0.94, True), ("translucent/", 0.78, True),
                               ("opaque/", 1.0, False), ("solid/", 1.0, True)):
        write(folder + "widgets/panel-background",
              background_svg(R, op, 14 if shadow else 0, hints=ph, extra=panel_extra,
                             shadow_strength=0.30))
        write(folder + "dialogs/background",
              background_svg(R, min(1.0, op + 0.04), 22 if shadow else 0, hints=dh))
        write(folder + "widgets/tooltip",
              background_svg(8, min(1.0, op + 0.04), 12 if shadow else 0, hints=th,
                             shadow_strength=0.28))
        if folder != "opaque/":
            write(folder + "widgets/background",
                  background_svg(R, min(1.0, op + 0.02), 16 if shadow else 0, hints=wb))
    write("widgets/translucentbackground",
          background_svg(R, 0.55, 16, hints=wb))
    write("widgets/button", button_svg())
    write("widgets/lineedit", lineedit_svg())
    write("widgets/viewitem", viewitem_svg())
    write("widgets/menubaritem", menubaritem_svg())
    write("widgets/tasks", tasks_svg())
    write("widgets/tabbar", tabbar_svg())
    write("widgets/scrollbar", scrollbar_svg())
    write("widgets/slider", slider_svg())
    write("widgets/switch", switch_svg())
    write("widgets/plasmoidheading", plasmoidheading_svg())
    write("widgets/pager", pager_svg())
    write("widgets/checkmarks", checkmarks_svg())
    write("widgets/radiobutton", radiobutton_svg())
    write("widgets/bar_meter_horizontal", bar_meter_svg())
    write("widgets/busywidget", busywidget_svg())
    write("widgets/listitem", listitem_svg())
    write("widgets/line", line_svg())

    meta = {
        "KPlugin": {
            "Authors": [{"Name": AUTHOR, "Email": EMAIL}],
            "Category": "",
            "Description": "Frosted, rounded Plasma style that follows your color scheme",
            "EnabledByDefault": True,
            "Id": "Borealis",
            "License": LICENSE,
            "Name": "Borealis",
            "Version": VERSION,
            "Website": "",
        },
        "KPackageStructure": "Plasma/Theme",
        "X-Plasma-API": "5.0",
    }
    with open(os.path.join(base, "metadata.json"), "w") as f:
        json.dump(meta, f, indent=4)
    with open(os.path.join(base, "plasmarc"), "w") as f:
        f.write("[Settings]\nFallbackTheme=default\n\n"
                "[AdaptiveTransparency]\nenabled=true\n\n"
                "[BlurBehindEffect]\nenabled=true\n\n"
                "[ContrastEffect]\nenabled=true\n\n"
                "[Wallpaper]\ndefaultWallpaperTheme=Borealis\n")
    return base


if __name__ == "__main__":
    print(build(sys.argv[1]))
