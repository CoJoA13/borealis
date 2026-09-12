"""Global Theme (Look-and-Feel) packages: Borealis-Dark and Borealis-Light."""
import json
import os
import shutil
import sys

from PIL import Image, ImageEnhance, ImageFilter

sys.path.insert(0, os.path.dirname(__file__))
from tokens import (AUTHOR, DARK, EMAIL, IDS, LICENSE, LIGHT, NAME, TITLES,  # noqa: E402
                    VERSION, remix_text)

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")

PACKAGES = {
    "dark": {
        "id": IDS["lnf_dark"],
        "name": TITLES["dark"],
        "desc": "Aurora night: ink-navy surfaces, periwinkle and aurora-teal accents",
        "colors": IDS["colors_dark"],
        "icons": IDS["icons_dark"],
        "cursors": IDS["cursors_dark"],
        "aurorae": IDS["aurorae_dark"],
        "palette": DARK,
    },
    "light": {
        "id": IDS["lnf_light"],
        "name": TITLES["light"],
        "desc": "Polar dawn: frosted snow surfaces, periwinkle and aurora-teal accents",
        "colors": IDS["colors_light"],
        "icons": IDS["icons_light"],
        "cursors": IDS["cursors_light"],
        "aurorae": IDS["aurorae_light"],
        "palette": LIGHT,
    },
}


def metadata(pkg):
    return {
        "KPackageStructure": "Plasma/LookAndFeel",
        "KPlugin": {
            "Authors": [{"Name": AUTHOR, "Email": EMAIL}],
            "Category": "",
            "Description": pkg["desc"],
            "Id": pkg["id"],
            "License": LICENSE,
            "Name": pkg["name"],
            "Version": VERSION,
            "Website": "",
        },
        "Keywords": "Desktop;Workspace;Appearance;Look and Feel;",
        "X-Plasma-APIVersion": "2",
    }


UI_FONT, MONO_FONT = "Inter", "JetBrains Mono"


def qfont(family, size, weight=400, mono=False):
    """Qt 6 QFont::toString() form. Monospace fonts carry the Monospace style
    hint and fixed pitch, so a missing family falls back to another monospace
    font instead of the default sans."""
    hint, fixed = (7, 1) if mono else (5, 0)
    return f"{family},{size},-1,{hint},{weight},0,0,0,{fixed},0,0,0,0,0,0,1"


FONT_KEYS = {
    "font": qfont(UI_FONT, 10),
    "fixed": qfont(MONO_FONT, 10, mono=True),
    "smallestReadableFont": qfont(UI_FONT, 8),
    "toolBarFont": qfont(UI_FONT, 10),
    "menuFont": qfont(UI_FONT, 10),
    "activeFont": qfont(UI_FONT, 10, 600),
}


def font_lines():
    # Plasma 6.7.5 only applies fonts if it finds them in *both* groups
    # (detection looks at [WM], values are read from [General]).
    return [f"{k}={v}" for k, v in FONT_KEYS.items()]


def defaults(pkg):
    return "\n".join([
        "[kdeglobals][KDE]",
        "widgetStyle=Breeze",
        "",
        "[kdeglobals][General]",
        f"ColorScheme={pkg['colors']}",
        *font_lines(),
        "",
        "[kdeglobals][WM]",
        *font_lines(),
        "",
        "[kdeglobals][Icons]",
        f"Theme={pkg['icons']}",
        "",
        "[plasmarc][Theme]",
        f"name={IDS['style']}",
        "",
        "[Wallpaper]",
        f"Image={IDS['wallpaper']}",
        "",
        "[kcminputrc][Mouse]",
        f"cursorTheme={pkg['cursors']}",
        "",
        "[kwinrc][org.kde.kdecoration2]",
        "library=org.kde.kwin.aurorae.v2",
        f"theme=__aurorae__svg__{pkg['aurorae']}",
        "BorderSize=Normal",
        "",
        "[kwinrc][WindowSwitcher]",
        f"LayoutName={pkg['id']}",
        "",
        "[ksplashrc][KSplash]",
        f"Theme={pkg['id']}",
        "",
    ])


LAYOUT_JS = """// Borealis desktop layout: floating frosted top bar + centred floating dock.
var desktopsArray = desktopsForActivity(currentActivity());
for (var j = 0; j < desktopsArray.length; j++) {
    desktopsArray[j].wallpaperPlugin = "org.kde.image";
}

var bar = new Panel;
bar.location = "top";
bar.height = 2 * Math.ceil(gridUnit * 1.6 / 2);
bar.floating = true;
bar.lengthMode = "fill";
bar.alignment = "center";
bar.hiding = "none";
bar.opacity = "adaptive";

var kickoff = bar.addWidget("org.kde.plasma.kickoff");
kickoff.currentConfigGroup = ["General"];
kickoff.writeConfig("icon", "start-here-kde");
kickoff.globalShortcut = "Alt+F1";
bar.addWidget("org.kde.plasma.appmenu");
bar.addWidget("org.kde.plasma.panelspacer");
var clock = bar.addWidget("org.kde.plasma.digitalclock");
clock.currentConfigGroup = ["Appearance"];
clock.writeConfig("showDate", true);
clock.writeConfig("dateDisplayFormat", "BesideTime");
clock.writeConfig("dateFormat", "custom");
clock.writeConfig("customDateFormat", "ddd d MMM");
bar.addWidget("org.kde.plasma.panelspacer");
bar.addWidget("org.kde.plasma.systemtray");

var dock = new Panel;
dock.location = "bottom";
dock.height = 2 * Math.ceil(gridUnit * 3.1 / 2);
dock.floating = true;
dock.lengthMode = "fit";
dock.alignment = "center";
dock.hiding = "dodgewindows";
dock.opacity = "translucent";

var tasks = dock.addWidget("org.kde.plasma.icontasks");
tasks.currentConfigGroup = ["General"];
tasks.writeConfig("launchers", [
    "applications:org.kde.dolphin.desktop",
    "preferred://browser",
    "applications:org.kde.konsole.desktop",
    "applications:org.kde.kwrite.desktop",
    "applications:org.kde.discover.desktop",
    "applications:systemsettings.desktop"
]);
tasks.writeConfig("fill", false);
tasks.writeConfig("iconSpacing", 1);
tasks.writeConfig("showOnlyCurrentDesktop", false);
dock.addWidget("org.kde.plasma.marginsseparator");
dock.addWidget("org.kde.plasma.trash");
"""

