"""Borealis Aurora: an animated Plasma wallpaper plugin (desktop + lock screen).

Layers (bottom to top): sky + stars (with a cheap twinkle shader), the aurora
(fragment shader, rendered at reduced resolution, additive at night), then the
mountains. Night or dawn artwork follows the colour scheme unless pinned.
"""
import json
import os
import shutil
import subprocess
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
import gen_wallpaper as GW  # noqa: E402
from tokens import AUTHOR, EMAIL, LICENSE, VERSION  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ID = "org.borealis.aurora"
LAYER_SIZE = (2560, 1600)
QSB = shutil.which("qsb") or "/usr/lib64/qt6/bin/qsb"


def layers(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    for name, sky, mountains in (("night", GW.night_sky, GW.night_mountains),
                                 ("dawn", GW.dawn_sky, GW.dawn_mountains)):
        s = sky()
        s = GW.vignette(s, 0.30 if name == "night" else 0.07)
        s = GW.add_grain(s, strength=5)
        s.resize(LAYER_SIZE, Image.LANCZOS).save(os.path.join(out_dir, f"sky-{name}.jpg"),
                                                 quality=93, subsampling=0)
        m = mountains()
        m.resize(LAYER_SIZE, Image.LANCZOS).save(os.path.join(out_dir, f"mountains-{name}.png"),
                                                 optimize=True)


def shaders(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    for name in ("aurora", "twinkle"):
        subprocess.run([QSB, "--glsl", "100 es,120,150", "--hlsl", "50", "--msl", "12",
                        "-o", os.path.join(out_dir, f"{name}.frag.qsb"),
                        os.path.join(HERE, "live", f"{name}.frag")], check=True)


def build(out_root, cache_dir):
    base = os.path.join(out_root, "plasma", "wallpapers", PLUGIN_ID)
    if os.path.exists(base):
        shutil.rmtree(base)
    contents = os.path.join(base, "contents")
    img_cache = os.path.join(cache_dir, "live-layers")
    src_mtime = max(os.path.getmtime(os.path.join(HERE, f)) for f in ("gen_wallpaper.py", "gen_live.py"))
    if not os.path.exists(os.path.join(img_cache, "mountains-dawn.png")) or \
            os.path.getmtime(os.path.join(img_cache, "mountains-dawn.png")) < src_mtime:
        layers(img_cache)
    shutil.copytree(img_cache, os.path.join(contents, "images"))
    shaders(os.path.join(contents, "shaders"))
    for sub in ("ui", "config"):
        shutil.copytree(os.path.join(HERE, "live", sub), os.path.join(contents, sub))
    meta = {
        "KPackageStructure": "Plasma/Wallpaper",
        "KPlugin": {
            "Authors": [{"Name": AUTHOR, "Email": EMAIL}],
            "Category": "",
            "Description": "Animated aurora over the Borealis mountains",
            "Icon": "preferences-desktop-wallpaper",
            "Id": PLUGIN_ID,
            "License": LICENSE,
            "Name": "Borealis Aurora (animated)",
            "Version": VERSION,
        },
        "X-Plasma-API-Minimum-Version": "6.0",
    }
    with open(os.path.join(base, "metadata.json"), "w") as f:
        json.dump(meta, f, indent=4)
    return base
