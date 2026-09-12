"""Borealis plasmoids: the dock and the quick settings widget.

Static QML packaged as Plasma applets, with the ids filled in so a remix ships
its own copies (org.borealisember.dock and so on).
"""
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(__file__))
from tokens import AUTHOR, EMAIL, IDS, NAME, SLUG, VERSION  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
APPLETS = ("dock", "quicksettings")


def applet_id(kind):
    return IDS[kind]


def build(out_root):
    made = []
    for kind in APPLETS:
        src = os.path.join(HERE, "plasmoids", kind)
        if not os.path.isdir(src):
            continue
        dest = os.path.join(out_root, "plasma", "plasmoids", applet_id(kind))
        if os.path.exists(dest):
            shutil.rmtree(dest)
        shutil.copytree(src, dest, ignore=shutil.ignore_patterns("*.in"))
        fields = {"@ID@": applet_id(kind), "@NAME@": NAME, "@AUTHOR@": AUTHOR,
                  "@EMAIL@": EMAIL, "@VERSION@": VERSION, "@LOGO@": IDS["logo"],
                  "@LNF_DARK@": IDS["lnf_dark"], "@LNF_LIGHT@": IDS["lnf_light"],
                  "@AURORA@": IDS["live"]}
        meta = open(os.path.join(src, "metadata.json.in")).read()
        for key, value in fields.items():
            meta = meta.replace(key, value)
        with open(os.path.join(dest, "metadata.json"), "w") as f:
            f.write(meta)
        # the same placeholders appear in the config schema
        schema = os.path.join(dest, "contents", "config", "main.xml")
        if os.path.exists(schema):
            text = open(schema).read()
            for key, value in fields.items():
                text = text.replace(key, value)
            with open(schema, "w") as f:
                f.write(text)
        # the translation domain and any other id reference follow the package
        for root, _dirs, files in os.walk(dest):
            for fn in files:
                if not fn.endswith(".qml"):
                    continue
                path = os.path.join(root, fn)
                text = open(path).read()
                new = re.sub(r"org\.borealis\.(dock|quicksettings)",
                             lambda m: applet_id(m.group(1)), text)
                if new != text:
                    with open(path, "w") as f:
                        f.write(new)
        made.append(dest)
    return made


if __name__ == "__main__":
    print("\n".join(build(sys.argv[1])))
