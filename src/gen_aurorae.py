"""Borealis window decorations (Aurorae v2 SVG themes): Borealis-Dark/-Light.

Frame model (KWin 6.7 Aurorae v2): decoration.svg is a KSvg 9-slice drawn at
window size + Padding*; column/row sizes are the pieces' natural sizes, edges
tile, the centre stretches. Buttons are one '<state>-center' element each,
stretched to ButtonWidth x ButtonHeight.
"""
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(__file__))
from svgkit import fmt  # noqa: E402
from tokens import AUTHOR, DARK, EMAIL, IDS, LICENSE, LIGHT, VERSION, kde, mix  # noqa: E402

PAD_L = PAD_R = 24
PAD_T, PAD_B = 16, 32
SHADOW_DY = 8          # shadow centre offset (so: 16 above, 32 below, 24 aside)
SHADOW_EXT = 24        # blur extent
R_TOP = 12             # rounded titlebar corners
R_BOT = 4              # bottom corners (<= border so the client never pokes out)
BORDER = 4
TITLE_EDGE_T, TITLE_H, TITLE_EDGE_B = 6, 22, 6
TITLE = TITLE_EDGE_T + TITLE_H + TITLE_EDGE_B
BTN_W, BTN_H = 28, 22

FALLOFF = ((0.0, 1.0), (0.1, 0.78), (0.25, 0.5), (0.45, 0.24), (0.7, 0.07), (1.0, 0.0))


# ---------------------------------------------------------------- frame ----
class Deco:
    def __init__(self):
        self.parts, self.defs, self.n, self.y = [], [], 0, 8

    def uid(self):
        self.n += 1
        return f"g{self.n}"

    def piece(self, eid, w, h, body, x):
        self.parts.append(f'<g id="{eid}" transform="translate({x} {self.y})">'
                          f'<rect width="{w}" height="{h}" fill="#000" fill-opacity="0"/>{body}</g>')

    def svg(self, width=900):
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{self.y + 8}" '
                f'viewBox="0 0 {width} {self.y + 8}"><defs>{"".join(self.defs)}</defs>'
                f'{"".join(self.parts)}</svg>')


def stops(color, strength):
    return "".join(f'<stop offset="{fmt(o)}" stop-color="{color}" stop-opacity="{fmt(a * strength)}"/>'
                   for o, a in FALLOFF)


