"""Borealis Dock: the standalone dock and its KWin bridge, packaged.

The app is plain source (src/dock) and the bridge a declarative KWin script
(src/dockbridge). The build copies both with the names filled in, so a remix
runs its own dock beside this one, and adds the dock's .desktop entry and
systemd user unit; their Exec lines are completed at install time.
"""
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
from tokens import AUTHOR, EMAIL, IDS, NAME, SLUG, VERSION  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE_BUS = "org.borealis.Dock"
SOURCE_SHORTCUT = "Borealis Dock: sync"
SOURCE_SLOT_SHORTCUT = "Borealis Dock: activate app "
SOURCE_LAUNCHPAD_SHORTCUT = "Borealis Dock: Launchpad"


def shortcut():
    return f"{NAME} Dock: sync"


def ids_py():
    slug = SLUG.lower()
    return (
        '"""Names filled in by gen_dock.py, so a remix runs its own dock."""\n'
        f"NAME = {NAME!r}\n"
        f"SLUG = {slug!r}\n"
        f"VERSION = {VERSION!r}\n"
        f"APP_ID = {IDS['dockapp']!r}\n"
        f"TWEAKS_ID = {'org.' + slug + '.tweaks'!r}\n"
        f"BUS = {IDS['dockbus']!r}\n"
        'PATH = "/Dock"\n'
        f"INTERFACE = {IDS['dockbus'] + '1'!r}\n"
        f"BRIDGE = {IDS['dockbridge']!r}\n"
        f"SHORTCUT = {shortcut()!r}\n"
        f"LAUNCHPAD_SHORTCUT = {NAME + ' Dock: Launchpad'!r}\n"
    )


def desktop_entry():
    return f"""[Desktop Entry]
Type=Application
Name={NAME} Dock
GenericName=Dock
Comment=Your apps and open windows in a magnifying dock
Exec=@EXEC@
Icon={IDS['logo']}
Terminal=false
NoDisplay=true
Categories=Utility;Qt;KDE;
X-KDE-StartupNotify=false
X-DBUS-ServiceName={IDS['dockbus']}
X-Borealis-App={IDS['dockexe']}
"""


def service_unit():
    return f"""# Installed by the Borealis theme (./install.sh); ./uninstall.sh --remove takes it out
[Unit]
Description={NAME} Dock
X-Borealis-App={IDS['dockexe']}
PartOf=graphical-session.target
After=plasma-kwin_wayland.service plasma-plasmashell.service
StartLimitIntervalSec=60s
StartLimitBurst=5

[Service]
Type=dbus
BusName={IDS['dockbus']}
ExecStart=@EXEC@
Restart=on-failure
RestartSec=2
Slice=session.slice
TimeoutStopSec=5

[Install]
WantedBy=plasma-workspace.target
"""


def bridge(out_root):
    src = os.path.join(HERE, "dockbridge")
    dest = os.path.join(out_root, "kwin", "scripts", IDS["dockbridge"])
    shutil.rmtree(dest, ignore_errors=True)
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns("*.in"))
    fields = {"@ID@": IDS["dockbridge"], "@NAME@": NAME, "@AUTHOR@": AUTHOR, "@EMAIL@": EMAIL,
              "@VERSION@": VERSION, "@LOGO@": IDS["logo"]}
    meta = open(os.path.join(src, "metadata.json.in")).read()
    for key, value in fields.items():
        meta = meta.replace(key, value)
    with open(os.path.join(dest, "metadata.json"), "w") as f:
        f.write(meta)
    qml = os.path.join(dest, "contents", "ui", "main.qml")
    text = open(qml).read()
    text = (text.replace(f'"{SOURCE_BUS}1"', f'"{IDS["dockbus"]}1"')
                .replace(f'"{SOURCE_BUS}"', f'"{IDS["dockbus"]}"')
                .replace(f'"{SOURCE_SHORTCUT}"', f'"{shortcut()}"')
                .replace(f'"{SOURCE_SLOT_SHORTCUT}"', f'"{NAME} Dock: activate app "')
                .replace(f'"{SOURCE_LAUNCHPAD_SHORTCUT}"', f'"{NAME} Dock: Launchpad"'))
    with open(qml, "w") as f:
        f.write(text)
    # the previews' rounded corners: the Alt+Tab switcher's mask shader
    qsb = shutil.which("qsb") or "/usr/lib64/qt6/bin/qsb"
    subprocess.run([qsb, "--glsl", "100 es,120,150", "--hlsl", "50", "--msl", "12",
                    "-o", os.path.join(dest, "contents", "ui", "roundedmask.frag.qsb"),
                    os.path.join(HERE, "switcher", "roundedmask.frag")], check=True)
    return dest


def copy_shellkit(app):
    """The code the dock, the bar and Tweaks share, beside each app's own."""
    kit = os.path.join(HERE, "shellkit")
    for name in sorted(os.listdir(kit)):
        if name.endswith((".py", ".qml")):
            shutil.copy(os.path.join(kit, name), os.path.join(app, name))


def build(out_root):
    app = os.path.join(out_root, IDS["dockexe"])
    shutil.rmtree(app, ignore_errors=True)
    shutil.copytree(os.path.join(HERE, "dock"), app,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    copy_shellkit(app)
    with open(os.path.join(app, "ids.py"), "w") as f:
        f.write(ids_py())
    os.chmod(os.path.join(app, "main.py"), 0o755)
    apps = os.path.join(out_root, "applications")
    os.makedirs(apps, exist_ok=True)
    with open(os.path.join(apps, IDS["dockapp"] + ".desktop"), "w") as f:
        f.write(desktop_entry())
    units = os.path.join(out_root, "systemd", "user")
    os.makedirs(units, exist_ok=True)
    with open(os.path.join(units, IDS["dockexe"] + ".service"), "w") as f:
        f.write(service_unit())
    return [app, bridge(out_root)]


if __name__ == "__main__":
    print("\n".join(build(sys.argv[1])))
