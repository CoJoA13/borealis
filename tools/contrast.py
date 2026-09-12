#!/usr/bin/env python3
"""WCAG contrast audit for every Borealis text/background pair.

    tools/contrast.py          report; exit code 1 if anything is below target
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "src"))
from tokens import DARK, LIGHT, contrast  # noqa: E402
import gen_apps  # noqa: E402

TARGET = 4.5          # WCAG AA, normal text
TARGET_UI = 3.0       # large text / UI glyphs


def ratio(fg, bg):
    return contrast(fg, bg)


def pairs_for(p):
    t = p
    out = []
    for bg_key in ("window", "view", "button", "header", "tooltip"):
        out.append((f"text on {bg_key}", t["text"], t[bg_key], TARGET))
    for bg_key in ("window", "view"):
        out.append((f"inactive text on {bg_key}", t["text_inactive"], t[bg_key], TARGET))
        for k in ("link", "visited", "positive", "neutral", "negative", "secondary"):
            out.append((f"{k} on {bg_key}", t[k], t[bg_key], TARGET))
    out.append(("selected text on accent", t["on_accent"], t["accent"], TARGET))
    out.append(("title text on header", t["text"], t["header"], TARGET))
    out.append(("inactive title on inactive header", t["text_inactive"], t["header_inactive"], TARGET))
    out.append(("pill glyph on close pill", t["pill_glyph"], t["pill_close"], TARGET_UI))
    out.append(("pill glyph on max pill", t["pill_glyph"], t["pill_max"], TARGET_UI))
    out.append(("pill glyph on min pill", t["pill_glyph"], t["pill_min"], TARGET_UI))
    return out


def terminal_pairs(vid):
    t = gen_apps.TERM[vid]
    out = [("terminal fg on bg", t["fg"], t["bg"], TARGET)]
    names = ["black", "red", "green", "yellow", "blue", "magenta", "cyan", "white"]
    for i, (n, hi) in enumerate(t["ansi"]):
        # black on a dark bg / white on a light bg are not meant as text colours
        if (vid == "dark" and i == 0) or (vid == "light" and i == 7):
            continue
        n, hi = gen_apps.ansi_colors(vid)[i]
        out.append((f"terminal {names[i]} on bg", n, t["bg"], TARGET))
        out.append((f"terminal bright {names[i]} on bg", hi, t["bg"], TARGET))
    return out


def editor_pairs(vid):
    th = gen_apps.kate_theme(vid, "x")
    bg = th["editor-colors"]["BackgroundColor"]
    out = []
    for name, st in th["text-styles"].items():
        out.append((f"editor {name}", st["text-color"], st.get("background-color", bg), TARGET))
    out.append(("editor line numbers", th["editor-colors"]["LineNumbers"], bg, TARGET_UI))
    return out


def main():
    bad = 0
    for p in (DARK, LIGHT):
        vid = p["id"]
        rows = pairs_for(p) + terminal_pairs(vid) + editor_pairs(vid)
        print(f"== {p['title']}")
        for name, fg, bg, target in rows:
            r = ratio(fg, bg)
            flag = "" if r >= target else f"   <-- below {target}"
            if flag:
                bad += 1
            if flag or "-v" in sys.argv:
                print(f"  {r:5.2f}  {name:<36} {fg} on {bg}{flag}")
    print(f"{bad} pair(s) below target")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
