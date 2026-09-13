"""Borealis Bar: the standalone top bar, packaged.

The app is plain source (src/bar) plus the code it shares with the dock
(src/shellkit). The build copies both with the names filled in, so a remix runs
its own bar, and adds the bar's .desktop entry and systemd user unit. Their
Exec lines are completed at install time: @PYTHON@ becomes the private
interpreter copy KWin trusts with its window list (the entry's
X-KDE-Wayland-Interfaces), @EXEC@ the installed main.py.
"""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(__file__))
from gen_dock import copy_shellkit  # noqa: E402
from tokens import IDS, NAME, SLUG, VERSION  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def ids_py():
    slug = SLUG.lower()
    return (
        '"""Names filled in by gen_bar.py, so a remix runs its own bar."""\n'
        f"NAME = {NAME!r}\n"
        f"SLUG = {slug!r}\n"
        f"VERSION = {VERSION!r}\n"
        f"APP_ID = {IDS['barapp']!r}\n"
        f"TWEAKS_ID = {'org.' + slug + '.tweaks'!r}\n"
        f"BUS = {IDS['barbus']!r}\n"
        'PATH = "/Bar"\n'
        f"INTERFACE = {IDS['barbus'] + '1'!r}\n"
        f"LNF_DARK = {IDS['lnf_dark']!r}\n"
        f"LNF_LIGHT = {IDS['lnf_light']!r}\n"
        f"AURORA = {IDS['live']!r}\n"
    )


def desktop_entry():
    return f"""[Desktop Entry]
Type=Application
Name={NAME} Bar
GenericName=Top bar
Comment=The top bar of the {NAME} desktop: app menus, clock, tray and Control Center
Exec=@PYTHON@ @EXEC@
Icon={IDS['logo']}
Terminal=false
NoDisplay=true
Categories=Utility;Qt;KDE;
X-KDE-StartupNotify=false
X-DBUS-ServiceName={IDS['barbus']}
X-Borealis-App={IDS['barexe']}
X-KDE-Wayland-Interfaces=org_kde_plasma_window_management
"""


def service_unit():
    return f"""# Installed by the Borealis theme (./install.sh); ./uninstall.sh --remove takes it out
[Unit]
Description={NAME} Bar
X-Borealis-App={IDS['barexe']}
PartOf=graphical-session.target
After=plasma-kwin_wayland.service plasma-plasmashell.service
StartLimitIntervalSec=60s
StartLimitBurst=5

[Service]
Type=dbus
BusName={IDS['barbus']}
ExecStart=@PYTHON@ @EXEC@
Restart=on-failure
RestartSec=2
Slice=session.slice
TimeoutStopSec=5

[Install]
WantedBy=plasma-workspace.target
"""


def build(out_root):
    app = os.path.join(out_root, IDS["barexe"])
    shutil.rmtree(app, ignore_errors=True)
    shutil.copytree(os.path.join(HERE, "bar"), app, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    copy_shellkit(app)
    with open(os.path.join(app, "ids.py"), "w") as f:
        f.write(ids_py())
    os.chmod(os.path.join(app, "main.py"), 0o755)
    apps = os.path.join(out_root, "applications")
    os.makedirs(apps, exist_ok=True)
    with open(os.path.join(apps, IDS["barapp"] + ".desktop"), "w") as f:
        f.write(desktop_entry())
    units = os.path.join(out_root, "systemd", "user")
    os.makedirs(units, exist_ok=True)
    with open(os.path.join(units, IDS["barexe"] + ".service"), "w") as f:
        f.write(service_unit())
    return [app]


if __name__ == "__main__":
    print("\n".join(build(sys.argv[1])))