def shadow_layer(d, piece, w, h, color, strength):
    """Shadow of the window rect (offset by SHADOW_DY) inside one frame piece.

    Frame coords: window outer box spans x in [PAD_L, W-PAD_R], y in [PAD_T, H-PAD_B].
    Pieces: left column width = PAD_L + R_TOP, top row = PAD_T + TITLE,
    bottom row = PAD_B + BORDER.
    """
    ext = SHADOW_EXT
    out = []

    def lin(x1, y1, x2, y2, rx, ry, rw, rh):
        g = d.uid()
        d.defs.append(f'<linearGradient id="{g}" gradientUnits="userSpaceOnUse" x1="{fmt(x1)}" '
                      f'y1="{fmt(y1)}" x2="{fmt(x2)}" y2="{fmt(y2)}">{stops(color, strength)}</linearGradient>')
        if rw > 0 and rh > 0:
            out.append(f'<rect x="{fmt(rx)}" y="{fmt(ry)}" width="{fmt(rw)}" height="{fmt(rh)}" fill="url(#{g})"/>')

    def rad(cx, cy, r0, rx, ry, rw, rh):
        """Rounded shadow-box corner: solid inside radius r0, then falloff."""
        g = d.uid()
        total = r0 + ext
        s0 = r0 / total
        st = f'<stop offset="0" stop-color="{color}" stop-opacity="{fmt(strength)}"/>'
        st += "".join(f'<stop offset="{fmt(s0 + (1 - s0) * o)}" stop-color="{color}" '
                      f'stop-opacity="{fmt(a * strength)}"/>' for o, a in FALLOFF)
        d.defs.append(f'<radialGradient id="{g}" gradientUnits="userSpaceOnUse" cx="{fmt(cx)}" '
                      f'cy="{fmt(cy)}" r="{fmt(total)}">{st}</radialGradient>')
        if rw > 0 and rh > 0:
            out.append(f'<rect x="{fmt(rx)}" y="{fmt(ry)}" width="{fmt(rw)}" height="{fmt(rh)}" fill="url(#{g})"/>')

    def solid(rx, ry, rw, rh):
        if rw > 0 and rh > 0:
            out.append(f'<rect x="{fmt(rx)}" y="{fmt(ry)}" width="{fmt(rw)}" height="{fmt(rh)}" '
                       f'fill="{color}" fill-opacity="{fmt(strength)}"/>')

    # shadow box edges in piece-local coordinates
    left_x, top_y = PAD_L, PAD_T + SHADOW_DY
    if piece == "topleft":
        cx, cy = PAD_L + R_TOP, top_y + R_TOP
        rad(cx, cy, R_TOP, 0, 0, cx, cy)
        lin(left_x, 0, left_x - ext, 0, 0, cy, left_x, h - cy)
    elif piece == "topright":
        cx, cy = w - PAD_R - R_TOP, top_y + R_TOP
        rad(cx, cy, R_TOP, cx, 0, w - cx, cy)
        lin(w - PAD_R, 0, w - PAD_R + ext, 0, w - PAD_R, cy, PAD_R, h - cy)
    elif piece == "top":
        lin(0, top_y, 0, top_y - ext, 0, 0, w, top_y)
    elif piece == "left":
        lin(left_x, 0, left_x - ext, 0, 0, 0, left_x, h)
    elif piece == "right":
        lin(w - PAD_R, 0, w - PAD_R + ext, 0, w - PAD_R, 0, PAD_R, h)
    elif piece in ("bottomleft", "bottomright", "bottom"):
        yb = h - PAD_B                     # window bottom edge
        bottom_y = yb + SHADOW_DY          # shadow box bottom edge
        rb = R_BOT
        if piece == "bottom":
            solid(0, yb, w, bottom_y - yb)
            lin(0, bottom_y, 0, bottom_y + ext, 0, bottom_y, w, h - bottom_y)
        elif piece == "bottomleft":
            xl = PAD_L
            cx, cy = xl + rb, bottom_y - rb
            lin(xl, 0, xl - ext, 0, 0, 0, xl, cy)
            rad(cx, cy, rb, 0, cy, cx, h - cy)
            lin(0, bottom_y, 0, bottom_y + ext, cx, bottom_y, w - cx, h - bottom_y)
            solid(cx, yb, w - cx, bottom_y - yb)
            solid(xl, yb, cx - xl, cy - yb)
        else:
            xr = w - PAD_R
            cx, cy = xr - rb, bottom_y - rb
            lin(xr, 0, xr + ext, 0, xr, 0, w - xr, cy)
            rad(cx, cy, rb, cx, cy, w - cx, h - cy)
            lin(0, bottom_y, 0, bottom_y + ext, 0, bottom_y, cx, h - bottom_y)
            solid(0, yb, cx, bottom_y - yb)
            solid(cx, yb, xr - cx, cy - yb)
    return "".join(out)


