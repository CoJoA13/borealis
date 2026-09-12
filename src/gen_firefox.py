"""Borealis for Firefox: a userChrome.css built from the same palette.

Firefox draws its own chrome, so nothing in KDE reaches it. This restyles the
toolbars, tabs, address bar, menus and sidebar to match, and comes with a
userContent.css so the built-in pages (new tab, about:*) stop flashing white.
Installed by `install.sh --firefox`, which also flips the pref Firefox needs
to read these files at all.
"""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(__file__))
from tokens import DARK, LIGHT, NAME, RADIUS, RADIUS_CTRL, SLUG, mix  # noqa: E402


def block(p, indent=0):
    """Firefox's own theme variables, filled in from the Borealis palette."""
    pad = " " * indent
    v = {
        # window + toolbars
        "--borealis-bg": p["window"],
        "--borealis-header": p["header"],
        "--borealis-view": p["view"],
        "--borealis-text": p["text"],
        "--borealis-dim": p["text_inactive"],
        "--borealis-border": p["border"],
        "--borealis-accent": p["accent"],
        "--borealis-on-accent": p["on_accent"],
        "--borealis-hover": mix(p["header"], p["text"], 0.08),
        "--borealis-tooltip": p["tooltip"],
        # variables Firefox itself reads
        "--toolbar-bgcolor": p["header"],
        "--toolbar-color": p["text"],
        "--toolbar-field-background-color": p["view"],
        "--toolbar-field-color": p["text"],
        "--toolbar-field-focus-background-color": p["view"],
        "--toolbar-field-focus-border-color": p["accent"],
        "--toolbar-field-border-color": p["border"],
        "--tabpanel-background-color": p["window"],
        "--lwt-accent-color": p["header_inactive"],
        "--lwt-text-color": p["text"],
        "--lwt-tab-line-color": p["accent"],
        "--lwt-selected-tab-background-color": p["window"],
        "--tab-selected-bgcolor": p["window"],
        "--tab-selected-textcolor": p["text"],
        "--panel-background": p["tooltip"],
        "--panel-color": p["text"],
        "--panel-border-color": p["border"],
        "--panel-separator-color": p["border"],
        "--arrowpanel-background": p["tooltip"],
        "--arrowpanel-color": p["text"],
        "--arrowpanel-border-color": p["border"],
        "--button-hover-bgcolor": mix(p["header"], p["text"], 0.10),
        "--button-active-bgcolor": mix(p["header"], p["text"], 0.16),
        "--focus-outline-color": p["accent"],
        "--sidebar-background-color": p["window"],
        "--sidebar-text-color": p["text"],
        "--sidebar-border-color": p["border"],
        "--urlbar-box-bgcolor": p["button"],
        "--urlbar-box-text-color": p["text"],
        "--urlbar-box-hover-bgcolor": mix(p["button"], p["text"], 0.10),
        "--newtab-background-color": p["window"],
        "--newtab-text-primary-color": p["text"],
    }
    return "\n".join(f"{pad}  {k}: {val};" for k, val in v.items())


CHROME_RULES = f"""
/* ---- shape: Borealis' {RADIUS} px corners and pill-ish controls ---- */
#navigator-toolbox {{
  border-bottom: 1px solid var(--borealis-border) !important;
}}

.tab-background {{
  border-radius: {RADIUS_CTRL}px {RADIUS_CTRL}px 0 0 !important;
  margin-block: 2px 0 !important;
}}

.tab-background[selected] {{
  background: var(--borealis-bg) !important;
  border: 1px solid var(--borealis-border) !important;
  border-bottom: none !important;
}}

.tabbrowser-tab:not([selected]):hover .tab-background {{
  background: var(--borealis-hover) !important;
}}

#urlbar,
#searchbar {{
  border-radius: {RADIUS_CTRL}px !important;
}}

#urlbar[focused="true"] {{
  outline: 2px solid var(--borealis-accent) !important;
  outline-offset: -2px !important;
}}

#urlbar-background,
#searchbar .searchbar-textbox {{
  border: 1px solid var(--borealis-border) !important;
}}

/* results, menus and panels */
.urlbarView-row[selected] > .urlbarView-row-inner,
.urlbarView-row:hover > .urlbarView-row-inner {{
  background: var(--borealis-hover) !important;
  border-radius: {RADIUS_CTRL}px !important;
}}

menupopup,
panel {{
  --panel-border-radius: {RADIUS}px !important;
}}

menupopup > menuitem[_moz-menuactive="true"],
menupopup > menu[_moz-menuactive="true"] {{
  background-color: var(--borealis-accent) !important;
  color: var(--borealis-on-accent) !important;
}}

/* findbar, sidebar and the notification bars */
findbar,
#sidebar-box,
#sidebar-header {{
  background-color: var(--borealis-bg) !important;
  color: var(--borealis-text) !important;
}}

#sidebar-header {{
  border-bottom: 1px solid var(--borealis-border) !important;
}}

/* toolbars: one Borealis surface, with the accent marking the live tab */
#nav-bar,
#PersonalToolbar {{
  background-color: var(--borealis-header) !important;
  box-shadow: none !important;
}}

.tabbrowser-tab[selected] .tab-background {{
  box-shadow: inset 0 -2px 0 0 var(--borealis-accent) !important;
}}

tooltip {{
  --panel-background: var(--borealis-tooltip) !important;
  --panel-color: var(--borealis-text) !important;
}}
"""

