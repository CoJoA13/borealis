"""Borealis cursor glyphs, drawn on a 32x32 canvas (nominal size 24).

Every glyph is a list of layers; the builder turns them into SVG with
    shadow -> outline underlay -> fill -> details/badges
so compound shapes merge into one clean silhouette.
Each entry returns (body_svg, hotspot_x, hotspot_y).
"""
import math

OUT_W = 1.5  # outline thickness (each side)

# palettes: fill, outline, detail (lines drawn on the fill)
SNOW = {"fill": "#f7f8fc", "outline": "#0e121b", "detail": "#0e121b", "shade": "#dfe4f0"}
INK = {"fill": "#171c29", "outline": "#ffffff", "detail": "#ffffff", "shade": "#232b40"}

TEAL, PERI, VIOLET, ROSE = "#5fe0c8", "#8b9cff", "#b18cff", "#ff6b81"
BADGE_TEXT = "#0b0f19"


# --------------------------------------------------------------- shapes ----
ARROW = "M5 4 L5 21.8 L9.6 17.6 L12.6 24.5 L15.9 23.1 L12.9 16.4 L19.2 16.4 Z"


def rrect(x, y, w, h, r):
    r = min(r, w / 2, h / 2)
    return (f"M{x + r} {y} H{x + w - r} A{r} {r} 0 0 1 {x + w} {y + r} "
            f"V{y + h - r} A{r} {r} 0 0 1 {x + w - r} {y + h} H{x + r} "
            f"A{r} {r} 0 0 1 {x} {y + h - r} V{y + r} A{r} {r} 0 0 1 {x + r} {y} Z")


def circle(cx, cy, r):
    return (f"M{cx - r} {cy} A{r} {r} 0 1 0 {cx + r} {cy} "
            f"A{r} {r} 0 1 0 {cx - r} {cy} Z")


def silhouette(paths, pal, transform=None, shadow=True):
    """Filled compound shape with a merged outline and soft drop shadow."""
    t = f' transform="{transform}"' if transform else ""
    d = " ".join(paths)
    out = []
    if shadow:
        out.append(f'<g{t}><path d="{d}" fill="#000" fill-opacity="0.28" '
                   f'stroke="#000" stroke-opacity="0.28" stroke-width="{OUT_W * 2}" '
                   f'stroke-linejoin="round" transform="translate(0.4 1.1)" '
                   f'filter="url(#shadow)"/></g>')
    out.append(f'<path{t} d="{d}" fill="{pal["outline"]}" stroke="{pal["outline"]}" '
               f'stroke-width="{OUT_W * 2}" stroke-linejoin="round"/>')
    out.append(f'<path{t} d="{d}" fill="{pal["fill"]}"/>')
    return "".join(out)


def strokes(d, pal, width=2.2, transform=None, cap="round", shadow=True):
    """Glyph made of strokes (I-beam, crosshair...): outline under fill."""
    t = f' transform="{transform}"' if transform else ""
    out = []
    if shadow:
        out.append(f'<path{t} d="{d}" fill="none" stroke="#000" stroke-opacity="0.3" '
                   f'stroke-width="{width + OUT_W * 2}" stroke-linecap="{cap}" '
                   f'stroke-linejoin="round" filter="url(#shadow)"/>')
    out.append(f'<path{t} d="{d}" fill="none" stroke="{pal["outline"]}" '
               f'stroke-width="{width + OUT_W * 2}" stroke-linecap="{cap}" stroke-linejoin="round"/>')
    out.append(f'<path{t} d="{d}" fill="none" stroke="{pal["fill"]}" '
               f'stroke-width="{width}" stroke-linecap="{cap}" stroke-linejoin="round"/>')
    return "".join(out)


def detail(d, pal, width=0.9, opacity=0.55):
    return (f'<path d="{d}" fill="none" stroke="{pal["detail"]}" stroke-opacity="{opacity}" '
            f'stroke-width="{width}" stroke-linecap="round"/>')


# --------------------------------------------------------------- badges ----
BX, BY, BR = 23.5, 23.5, 5.8


def badge_disk(color, pal):
    return (f'<path d="{circle(BX, BY, BR + OUT_W)}" fill="{pal["outline"]}"/>'
            f'<path d="{circle(BX, BY, BR)}" fill="{color}"/>')