def window_shape(piece, w, h, fill, outline, title_fill):
    """Titlebar + border fill and the 1px outline, per piece."""
    L, T = PAD_L, PAD_T
    out = []
    ttl_bottom = PAD_T + TITLE

    def path(d_, color, op=1.0):
        out.append(f'<path d="{d_}" fill="{color}" fill-opacity="{fmt(op)}"/>')

    o_col, o_op = outline
    if piece == "topleft":
        # outer rounded corner, filled down to the piece bottom
        shape = (f"M{L} {h} V{T + R_TOP} A{R_TOP} {R_TOP} 0 0 1 {L + R_TOP} {T} H{w} V{h} Z")
        path(shape, o_col, o_op)
        inner = (f"M{L + 1} {h} V{T + R_TOP} A{R_TOP - 1} {R_TOP - 1} 0 0 1 {L + R_TOP} {T + 1} "
                 f"H{w} V{h} Z")
        path(inner, title_fill)
        if h > ttl_bottom:
            path(f"M{L + 1} {ttl_bottom} H{w} V{h} H{L + 1} Z", fill)
    elif piece == "topright":
        rx = w - PAD_R
        shape = f"M0 {T} H{rx - R_TOP} A{R_TOP} {R_TOP} 0 0 1 {rx} {T + R_TOP} V{h} H0 Z"
        path(shape, o_col, o_op)
        inner = (f"M0 {T + 1} H{rx - R_TOP} A{R_TOP - 1} {R_TOP - 1} 0 0 1 {rx - 1} {T + R_TOP} "
                 f"V{h} H0 Z")
        path(inner, title_fill)
        if h > ttl_bottom:
            path(f"M0 {ttl_bottom} H{rx - 1} V{h} H0 Z", fill)
    elif piece == "top":
        path(f"M0 {T} H{w} V{T + 1} H0 Z", o_col, o_op)
        path(f"M0 {T + 1} H{w} V{ttl_bottom} H0 Z", title_fill)
        if h > ttl_bottom:
            path(f"M0 {ttl_bottom} H{w} V{h} H0 Z", fill)
    elif piece == "left":
        path(f"M{L} 0 H{L + 1} V{h} H{L} Z", o_col, o_op)
        path(f"M{L + 1} 0 H{w} V{h} H{L + 1} Z", fill)
    elif piece == "right":
        rx = w - PAD_R
        path(f"M{rx - 1} 0 H{rx} V{h} H{rx - 1} Z", o_col, o_op)
        path(f"M0 0 H{rx - 1} V{h} H0 Z", fill)
    elif piece == "center":
        path(f"M0 0 H{w} V{h} H0 Z", fill)
    elif piece == "bottom":
        by = h - PAD_B
        path(f"M0 {by - 1} H{w} V{by} H0 Z", o_col, o_op)
        path(f"M0 0 H{w} V{by - 1} H0 Z", fill)
    elif piece == "bottomleft":
        by = h - PAD_B
        rb = R_BOT
        path(f"M{L} 0 V{by - rb} A{rb} {rb} 0 0 0 {L + rb} {by} H{w} V0 Z", o_col, o_op)
        path(f"M{L + 1} 0 V{by - rb} A{rb - 1} {rb - 1} 0 0 0 {L + rb} {by - 1} H{w} V0 Z", fill)
    elif piece == "bottomright":
        by = h - PAD_B
        rx = w - PAD_R
        rb = R_BOT
        path(f"M0 {by} H{rx - rb} A{rb} {rb} 0 0 0 {rx} {by - rb} V0 H0 Z", o_col, o_op)
        path(f"M0 {by - 1} H{rx - rb} A{rb - 1} {rb - 1} 0 0 0 {rx - 1} {by - rb} V0 H0 Z", fill)
    return "".join(out)


def decoration_svg(p):
    d = Deco()
    cw, rh = PAD_L + R_TOP, PAD_T + TITLE          # corner column width, top row height
    bh = PAD_B + BORDER + 2                        # bottom row height
    edge = 40
    sizes = {"topleft": (cw, rh), "top": (edge, rh), "topright": (cw, rh),
             "left": (cw, edge), "center": (edge, edge), "right": (cw, edge),
             "bottomleft": (cw, bh), "bottom": (edge, bh), "bottomright": (cw, bh)}
    shadow_col = "#000000" if p["is_dark"] else "#1b2130"
    looks = {
        "decoration": (p["header"], (p["border_strong"], 1.0), 0.55 if p["is_dark"] else 0.26),
        "decoration-inactive": (p["header_inactive"], (p["border"], 1.0), 0.36 if p["is_dark"] else 0.16),
    }
    for prefix, (bg, outline, strength) in looks.items():
        x = 8
        for piece in ("topleft", "top", "topright", "left", "center", "right",
                      "bottomleft", "bottom", "bottomright"):
            w, h = sizes[piece]
            body = shadow_layer(d, piece, w, h, shadow_col, strength)
            body += window_shape(piece, w, h, bg, outline, bg)
            d.piece(f"{prefix}-{piece}", w, h, body, x)
            x += w + 8
        d.y += max(s[1] for s in sizes.values()) + 16
    # maximized: only the centre is used, stretched over the title bar
    for prefix, bg in (("decoration-maximized", p["header"]),
                       ("decoration-maximized-inactive", p["header_inactive"])):
        d.piece(f"{prefix}-center", 40, TITLE, f'<rect width="40" height="{TITLE}" fill="{bg}"/>', 8)
        d.y += TITLE + 16
    return d.svg()


