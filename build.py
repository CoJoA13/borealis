#!/usr/bin/env python3
"""Build every Borealis component into build/share/ (mirrors ~/.local/share/).

    ./build.py            build everything
    ./build.py colors lnf build only some steps
"""
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "src"))

OUT = os.path.join(HERE, "build", "share")
CACHE = os.path.join(HERE, "build", "cache")


def wallpapers():
    """Render (or reuse) the wallpaper masters: (night, dawn) PIL images."""
    from PIL import Image
    import gen_wallpaper
    n, d = (os.path.join(CACHE, f) for f in ("night-master.png", "dawn-master.png"))
    src = os.path.join(HERE, "src", "gen_wallpaper.py")
    fresh = all(os.path.exists(p) and os.path.getmtime(p) > os.path.getmtime(src) for p in (n, d))
    if not fresh:
        os.makedirs(CACHE, exist_ok=True)
        gen_wallpaper.main(CACHE)
    return Image.open(n).convert("RGB"), Image.open(d).convert("RGB")


def step_colors():
    import gen_colors
    gen_colors.build(OUT)


def step_apps():
    import gen_apps
    gen_apps.build(OUT)


def step_cursors():
    import gen_cursors
    gen_cursors.build(OUT)


def step_wallpaper():
    import gen_wallpaper
    night, dawn = wallpapers()
    gen_wallpaper.package(OUT, night, dawn)


def step_plasmastyle():
    import gen_plasmastyle
    gen_plasmastyle.build(OUT)


def step_aurorae():
    import gen_aurorae
    gen_aurorae.build(OUT)


def step_icons():
    import gen_icons
    gen_icons.build(OUT)


def step_sounds():
    import gen_sounds
    out = os.path.join(OUT, "sounds", "Borealis", "index.theme")
    src = os.path.join(HERE, "src", "gen_sounds.py")
    cached = os.path.join(CACHE, "sounds")
    if not (os.path.exists(os.path.join(cached, "sounds", "Borealis", "index.theme"))
            and os.path.getmtime(os.path.join(cached, "sounds", "Borealis", "index.theme"))
            > os.path.getmtime(src)):
        shutil.rmtree(cached, ignore_errors=True)
        gen_sounds.build(cached)
    dst = os.path.dirname(out)
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(os.path.join(cached, "sounds", "Borealis"), dst, symlinks=True)


def step_live():
    import gen_live
    gen_live.build(OUT, CACHE)


def step_plymouth():
    import gen_plymouth
    gen_plymouth.build(OUT)


def step_gtk():
    import gen_gtk
    gen_gtk.build(OUT)


def step_lnf():
    import gen_lnf
    night, dawn = wallpapers()
    shots = os.path.join(HERE, "build", "shots")
    gen_lnf.build(OUT, night, dawn, previews=gen_lnf.previews_from_shots(shots))


STEPS = {
    "colors": step_colors,
    "apps": step_apps,
    "cursors": step_cursors,
    "wallpaper": step_wallpaper,
    "plasmastyle": step_plasmastyle,
    "aurorae": step_aurorae,
    "icons": step_icons,
    "sounds": step_sounds,
    "live": step_live,
    "plymouth": step_plymouth,
    "gtk": step_gtk,
    "lnf": step_lnf,
}


def main(argv):
    wanted = argv or list(STEPS)
    unknown = [w for w in wanted if w not in STEPS]
    if unknown:
        sys.exit(f"unknown step(s): {', '.join(unknown)}; choose from {', '.join(STEPS)}")
    if not argv and os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT, exist_ok=True)
    for name in wanted:
        t = time.time()
        STEPS[name]()
        print(f"  {name:<12} {time.time() - t:5.1f}s")
    print(f"built into {OUT}")


if __name__ == "__main__":
    main(sys.argv[1:])
