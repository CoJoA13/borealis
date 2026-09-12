"""Tiny SVG toolkit for Plasma-style 9-slice frames, shadows and masks.

A frame is drawn as nine separate elements (<prefix>-topleft ... -center).
KSvg only uses each element's own bounding box, so pieces are laid out on a
grid (cell by cell) just to keep the files readable in an editor.
Colors come from Plasma's live stylesheet via ColorScheme-* classes.
"""

STYLESHEET = """<style type="text/css" id="current-color-scheme">
.ColorScheme-Text { color:#232629; }
.ColorScheme-Background { color:#eff0f1; }
.ColorScheme-Highlight { color:#3daee9; }
.ColorScheme-HighlightedText { color:#ffffff; }
.ColorScheme-ViewText { color:#232629; }
.ColorScheme-ViewBackground { color:#fcfcfc; }
.ColorScheme-ViewHover { color:#93cee9; }
.ColorScheme-ViewFocus { color:#3daee9; }
.ColorScheme-ButtonText { color:#232629; }
.ColorScheme-ButtonBackground { color:#eff0f1; }
.ColorScheme-ButtonHover { color:#93cee9; }
.ColorScheme-ButtonFocus { color:#3daee9; }
.ColorScheme-NegativeText { color:#da4453; }
.ColorScheme-PositiveText { color:#27ae60; }
.ColorScheme-NeutralText { color:#f67400; }
</style>"""

PIECES = ("topleft", "top", "topright", "left", "center", "right",
          "bottomleft", "bottom", "bottomright")


def fmt(v):
    return ("%.3f" % v).rstrip("0").rstrip(".")


class Doc:
    """Accumulates elements; each add_* call gets its own layout cell."""

    def __init__(self, cell=160):
        self.parts = []
        self.defs = []
        self.cell = cell
        self.col = 0
        self.row = 0
        self.max_h = 0
        self.width = 0
        self.height = 0
        self.gid = 0

    def next_cell(self, w, h):
        pad = 8
        if self.col + w + pad > 1400:
            self.col = 0
            self.row += self.max_h + pad
            self.max_h = 0
        x, y = self.col + pad, self.row + pad
        self.col += w + pad
        self.max_h = max(self.max_h, h + pad)
        self.width = max(self.width, x + w + pad)
        self.height = max(self.height, y + h + pad)
        return x, y

    def uid(self, base):
        self.gid += 1
        return f"{base}{self.gid}"

    def add(self, svg):
        self.parts.append(svg)

    def svg(self):
        return (f'<svg xmlns="http://www.w3.org/2000/svg" '
                f'xmlns:xlink="http://www.w3.org/1999/xlink" '
                f'width="{self.width}" height="{self.height}" '
                f'viewBox="0 0 {self.width} {self.height}">'
                f"{STYLESHEET}<defs>{''.join(self.defs)}</defs>"
                f"{''.join(self.parts)}</svg>")

    # ---------------------------------------------------------------------
    def hint(self, name, w, h):
        """Invisible sizing element (hint-*)."""
        # KSvg treats a 0-sized rect as missing, so "zero" hints are 0.001
        w, h = (w or 0.001), (h or 0.001)
        x, y = self.next_cell(max(w, 1), max(h, 1))
        self.add(f'<rect id="{name}" x="{x}" y="{y}" width="{w:g}" height="{h:g}" '
                 f'fill="#ff00ff" fill-opacity="0"/>')

    def element(self, name, w, h, body):
        """Arbitrary element: body is SVG drawn in local coords (0,0)-(w,h)."""
        x, y = self.next_cell(w, h)
        self.add(f'<g id="{name}" transform="translate({x} {y})">'
                 f'<rect width="{fmt(w)}" height="{fmt(h)}" fill="none"/>{body}</g>')

    def frame(self, prefix, painter, corner, edge_len=20, center=20, sizes=None):
        """Nine pieces from `painter(piece, w, h) -> svg body`.

        corner: (left, top, right, bottom) border sizes, or a single number.
        """
        if isinstance(corner, (int, float)):
            corner = (corner,) * 4
        l, t, r, b = corner
        dims = {
            "topleft": (l, t), "top": (edge_len, t), "topright": (r, t),
            "left": (l, edge_len), "center": (center, center), "right": (r, edge_len),
            "bottomleft": (l, b), "bottom": (edge_len, b), "bottomright": (r, b),
        }
        if sizes:
            dims.update(sizes)
        p = f"{prefix}-" if prefix else ""
        for piece in PIECES:
            w, h = dims[piece]
            if w <= 0 or h <= 0:
                continue
            body = painter(piece, w, h)
            # every piece keeps a transparent box so its bounds are exact
            x, y = self.next_cell(w, h)
            self.add(f'<g id="{p}{piece}" transform="translate({x} {y})">'
                     f'<rect width="{fmt(w)}" height="{fmt(h)}" fill="#000" fill-opacity="0"/>'
                     f"{body}</g>")