def badge_help(pal):
    q = (f"M{BX - 2.1} {BY - 1.6} C{BX - 2.1} {BY - 3.3} {BX - 0.9} {BY - 4.1} {BX} {BY - 4.1} "
         f"C{BX + 1.3} {BY - 4.1} {BX + 2.2} {BY - 3.2} {BX + 2.2} {BY - 2.0} "
         f"C{BX + 2.2} {BY - 0.3} {BX} {BY - 0.2} {BX} {BY + 1.6}")
    return (badge_disk(PERI, pal) +
            f'<path d="{q}" fill="none" stroke="{BADGE_TEXT}" stroke-width="1.6" stroke-linecap="round"/>'
            f'<path d="{circle(BX, BY + 3.6, 0.95)}" fill="{BADGE_TEXT}"/>')


def badge_forbidden(pal, cx=BX, cy=BY, r=BR):
    s = r * 0.62
    return (f'<path d="{circle(cx, cy, r + OUT_W)}" fill="{pal["outline"]}"/>'
            f'<path d="{circle(cx, cy, r)}" fill="{ROSE}"/>'
            f'<path d="{circle(cx, cy, r - 1.7)}" fill="#ffffff"/>'
            f'<path d="M{cx - s} {cy + s} L{cx + s} {cy - s}" stroke="{ROSE}" '
            f'stroke-width="1.8" stroke-linecap="round" transform="rotate(90 {cx} {cy})"/>')


def badge_plus(pal):
    return (badge_disk(TEAL, pal) +
            f'<path d="M{BX - 3} {BY} H{BX + 3} M{BX} {BY - 3} V{BY + 3}" stroke="{BADGE_TEXT}" '
            f'stroke-width="1.7" stroke-linecap="round"/>')


def badge_link(pal):
    d = (f"M{BX - 2.6} {BY + 2.8} V{BY + 0.6} C{BX - 2.6} {BY - 1.2} {BX - 1.4} {BY - 2.0} "
         f"{BX + 0.4} {BY - 2.0} H{BX + 2.6}")
    head = f"M{BX + 0.8} {BY - 4.0} L{BX + 2.9} {BY - 2.0} L{BX + 0.8} {BY}"
    return (badge_disk(TEAL, pal) +
            f'<path d="{d} {head}" fill="none" stroke="{BADGE_TEXT}" stroke-width="1.5" '
            f'stroke-linecap="round" stroke-linejoin="round"/>')


def badge_menu(pal):
    x, y, w, h = 17.2, 18.5, 12, 10.5
    lines = "".join(
        f'<path d="M{x + 2.6} {y + 2.8 + i * 2.5} H{x + w - 2.6}" stroke="{pal["detail"]}" '
        f'stroke-opacity="0.75" stroke-width="1.2" stroke-linecap="round"/>' for i in range(3))
    return (f'<path d="{rrect(x - OUT_W, y - OUT_W, w + 2 * OUT_W, h + 2 * OUT_W, 3.2)}" fill="{pal["outline"]}"/>'
            f'<path d="{rrect(x, y, w, h, 2)}" fill="{pal["fill"]}"/>'
            f'<path d="M{x} {y + 1.4} a1.4 1.4 0 0 1 1.4 -1.4 H{x + w - 1.4} a1.4 1.4 0 0 1 1.4 1.4" '
            f'fill="none" stroke="{PERI}" stroke-width="1.4"/>' + lines)


def badge_move(pal):
    x, y, w = 18, 18.5, 10
    return (f'<path d="{rrect(x - OUT_W, y - OUT_W, w + 2 * OUT_W, w + 2 * OUT_W, 3.2)}" fill="{pal["outline"]}"/>'
            f'<path d="{rrect(x, y, w, w, 2)}" fill="{PERI}"/>'
            f'<path d="{rrect(x + 2.6, y + 2.6, w - 5.2, w - 5.2, 1)}" fill="none" '
            f'stroke="{BADGE_TEXT}" stroke-width="1.3" stroke-dasharray="1.6 1.2"/>')


# -------------------------------------------------------------- spinner ----
SPIN = [TEAL, "#6fcfe0", PERI, "#9e92ff", VIOLET]


def lerp_hex(stops, t):
    t = max(0.0, min(1.0, t)) * (len(stops) - 1)
    i = min(int(t), len(stops) - 2)
    f = t - i
    a, b = stops[i], stops[i + 1]
    ca = [int(a[k:k + 2], 16) for k in (1, 3, 5)]
    cb = [int(b[k:k + 2], 16) for k in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * f) for x, y in zip(ca, cb))


