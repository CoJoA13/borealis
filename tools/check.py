#!/usr/bin/env python3
"""Borealis self-check: run it after ./build.py, before packaging.

  tools/check.py            everything
  tools/check.py qml svg    only those checks

Checks: Python syntax, shell syntax, QML compiles (Qt's own engine, offscreen),
every generated SVG parses, package structures are complete, the Plymouth key
file follows plymouth's parser rules, and the WCAG contrast audit passes.
"""
import glob
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHARE = os.path.join(HERE, "build", "share")
fails = []
notes = []


def ok(name, detail=""):
    print(f"  \033[32m✓\033[0m {name}{' — ' + detail if detail else ''}")


def bad(name, detail):
    fails.append(f"{name}: {detail}")
    print(f"  \033[31m✗\033[0m {name} — {detail}")


def skip(name, why):
    notes.append(f"{name} skipped ({why})")
    print(f"  \033[33m–\033[0m {name} — skipped: {why}")


def check_python():
    files = [os.path.join(HERE, "build.py")] + glob.glob(os.path.join(HERE, "src", "*.py")) \
        + glob.glob(os.path.join(HERE, "tools", "*.py"))
    errs = []
    for f in files:
        try:
            compile(open(f).read(), f, "exec")
        except SyntaxError as e:
            errs.append(f"{os.path.basename(f)}: line {e.lineno}: {e.msg}")
    bad("python", "; ".join(errs)) if errs else ok("python", f"{len(files)} files")


def check_shell():
    files = sorted(glob.glob(os.path.join(HERE, "*.sh")))
    errs = [os.path.basename(f) for f in files
            if subprocess.run(["bash", "-n", f], capture_output=True).returncode]
    bad("shell", "syntax errors in " + ", ".join(errs)) if errs else ok("shell", f"{len(files)} scripts")


# Modules that only exist inside their host process; a plain QML engine can
# never resolve them, so their import errors are expected.
HOST_ONLY = ("org.kde.kwin", "org.kde.plasma.plasmoid", "org.kde.plasma.private")


def check_qml():
    try:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtQml import QQmlComponent, QQmlEngine
    except ImportError:
        return skip("qml", "PySide6 is not installed")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QT_FORCE_STDERR_LOGGING", "1")
    files = sorted(glob.glob(os.path.join(HERE, "src", "**", "*.qml"), recursive=True)
                   + glob.glob(os.path.join(SHARE, "**", "*.qml"), recursive=True))
    app = QGuiApplication.instance() or QGuiApplication([])
    engine = QQmlEngine()
    engine.addImportPath("/usr/lib64/qt6/qml")
    problems = []
    for f in files:
        comp = QQmlComponent(engine, QUrl.fromLocalFile(f))
        for e in comp.errors():
            msg = e.toString()
            if any(m in msg for m in HOST_ONLY) and "is not installed" in msg:
                continue        # only resolvable inside plasmashell / KWin
            problems.append(msg)
    del engine
    app.processEvents()
    bad("qml", "; ".join(problems)) if problems else ok("qml", f"{len(files)} files compile")


def check_svg():
    import gzip
    files = glob.glob(os.path.join(SHARE, "**", "*.svg"), recursive=True)
    files += glob.glob(os.path.join(SHARE, "**", "*.svgz"), recursive=True)
    files += glob.glob(os.path.join(HERE, "src", "assets", "*.svg"))
    errs = []
    for f in files:
        if os.path.islink(f):
            continue
        try:
            opener = gzip.open if f.endswith(".svgz") else open
            with opener(f, "rb") as fh:
                ET.parse(fh)
        except (ET.ParseError, OSError) as e:
            errs.append(f"{os.path.relpath(f, HERE)}: {e}")
    bad("svg", "; ".join(errs[:5])) if errs else ok("svg", f"{len(files)} files parse")


def check_json():
    files = glob.glob(os.path.join(SHARE, "**", "*.json"), recursive=True) \
        + glob.glob(os.path.join(SHARE, "org.kde.syntax-highlighting", "themes", "*.theme"))
    errs = []
    for f in files:
        try:
            json.load(open(f))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            errs.append(f"{os.path.relpath(f, HERE)}: {e}")
    bad("json", "; ".join(errs[:5])) if errs else ok("json", f"{len(files)} files parse")