CONTENT_RULES = """
/* Built-in pages: keep about:blank and new tabs from flashing white. */
@-moz-document url("about:blank"), url-prefix("about:newtab"), url-prefix("about:home"),
               url-prefix("about:privatebrowsing"), url-prefix("about:sessionrestore") {
  :root, body {
    background-color: var(--borealis-page-bg) !important;
    color: var(--borealis-page-fg) !important;
  }
}
"""


def user_chrome():
    return "\n".join([
        f"/* {NAME} for Firefox — generated by gen_firefox.py.",
        " * Needs toolkit.legacyUserProfileCustomizations.stylesheets = true",
        " * (install.sh --firefox sets it). Light values first, dark under the",
        " * media query, so it follows the system like the rest of the theme. */",
        "",
        ":root {",
        block(LIGHT),
        "}",
        "",
        "@media (prefers-color-scheme: dark) {",
        "  :root {",
        block(DARK, 2),
        "  }",
        "}",
        CHROME_RULES,
    ])


def user_content():
    return "\n".join([
        f"/* {NAME} for Firefox' built-in pages — generated by gen_firefox.py. */",
        ":root {",
        f"  --borealis-page-bg: {LIGHT['window']};",
        f"  --borealis-page-fg: {LIGHT['text']};",
        "}",
        "",
        "@media (prefers-color-scheme: dark) {",
        "  :root {",
        f"    --borealis-page-bg: {DARK['window']};",
        f"    --borealis-page-fg: {DARK['text']};",
        "  }",
        "}",
        CONTENT_RULES,
    ])


README = f"""# {NAME} for Firefox

Firefox draws its own title bar by default. For the Borealis pill buttons and
rounded corners, turn that off: right-click an empty spot on the tab strip →
*Customize Toolbar…* → tick **Title Bar** (or set `browser.tabs.inTitlebar` to
`0` in `about:config`).

`install.sh --firefox` copies these into your Firefox profile's `chrome/`
folder, adds one `@import` line to `userChrome.css` / `userContent.css`, and
sets `toolkit.legacyUserProfileCustomizations.stylesheets` to true in
`user.js`. Restart Firefox afterwards.

By hand:

1. `about:support` → Profile Folder → Open Folder
2. create `chrome/` there and copy `{SLUG.lower()}-userChrome.css` and
   `{SLUG.lower()}-userContent.css` into it
3. in `chrome/userChrome.css` add `@import "{SLUG.lower()}-userChrome.css";`
   (same for `userContent.css`)
4. `about:config` → `toolkit.legacyUserProfileCustomizations.stylesheets` → true
5. restart Firefox

To undo, delete the two files and the import lines; `uninstall.sh --remove`
does that for you.
"""


def build(out_root):
    base = os.path.join(out_root, "firefox", SLUG.lower())
    if os.path.exists(base):
        shutil.rmtree(base)
    os.makedirs(base)
    files = {
        f"{SLUG.lower()}-userChrome.css": user_chrome(),
        f"{SLUG.lower()}-userContent.css": user_content(),
        "README.md": README,
    }
    for name, text in files.items():
        with open(os.path.join(base, name), "w") as f:
            f.write(text)
    return base


if __name__ == "__main__":
    print(build(sys.argv[1]))