def spinner(cx, cy, r, width, phase, pal, sweep=280, segments=14):
    """Ring track + aurora-gradient arc (phase in [0,1) turns)."""
    out = [f'<path d="{circle(cx, cy, r)}" fill="none" stroke="{pal["outline"]}" '
           f'stroke-width="{width + OUT_W * 2}"/>',
           f'<path d="{circle(cx, cy, r)}" fill="none" stroke="{pal["shade"]}" '
           f'stroke-width="{width}"/>']
    start = -90 + phase * 360
    seg = sweep / segments
    for i in range(segments):
        a0 = math.radians(start + i * seg)
        a1 = math.radians(start + (i + 1) * seg + 0.8)
        x0, y0 = cx + r * math.cos(a0), cy + r * math.sin(a0)
        x1, y1 = cx + r * math.cos(a1), cy + r * math.sin(a1)
        col = lerp_hex(SPIN, i / (segments - 1))
        cap = "round" if i == segments - 1 else "butt"
        op = 0.35 + 0.65 * (i / (segments - 1))
        out.append(f'<path d="M{x0:.3f} {y0:.3f} A{r} {r} 0 0 1 {x1:.3f} {y1:.3f}" '
                   f'fill="none" stroke="{col}" stroke-opacity="{op:.2f}" '
                   f'stroke-width="{width}" stroke-linecap="{cap}"/>')
    return "".join(out)


# --------------------------------------------------------------- glyphs ----
def g_default(pal):
    return silhouette([ARROW], pal), 5, 4


def g_right_ptr(pal):
    return silhouette([ARROW], pal, transform="translate(32 0) scale(-1 1)"), 27, 4


def arrow_with(badge):
    def g(pal):
        return silhouette([ARROW], pal) + badge(pal), 5, 4
    return g


def g_pointer(pal):
    parts = [
        rrect(10.6, 3, 4.2, 17, 2.1),        # index
        rrect(14.6, 10.2, 4.1, 10.5, 2.05),  # middle
        rrect(18.5, 11.4, 3.8, 10, 1.9),     # ring
        rrect(22.1, 13.2, 3.5, 9.5, 1.75),   # pinky
        "M10.6 15 L25.6 15 L25.6 22.4 C25.6 26.6 22.6 28.8 18.6 28.8 L15.2 28.8 "
        "C12.1 28.8 10.1 27.3 8.9 25.3 L5.9 20.3 C5.1 18.9 5.6 17.4 6.9 16.9 "
        "C8.1 16.4 9.2 17.0 9.9 18.0 L10.6 19.1 Z",
    ]
    body = silhouette(parts, pal)
    body += detail("M14.7 16.3 V19.4 M18.6 16.9 V20.2 M22.2 17.6 V20.8", pal)
    return body, 12, 3


def g_grab(pal):
    parts = [
        rrect(9.9, 7.2, 3.6, 13, 1.8),
        rrect(13.9, 4.6, 3.7, 14.5, 1.85),
        rrect(18.0, 5.6, 3.6, 14, 1.8),
        rrect(21.8, 8.8, 3.3, 12, 1.65),
        "M9.9 15.5 L25.1 15.5 L25.1 22.3 C25.1 26.5 22.2 28.6 18.4 28.6 L15.2 28.6 "
        "C12.1 28.6 10.3 27.1 9.2 25.2 L6.2 19.8 C5.5 18.5 6.0 17.1 7.2 16.6 "
        "C8.3 16.2 9.3 16.8 9.9 17.7 Z",
    ]
    body = silhouette(parts, pal)
    body += detail("M13.7 16.2 V19 M17.8 16.2 V19.2 M21.7 16.6 V19.6", pal)
    return body, 16, 16


def g_grabbing(pal):
    parts = [
        rrect(9.2, 11.2, 16.4, 16.8, 5.2),
        rrect(9.6, 9.6, 4.0, 7, 2),
        rrect(13.6, 8.8, 4.0, 7, 2),
        rrect(17.6, 9.2, 4.0, 7, 2),
        rrect(21.4, 10.4, 3.8, 7, 1.9),
        "M6.6 17.6 C6.0 16.2 6.9 14.9 8.3 14.9 L12.6 15.2 C14.0 15.3 14.6 16.8 13.8 17.9 "
        "L12.2 20.1 Z",
    ]
    body = silhouette(parts, pal)
    body += detail("M13.6 12.4 V14.8 M17.6 12.2 V14.6 M21.5 12.8 V15.2", pal)
    return body, 16, 16


def g_text(pal):
    d = ("M11 5 C13 5 15 5.8 16 7.2 C17 5.8 19 5 21 5 M16 7.2 V24.8 "
         "M11 27 C13 27 15 26.2 16 24.8 C17 26.2 19 27 21 27")
    return strokes(d, pal, width=2.0), 16, 16


