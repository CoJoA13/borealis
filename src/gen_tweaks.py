"""Borealis Tweaks: the little desktop app, packaged for installation.

The app itself is plain source (src/tweaks); this copies it into the build tree
with a .desktop entry whose Exec is filled in at install time.
"""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(__file__))
from tokens import IDS, NAME, SLUG  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
APP_ID = f"org.{SLUG.lower()}.tweaks"


def desktop_entry():
    return f"""[Desktop Entry]
Type=Application
Name={NAME} Tweaks
GenericName=Theme settings
Comment=Switch the {NAME} variant, remix its colours and control the animated wallpaper
Exec=@EXEC@
Icon={IDS['logo']}
Terminal=false
Categories=Settings;DesktopSettings;Qt;KDE;
Keywords=theme;colour;color;accent;wallpaper;aurora;{NAME};
StartupNotify=true
X-KDE-StartupNotify=true
X-Borealis-App={SLUG.lower()}-tweaks
"""


def build(out_root):
    app = os.path.join(out_root, f"{SLUG.lower()}-tweaks")
    if os.path.exists(app):
        shutil.rmtree(app)
    shutil.copytree(os.path.join(HERE, "tweaks"), app,
                    ignore=shutil.ignore_patterns("__pycache__"))
    os.chmod(os.path.join(app, "main.py"), 0o755)
    apps = os.path.join(out_root, "applications")
    os.makedirs(apps, exist_ok=True)
    with open(os.path.join(apps, f"{APP_ID}.desktop"), "w") as f:
        f.write(desktop_entry())
    return app


if __name__ == "__main__":
    print(build(sys.argv[1]))
