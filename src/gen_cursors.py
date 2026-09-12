"""Borealis cursor themes (Snow = light cursor, Ink = dark cursor).

Output per theme (in <out>/icons/<dir>/):
  index.theme
  cursors_scalable/<name>/{*.svg, metadata.json}   (KWin SVG cursors, Plasma >= 6.2)
  cursors/<name>                                   (Xcursor fallback, sizes 24..96)
  + flat alias symlinks in both folders (KWin resolves a single link level).
"""
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(__file__))
import cursor_glyphs as G  # noqa: E402
import xcursor as X  # noqa: E402

NOMINAL = 24
SIZES = (24, 30, 36, 48, 60, 72, 96)

# Breeze's 47 real cursor names -> Borealis glyph keys
CANON = {
    "alias": "alias", "all-scroll": "move", "bottom_left_corner": "sw-resize",
    "bottom_right_corner": "se-resize", "bottom_side": "s-resize", "cell": "cell",
    "center_ptr": "up-arrow", "col-resize": "col-resize", "color-picker": "color-picker",
    "context-menu": "context-menu", "copy": "copy", "crosshair": "crosshair",
    "default": "default", "dnd-move": "grabbing", "dnd-no-drop": "not-allowed",
    "down-arrow": "down-arrow", "draft": "pencil", "fleur": "move", "help": "help",
    "left-arrow": "left-arrow", "left_side": "w-resize", "no-drop": "not-allowed",
    "not-allowed": "forbidden", "openhand": "grab", "pencil": "pencil",
    "pirate": "forbidden", "pointer": "pointer", "progress": "progress",
    "right-arrow": "right-arrow", "right_ptr": "right_ptr", "right_side": "e-resize",
    "row-resize": "row-resize", "size_bdiag": "nesw-resize", "size_fdiag": "nwse-resize",
    "size_hor": "ew-resize", "size_ver": "ns-resize", "text": "text",
    "top_left_corner": "nw-resize", "top_right_corner": "ne-resize", "top_side": "n-resize",
    "up-arrow": "up-arrow", "vertical-text": "vertical-text", "wait": "wait",
    "wayland-cursor": "default", "x-cursor": "x-cursor", "zoom-in": "zoom-in",
    "zoom-out": "zoom-out",
}
EXTRA_ALIASES = {"alias": ["dnd-link"], "context-menu": ["dnd-ask"]}

THEMES = (
    ("Borealis-Snow-Cursors", "Borealis Snow", "Light cursors for dark desktops", G.SNOW),
    ("Borealis-Ink-Cursors", "Borealis Ink", "Dark cursors for light desktops", G.INK),
)

SVG_HEAD = ('<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32">'
            '<defs><filter id="shadow" x="-50%" y="-50%" width="200%" height="200%" '
            'color-interpolation-filters="sRGB"><feGaussianBlur stdDeviation="0.7"/>'
            '</filter></defs>')


def frames_for(key, pal):
    """[(svg_text, hx, hy, delay)] for a glyph key."""
    if key in G.ANIMATED:
        out = []
        for i in range(G.WAIT_FRAMES):
            body, hx, hy = G.ANIMATED[key](i / G.WAIT_FRAMES)(pal)
            out.append((SVG_HEAD + body + "</svg>", hx, hy, G.WAIT_DELAY))
        return out
    body, hx, hy = G.STATIC[key](pal)
    return [(SVG_HEAD + body + "</svg>", hx, hy, 0)]


def build_theme(root, dirname, title, comment, pal):
    base = os.path.join(root, dirname)
    if os.path.exists(base):
        shutil.rmtree(base)
    sc = os.path.join(base, "cursors_scalable")
    xc = os.path.join(base, "cursors")
    os.makedirs(sc)
    os.makedirs(xc)
    for name, key in CANON.items():
        d = os.path.join(sc, name)
        os.makedirs(d)
        meta, frames = [], []
        fr = frames_for(key, pal)
        for i, (svg, hx, hy, delay) in enumerate(fr):
            fn = f"{name}.svg" if len(fr) == 1 else f"{name}-{i + 1:02d}.svg"
            with open(os.path.join(d, fn), "w") as f:
                f.write(svg)
            entry = {"filename": fn, "hotspot_x": hx, "hotspot_y": hy,
                     "nominal_size": NOMINAL}
            if len(fr) > 1:
                entry["delay"] = delay
            meta.append(entry)
            frames.append(X.Frame(os.path.join(d, fn), hx, hy, NOMINAL, delay))
        with open(os.path.join(d, "metadata.json"), "w") as f:
            json.dump(meta, f, indent=4)
        X.write_xcursor(os.path.join(xc, name), X.build_images(frames, SIZES))
    aliases = {k: list(v) for k, v in X.BREEZE_ALIASES.items()}
    for k, v in EXTRA_ALIASES.items():
        aliases.setdefault(k, []).extend(v)
    for folder in (sc, xc):
        X.make_alias_symlinks(folder, aliases)
    with open(os.path.join(base, "index.theme"), "w") as f:
        f.write("[Icon Theme]\n"
                f"Name={title}\n"
                f"Comment={comment} — Borealis\n"
                "Inherits=breeze_cursors\n")
    return base


def build(out_root):
    root = os.path.join(out_root, "icons")
    os.makedirs(root, exist_ok=True)
    return [build_theme(root, *t) for t in THEMES]


if __name__ == "__main__":
    for p in build(sys.argv[1]):
        print(p)