def g_vertical_text(pal):
    d = ("M11 5 C13 5 15 5.8 16 7.2 C17 5.8 19 5 21 5 M16 7.2 V24.8 "
         "M11 27 C13 27 15 26.2 16 24.8 C17 26.2 19 27 21 27")
    return strokes(d, pal, width=2.0, transform="rotate(90 16 16)"), 16, 16


def g_crosshair(pal):
    d = "M16 3.5 V12.3 M16 19.7 V28.5 M3.5 16 H12.3 M19.7 16 H28.5"
    body = strokes(d, pal, width=2.0)
    body += (f'<path d="{circle(16, 16, 1.6 + OUT_W)}" fill="{pal["outline"]}"/>'
             f'<path d="{circle(16, 16, 1.6)}" fill="{PERI}"/>')
    return body, 16, 16


def g_cell(pal):
    d = ("M13.4 5.5 H18.6 V13.4 H26.5 V18.6 H18.6 V26.5 H13.4 V18.6 H5.5 V13.4 H13.4 Z")
    return silhouette([d], pal), 16, 16


def g_xcursor(pal):
    return strokes("M8.5 8.5 L23.5 23.5 M23.5 8.5 L8.5 23.5", pal, width=3.2), 16, 16


def arrowhead(x, y, rot):
    """Filled triangular head pointing up, tip at (x, y), rotated."""
    return (f'<path d="M{x} {y} L{x + 5} {y + 5.6} L{x - 5} {y + 5.6} Z" '
            f'transform="rotate({rot} {x} {y})"/>')


def double_arrow_paths(rot):
    """Vertical double arrow (rotate for other axes) as silhouette paths."""
    shaft = rrect(14.9, 8, 2.2, 16, 1.1)
    top = "M16 3.6 L21.6 9.6 L10.4 9.6 Z"
    bot = "M16 28.4 L21.6 22.4 L10.4 22.4 Z"
    return [shaft, top, bot], f"rotate({rot} 16 16)"


def g_resize(rot):
    def g(pal):
        paths, t = double_arrow_paths(rot)
        return silhouette(paths, pal, transform=t), 16, 16
    return g


def g_move(pal):
    paths = [rrect(14.9, 8, 2.2, 16, 1.1), rrect(8, 14.9, 16, 2.2, 1.1),
             "M16 3.2 L20.6 8.4 L11.4 8.4 Z", "M16 28.8 L20.6 23.6 L11.4 23.6 Z",
             "M3.2 16 L8.4 11.4 L8.4 20.6 Z", "M28.8 16 L23.6 11.4 L23.6 20.6 Z"]
    body = silhouette(paths, pal)
    body += f'<path d="{circle(16, 16, 1.5)}" fill="{PERI}"/>'
    return body, 16, 16


def g_split(rot):
    def g(pal):
        paths = [rrect(13.1, 6.5, 2.0, 19, 1), rrect(16.9, 6.5, 2.0, 19, 1),
                 rrect(5.5, 15, 6.5, 2, 1), rrect(20, 15, 6.5, 2, 1),
                 "M2.8 16 L8 11.2 L8 20.8 Z", "M29.2 16 L24 11.2 L24 20.8 Z"]
        return silhouette(paths, pal, transform=f"rotate({rot} 16 16)"), 16, 16
    return g


def rot_point(x, y, rot):
    a = math.radians(rot)
    dx, dy = x - 16, y - 16
    return (round(16 + dx * math.cos(a) - dy * math.sin(a)),
            round(16 + dx * math.sin(a) + dy * math.cos(a)))


def g_side(rot):
    """Arrow pushing against an edge; rot 0 = top edge."""
    def g(pal):
        paths = [rrect(7.5, 4.2, 17, 2.4, 1.2), rrect(14.9, 12, 2.2, 15.5, 1.1),
                 "M16 8.2 L21.6 14.2 L10.4 14.2 Z"]
        hx, hy = rot_point(16, 5, rot)
        return silhouette(paths, pal, transform=f"rotate({rot} 16 16)"), hx, hy
    return g


def g_corner(rot):
    """Diagonal arrow into a corner bracket; rot 0 = top-left corner."""
    def g(pal):
        paths = ["M5 16 V7.2 C5 6 6 5 7.2 5 H16 V7.6 H7.6 V16 Z",
                 "M11 11 L11.2 19 L19 11.2 Z",
                 "M15.4 17.1 L17.1 15.4 L26.2 24.5 L24.5 26.2 Z"]
        hx, hy = rot_point(6, 6, rot)
        return silhouette(paths, pal, transform=f"rotate({rot} 16 16)"), hx, hy
    return g


