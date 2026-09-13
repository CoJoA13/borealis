#!/usr/bin/env python3
"""Build every Borealis component into build/share/ (mirrors ~/.local/share/).

    ./build.py                       build everything
    ./build.py colors lnf            build only some steps
    ./build.py --accent "#ff8a5b" --name "Borealis Ember"
                                     a remix: the whole theme rotated onto a
                                     new accent, installable next to the original
    ./build.py --out ~/ember/share   write somewhere else
"""
import argparse
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
    from tokens import HUE_SHIFT, SATURATION
    tag = "" if (HUE_SHIFT, SATURATION) == (0.0, 1.0) else f"-{HUE_SHIFT:.4f}x{SATURATION:g}"
    n, d = (os.path.join(CACHE, f"{v}-master{tag}.png") for v in ("night", "dawn"))
    src = os.path.join(HERE, "src", "gen_wallpaper.py")
    fresh = all(os.path.exists(p) and os.path.getmtime(p) > os.path.getmtime(src) for p in (n, d))
    if not fresh:
        os.makedirs(CACHE, exist_ok=True)
        gen_wallpaper.main(CACHE, tag)
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
    gen_wallpaper.lock_package(OUT, night, dawn)


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
    from tokens import IDS
    # the chimes don't depend on the palette, so one render serves every remix
    src = os.path.join(HERE, "src", "gen_sounds.py")
    cached = os.path.join(CACHE, "sounds")
    stamp = os.path.join(cached, "sounds", IDS["sounds"], "index.theme")
    if not (os.path.exists(stamp) and os.path.getmtime(stamp) > os.path.getmtime(src)):
        shutil.rmtree(cached, ignore_errors=True)
        gen_sounds.build(cached)
    dst = os.path.join(OUT, "sounds", IDS["sounds"])
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(os.path.join(cached, "sounds", IDS["sounds"]), dst, symlinks=True)


def step_live():
    import gen_live
    gen_live.build(OUT, CACHE)


def step_plymouth():
    import gen_plymouth
    gen_plymouth.build(OUT)


def step_terminal():
    import gen_terminal
    gen_terminal.build(OUT)


def step_plasmoids():
    import gen_plasmoids
    gen_plasmoids.build(OUT)


def step_grub():
    import gen_grub
    night, _ = wallpapers()
    gen_grub.build(OUT, night)


def step_firefox():
    import gen_firefox
    gen_firefox.build(OUT)


def step_dock():
    import gen_dock
    gen_dock.build(OUT)


def step_tweaks():
    import gen_tweaks
    gen_tweaks.build(OUT)


def step_gtk():
    import gen_gtk
    gen_gtk.build(OUT)


def step_lnf():
    import gen_lnf
    night, dawn = wallpapers()
    shots = os.path.join(HERE, "build", "shots")
    gen_lnf.build(OUT, night, dawn, previews=gen_lnf.previews_from_shots(shots))


def step_bar():
    import gen_bar
    gen_bar.build(OUT)


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
    "terminal": step_terminal,
    "plasmoids": step_plasmoids,
    "grub": step_grub,
    "firefox": step_firefox,
    "dock": step_dock,
    "bar": step_bar,
    "tweaks": step_tweaks,
    "gtk": step_gtk,
    "lnf": step_lnf,
}


def main(argv):
    global OUT
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("steps", nargs="*", help=f"one or more of: {', '.join(STEPS)}")
    ap.add_argument("--accent", help="hex colour the whole theme is rotated onto, e.g. '#ff8a5b'")
    ap.add_argument("--name", help='theme name for a remix, e.g. "Borealis Ember"')
    ap.add_argument("--saturation", type=float, help="multiply every colour's saturation")
    ap.add_argument("--out", help="output directory (default build/share)")
    a = ap.parse_args(argv)
    if a.accent:
        os.environ["BOREALIS_ACCENT"] = a.accent
    if a.name:
        os.environ["BOREALIS_NAME"] = a.name
    if a.saturation:
        os.environ["BOREALIS_SATURATION"] = str(a.saturation)
    if a.out:
        OUT = os.path.abspath(os.path.expanduser(a.out))
    if "tokens" in sys.modules:
        sys.exit("build.py: set the palette before importing the generators")
    wanted = a.steps or list(STEPS)
    unknown = [w for w in wanted if w not in STEPS]
    if unknown:
        sys.exit(f"unknown step(s): {', '.join(unknown)}; choose from {', '.join(STEPS)}")
    argv = a.steps
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
