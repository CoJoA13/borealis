#!/usr/bin/env python3
"""Compose Plasma-style 9-slice frames the way KSvg does, for quick previews.

    tools/framepreview.py <file.svgz> <prefix> WxH [dark|light] [out.png]
"""
import gzip
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "src"))

import gi  # noqa: E402
gi.require_version("Rsvg", "2.0")
from gi.repository import Rsvg  # noqa: E402
from PIL import Image  # noqa: E402

from render import surface_to_image  # noqa: E402
from tokens import DARK, LIGHT  # noqa: E402
import cairo  # noqa: E402


def sheet_for(p):
    c = {
        "Text": p["text"], "Background": p["window"], "Highlight": p["accent"],
        "HighlightedText": p["on_accent"], "ViewText": p["text"], "ViewBackground": p["view"],
        "ViewHover": p["accent_hover"], "ViewFocus": p["accent"], "ButtonText": p["text"],
        "ButtonBackground": p["button"], "ButtonHover": p["accent_hover"],
        "ButtonFocus": p["accent"], "NegativeText": p["negative"],
        "PositiveText": p["positive"], "NeutralText": p["neutral"],
    }
    return "".join(f".ColorScheme-{k} {{ color:{v} !important; }}\n" for k, v in c.items())


def load(path):
    data = open(path, "rb").read()
    if data[:2] == b"\x1f\x8b":
        data = gzip.decompress(data)
    return data


def piece(handle, eid):
    ok, ink, log = handle.get_geometry_for_element("#" + eid)
    w, h = max(1, round(log.width)), max(1, round(log.height))
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, w * 4, h * 4)
    ctx = cairo.Context(surf)
    vp = Rsvg.Rectangle()
    vp.x, vp.y, vp.width, vp.height = 0, 0, w * 4, h * 4
    handle.render_element(ctx, "#" + eid, vp)
    return surface_to_image(surf).resize((w, h), Image.LANCZOS)


def has(handle, eid):
    try:
        return handle.has_sub("#" + eid)
    except Exception:
        return False


def compose(data, prefix, W, H, palette):
    handle = Rsvg.Handle.new_from_data(data)
    handle.set_stylesheet(sheet_for(palette).encode())
    p = f"{prefix}-" if prefix else ""
    parts = {n: piece(handle, p + n) for n in
             ("topleft", "top", "topright", "left", "center", "right",
              "bottomleft", "bottom", "bottomright") if has(handle, p + n)}
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    l = parts["left"].width if "left" in parts else 0
    r = parts["right"].width if "right" in parts else 0
    t = parts["top"].height if "top" in parts else 0
    b = parts["bottom"].height if "bottom" in parts else 0
    cw, ch = max(1, W - l - r), max(1, H - t - b)
    place = {
        "topleft": (0, 0, l, t), "top": (l, 0, cw, t), "topright": (W - r, 0, r, t),
        "left": (0, t, l, ch), "center": (l, t, cw, ch), "right": (W - r, t, r, ch),
        "bottomleft": (0, H - b, l, b), "bottom": (l, H - b, cw, b),
        "bottomright": (W - r, H - b, r, b),
    }
    for n, img in parts.items():
        x, y, w, h = place[n]
        if w > 0 and h > 0:
            out.alpha_composite(img.resize((w, h), Image.BILINEAR), (x, y))
    return out


def main():
    path, prefix, size = sys.argv[1:4]
    variant = sys.argv[4] if len(sys.argv) > 4 else "dark"
    outp = sys.argv[5] if len(sys.argv) > 5 else "frame.png"
    W, H = map(int, size.split("x"))
    img = compose(load(path), "" if prefix == "-" else prefix, W, H,
                  DARK if variant == "dark" else LIGHT)
    img.save(outp)


if __name__ == "__main__":
    main()