def g_bigarrow(rot):
    def g(pal):
        d = "M16 3.8 L25 13.6 L19.2 13.6 L19.2 27.5 L12.8 27.5 L12.8 13.6 L7 13.6 Z"
        hx, hy = rot_point(16, 4, rot)
        return silhouette([d], pal, transform=f"rotate({rot} 16 16)"), hx, hy
    return g


def g_pencil(pal):
    body = silhouette(["M5 27 L6.9 20.6 L21.4 6.1 C22.5 5 24.3 5 25.4 6.1 L25.9 6.6 "
                       "C27 7.7 27 9.5 25.9 10.6 L11.4 25.1 Z"], pal)
    body += (f'<path d="M19.3 8.2 L23.8 12.7 L25.9 10.6 C27 9.5 27 7.7 25.9 6.6 L25.4 6.1 '
             f'C24.3 5 22.5 5 21.4 6.1 Z" fill="{PERI}"/>'
             f'<path d="M5 27 L5.9 23.8 L8.2 26.1 Z" fill="{pal["outline"]}"/>'
             + detail("M6.9 20.6 L11.4 25.1", pal, 0.9, 0.6))
    return body, 5, 27


def g_color_picker(pal):
    body = silhouette(["M5 27 L5.6 23.6 L16.2 13 L19 15.8 L8.4 26.4 Z",
                       "M14.6 11.4 L20.6 17.4 L22.2 15.8 L16.2 9.8 Z",
                       circle(22.6, 9.4, 4.6)], pal)
    body += (f'<path d="{circle(22.6, 9.4, 3.3)}" fill="{PERI}"/>'
             f'<path d="M5.6 23.6 L11 18.2 L13.8 21 L8.4 26.4 Z" fill="{TEAL}" fill-opacity="0.85"/>')
    return body, 5, 27


def g_zoom(plus):
    def g(pal):
        body = strokes("M19.4 19.4 L26.6 26.6", pal, width=3.6)
        body += (f'<path d="{circle(13, 13, 8.4 + OUT_W)}" fill="{pal["outline"]}"/>'
                 f'<path d="{circle(13, 13, 8.4)}" fill="{pal["fill"]}"/>'
                 f'<path d="{circle(13, 13, 6.2)}" fill="{PERI}" fill-opacity="0.22"/>')
        sign = "M9.6 13 H16.4" + (" M13 9.6 V16.4" if plus else "")
        body += (f'<path d="{sign}" stroke="{pal["detail"]}" stroke-width="1.9" '
                 f'stroke-linecap="round"/>')
        return body, 13, 13
    return g


def g_forbidden(pal):
    return badge_forbidden(pal, 16, 16, 9.5), 16, 16


def g_wait(phase):
    def g(pal):
        return spinner(16, 16, 8.6, 3.4, phase, pal), 16, 16
    return g


def g_progress(phase):
    def g(pal):
        return silhouette([ARROW], pal) + spinner(23.2, 23.2, 4.7, 2.4, phase, pal), 5, 4
    return g


WAIT_FRAMES = 24
WAIT_DELAY = 30

# canonical name -> glyph (static) ; animated ones handled in builder
STATIC = {
    "default": g_default,
    "right_ptr": g_right_ptr,
    "pointer": g_pointer,
    "grab": g_grab,
    "grabbing": g_grabbing,
    "text": g_text,
    "vertical-text": g_vertical_text,
    "crosshair": g_crosshair,
    "cell": g_cell,
    "x-cursor": g_xcursor,
    "move": g_move,
    "ns-resize": g_resize(0),
    "ew-resize": g_resize(90),
    "nwse-resize": g_resize(-45),
    "nesw-resize": g_resize(45),
    "col-resize": g_split(0),
    "row-resize": g_split(90),
    "n-resize": g_side(0),
    "e-resize": g_side(90),
    "s-resize": g_side(180),
    "w-resize": g_side(270),
    "nw-resize": g_corner(0),
    "ne-resize": g_corner(90),
    "se-resize": g_corner(180),
    "sw-resize": g_corner(270),
    "up-arrow": g_bigarrow(0),
    "right-arrow": g_bigarrow(90),
    "down-arrow": g_bigarrow(180),
    "left-arrow": g_bigarrow(270),
    "pencil": g_pencil,
    "color-picker": g_color_picker,
    "zoom-in": g_zoom(True),
    "zoom-out": g_zoom(False),
    "not-allowed": arrow_with(badge_forbidden),
    "forbidden": g_forbidden,
    "help": arrow_with(badge_help),
    "copy": arrow_with(badge_plus),
    "alias": arrow_with(badge_link),
    "context-menu": arrow_with(badge_menu),
    "dnd-move": arrow_with(badge_move),
}
ANIMATED = {"wait": g_wait, "progress": g_progress}