# path -> files that must exist inside it
PACKAGES = {
    "plasma/look-and-feel/Borealis-Dark": [
        "metadata.json", "contents/defaults", "contents/layouts/org.kde.plasma.desktop-layout.js",
        "contents/splash/Splash.qml", "contents/windowswitcher/WindowSwitcher.qml",
        "contents/windowswitcher/roundedmask.frag.qsb"],
    "plasma/look-and-feel/Borealis-Light": ["metadata.json", "contents/defaults"],
    "plasma/desktoptheme/Borealis": [
        "metadata.json", "plasmarc", "widgets/panel-background.svgz", "dialogs/background.svgz",
        "widgets/button.svgz", "widgets/viewitem.svgz", "widgets/checkmarks.svgz",
        "widgets/bar_meter_horizontal.svgz", "opaque/dialogs/background.svgz"],
    "plasma/wallpapers/org.borealis.aurora": [
        "metadata.json", "contents/ui/main.qml", "contents/ui/config.qml",
        "contents/config/main.xml", "contents/shaders/aurora.frag.qsb",
        "contents/shaders/twinkle.frag.qsb", "contents/images/sky-night.jpg"],
    "aurorae/themes/Borealis-Dark": ["metadata.desktop", "decoration.svg", "Borealis-Darkrc"],
    "wallpapers/Borealis": ["metadata.json", "contents/images/3840x2400.jpg",
                            "contents/images_dark/3840x2400.jpg"],
    "wallpapers/Borealis-Lock": ["metadata.json", "contents/images/3840x2400.jpg"],
    "icons/Borealis-Dark": ["index.theme", "scalable/apps/org.kde.dolphin.svg"],
    "sounds/Borealis": ["index.theme", "stereo/message-new-instant.oga", "stereo/desktop-login.oga"],
    "plymouth/themes/borealis": ["borealis.plymouth", "lock.png", "entry.png", "bullet.png",
                                 "watermark.png", "throbber-0001.png"],
    "gtk/borealis": ["borealis-libadwaita.css"],
    "terminal/borealis": ["Borealis Dark.tmTheme", "tmux-dark.conf", "dircolors-dark",
                          "git-dark.conf", "borealis-dark.bash", "README.md"],
    "color-schemes": ["BorealisDark.colors", "BorealisLight.colors"],
    "konsole": ["BorealisDark.colorscheme", "Borealis Dark.profile"],
}


def check_packages():
    if not os.path.isdir(SHARE):
        return bad("packages", "build/share is missing — run ./build.py")
    missing = []
    # KCM previews come from tools/testsession.py, so they only exist locally
    if os.path.exists(os.path.join(HERE, "build", "shots", "dark", "windows.png")):
        for vid in ("Dark", "Light"):
            rel = f"plasma/look-and-feel/Borealis-{vid}/contents/previews/preview.png"
            if not os.path.exists(os.path.join(SHARE, rel)):
                missing.append(rel + " (rebuild the lnf step after a test session)")
    for pkg, files in PACKAGES.items():
        for rel in files:
            if not os.path.exists(os.path.join(SHARE, pkg, rel)):
                missing.append(f"{pkg}/{rel}")
    bad("packages", f"{len(missing)} missing: " + ", ".join(missing[:6])) if missing \
        else ok("packages", f"{len(PACKAGES)} packages complete")


def check_plymouth():
    """plymouth's key-file parser: whole-line comments only, no empty values
    (they swallow the next line), no trailing spaces, colours as 0xRRGGBB."""
    path = os.path.join(SHARE, "plymouth", "themes", "borealis", "borealis.plymouth")
    if not os.path.exists(path):
        return bad("plymouth", "borealis.plymouth is missing")
    errs = []
    for n, raw in enumerate(open(path).read().splitlines(), 1):
        if raw != raw.rstrip():
            errs.append(f"line {n}: trailing whitespace")
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("["):
            continue
        if "=" not in line:
            errs.append(f"line {n}: not a key=value line")
            continue
        key, _, value = line.partition("=")
        if not value.strip():
            errs.append(f"line {n}: empty value for {key} (would eat the next line)")
        if "Color" in key and not re.fullmatch(r"0x[0-9a-fA-F]{6,8}", value.strip()):
            errs.append(f"line {n}: {key} must be 0xRRGGBB, got {value.strip()!r}")
    # UseEndAnimation=false needs ShowAnimationPercent=1.0 or progress overshoots
    text = open(path).read()
    if "UseEndAnimation=false" in text and "ShowAnimationPercent=1.0" not in text:
        errs.append("UseEndAnimation=false without ShowAnimationPercent=1.0")
    bad("plymouth", "; ".join(errs)) if errs else ok("plymouth", "theme file is valid")


def check_contrast():
    r = subprocess.run([sys.executable, os.path.join(HERE, "tools", "contrast.py")],
                       capture_output=True, text=True)
    last = (r.stdout.strip().splitlines() or ["no output"])[-1]
    bad("contrast", last) if not last.startswith("0 pair") else ok("contrast", last)


CHECKS = {"python": check_python, "shell": check_shell, "qml": check_qml, "svg": check_svg,
          "json": check_json, "packages": check_packages, "plymouth": check_plymouth,
          "contrast": check_contrast}

if __name__ == "__main__":
    wanted = sys.argv[1:] or list(CHECKS)
    unknown = [w for w in wanted if w not in CHECKS]
    if unknown:
        sys.exit(f"unknown check(s): {', '.join(unknown)}\navailable: {', '.join(CHECKS)}")
    print("Borealis check")
    for name in wanted:
        CHECKS[name]()
    print()
    if fails:
        print(f"\033[31m{len(fails)} check(s) failed\033[0m")
        sys.exit(1)
    print("\033[32mall checks passed\033[0m" + (f" ({'; '.join(notes)})" if notes else ""))
