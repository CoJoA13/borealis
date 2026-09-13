"""Borealis Tweaks — the Python side: reads and changes the desktop's theme.

Everything that touches the session goes through here, so the QML stays a view.
Long jobs (a remix rebuild) run in a thread and report progress line by line.
"""
import configparser
import json
import os
import re
import shutil
import subprocess
import threading
import time

from PySide6.QtCore import Property, QObject, Signal, Slot

CONF = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
DATA = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
STATE = os.path.join(CONF, "borealis", "tweaks.json")
def _project():
    """Where the generator lives; install.sh records it, and BOREALIS_PROJECT wins."""
    candidates = [os.environ.get("BOREALIS_PROJECT")]
    marker = os.path.join(CONF, "borealis", "project")
    if os.path.exists(marker):
        candidates.append(open(marker).read().strip())
    candidates += ["~/Desktop/Claude/Borealis", "~/Borealis", "~/src/Borealis", "~/Projects/Borealis"]
    for c in candidates:
        if c and os.path.exists(os.path.join(os.path.expanduser(c), "build.py")):
            return os.path.expanduser(c)
    return os.path.expanduser(candidates[-1])


PROJECT = _project()

PRESETS = [
    ("Nocturne", "#8b9cff", "the original periwinkle"),
    ("Ember", "#ff8a5b", "warm orange over ink"),
    ("Moss", "#4fbf6a", "forest green"),
    ("Orchid", "#c77dff", "soft violet"),
    ("Rose", "#ff6f9c", "deep pink"),
    ("Glacier", "#4fd6e8", "ice cyan"),
    ("Amber", "#f7b955", "honey gold"),
]

# what each install.sh extra does, said once it's done
EXTRAS = {
    "--gtk": "GTK apps get the Borealis colours when they next start.",
    "--konsole": "Konsole opens with the Borealis profile.",
    "--terminal": "New terminals pick up the Borealis colours.",
    "--firefox": "Firefox is styled; restart it to see.",
}

# install-system.sh options, with what to say afterwards
SYSTEM_WIDE = {
    "": "Copied system-wide; now use Login Screen › Apply Plasma Settings.",
    "--plymouth": "Done — the boot splash appears at the next start.",
    "--plymouth-revert": "The previous boot splash is back from the next start.",
    "--grub": "The Borealis boot menu appears at the next start.",
    "--grub-revert": "The plain boot menu is back from the next start.",
}


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def kread(file, group, key, default=""):
    groups = []
    for g in group.split("/"):
        groups += ["--group", g]
    r = run(["kreadconfig6", "--file", file] + groups + ["--key", key])
    return (r.stdout.strip() or default) if r.returncode == 0 else default


def kwrite(file, group, key, value):
    groups = []
    for g in group.split("/"):
        groups += ["--group", g]
    # --notify: running apps that watch the file see the change at once
    run(["kwriteconfig6", "--notify", "--file", file] + groups + ["--key", key, value])


