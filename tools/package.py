#!/usr/bin/env python3
"""Build ready-to-upload archives for store.kde.org into dist/.

One archive per KDE Store category (Global Themes, Plasma Style, Aurorae,
cursors, icons, wallpapers, ...), plus a complete release tarball and a
checksum list. Run ./build.py first.
"""
import hashlib
import os
import shutil
import sys
import tarfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHARE = os.path.join(HERE, "build", "share")
DIST = os.path.join(HERE, "dist")
sys.path.insert(0, os.path.join(HERE, "src"))
from tokens import IDS, SLUG, TITLES, VERSION  # noqa: E402

D, L = IDS["lnf_dark"], IDS["lnf_light"]

# archive name -> (store category, [paths relative to build/share])
ARCHIVES = {
    f"{D}-global-theme": ("Global Themes (Plasma 6)", [f"plasma/look-and-feel/{D}"]),
    f"{L}-global-theme": ("Global Themes (Plasma 6)", [f"plasma/look-and-feel/{L}"]),
    f"{SLUG}-plasma-style": ("Plasma Themes", [f"plasma/desktoptheme/{IDS['style']}"]),
    f"{SLUG}-color-schemes": ("Plasma Color Schemes", [f"color-schemes/{IDS['colors_dark']}.colors",
                                                       f"color-schemes/{IDS['colors_light']}.colors"]),
    f"{D}-aurorae": ("Plasma Window Decorations", [f"aurorae/themes/{IDS['aurorae_dark']}"]),
    f"{L}-aurorae": ("Plasma Window Decorations", [f"aurorae/themes/{IDS['aurorae_light']}"]),
    f"{SLUG}-Snow-cursors": ("Cursors", [f"icons/{IDS['cursors_dark']}"]),
    f"{SLUG}-Ink-cursors": ("Cursors", [f"icons/{IDS['cursors_light']}"]),
    f"{SLUG}-icons": ("Full Icon Themes", [f"icons/{IDS['icons_dark']}", f"icons/{IDS['icons_light']}"]),
    f"{SLUG}-wallpaper": ("Wallpapers KDE Plasma", [f"wallpapers/{IDS['wallpaper']}",
                                                     f"wallpapers/{IDS['wallpaper_lock']}"]),
    f"{SLUG}-Aurora-animated-wallpaper": ("Plasma 6 Wallpaper Plugins",
                                          [f"plasma/wallpapers/{IDS['live']}"]),
    f"{SLUG}-sound-theme": ("System Sounds", [f"sounds/{IDS['sounds']}"]),
    f"{SLUG}-konsole": ("Konsole Color Schemes", [f"konsole/{IDS['colors_dark']}.colorscheme",
                                                   f"konsole/{IDS['colors_light']}.colorscheme",
                                                   f"konsole/{TITLES['dark']}.profile",
                                                   f"konsole/{TITLES['light']}.profile"]),
    f"{SLUG}-kate": ("Kate/KWrite Color Schemes",
                     [f"org.kde.syntax-highlighting/themes/{IDS['kate_dark']}.theme",
                      f"org.kde.syntax-highlighting/themes/{IDS['kate_light']}.theme"]),
    f"{SLUG}-plymouth": ("Plymouth Themes", [f"plymouth/themes/{IDS['plymouth']}"]),
    f"{SLUG}-gtk4": ("GTK4/libadwaita Themes", [f"gtk/{SLUG.lower()}"]),
    f"{SLUG}-terminal": ("Terminal / CLI", [f"terminal/{SLUG.lower()}"]),
    f"{SLUG}-firefox": ("Firefox", [f"firefox/{SLUG.lower()}"]),
    f"{SLUG}-grub": ("GRUB Themes", [f"grub/themes/{IDS['plymouth']}"]),
    f"{SLUG}-tweaks-app": ("Plasma Add-ons", [f"{SLUG.lower()}-tweaks"]),
}


def add(tar, rel):
    """Store the component under its own directory name (what KNS expects)."""
    src = os.path.join(SHARE, rel)
    tar.add(src, arcname=os.path.basename(rel))


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if not os.path.isdir(SHARE):
        sys.exit("build/share missing: run ./build.py first")
    shutil.rmtree(DIST, ignore_errors=True)
    os.makedirs(DIST)
    lines = []
    for name, (category, paths) in ARCHIVES.items():
        present = [p for p in paths if os.path.exists(os.path.join(SHARE, p))]
        if not present:
            continue
        out = os.path.join(DIST, f"{name}-{VERSION}.tar.gz")
        with tarfile.open(out, "w:gz") as tar:
            for rel in present:
                add(tar, rel)
        lines.append(f"{sha256(out)}  {os.path.basename(out)}  [{category}]")
    # complete release: sources, scripts, docs and the prebuilt tree
    full = os.path.join(DIST, f"{SLUG}-{VERSION}-complete.tar.gz")
    with tarfile.open(full, "w:gz") as tar:
        for item in ("README.md", "STORE.md", "LICENSE", "build.py", "install.sh", "uninstall.sh",
                     "install-system.sh", "src", "tools", "docs"):
            p = os.path.join(HERE, item)
            if os.path.exists(p):
                tar.add(p, arcname=f"{SLUG}-{VERSION}/{item}",
                        filter=lambda t: None if "__pycache__" in t.name else t)
        tar.add(SHARE, arcname=f"{SLUG}-{VERSION}/build/share")
    lines.append(f"{sha256(full)}  {os.path.basename(full)}  [complete release]")
    with open(os.path.join(DIST, "SHA256SUMS"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