# --------------------------------------------------------------- buttons ---
GLYPHS = {
    "close": "M-2.6 -2.6 L2.6 2.6 M2.6 -2.6 L-2.6 2.6",
    "minimize": "M-3 0 H3",
    "maximize": "M-2.8 -1.6 A1.2 1.2 0 0 1 -1.6 -2.8 H1.6 A1.2 1.2 0 0 1 2.8 -1.6 V1.6 "
                "A1.2 1.2 0 0 1 1.6 2.8 H-1.6 A1.2 1.2 0 0 1 -2.8 1.6 Z",
    "restore": "M-2.8 -0.6 H1.2 V3 H-2.8 Z M-1 -2.8 H3 V1",
    "alldesktops": "M-1.8 0 A1.8 1.8 0 1 0 1.8 0 A1.8 1.8 0 1 0 -1.8 0 Z",
    "keepabove": "M-3 1.6 L0 -1.4 L3 1.6",
    "keepbelow": "M-3 -1.6 L0 1.4 L3 -1.6",
    "shade": "M-3 -2 H3 M-3 1.6 L0 -0.6 L3 1.6",
    "help": "M-1.8 -1.2 C-1.8 -2.6 -0.9 -3.2 0 -3.2 C1.1 -3.2 1.9 -2.5 1.9 -1.5 "
            "C1.9 -0.1 0 0 0 1.4 M0 3.1 V3.2",
    "appmenu": "M-3 -2.2 H3 M-3 0 H3 M-3 2.2 H3",
}


def pill(w, h, color, op=1.0, glyph=None, glyph_color="#000", glyph_op=0.85):
    x, y = (BTN_W - w) / 2, (BTN_H - h) / 2
    s = (f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" height="{fmt(h)}" rx="{fmt(h / 2)}" '
         f'fill="{color}" fill-opacity="{fmt(op)}"/>')
    if glyph:
        s += (f'<path transform="translate({BTN_W / 2} {BTN_H / 2})" d="{glyph}" fill="none" '
              f'stroke="{glyph_color}" stroke-opacity="{fmt(glyph_op)}" stroke-width="1.5" '
              f'stroke-linecap="round" stroke-linejoin="round"/>')
    return s


def button_svg(p, name):
    main = {"minimize": p["pill_min"], "maximize": p["pill_max"], "restore": p["pill_max"],
            "close": p["pill_close"]}.get(name)
    g = GLYPHS[name]
    ink = p["pill_glyph"]
    other = p["pill_other"]
    darker = lambda c: mix(c, "#000000", 0.18)  # noqa: E731
    small, big = (16, 7), (24, 12)
    if main:
        st = {
            "active": pill(*small, main),
            "inactive": pill(*small, p["pill_inactive"]),
            "hover": pill(*big, main, glyph=g, glyph_color=ink),
            "pressed": pill(*big, darker(main), glyph=g, glyph_color=ink),
            "deactivated": pill(*small, other, op=0.35),
            "hover-inactive": pill(*big, main, glyph=g, glyph_color=ink),
            "pressed-inactive": pill(*big, darker(main), glyph=g, glyph_color=ink),
            "deactivated-inactive": pill(*small, p["pill_inactive"], op=0.5),
        }
    else:
        txt = p["text"]
        st = {
            "active": pill(*small, other),
            "inactive": pill(*small, p["pill_inactive"]),
            "hover": pill(*big, mix(other, txt, 0.12), glyph=g, glyph_color=txt, glyph_op=0.9),
            # pressed doubles as the 'checked' look for toggles (pin, keep above...)
            "pressed": pill(*big, p["accent"], glyph=g, glyph_color=ink),
            "deactivated": pill(*small, other, op=0.35),
            "hover-inactive": pill(*big, mix(other, txt, 0.12), glyph=g, glyph_color=txt, glyph_op=0.9),
            "pressed-inactive": pill(*big, p["accent"], glyph=g, glyph_color=ink),
            "deactivated-inactive": pill(*small, p["pill_inactive"], op=0.5),
        }
    parts, x = [], 4
    for state, body in st.items():
        parts.append(f'<g id="{state}-center" transform="translate({x} 4)">'
                     f'<rect width="{BTN_W}" height="{BTN_H}" fill="#000" fill-opacity="0"/>{body}</g>')
        x += BTN_W + 4
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{x}" height="{BTN_H + 8}" '
            f'viewBox="0 0 {x} {BTN_H + 8}">{"".join(parts)}</svg>')


