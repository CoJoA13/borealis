"""Switching Global Themes (Borealis Dark and Light) without losing what you
set yourself.

Applying a Global Theme puts back everything the theme carries, and the
Borealis one carries fonts and a pointer theme: a switch between Dark and Light
would quietly undo the fonts and pointer chosen on Borealis Tweaks' Text &
Pointer page (or in System Settings). So this notes which of those your own
config sets, applies the theme, and writes them back.

    lookandfeel.py PACKAGE [--keep-auto]
"""
import os
import re
import subprocess
import sys

# yours to keep across a theme switch: (file, group, key)
KEPT = (
    ("kdeglobals", "General", "font"),
    ("kdeglobals", "General", "fixed"),
    ("kdeglobals", "General", "smallestReadableFont"),
    ("kdeglobals", "General", "toolBarFont"),
    ("kdeglobals", "General", "menuFont"),
    ("kdeglobals", "WM", "activeFont"),
    ("kcminputrc", "Mouse", "cursorTheme"),
)
_UNESCAPE = {"s": " ", "t": "\t", "n": "\n", "r": "\r", "\\": "\\"}


def config_home():
    return os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")


def own_values():
    """{(file, group, key): value} for each kept key your own config file sets."""
    found = {}
    for name in dict.fromkeys(file for file, _group, _key in KEPT):
        try:
            with open(os.path.join(config_home(), name), encoding="utf-8", errors="replace") as f:
                lines = f.read().splitlines()
        except OSError:
            continue
        group = None
        for raw in lines:
            line = raw.strip()
            if not line or line[0] in "#;":
                continue
            if line.startswith("["):
                group = "/".join(n for n in re.findall(r"\[([^\]]*)\]", line) if not n.startswith("$"))
            elif group is None:
                continue
            elif "=" in line:
                key, value = (part.strip() for part in line.split("=", 1))
                if (name, group, key) in KEPT:
                    found[(name, group, key)] = re.sub(r"\\(.)", lambda m: _UNESCAPE.get(m.group(1), m.group(1)),
                                                       value)
            elif line.endswith("[$d]"):
                found.pop((name, group, line[:-4].strip()), None)
    return found


def _quiet(argv):
    try:
        return subprocess.run(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30).returncode
    except (OSError, subprocess.TimeoutExpired):
        return 1


def _ask(argv):
    try:
        return subprocess.run(argv, capture_output=True, text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


def restore(values):
    """Writes the kept keys back, and tells the programs that show them."""
    for (name, group, key), value in values.items():
        _quiet(["kwriteconfig6", "--notify", "--file", name, "--group", group, "--key", key, value])
    if any(name == "kdeglobals" for name, _group, _key in values):
        _quiet(["dbus-send", "--session", "--type=signal", "/KDEPlatformTheme",
                "org.kde.KDEPlatformTheme.refreshFonts"])
    if ("kdeglobals", "WM", "activeFont") in values:
        _quiet(["dbus-send", "--session", "--type=signal", "/KWin", "org.kde.KWin.reloadConfig"])
    theme = values.get(("kcminputrc", "Mouse", "cursorTheme"))
    if theme:
        size = _ask(["kreadconfig6", "--file", "kcminputrc", "--group", "Mouse", "--key", "cursorSize"])
        _quiet(["plasma-apply-cursortheme", theme] + (["--size", size] if size.isdigit() else []))


def apply(package, keep_auto=False):
    """Applies a Global Theme and keeps your own fonts and pointer; returns lookandfeeltool's status."""
    kept = own_values()
    try:
        status = subprocess.run(["lookandfeeltool", "--apply", package]
                                + (["--keep-auto"] if keep_auto else [])).returncode
    except OSError as e:
        print(e, file=sys.stderr)
        return 1
    if kept:
        restore(kept)
        kinds = sorted({"pointer theme" if name == "kcminputrc" else "fonts" for name, _group, _key in kept})
        print("kept your own " + " and ".join(kinds))
    return status


if __name__ == "__main__":
    packages = [a for a in sys.argv[1:] if a != "--keep-auto"]
    if len(packages) != 1 or packages[0].startswith("-"):
        sys.exit("usage: lookandfeel.py PACKAGE [--keep-auto]")
    sys.exit(apply(packages[0], keep_auto="--keep-auto" in sys.argv[1:]))