def read_text(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def firefox_profile():
    """Firefox's default profile, found the way install.sh finds it."""
    roots = (os.path.join(CONF, "mozilla", "firefox"), os.path.expanduser("~/.mozilla/firefox"))
    for root in roots:
        ini = os.path.join(root, "profiles.ini")
        if not os.path.exists(ini):
            continue
        cp = configparser.ConfigParser(interpolation=None)
        try:
            cp.read(ini)
        except configparser.Error:
            continue
        path = next((cp[s]["Default"] for s in cp.sections() if s.startswith("Install") and cp[s].get("Default")), "")
        path = path or next((cp[s].get("Path", "") for s in cp.sections()
                             if s.startswith("Profile") and cp[s].get("Default") == "1"), "")
        path = path or next((cp[s]["Path"] for s in cp.sections() if s.startswith("Profile") and cp[s].get("Path")),
                            "")
        if path:
            full = path if os.path.isabs(path) else os.path.join(root, path)
            if os.path.isdir(full):
                return full
    return ""


class Backend(QObject):
    changed = Signal()
    busyChanged = Signal()
    logged = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._busy = False
        self._live_override = None
        self._cache = {}
        self._state = {}
        if os.path.exists(STATE):
            try:
                self._state = json.load(open(STATE))
            except ValueError:
                pass

    def _cached(self, key, compute, ttl=3.0):
        """Slow answers (other programs) are kept for a moment: QML asks often."""
        now = time.monotonic()
        hit = self._cache.get(key)
        if hit is None or now - hit[0] > ttl:
            hit = (now, compute())
            self._cache[key] = hit
        return hit[1]

    # ---------------------------------------------------------- readers ---
    def _lnf(self):
        return kread("kdeglobals", "KDE", "LookAndFeelPackage")

    @Property(str, notify=changed)
    def themeName(self):
        pkg = self._lnf()
        meta = os.path.join(DATA, "plasma/look-and-feel", pkg, "metadata.json")
        if os.path.exists(meta):
            try:
                return json.load(open(meta))["KPlugin"]["Name"]
            except (ValueError, KeyError):
                pass
        return pkg or "not set"

    @Property(bool, notify=changed)
    def isBorealis(self):
        return self._lnf().lower().startswith(("borealis",))

    @Property(str, notify=changed)
    def variant(self):
        if kread("kdeglobals", "KDE", "AutomaticLookAndFeel").lower() == "true":
            return "auto"
        return "light" if self._lnf().endswith("-Light") else "dark"

    @Property(str, notify=changed)
    def accent(self):
        return self._state.get("accent", "#8b9cff")

    @Property(str, notify=changed)
    def paletteName(self):
        return self._state.get("name", "Borealis")

    def _wallpaper_plugins(self):
        """What the desktops actually use: ask plasmashell, fall back to config.

        The config key is `wallpaperplugin` directly under [Containments][<n>],
        where <n> is whatever number that desktop happens to have."""
        r = run(["qdbus-qt6", "org.kde.plasmashell", "/PlasmaShell",
                 "org.kde.PlasmaShell.evaluateScript",
                 "var d = desktops(); var out = []; "
                 "for (var i = 0; i < d.length; i++) { out.push(d[i].wallpaperPlugin); } "
                 "print(out.join(','));"])
        if r.returncode == 0 and r.stdout.strip():
            return [x.strip() for x in r.stdout.strip().split(",") if x.strip()]
        found, section = [], ""
        path = os.path.join(CONF, "plasma-org.kde.plasma.desktop-appletsrc")
        if os.path.exists(path):
            for line in open(path):
                line = line.rstrip("\n")
                if line.startswith("["):
                    section = line
                elif line.startswith("wallpaperplugin=") and re.fullmatch(r"\[Containments\]\[\d+\]", section):
                    found.append(line.split("=", 1)[1])
        return found

    @Property(bool, notify=changed)
    def liveWallpaper(self):
        if self._live_override is not None:
            return self._live_override        # until plasmashell catches up
        live = self._state.get("live_id", "org.borealis.aurora")
        return any(p == live for p in self._cached("wallpapers", self._wallpaper_plugins))

    @Property(bool, notify=changed)
    def flatpakColors(self):
        """True when Flatpak apps may read ~/.config/gtk-4.0."""
        if not shutil.which("flatpak"):
            return False
        return self._cached("flatpak", lambda: "xdg-config/gtk-4.0" in run(["flatpak", "override", "--user",
                                                                            "--show"]).stdout)

    @Property(bool, constant=True)
    def hasFlatpak(self):
        return bool(shutil.which("flatpak"))

    @Property(str, notify=changed)
    def bootSplash(self):
        def compute():
            r = run(["plymouth-set-default-theme"]) if shutil.which("plymouth-set-default-theme") else None
            return r.stdout.strip() if r is not None and r.returncode == 0 else ""
        return self._cached("plymouth", compute)

    @Property(bool, notify=changed)
    def grubMenu(self):
        """True when GRUB draws the Borealis menu (install-system.sh --grub)."""
        m = re.search(r'^GRUB_THEME="?([^"\n]*)', read_text("/etc/default/grub"), re.M)
        return bool(m and "borealis" in m.group(1).lower())

    @Property(bool, notify=changed)
    def systemWide(self):
        """The login screen can only use themes installed outside $HOME."""
        pkg = self._lnf()
        return bool(pkg) and os.path.isdir(f"/usr/local/share/plasma/look-and-feel/{pkg}")

    @Property(bool, notify=changed)
    def fontsInstalled(self):
        def compute():
            names = {n.strip() for line in run(["fc-list", ":", "family"]).stdout.splitlines()
                     for n in line.split(",")}
            return bool(names & {"Inter", "Inter Variable"}) and "JetBrains Mono" in names
        return self._cached("fonts", compute)

    @Property(bool, notify=changed)
    def gtkColors(self):
        """install.sh --gtk adds one @import of its own stylesheet to gtk.css."""
        return bool(re.search(r"@import '[^']*-libadwaita\.css';",
                              read_text(os.path.join(CONF, "gtk-4.0", "gtk.css"))))

    @Property(bool, notify=changed)
    def konsoleDefault(self):
        return kread("konsolerc", "Desktop Entry", "DefaultProfile").lower().startswith("borealis")

    @Property(bool, notify=changed)
    def terminalKit(self):
        return "/borealis/terminal/" in read_text(os.path.expanduser("~/.bashrc"))

    @Property(bool, notify=changed)
    def hasFirefox(self):
        return bool(self._cached("firefox", firefox_profile))

    @Property(bool, notify=changed)
    def firefoxStyled(self):
        profile = self._cached("firefox", firefox_profile)
        css = read_text(os.path.join(profile, "chrome", "userChrome.css")) if profile else ""
        return bool(re.search(r'@import "[^"]*-userChrome\.css";', css))

    @Property(bool, notify=changed)
    def hasProject(self):
        return os.path.exists(os.path.join(PROJECT, "build.py"))

    @Property(bool, notify=busyChanged)
    def busy(self):
        return self._busy

    @Property("QVariantList", constant=True)
    def presets(self):
        return [{"name": n, "color": c, "hint": h} for n, c, h in PRESETS]

    @Property("QVariantList", notify=changed)
    def backups(self):
        root = os.path.join(DATA, "..", "state", "borealis-backup")
        root = os.path.normpath(root)
        if not os.path.isdir(root):
            return []
        return sorted(os.listdir(root), reverse=True)[:10]

    # ---------------------------------------------------------- actions ---
    def _set_busy(self, value):
        self._busy = value
        self.busyChanged.emit()

    def _job(self, steps, done_msg, on_success=None):
        """Run (label, argv) steps in order, streaming their output."""
        def work():
            ok = True
            for label, cmd in steps:
                self.logged.emit(f"$ {label}")
                try:
                    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                         cwd=PROJECT if os.path.isdir(PROJECT) else None)
                except OSError as e:
                    self.logged.emit(str(e))
                    ok = False
                    break
                for line in p.stdout:
                    self.logged.emit(line.rstrip())
                if p.wait() != 0:
                    ok = False
                    break
            if ok and on_success:
                on_success()
            self._cache.clear()
            self._set_busy(False)
            self.changed.emit()
            self.finished.emit(ok, done_msg if ok else "Something went wrong — see the log.")
        self._set_busy(True)
        threading.Thread(target=work, daemon=True).start()

    @Slot(str)
    def setVariant(self, variant):
        pkg = self._lnf() or "Borealis-Dark"
        base = pkg.rsplit("-", 1)[0] if pkg.endswith(("-Dark", "-Light")) else "Borealis"
        if variant == "auto":
            kwrite("kdeglobals", "KDE", "DefaultLightLookAndFeel", f"{base}-Light")
            kwrite("kdeglobals", "KDE", "DefaultDarkLookAndFeel", f"{base}-Dark")
            kwrite("kdeglobals", "KDE", "AutomaticLookAndFeel", "true")
            target = f"{base}-Dark"
            extra = ["--keep-auto"]
        else:
            kwrite("kdeglobals", "KDE", "AutomaticLookAndFeel", "false")
            target = f"{base}-{'Light' if variant == 'light' else 'Dark'}"
            extra = []
        self._job([(f"lookandfeeltool --apply {target}",
                    ["lookandfeeltool", "--apply", target] + extra)],
                  f"Switched to {target.replace('-', ' ')}.")

    @Slot(bool)
    def setLiveWallpaper(self, on):
        live = self._state.get("live_id", "org.borealis.aurora")
        plugin = live if on else "org.kde.image"
        script = ("var d = desktops(); for (var i = 0; i < d.length; i++) "
                  f"{{ d[i].wallpaperPlugin = '{plugin}'; }}")
        run(["qdbus-qt6", "org.kde.plasmashell", "/PlasmaShell",
             "org.kde.PlasmaShell.evaluateScript", script])
        kwrite("kscreenlockerrc", "Greeter", "WallpaperPlugin", plugin)
        if not on:
            # a plain image desktop needs an image; keep ours
            wall = os.path.join(DATA, "wallpapers", self._state.get("name", "Borealis").replace(" ", ""))
            if os.path.isdir(wall):
                run(["plasma-apply-wallpaperimage", wall])
        # show the new state at once; re-read once plasmashell has applied it
        self._live_override = on
        self._cache.pop("wallpapers", None)
        self.changed.emit()
        threading.Timer(2.5, self._clear_override).start()

    def _clear_override(self):
        self._live_override = None
        self._cache.pop("wallpapers", None)
        self.changed.emit()

    def build_flags(self):
        """build.py's palette flags for the Borealis that's on, so a rebuilt part of a remix keeps its colours."""
        name, accent = self._state.get("name", "Borealis"), self._state.get("accent", "#8b9cff")
        if name != "Borealis":
            return ["--accent", accent, "--name", name]
        return ["--accent", accent] if accent.lower() != "#8b9cff" else []

    @Slot(str, str, bool, bool)
    def remix(self, accent, name, gtk, terminal):
        """Rebuild the whole theme on a new accent and apply it."""
        out = os.path.join(os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache"),
                           "borealis", "remix", "share")
        build = ["python3", os.path.join(PROJECT, "build.py"), "--out", out]
        if name != "Borealis":
            build += ["--accent", accent, "--name", name]
        elif accent.lower() != "#8b9cff":
            build += ["--accent", accent]
        apply_cmd = [os.path.join(PROJECT, "install.sh"), "--from", out,
                     "--apply", "light" if self.variant == "light" else "dark"]
        if gtk:
            apply_cmd.append("--gtk")
        if terminal:
            apply_cmd.append("--terminal")
        def remember():
            self._state.update({"accent": accent, "name": name,
                                "live_id": "org." + "".join(name.split()).lower() + ".aurora"})
            os.makedirs(os.path.dirname(STATE), exist_ok=True)
            json.dump(self._state, open(STATE, "w"), indent=2)

        self._job([("building " + name, build), ("installing", apply_cmd)],
                  f"{name} is on. Your old settings are in ~/.local/state/borealis-backup.",
                  on_success=remember)

    @Slot(str)
    def restore(self, stamp):
        root = os.path.normpath(os.path.join(DATA, "..", "state", "borealis-backup"))
        self._job([("restoring " + stamp,
                    [os.path.join(PROJECT, "uninstall.sh"), "--restore", os.path.join(root, stamp)])],
                  "Restored. Some apps may need restarting.")

    @Slot()
    def grantFlatpakColors(self):
        run(["flatpak", "override", "--user", "--filesystem=xdg-config/gtk-4.0:ro"])
        self._cache.pop("flatpak", None)
        self.changed.emit()

    @Slot(str)
    def installSystemWide(self, what):
        """install-system.sh needs root: ask through polkit, in the background."""
        script = os.path.join(PROJECT, "install-system.sh")
        if what not in SYSTEM_WIDE:
            return
        if not os.path.exists(script):
            return self.finished.emit(False, "install-system.sh was not found.")
        cmd = ["pkexec", script] + ([what] if what else [])
        self._job([("pkexec install-system.sh " + what, cmd)], SYSTEM_WIDE[what])

    @Slot(str)
    def installExtra(self, flag):
        """One of install.sh's extras, for the variant already in use."""
        if flag in EXTRAS:
            self.runInstaller([flag], EXTRAS[flag])

    @Slot()
    def installFonts(self):
        packages = ["rsms-inter-fonts", "jetbrains-mono-fonts"]
        self._job([("pkexec dnf install " + " ".join(packages), ["pkexec", "dnf", "install", "-y"] + packages)],
                  "Fonts installed. Apps pick them up when they next start.")

    def runInstaller(self, args, done_msg):
        script = os.path.join(PROJECT, "install.sh")
        if not os.path.exists(script):
            return self.finished.emit(False, "install.sh was not found.")
        self._job([("install.sh " + " ".join(args), [script] + list(args))], done_msg)

    @Slot(str)
    def launch(self, what):
        cmds = {
            "globaltheme": ["systemsettings", "kcm_lookandfeel"],
            "wallpaper": ["plasma-open-settings", "kcm_wallpaper"],
            "colors": ["systemsettings", "kcm_colors"],
            "login": ["systemsettings", "kcm_plasmalogin"],
            "fonts": ["systemsettings", "kcm_fonts"],
        }
        cmd = cmds.get(what)
        if cmd and shutil.which(cmd[0]):
            subprocess.Popen(cmd, start_new_session=True)
