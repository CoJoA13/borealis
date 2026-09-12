"""Procedural Borealis wallpapers: 'night' (dark) and 'dawn' (light).

Renders a 3840x2400 master per variant with pycairo + PIL, then derives the
resolutions Plasma picks from (images/ = light, images_dark/ = dark).
"""
import math
import os
import random
import sys

import cairo
from PIL import Image, ImageChops, ImageEnhance, ImageFilter

sys.path.insert(0, os.path.dirname(__file__))
from tokens import rgbf  # noqa: E402

W, H = 3840, 2400


# ---------------------------------------------------------------- noise ----
def value_noise(n, period, seed):
    """Smooth 1-D value noise in [0,1], one random knot every `period` px."""
    rnd = random.Random(seed)
    knots = [rnd.random() for _ in range(int(n / period) + 3)]
    out = []
    for i in range(n):
        x = i / period
        k = int(x)
        t = x - k
        t = t * t * (3 - 2 * t)
        out.append(knots[k] * (1 - t) + knots[k + 1] * t)
    return out


def fbm(n, period, octaves, seed, gain=0.5):
    total = [0.0] * n
    amp, norm = 1.0, 0.0
    for o in range(octaves):
        v = value_noise(n, max(1.0, period / (2 ** o)), seed + 7919 * o)
        for i in range(n):
            total[i] += v[i] * amp
        norm += amp
        amp *= gain
    return [t / norm for t in total]


def ridge(n, seed, rough=0.52, levels=12):
    """Midpoint-displacement ridge line, normalised to [0,1], length n."""
    size = 2 ** levels + 1
    rnd = random.Random(seed)
    pts = [0.0] * size
    pts[0], pts[-1] = rnd.uniform(-1, 1), rnd.uniform(-1, 1)
    step, scale = size - 1, 1.0
    while step > 1:
        half = step // 2
        for i in range(half, size - 1, step):
            pts[i] = (pts[i - half] + pts[i + half]) / 2 + rnd.uniform(-1, 1) * scale
        scale *= rough
        step = half
    lo, hi = min(pts), max(pts)
    pts = [(p - lo) / (hi - lo) for p in pts]
    out = []
    for i in range(n):
        x = i / (n - 1) * (size - 1)
        k = min(int(x), size - 2)
        t = x - k
        out.append(pts[k] * (1 - t) + pts[k + 1] * t)
    return out


