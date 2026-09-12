"""Borealis icon overlays: aurora-gradient folders, squircle app icons for
generic apps (>= 28px) and the Borealis launcher logo.

Borealis-Dark inherits Tela-dark and Borealis-Light inherits Tela-light (both
fall back to Breeze). Only folders (>= 33px, so Tela's crisp small folders
still win at panel/sidebar sizes) and the start-here logo are overridden.
"""
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(__file__))
HERE = os.path.dirname(os.path.abspath(__file__))

THEMES = (
    ("Borealis-Dark", "Borealis Dark", "Tela-dark,breeze-dark,hicolor"),
    ("Borealis-Light", "Borealis Light", "Tela-light,breeze,hicolor"),
)
GRADIENT = (("0", "#5fe0c8"), ("0.55", "#8b9cff"), ("1", "#b18cff"))
# Only folder-like names are overridden; generic names such as "network"
# would otherwise catch icon-name fallbacks (e.g. tray status icons).
KEEP_PREFIXES = ("folder", "user-home", "user-desktop", "desktop", "inode-directory")
LOGO_NAMES = ("start-here-kde", "start-here-kde-plasma", "start-here-kde-symbolic",
              "start-here", "start-here-symbolic", "borealis")


def find_tela():
    dirs = [os.path.expanduser("~/.local/share/icons")]
    dirs += [os.path.join(d, "icons") for d in
             os.environ.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share").split(":")]
    for d in dirs:
        p = os.path.join(d, "Tela", "scalable", "places")
        if os.path.isdir(p):
            return p
    return None


def recolor(svg):
    """Swap the ColorScheme-Highlight body fill for an aurora gradient."""
    stops = "".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in GRADIENT)
    grad = f'<linearGradient id="borealisFolder" x1="0" y1="0" x2="1" y2="1">{stops}</linearGradient>'

    def fix(m):
        tag = m.group(0)
        tag = re.sub(r'\sclass="ColorScheme-Highlight"', "", tag)
        tag = tag.replace('fill="currentColor"', 'fill="url(#borealisFolder)"')
        tag = re.sub(r"fill:currentColor", "fill:url(#borealisFolder)", tag)
        return tag

    out = re.sub(r"<[^<>]*class=\"ColorScheme-Highlight\"[^<>]*>", fix, svg)
    if "<defs>" in out:
        out = out.replace("<defs>", "<defs>" + grad, 1)
    else:
        out = re.sub(r"(<svg[^>]*>)", r"\1<defs>" + grad + "</defs>", out, count=1)
    return out


def build_app_icons(base):
    """Borealis squircle icons for generic apps (scalable/apps)."""
    import app_icons
    apps = os.path.join(base, "scalable", "apps")
    os.makedirs(apps)
    for glyph, names in app_icons.NAMES.items():
        first = names[0] + ".svg"
        with open(os.path.join(apps, first), "w") as f:
            f.write(app_icons.icon_svg(glyph))
        for alias in names[1:]:
            os.symlink(first, os.path.join(apps, alias + ".svg"))


def build_theme(root, dirname, title, inherits, tela):
    base = os.path.join(root, dirname)
    if os.path.exists(base):
        shutil.rmtree(base)
    places = os.path.join(base, "scalable", "places")
    brand = os.path.join(base, "scalable", "branding")
    os.makedirs(places)
    os.makedirs(brand)
    build_app_icons(base)
    logo = os.path.join(HERE, "assets", "logo.svg")
    for n in LOGO_NAMES:
        shutil.copy(logo, os.path.join(brand, n + ".svg"))
    count = 0
    if tela:
        made = set()
        for fn in sorted(os.listdir(tela)):
            p = os.path.join(tela, fn)
            if (fn.startswith("default-folder") or fn in ("default-user-home.svg",
                                                            "default-user-desktop.svg")) \
                    and fn.endswith(".svg") and not os.path.islink(p):
                svg = open(p, encoding="utf-8").read()
                if "ColorScheme-Highlight" not in svg:
                    continue
                with open(os.path.join(places, fn), "w", encoding="utf-8") as f:
                    f.write(recolor(svg))
                made.add(fn)
        for fn in sorted(os.listdir(tela)):
            p = os.path.join(tela, fn)
            if os.path.islink(p):
                target = os.path.basename(os.path.realpath(p))
                if target in made and fn not in made and fn.startswith(KEEP_PREFIXES):
                    os.symlink(target, os.path.join(places, fn))
        count = len(os.listdir(places))
    with open(os.path.join(base, "index.theme"), "w") as f:
        f.write("[Icon Theme]\n"
                f"Name={title}\n"
                "Comment=Aurora-gradient folders and the Borealis logo on top of Tela\n"
                f"Inherits={inherits}\n"
                "Example=folder\n"
                "FollowsColorScheme=true\n"
                "DisplayDepth=32\n"
                "Directories=scalable/places,scalable/branding,scalable/apps\n\n"
                "[scalable/places]\n"
                "Context=Places\nSize=64\nMinSize=33\nMaxSize=512\nType=Scalable\n\n"
                "[scalable/branding]\n"
                "Context=Places\nSize=64\nMinSize=8\nMaxSize=512\nType=Scalable\n\n"
                "[scalable/apps]\n"
                "Context=Applications\nSize=128\nMinSize=28\nMaxSize=512\nType=Scalable\n")
    return base, count


def build(out_root):
    root = os.path.join(out_root, "icons")
    os.makedirs(root, exist_ok=True)
    tela = find_tela()
    if not tela:
        print("  (Tela not found: icon overlays will only carry the logo)")
    return [build_theme(root, *t, tela) for t in THEMES]


if __name__ == "__main__":
    print(build(sys.argv[1]))
