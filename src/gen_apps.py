"""App themes: Konsole color schemes + profiles, Kate/KWrite editor themes."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from tokens import AUTHOR, EMAIL, TITLES, ensure_contrast, kde, mix  # noqa: E402

TERM = {
    "dark": {
        "bg": "#0e121b", "fg": "#d9deea", "fg_intense": "#f2f4fa",
        "ansi": [  # normal, intense
            ("#1b2130", "#3a4258"), ("#ff6b81", "#ff8fa0"),
            ("#7ee0a6", "#a1ecc0"), ("#ffc46b", "#ffd594"),
            ("#8b9cff", "#aab7ff"), ("#c49bff", "#d8bbff"),
            ("#5fe0c8", "#8aeedc"), ("#c9cfdd", "#f2f4fa"),
        ],
    },
    "light": {
        "bg": "#fbfcfe", "fg": "#1b2130", "fg_intense": "#0b0f19",
        "ansi": [
            ("#1b2130", "#5d6680"), ("#d93f5a", "#e8607a"),
            ("#1f9d5c", "#2fb872"), ("#b7791f", "#d18f2a"),
            ("#4c5ed8", "#6b7bea"), ("#8a55d9", "#a174ea"),
            ("#12957f", "#19ad95"), ("#b8c0d2", "#e4e8f2"),
        ],
    },
}


def ansi_colors(vid):
    """ANSI palette with every text colour readable on the terminal background
    (black on dark / white on light are background slots and stay as-is)."""
    t = TERM[vid]
    out = []
    for i, (n, hi) in enumerate(t["ansi"]):
        if (vid == "dark" and i == 0) or (vid == "light" and i == 7):
            out.append((n, hi))
        else:
            out.append((ensure_contrast(n, t["bg"]), ensure_contrast(hi, t["bg"])))
    return out


def konsole_scheme(vid, title):
    t = TERM[vid]
    bg = t["bg"]
    out = [f"[Background]\nColor={kde(bg)}\n",
           f"[BackgroundFaint]\nColor={kde(bg)}\n",
           f"[BackgroundIntense]\nColor={kde(mix(bg, t['fg'], 0.06))}\n"]
    for i, (n, hi) in enumerate(ansi_colors(vid)):
        out.append(f"[Color{i}]\nColor={kde(n)}\n")
        out.append(f"[Color{i}Faint]\nColor={kde(mix(n, bg, 0.35))}\n")
        out.append(f"[Color{i}Intense]\nColor={kde(hi)}\n")
    out += [f"[Foreground]\nColor={kde(t['fg'])}\n",
            f"[ForegroundFaint]\nColor={kde(mix(t['fg'], bg, 0.4))}\n",
            f"[ForegroundIntense]\nColor={kde(t['fg_intense'])}\n",
            "[General]\nAnchor=0.5,0.5\nBlur=false\nColorRandomization=false\n"
            f"Description={title}\nFillStyle=Tile\nOpacity=1\nWallpaper=\n"
            "WallpaperFlipType=NoFlip\nWallpaperOpacity=1\n"]
    return "\n".join(out)


def konsole_profile(sid, title):
    return ("[Appearance]\n"
            f"ColorScheme={sid}\n"
            "Font=JetBrains Mono,11,-1,7,400,0,0,0,1,0,0,0,0,0,0,1\n\n"
            "[General]\n"
            f"Name={title}\n"
            "Parent=FALLBACK/\n\n"
            "[Scrolling]\n"
            "ScrollBarPosition=2\n")


# ------------------------------------------------------------------ Kate ---
def style(color, bold=False, italic=False, underline=False, bg=None, sel=None):
    s = {"text-color": color, "selected-text-color": sel or color}
    if bold:
        s["bold"] = True
    if italic:
        s["italic"] = True
    if underline:
        s["underline"] = True
    if bg:
        s["background-color"] = bg
    return s


def kate_theme(vid, title):
    d = vid == "dark"
    c = {  # role -> color
        "normal": "#d9deea" if d else "#1b2130",
        "kw": "#c49bff" if d else "#7b3fd0",
        "fn": "#8b9cff" if d else "#4052cf",
        "var": "#ffa7b6" if d else "#c2334f",
        "op": "#93a0b8" if d else "#5d6680",
        "builtin": "#5fe0c8" if d else "#0f8a75",
        "ext": "#7fd0ff" if d else "#1f7ab8",
        "pre": "#ffc46b" if d else "#a8690f",
        "str": "#7ee0a6" if d else "#1d8a4f",
        "str2": "#9debbe" if d else "#2a9d61",
        "sstr": "#ff9fb0" if d else "#c4405c",
        "num": "#ffb86b" if d else "#b8601a",
        "comment": "#6b7590" if d else "#8a92a8",
        "doc": "#7e89a6" if d else "#6f7890",
        "commentvar": "#b18cff" if d else "#8a55d9",
        "info": "#5fe0c8" if d else "#12957f",
        "warn": "#ffc46b" if d else "#b7791f",
        "err": "#ff6b81" if d else "#d93f5a",
    }
    sel = "#f2f4fa" if d else "#0b0f19"
    bg = "#0e121b" if d else "#fbfcfe"
    c = {k: ensure_contrast(v, bg) for k, v in c.items()}

    def st(k, **kw):
        return style(c[k], sel=sel, **kw)

    text_styles = {
        "Normal": st("normal"),
        "Keyword": st("kw", bold=True),
        "Function": st("fn"),
        "Variable": st("var"),
        "ControlFlow": st("kw", bold=True),
        "Operator": st("op"),
        "BuiltIn": st("builtin"),
        "Extension": st("ext", bold=True),
        "Preprocessor": st("pre"),
        "Attribute": st("ext"),
        "Char": st("str"),
        "SpecialChar": st("builtin"),
        "String": st("str"),
        "VerbatimString": st("str2"),
        "SpecialString": st("sstr"),
        "Import": st("kw"),
        "DataType": st("builtin"),
        "DecVal": st("num"),
        "BaseN": st("num"),
        "Float": st("num"),
        "Constant": st("pre", bold=True),
        "Comment": st("comment", italic=True),
        "Documentation": st("doc", italic=True),
        "Annotation": st("fn"),
        "CommentVar": st("commentvar"),
        "RegionMarker": style(c["fn"], sel=sel,
                              bg="#1c2340" if d else "#e4e8fb"),
        "Information": st("info"),
        "Warning": st("warn"),
        "Alert": style(ensure_contrast(c["err"], "#3a1c26" if d else "#fde4e8"), bold=True,
                       sel=sel, bg="#3a1c26" if d else "#fde4e8"),
        "Others": st("str"),
        "Error": st("err", underline=True),
    }
    e = {
        "BackgroundColor": "#0e121b" if d else "#fbfcfe",
        "CodeFolding": "#1f2a45" if d else "#e1e6f8",
        "BracketMatching": "#34406b" if d else "#cdd4f6",
        "CurrentLine": "#151b28" if d else "#f1f3f9",
        "IconBorder": "#0e121b" if d else "#fbfcfe",
        "IndentationLine": "#232a3a" if d else "#e1e5ee",
        "LineNumbers": ensure_contrast("#4a5370" if d else "#a2aabd", bg, 3.1),
        "CurrentLineNumber": "#a9b2c8" if d else "#3d4660",
        "MarkBookmark": "#8b9cff" if d else "#5566e0",
        "MarkBreakpointActive": "#ff6b81" if d else "#d93f5a",
        "MarkBreakpointReached": "#ffc46b" if d else "#b7791f",
        "MarkBreakpointDisabled": "#b18cff" if d else "#8a55d9",
        "MarkExecution": "#5fe0c8" if d else "#12957f",
        "MarkWarning": "#ffc46b" if d else "#b7791f",
        "MarkError": "#ff6b81" if d else "#d93f5a",
        "ModifiedLines": "#ffc46b" if d else "#d18f2a",
        "ReplaceHighlight": "#2c5e55" if d else "#c6f0e6",
        "SavedLines": "#5fe0c8" if d else "#19ad95",
        "SearchHighlight": "#4a3f8a" if d else "#e2d6fb",
        "TextSelection": "#2b355c" if d else "#d3daf8",
        "Separator": "#232a3a" if d else "#e1e5ee",
        "SpellChecking": "#ff6b81" if d else "#d93f5a",
        "TabMarker": "#2c3447" if d else "#d5dbe8",
        "TemplateBackground": "#151b28" if d else "#f1f3f9",
        "TemplatePlaceholder": "#1f2a45" if d else "#e1e6f8",
        "TemplateFocusedPlaceholder": "#2b355c" if d else "#d3daf8",
        "TemplateReadOnlyPlaceholder": "#1a1f2c" if d else "#eceff5",
        "WordWrapMarker": "#232a3a" if d else "#e1e5ee",
    }
    return {
        "metadata": {
            "name": title,
            "revision": 1,
            "license": "SPDX-License-Identifier: GPL-3.0-or-later",
            "copyright": [f"SPDX-FileCopyrightText: 2026 {AUTHOR} <{EMAIL}>"],
        },
        "text-styles": text_styles,
        "editor-colors": e,
        "custom-styles": {},
    }


def build(out_root):
    kon = os.path.join(out_root, "konsole")
    kth = os.path.join(out_root, "org.kde.syntax-highlighting", "themes")
    os.makedirs(kon, exist_ok=True)
    os.makedirs(kth, exist_ok=True)
    for vid, title in (("dark", TITLES["dark"]), ("light", TITLES["light"])):
        sid = title.replace(" ", "")
        with open(os.path.join(kon, sid + ".colorscheme"), "w") as f:
            f.write(konsole_scheme(vid, title))
        with open(os.path.join(kon, title + ".profile"), "w") as f:
            f.write(konsole_profile(sid, title))
        with open(os.path.join(kth, sid.lower() + ".theme"), "w") as f:
            json.dump(kate_theme(vid, title), f, indent=4)
            f.write("\n")


if __name__ == "__main__":
    build(sys.argv[1])