def smoothstep(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


# --------------------------------------------------------------- helpers ---
def surface_rgb(surf):
    return Image.frombuffer("RGB", (surf.get_width(), surf.get_height()),
                            bytes(surf.get_data()), "raw", "BGRX",
                            surf.get_stride(), 1).copy()


def surface_rgba(surf):
    return Image.frombuffer("RGBA", (surf.get_width(), surf.get_height()),
                            bytes(surf.get_data()), "raw", "BGRa",
                            surf.get_stride(), 1).copy()


def scaled(img, k):
    return ImageEnhance.Brightness(img).enhance(k)


def add_grain(img, sigma=22, strength=5):
    """Signed dither noise (+/- a few levels) to kill gradient banding."""
    noise = Image.effect_noise(img.size, sigma)
    pos = noise.point(lambda v: max(0, v - 128) * strength // 64)
    neg = noise.point(lambda v: max(0, 128 - v) * strength // 64)
    pos = Image.merge("RGB", (pos, pos, pos))
    neg = Image.merge("RGB", (neg, neg, neg))
    return ImageChops.subtract(ImageChops.add(img, pos), neg)


def vignette(img, strength):
    mask = cairo.ImageSurface(cairo.FORMAT_RGB24, W // 4, H // 4)
    c = cairo.Context(mask)
    g = cairo.RadialGradient(W / 8, H / 8 * 0.9, 0, W / 8, H / 8, W / 8 * 1.15)
    g.add_color_stop_rgb(0.0, 1, 1, 1)
    g.add_color_stop_rgb(0.55, 1, 1, 1)
    g.add_color_stop_rgb(1.0, 1 - strength, 1 - strength, 1 - strength)
    c.set_source(g)
    c.paint()
    m = surface_rgb(mask).resize(img.size, Image.BICUBIC)
    return ImageChops.multiply(img, m)


# ---------------------------------------------------------------- aurora ---
class Ribbon:
    def __init__(self, seed, y0, rise, amp, height, strength, t0=-0.2, t1=1.2,
                 slant=0.16, fold_amp=0.03, fold_freq=5.0, wave=1.0):
        self.seed = seed
        self.y0, self.rise, self.amp = y0, rise, amp
        self.height, self.strength = height, strength
        self.t0, self.t1 = t0, t1
        self.slant = slant
        self.fold_amp, self.fold_freq, self.wave = fold_amp, fold_freq, wave


def draw_ribbons(ctx, ribbons, colors, alpha_scale=1.0, edge_px=26):
    """Each ribbon is a curtain of thin rays hung from a folded base curve.

    The base curve's x runs back on itself in places (fold_amp*fold_freq
    close to 1/2pi), so curtain segments overlap there and read as bright
    folds under additive blending.
    """
    edge_c, core_c, mid_c, top_c = [rgbf(c) for c in colors]
    for rb in ribbons:
        n = int(W * 2.4 * (rb.t1 - rb.t0))
        rnd = random.Random(rb.seed)
        p1, p2, p3 = (rnd.uniform(0, 6.28) for _ in range(3))
        wobble = fbm(n, n / 5, 4, rb.seed + 1)
        hvar = fbm(n, n / 9, 4, rb.seed + 2)
        lowf = fbm(n, n / 7, 3, rb.seed + 3)
        rays = fbm(n, 90, 3, rb.seed + 4, gain=0.55)
        fine = fbm(n, 14, 2, rb.seed + 5, gain=0.7)
        tall = fbm(n, 40, 2, rb.seed + 6, gain=0.6)
        for i in range(n):
            t = rb.t0 + (rb.t1 - rb.t0) * i / (n - 1)
            x = (t + rb.fold_amp * math.sin(6.2832 * rb.fold_freq * t + p3)) * W
            env = smoothstep(rb.t0 - 0.05, rb.t0 + 0.3, t) * \
                (1 - smoothstep(rb.t1 - 0.35, rb.t1 + 0.05, t))
            if env <= 0.002 or x < -W * 0.3 or x > W * 1.05:
                continue
            yb = (rb.y0 - rb.rise * t
                  + rb.amp * math.sin(t * 6.28 * 0.8 * rb.wave + p1)
                  + rb.amp * 0.4 * math.sin(t * 6.28 * 2.1 * rb.wave + p2)
                  + (wobble[i] - 0.5) * rb.amp * 1.4) * H
            yb += (fine[i] - 0.5) * 3
            r = rays[i]
            ray = 0.38 + 0.62 * max(0.0, (r - 0.2) / 0.8) ** 1.3
            h = rb.height * H * (0.5 + 0.6 * hvar[i]) * (0.6 + 0.8 * tall[i] ** 2)
            a = rb.strength * env * (0.4 + 0.6 * lowf[i]) * ray * \
                (0.85 + 0.15 * fine[i])
            a = min(1.0, a) * alpha_scale * 0.42
            if a < 0.003:
                continue
            sl = rb.slant * h
            g = cairo.LinearGradient(0, yb + edge_px, 0, yb - h)
            e = edge_px / (h + edge_px)
            g.add_color_stop_rgba(0.0, *edge_c, 0.0)
            g.add_color_stop_rgba(e, *edge_c, a)
            g.add_color_stop_rgba(e + 0.08, *core_c, a * 0.85)
            g.add_color_stop_rgba(0.40, *mid_c, a * 0.40)
            g.add_color_stop_rgba(0.70, *top_c, a * 0.15)
            g.add_color_stop_rgba(1.0, *top_c, 0.0)
            ctx.set_source(g)
            wdt = 2.4
            ctx.move_to(x, yb + edge_px)
            ctx.line_to(x + wdt, yb + edge_px)
            ctx.line_to(x + wdt + sl, yb - h)
            ctx.line_to(x + sl, yb - h)
            ctx.close_path()
            ctx.fill()


RIBBONS = [
    # seed, y0, rise, amp, height, strength
    Ribbon(11, 0.64, 0.30, 0.060, 0.30, 1.00, fold_amp=0.020, fold_freq=4.0,
           wave=0.7),
    Ribbon(23, 0.42, 0.12, 0.030, 0.20, 0.50, t0=0.25, t1=1.25,
           fold_amp=0.018, fold_freq=5.0, slant=0.2, wave=1.1),
]


# ------------------------------------------------------------- mountains ---
def mountain_path(ctx, seed, base, amp, rough, x_shift=0.0):
    r = ridge(W // 2 + 1, seed, rough)
    ctx.move_to(0, H)
    for i, v in enumerate(r):
        x = i * 2
        u = x / W + x_shift
        # gentle large-scale shape so peaks sit off-centre
        shape = 0.55 + 0.45 * math.sin(u * 3.1 + seed)
        ctx.line_to(x, (base - amp * v * shape) * H)
    ctx.line_to(W, H)
    ctx.close_path()
    return r


def fill_vertical(ctx, top_hex, bottom_hex, y_top, y_bottom, alpha=1.0):
    g = cairo.LinearGradient(0, y_top * H, 0, y_bottom * H)
    g.add_color_stop_rgba(0, *rgbf(top_hex), alpha)
    g.add_color_stop_rgba(1, *rgbf(bottom_hex), alpha)
    ctx.set_source(g)
    ctx.fill()


# ----------------------------------------------------------------- night ---
def night_sky():
    """Sky gradient, horizon glow and stars (no aurora, no mountains)."""
    sky = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
    c = cairo.Context(sky)
    g = cairo.LinearGradient(0, 0, 0, H)
    for off, col in ((0.0, "#04060c"), (0.35, "#080d1a"), (0.62, "#0c1526"),
                     (0.80, "#12223a"), (1.0, "#0b1322")):
        g.add_color_stop_rgb(off, *rgbf(col))
    c.set_source(g)
    c.paint()
    # horizon glow picked up from the aurora
    rg = cairo.RadialGradient(W * 0.58, H * 0.86, 0, W * 0.58, H * 0.86, W * 0.62)
    rg.add_color_stop_rgba(0, *rgbf("#1f5160"), 0.55)
    rg.add_color_stop_rgba(0.5, *rgbf("#1a2f55"), 0.25)
    rg.add_color_stop_rgba(1, *rgbf("#0c1526"), 0.0)
    c.set_source(rg)
    c.paint()

    # stars
    rnd = random.Random(4242)
    tints = [(1, 1, 1), (0.82, 0.88, 1.0), (1.0, 0.93, 0.84), (0.86, 1.0, 0.97)]
    for _ in range(3200):
        x = rnd.uniform(0, W)
        y = H * 0.82 * rnd.random() ** 1.35
        fade = max(0.0, 1 - y / (H * 0.80)) ** 0.6
        size = 0.7 + 2.0 * rnd.random() ** 7
        b = (0.18 + 0.82 * rnd.random() ** 3) * fade
        tint = rnd.choice(tints)
        if size > 1.9 and b > 0.45:
            halo = cairo.RadialGradient(x, y, 0, x, y, size * 6)
            halo.add_color_stop_rgba(0, *tint, 0.22 * b)
            halo.add_color_stop_rgba(1, *tint, 0)
            c.set_source(halo)
            c.arc(x, y, size * 6, 0, 6.2832)
            c.fill()
        c.set_source_rgba(*tint, b)
        c.arc(x, y, size, 0, 6.2832)
        c.fill()
    return surface_rgb(sky)


def night_mountains():
    """RGBA: mountain ranges plus the aurora rim light on the far ridge."""
    m = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    mc = cairo.Context(m)
    mountain_path(mc, 5, 0.835, 0.17, 0.55)
    fill_vertical(mc, "#16263a", "#0b1424", 0.66, 0.90)
    rim = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    rc = cairo.Context(rim)
    mountain_path(rc, 5, 0.835, 0.17, 0.55)
    rc.set_source_rgba(*rgbf("#5fe0c8"), 0.55)
    rc.set_line_width(3)
    rc.stroke()
    mountain_path(mc, 17, 0.905, 0.15, 0.50, 0.3)
    fill_vertical(mc, "#0b1220", "#070b14", 0.76, 1.0)
    mountain_path(mc, 29, 0.975, 0.10, 0.47, 0.7)
    fill_vertical(mc, "#060910", "#04060b", 0.86, 1.0)
    out = surface_rgba(rim).filter(ImageFilter.GaussianBlur(3))
    out.alpha_composite(surface_rgba(m))
    return out


def render_night():
    img = night_sky()

    # aurora (additive light)
    au = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
    ac = cairo.Context(au)
    ac.set_operator(cairo.OPERATOR_ADD)
    draw_ribbons(ac, RIBBONS, ("#7ff2d2", "#33d6b0", "#4d6cf0", "#9a6cff"), edge_px=64)
    layer = surface_rgb(au)
    detail = layer.filter(ImageFilter.GaussianBlur(2.2))
    soft = layer.filter(ImageFilter.GaussianBlur(14))
    glow = layer.filter(ImageFilter.GaussianBlur(90))
    img = ImageChops.add(img, scaled(detail, 0.56))
    img = ImageChops.add(img, scaled(soft, 0.40))
    img = ImageChops.add(img, scaled(glow, 0.75))
    # light scattered below the lower edge, so it doesn't read as a hill
    under = ImageChops.offset(glow, 0, 140)
    img = ImageChops.add(img, scaled(under, 0.35))

    # mountains, far -> near
    img = img.convert("RGBA")
    img.alpha_composite(night_mountains())
    img = img.convert("RGB")
    img = vignette(img, 0.30)
    return add_grain(img, strength=6)


# ------------------------------------------------------------------ dawn ---
def dawn_sky():
    sky = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
    c = cairo.Context(sky)
    g = cairo.LinearGradient(0, 0, 0, H)
    for off, col in ((0.0, "#93a6ec"), (0.30, "#b7c3f5"), (0.55, "#dcd6f3"),
                     (0.72, "#f5dbe4"), (0.84, "#ffe4d6"), (1.0, "#f7e0da")):
        g.add_color_stop_rgb(off, *rgbf(col))
    c.set_source(g)
    c.paint()
    sun = cairo.RadialGradient(W * 0.70, H * 0.84, 0, W * 0.70, H * 0.84, W * 0.55)
    sun.add_color_stop_rgba(0, *rgbf("#fff4e6"), 0.85)
    sun.add_color_stop_rgba(0.35, *rgbf("#ffe7d8"), 0.35)
    sun.add_color_stop_rgba(1, *rgbf("#ffe7d8"), 0.0)
    c.set_source(sun)
    c.paint()
    return surface_rgb(sky)


def dawn_mountains():
    m = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    mc = cairo.Context(m)
    mountain_path(mc, 5, 0.835, 0.17, 0.55)
    fill_vertical(mc, "#c3c3e6", "#d9d0e8", 0.66, 0.90)
    mist = cairo.LinearGradient(0, 0.80 * H, 0, 0.93 * H)
    mist.add_color_stop_rgba(0, 1, 0.96, 0.95, 0.0)
    mist.add_color_stop_rgba(1, 1, 0.96, 0.95, 0.55)
    mc.rectangle(0, 0.80 * H, W, 0.2 * H)
    mc.set_source(mist)
    mc.fill()
    mountain_path(mc, 17, 0.905, 0.15, 0.50, 0.3)
    fill_vertical(mc, "#98a0d0", "#aeb1d8", 0.76, 1.0)
    mountain_path(mc, 29, 0.975, 0.10, 0.47, 0.7)
    fill_vertical(mc, "#6d77ad", "#7a82b6", 0.86, 1.0)
    return surface_rgba(m)


def render_dawn():
    img = dawn_sky().convert("RGBA")

    # pastel aurora veils (alpha-over, not additive, on a light sky)
    au = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ac = cairo.Context(au)
    draw_ribbons(ac, RIBBONS, ("#7fe6d2", "#55d0bd", "#7f8ff0", "#b39af2"),
                 alpha_scale=1.1, edge_px=64)
    layer = surface_rgba(au)
    pre = layer.convert("RGBa")        # premultiplied blur: no dark fringes
    img.alpha_composite(pre.filter(ImageFilter.GaussianBlur(6)).convert("RGBA"))
    glow = pre.filter(ImageFilter.GaussianBlur(70)).convert("RGBA")
    glow.putalpha(glow.getchannel("A").point(lambda v: v * 6 // 10))
    img.alpha_composite(glow)

    img.alpha_composite(dawn_mountains())
    img = img.convert("RGB")
    img = vignette(img, 0.07)
    return add_grain(img, strength=4)


# --------------------------------------------------------------- outputs ---
SIZES = [(3840, 2400), (3840, 2160), (3440, 1440), (1280, 1024), (1080, 1920)]


def crop_to(img, w, h):
    """Centre-ish crop to the target aspect (keep the horizon), then resize."""
    sw, sh = img.size
    target = w / h
    if sw / sh > target:           # too wide -> crop sides
        cw = round(sh * target)
        x0 = round((sw - cw) * 0.55)
        box = (x0, 0, x0 + cw, sh)
    else:                          # too tall -> crop top/bottom, favour bottom
        ch = round(sw / target)
        y0 = round((sh - ch) * 0.62)
        box = (0, y0, sw, y0 + ch)
    out = img.crop(box)
    return out if out.size == (w, h) else out.resize((w, h), Image.LANCZOS)


def export(img, folder):
    os.makedirs(folder, exist_ok=True)
    for w, h in SIZES:
        crop_to(img, w, h).save(os.path.join(folder, f"{w}x{h}.jpg"),
                                quality=94, subsampling=0, optimize=True)


def _package(out_root, pkg_id, name, desc, night, dawn):
    import json
    from tokens import AUTHOR, EMAIL, LICENSE
    base = os.path.join(out_root, "wallpapers", pkg_id)
    export(dawn, os.path.join(base, "contents", "images"))
    export(night, os.path.join(base, "contents", "images_dark"))
    shot = Image.new("RGB", (800, 500))
    shot.paste(crop_to(dawn, 400, 500), (0, 0))
    shot.paste(crop_to(night, 400, 500), (400, 0))
    shot.save(os.path.join(base, "contents", "screenshot.png"))
    meta = {"KPackageStructure": "Wallpaper/Images",
            "KPlugin": {"Authors": [{"Name": AUTHOR, "Email": EMAIL}],
                        "Id": pkg_id, "Name": name,
                        "Description": desc,
                        "License": LICENSE}}
    with open(os.path.join(base, "metadata.json"), "w") as f:
        json.dump(meta, f, indent=4)
    return base


def package(out_root, night, dawn):
    """share/wallpapers/Borealis: images/ = light (dawn), images_dark/ = night."""
    return _package(out_root, "Borealis", "Borealis",
                    "Aurora over the mountains — dawn and night", night, dawn)


def lock_package(out_root, night, dawn):
    """A dimmer dawn for the lock screen: Plasma draws its clock in white there,
    whatever the color scheme, and the bright dawn sky leaves it hard to read."""
    dim = ImageEnhance.Color(ImageEnhance.Brightness(dawn).enhance(0.62)).enhance(0.92)
    return _package(out_root, "Borealis-Lock", "Borealis (lock screen)",
                    "Aurora over the mountains, dimmed for white lock-screen text",
                    night, dim)


def main(out_dir):
    night = render_night()
    dawn = render_dawn()
    night.save(os.path.join(out_dir, "night-master.png"))
    dawn.save(os.path.join(out_dir, "dawn-master.png"))
    return night, dawn


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    os.makedirs(out, exist_ok=True)
    main(out)