# ------------------------------------------------------------------ files --
def rc(p):
    return "\n".join([
        "[General]",
        f"ActiveTextColor={kde(p['text'])}",
        f"InactiveTextColor={kde(p['text_inactive'])}",
        "TitleAlignment=Center",
        "TitleVerticalAlignment=Center",
        "Animation=0",
        "ButtonGroupHover=false",
        "",
        "[Layout]",
        f"BorderLeft={BORDER}",
        f"BorderRight={BORDER}",
        f"BorderBottom={BORDER}",
        f"TitleEdgeTop={TITLE_EDGE_T}",
        f"TitleEdgeBottom={TITLE_EDGE_B}",
        "TitleEdgeLeft=10",
        "TitleEdgeRight=8",
        f"TitleEdgeTopMaximized={TITLE_EDGE_T - 2}",
        f"TitleEdgeBottomMaximized={TITLE_EDGE_B - 2}",
        "TitleEdgeLeftMaximized=8",
        "TitleEdgeRightMaximized=6",
        "TitleBorderLeft=8",
        "TitleBorderRight=8",
        f"TitleHeight={TITLE_H}",
        f"ButtonWidth={BTN_W}",
        f"ButtonHeight={BTN_H}",
        "ButtonSpacing=0",
        "ButtonMarginTop=0",
        "ButtonMarginTopMaximized=0",
        "ExplicitButtonSpacer=10",
        f"PaddingLeft={PAD_L}",
        f"PaddingRight={PAD_R}",
        f"PaddingTop={PAD_T}",
        f"PaddingBottom={PAD_B}",
        "",
    ])


def build(out_root):
    made = []
    for p, dirname in ((DARK, IDS["aurorae_dark"]), (LIGHT, IDS["aurorae_light"])):
        base = os.path.join(out_root, "aurorae", "themes", dirname)
        if os.path.exists(base):
            shutil.rmtree(base)
        os.makedirs(base)
        with open(os.path.join(base, "decoration.svg"), "w") as f:
            f.write(decoration_svg(p))
        for name in GLYPHS:
            with open(os.path.join(base, f"{name}.svg"), "w") as f:
                f.write(button_svg(p, name))
        with open(os.path.join(base, f"{dirname}rc"), "w") as f:
            f.write(rc(p))
        with open(os.path.join(base, "metadata.desktop"), "w") as f:
            f.write("[Desktop Entry]\n"
                    f"Name={p['title']}\n"
                    f"X-KDE-PluginInfo-Author={AUTHOR}\n"
                    f"X-KDE-PluginInfo-Email={EMAIL}\n"
                    f"X-KDE-PluginInfo-Name={dirname}\n"
                    f"X-KDE-PluginInfo-Version={VERSION}\n"
                    "X-KDE-PluginInfo-Category=\n"
                    f"X-KDE-PluginInfo-License={LICENSE}\n"
                    "X-KDE-PluginInfo-EnabledByDefault=true\n")
        meta = {"KPackageStructure": "KWin/Aurorae",
                "KPlugin": {"Authors": [{"Name": AUTHOR, "Email": EMAIL}],
                            "Description": f"{p['title']} window decoration with aurora pill buttons",
                            "Id": dirname, "License": LICENSE, "Name": p["title"],
                            "Version": VERSION}}
        with open(os.path.join(base, "metadata.json"), "w") as f:
            json.dump(meta, f, indent=4)
        made.append(base)
    return made


if __name__ == "__main__":
    print(build(sys.argv[1]))
