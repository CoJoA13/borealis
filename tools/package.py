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
from tokens import VERSION  # noqa: E402

# archive name -> (store category, [paths relative to build/share])
ARCHIVES = {
    "Borealis-Dark-global-theme": ("Global Themes (Plasma 6)", ["plasma/look-and-feel/Borealis-Dark"]),
    "Borealis-Light-global-theme": ("Global Themes (Plasma 6)", ["plasma/look-and-feel/Borealis-Light"]),
    "Borealis-plasma-style": ("Plasma Themes", ["plasma/desktoptheme/Borealis"]),
    "Borealis-color-schemes": ("Plasma Color Schemes", ["color-schemes/BorealisDark.colors",
                                                        "color-schemes/BorealisLight.colors"]),
    "Borealis-Dark-aurorae": ("Plasma Window Decorations", ["aurorae/themes/Borealis-Dark"]),
    "Borealis-Light-aurorae": ("Plasma Window Decorations", ["aurorae/themes/Borealis-Light"]),
    "Borealis-Snow-cursors": ("Cursors", ["icons/Borealis-Snow-Cursors"]),
    "Borealis-Ink-cursors": ("Cursors", ["icons/Borealis-Ink-Cursors"]),
    "Borealis-icons": ("Full Icon Themes", ["icons/Borealis-Dark", "icons/Borealis-Light"]),
    "Borealis-wallpaper": ("Wallpapers KDE Plasma", ["wallpapers/Borealis"]),
    "Borealis-Aurora-animated-wallpaper": ("Plasma 6 Wallpaper Plugins",
                                           ["plasma/wallpapers/org.borealis.aurora"]),
    "Borealis-sound-theme": ("System Sounds", ["sounds/Borealis"]),
    "Borealis-konsole": ("Konsole Color Schemes", ["konsole/BorealisDark.colorscheme",
                                                   "konsole/BorealisLight.colorscheme",
                                                   "konsole/Borealis Dark.profile",
                                                   "konsole/Borealis Light.profile"]),
    "Borealis-kate": ("Kate/KWrite Color Schemes", ["org.kde.syntax-highlighting/themes/borealisdark.theme",
                                                    "org.kde.syntax-highlighting/themes/borealislight.theme"]),
    "Borealis-plymouth": ("Plymouth Themes", ["plymouth/themes/borealis"]),
    "Borealis-gtk4": ("GTK4/libadwaita Themes", ["gtk/borealis"]),
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
    full = os.path.join(DIST, f"Borealis-{VERSION}-complete.tar.gz")
    with tarfile.open(full, "w:gz") as tar:
        for item in ("README.md", "STORE.md", "LICENSE", "build.py", "install.sh", "uninstall.sh",
                     "install-system.sh", "src", "tools", "docs"):
            p = os.path.join(HERE, item)
            if os.path.exists(p):
                tar.add(p, arcname=f"Borealis-{VERSION}/{item}",
                        filter=lambda t: None if "__pycache__" in t.name else t)
        tar.add(SHARE, arcname=f"Borealis-{VERSION}/build/share")
    lines.append(f"{sha256(full)}  {os.path.basename(full)}  [complete release]")
    with open(os.path.join(DIST, "SHA256SUMS"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