# ------------------------------------------------------------------ paint --
def rounded_piece(piece, w, h, r, fill, stroke=None, inset=0.0):
    """Paint one piece of a rounded rectangle of radius r whose outer edge
    sits `inset` px inside the piece's outer edges.

    fill: (css_class_or_color, opacity) or None; stroke: (cls, opacity, width).
    """
    out = []

    def paint(shape_d, spec, is_stroke=False):
        if not spec:
            return
        cls, op = spec[0], spec[1]
        if cls.startswith("#"):
            color = f'fill="{cls}"'
        else:
            color = f'class="{cls}" fill="currentColor"'
        rule = ' fill-rule="evenodd"' if is_stroke else ""
        out.append(f'<path d="{shape_d}" {color} fill-opacity="{fmt(op)}"{rule}/>')

    def corner_shape(cx, cy, rad, quadrant, w_, h_):
        """Quarter disk centred at (cx,cy) radius rad plus filler rects, clipped
        to the piece. quadrant in tl,tr,bl,br."""
        if rad <= 0:
            return ""
        if quadrant == "tl":
            return (f"M{fmt(cx - rad)} {fmt(h_)} V{fmt(cy)} "
                    f"A{fmt(rad)} {fmt(rad)} 0 0 1 {fmt(cx)} {fmt(cy - rad)} "
                    f"H{fmt(w_)} V{fmt(h_)} Z")
        if quadrant == "tr":
            return (f"M0 {fmt(cy - rad)} H{fmt(cx)} "
                    f"A{fmt(rad)} {fmt(rad)} 0 0 1 {fmt(cx + rad)} {fmt(cy)} "
                    f"V{fmt(h_)} H0 Z")
        if quadrant == "bl":
            return (f"M{fmt(w_)} 0 V{fmt(cy + rad)} H{fmt(cx)} "
                    f"A{fmt(rad)} {fmt(rad)} 0 0 1 {fmt(cx - rad)} {fmt(cy)} "
                    f"V0 Z")
        return (f"M0 0 H{fmt(cx + rad)} V{fmt(cy)} "
                f"A{fmt(rad)} {fmt(rad)} 0 0 1 {fmt(cx)} {fmt(cy + rad)} H0 Z")

    s = inset
    if piece == "center":
        paint(f"M0 0 H{fmt(w)} V{fmt(h)} H0 Z", fill)
        return "".join(out)
    edges = {
        "top": (f"M0 {fmt(s)} H{fmt(w)} V{fmt(h)} H0 Z", "h"),
        "bottom": (f"M0 0 H{fmt(w)} V{fmt(h - s)} H0 Z", "h"),
        "left": (f"M{fmt(s)} 0 H{fmt(w)} V{fmt(h)} H{fmt(s)} Z", "v"),
        "right": (f"M0 0 H{fmt(w - s)} V{fmt(h)} H0 Z", "v"),
    }
    if piece in edges:
        d, _ = edges[piece]
        paint(d, fill)
        if stroke:
            sw = stroke[2]
            line = {
                "top": f"M0 {fmt(s)} H{fmt(w)} V{fmt(s + sw)} H0 Z",
                "bottom": f"M0 {fmt(h - s - sw)} H{fmt(w)} V{fmt(h - s)} H0 Z",
                "left": f"M{fmt(s)} 0 H{fmt(s + sw)} V{fmt(h)} H{fmt(s)} Z",
                "right": f"M{fmt(w - s - sw)} 0 H{fmt(w - s)} V{fmt(h)} H{fmt(w - s - sw)} Z",
            }[piece]
            paint(line, stroke)
        return "".join(out)
    # corners: circle centre sits r px in from both outer edges
    q = {"topleft": "tl", "topright": "tr", "bottomleft": "bl", "bottomright": "br"}[piece]
    cx = s + r if q in ("tl", "bl") else w - s - r
    cy = s + r if q in ("tl", "tr") else h - s - r
    paint(corner_shape(cx, cy, r, q, w, h), fill)
    if stroke:
        paint(_corner_ring(cx, cy, r, stroke[2], q, w, h), stroke, is_stroke=True)
    return "".join(out)