LAYOUT_DEFAULTS = """[kwinrc][org.kde.kdecoration2]
ButtonsOnLeft=M
ButtonsOnRight=IAX

[kwinrc][Windows]
BorderlessMaximizedWindows=false
"""


def previews_from_shots(shots_root):
    """Build the KCM preview images from tools/testsession.py screenshots."""
    def make(vid, dest):
        shots = os.path.join(shots_root, vid)
        full = os.path.join(shots, "windows.png")
        if not os.path.exists(full):
            return
        os.makedirs(dest, exist_ok=True)
        im = Image.open(full).convert("RGB")
        w, h = im.size
        ch = round(w * 9 / 16)
        im16 = im.crop((0, (h - ch) // 2, w, (h - ch) // 2 + ch)) if ch < h else im
        im16.resize((1920, 1080), Image.LANCZOS).save(os.path.join(dest, "fullscreenpreview.jpg"),
                                                     quality=90)
        im16.resize((600, 337), Image.LANCZOS).save(os.path.join(dest, "preview.png"))
        sp = os.path.join(shots, "splash.png")
        if os.path.exists(sp):
            s = Image.open(sp).convert("RGB")
            sw, sh = s.size
            sch = round(sw * 9 / 16)
            s = s.crop((0, (sh - sch) // 2, sw, (sh - sch) // 2 + sch))
            s.resize((300, 169), Image.LANCZOS).save(os.path.join(dest, "splash.png"))
        sw_shot = os.path.join(shots, "switcher-live.png")
        if os.path.exists(sw_shot):
            s = Image.open(sw_shot).convert("RGB")
            cx, cy = s.width // 2, s.height // 2      # the switcher is centred
            s = s.crop((cx - 560, cy - 150, cx + 560, cy + 150))
            s.resize((600, 161), Image.LANCZOS).save(os.path.join(dest, "windowswitcher.png"))
    return make


def splash(pkg, wall, dest):
    p = pkg["palette"]
    img_dir = os.path.join(dest, "images")
    os.makedirs(img_dir, exist_ok=True)
    qml = open(os.path.join(ASSETS, "Splash.qml.in")).read()
    qml = (qml.replace("@BASE@", p["base"])
              .replace("@TEXT@", p["text"])
              .replace("@TRACK@", "#26ffffff" if p["is_dark"] else "#261b2130"))
    with open(os.path.join(dest, "Splash.qml"), "w") as f:
        f.write(qml)
    for name in ("logo.svg", "halo.svg"):
        with open(os.path.join(img_dir, name), "w") as f:
            f.write(remix_text(open(os.path.join(ASSETS, name)).read()))
    # calm, blurred, dimmed wallpaper as the splash backdrop
    bd = wall.resize((1920, 1200), Image.LANCZOS).filter(ImageFilter.GaussianBlur(28))
    bd = ImageEnhance.Brightness(bd).enhance(0.55 if p["is_dark"] else 1.04)
    if not p["is_dark"]:
        bd = Image.blend(bd, Image.new("RGB", bd.size, (238, 241, 247)), 0.35)
    bd.save(os.path.join(img_dir, "backdrop.jpg"), quality=90)


def switcher(dest):
    """Alt+Tab switcher QML (+ compiled mask shader) shipped inside the LnF."""
    import subprocess
    src = os.path.join(HERE, "switcher")
    os.makedirs(dest, exist_ok=True)
    shutil.copy(os.path.join(src, "WindowSwitcher.qml"), dest)
    qsb = shutil.which("qsb") or "/usr/lib64/qt6/bin/qsb"
    subprocess.run([qsb, "--glsl", "100 es,120,150", "--hlsl", "50", "--msl", "12",
                    "-o", os.path.join(dest, "roundedmask.frag.qsb"),
                    os.path.join(src, "roundedmask.frag")], check=True)


def build(out_root, night, dawn, layout_js=LAYOUT_JS, previews=None):
    base = os.path.join(out_root, "plasma", "look-and-feel")
    made = []
    for vid, pkg in PACKAGES.items():
        root = os.path.join(base, pkg["id"])
        if os.path.exists(root):
            shutil.rmtree(root)
        contents = os.path.join(root, "contents")
        os.makedirs(contents)
        with open(os.path.join(root, "metadata.json"), "w") as f:
            json.dump(metadata(pkg), f, indent=4)
        with open(os.path.join(contents, "defaults"), "w") as f:
            f.write(defaults(pkg))
        splash(pkg, night if vid == "dark" else dawn, os.path.join(contents, "splash"))
        switcher(os.path.join(contents, "windowswitcher"))
        if layout_js:
            lay = os.path.join(contents, "layouts")
            os.makedirs(lay)
            with open(os.path.join(lay, "org.kde.plasma.desktop-layout.js"), "w") as f:
                f.write(layout_js)
            with open(os.path.join(lay, "defaults"), "w") as f:
                f.write(LAYOUT_DEFAULTS)
        if previews:
            previews(vid, os.path.join(contents, "previews"))
        made.append(root)
    return made