def _corner_ring(cx, cy, r, sw, q, w, h):
    ri = r - sw
    if q == "tl":
        return (f"M{fmt(cx - r)} {fmt(h)} V{fmt(cy)} A{fmt(r)} {fmt(r)} 0 0 1 {fmt(cx)} {fmt(cy - r)} "
                f"H{fmt(w)} V{fmt(cy - ri)} H{fmt(cx)} A{fmt(ri)} {fmt(ri)} 0 0 0 {fmt(cx - ri)} {fmt(cy)} "
                f"V{fmt(h)} Z")
    if q == "tr":
        return (f"M0 {fmt(cy - r)} H{fmt(cx)} A{fmt(r)} {fmt(r)} 0 0 1 {fmt(cx + r)} {fmt(cy)} "
                f"V{fmt(h)} H{fmt(cx + ri)} V{fmt(cy)} A{fmt(ri)} {fmt(ri)} 0 0 0 {fmt(cx)} {fmt(cy - ri)} "
                f"H0 Z")
    if q == "bl":
        return (f"M{fmt(w)} {fmt(cy + r)} H{fmt(cx)} A{fmt(r)} {fmt(r)} 0 0 1 {fmt(cx - r)} {fmt(cy)} "
                f"V0 H{fmt(cx - ri)} V{fmt(cy)} A{fmt(ri)} {fmt(ri)} 0 0 0 {fmt(cx)} {fmt(cy + ri)} "
                f"H{fmt(w)} Z")
    return (f"M0 {fmt(cy + r)} H{fmt(cx)} A{fmt(r)} {fmt(r)} 0 0 0 {fmt(cx + r)} {fmt(cy)} "
            f"V0 H{fmt(cx + ri)} V{fmt(cy)} A{fmt(ri)} {fmt(ri)} 0 0 1 {fmt(cx)} {fmt(cy + ri)} "
            f"H0 Z")


def shadow_piece(doc, piece, w, h, r, size, color="#000000", strength=0.32, falloff=None):
    """Soft shadow outside a rounded rect of radius r; tiles are (size+r) thick,
    the inner r px (under the frame) stay transparent except around corners."""
    stops = falloff or ((0.0, 1.0), (0.12, 0.72), (0.3, 0.42), (0.5, 0.2), (0.72, 0.07), (1.0, 0.0))
    total = size + r

    def stop_list(offset0):
        # offset0 = where the shadow begins (frame edge) in gradient space
        out = [f'<stop offset="0" stop-color="{color}" stop-opacity="0"/>']
        if offset0 > 0:
            out.append(f'<stop offset="{fmt(max(0, offset0 - 0.0001))}" stop-color="{color}" stop-opacity="0"/>')
        for o, a in stops:
            out.append(f'<stop offset="{fmt(offset0 + (1 - offset0) * o)}" '
                       f'stop-color="{color}" stop-opacity="{fmt(a * strength)}"/>')
        return "".join(out)

    gid = doc.uid("sg")
    if piece == "center":
        return ""
    if piece in ("top", "bottom", "left", "right"):
        # gradient runs from the frame edge (inner boundary at r) outwards
        if piece == "top":
            x1, y1, x2, y2 = 0, h - r, 0, h - total
        elif piece == "bottom":
            x1, y1, x2, y2 = 0, r, 0, total
        elif piece == "left":
            x1, y1, x2, y2 = w - r, 0, w - total, 0
        else:
            x1, y1, x2, y2 = r, 0, total, 0
        doc.defs.append(f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" '
                        f'x1="{fmt(x1)}" y1="{fmt(y1)}" x2="{fmt(x2)}" y2="{fmt(y2)}">'
                        f"{stop_list(0)}</linearGradient>")
        rect = {"top": (0, 0, w, h - r), "bottom": (0, r, w, h - r),
                "left": (0, 0, w - r, h), "right": (r, 0, w - r, h)}[piece]
        return (f'<rect x="{fmt(rect[0])}" y="{fmt(rect[1])}" width="{fmt(rect[2])}" '
                f'height="{fmt(rect[3])}" fill="url(#{gid})"/>')
    # corners: radial gradient centred on the frame's corner-circle centre,
    # which is the tile corner that points into the frame
    cx = w if piece in ("topleft", "bottomleft") else 0
    cy = h if piece in ("topleft", "topright") else 0
    rad = total
    doc.defs.append(f'<radialGradient id="{gid}" gradientUnits="userSpaceOnUse" '
                    f'cx="{fmt(cx)}" cy="{fmt(cy)}" r="{fmt(rad)}">'
                    f"{stop_list(r / rad)}</radialGradient>")
    return f'<rect width="{fmt(w)}" height="{fmt(h)}" fill="url(#{gid})"/>'
