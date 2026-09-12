"""Borealis for the command line: bat, tmux, git diffs, LS_COLORS, prompt, fzf.

Everything comes from the same palette as the Konsole schemes, so a terminal
running Borealis looks like one piece whatever it prints. Installed by
`install.sh --terminal` into ~/.config/borealis/terminal.
"""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(__file__))
from gen_apps import TERM, ansi_colors  # noqa: E402
from tokens import DARK, LIGHT, ensure_contrast, mix  # noqa: E402

VARIANTS = {"dark": DARK, "light": LIGHT}


def pal(vid):
    """Named colours for one variant: the ANSI ramp plus a few surfaces."""
    a = ansi_colors(vid)
    t = TERM[vid]
    p = VARIANTS[vid]
    return {
        "bg": t["bg"], "fg": t["fg"], "fg_bright": t["fg_intense"],
        "black": a[0][0], "red": a[1][0], "green": a[2][0], "yellow": a[3][0],
        "blue": a[4][0], "magenta": a[5][0], "cyan": a[6][0], "white": a[7][0],
        "bred": a[1][1], "bgreen": a[2][1], "byellow": a[3][1], "bblue": a[4][1],
        "bmagenta": a[5][1], "bcyan": a[6][1], "bwhite": a[7][1],
        "dim": ensure_contrast(mix(t["fg"], t["bg"], 0.45), t["bg"], 3.0),
        "line": mix(t["bg"], t["fg"], 0.14),
        "sel": mix(t["bg"], p["accent"], 0.30),
        "accent": ensure_contrast(p["accent"], t["bg"]),
    }


# ----------------------------------------------------------------- bat -----
# bat reads Sublime .tmTheme files from its config dir (`bat cache --build`).
def tm_settings(**kw):
    items = "".join(f"\t\t\t\t<key>{k}</key>\n\t\t\t\t<string>{v}</string>\n" for k, v in kw.items() if v)
    return "\t\t\t<dict>\n" + items + "\t\t\t</dict>\n"


def tm_rule(name, scope, fg=None, font=None):
    body = f"\t\t\t<key>name</key>\n\t\t\t<string>{name}</string>\n" \
           f"\t\t\t<key>scope</key>\n\t\t\t<string>{scope}</string>\n" \
           "\t\t\t<key>settings</key>\n" + tm_settings(foreground=fg, fontStyle=font)
    return "\t\t<dict>\n" + body + "\t\t</dict>\n"


def bat_theme(vid, name):
    c = pal(vid)
    rules = [
        "\t\t<dict>\n\t\t\t<key>settings</key>\n"
        + tm_settings(background=c["bg"], foreground=c["fg"], caret=c["accent"],
                      selection=c["sel"], lineHighlight=c["line"], invisibles=c["dim"])
        + "\t\t</dict>\n",
        tm_rule("Comment", "comment, punctuation.definition.comment", c["dim"], "italic"),
        tm_rule("String", "string, punctuation.definition.string, constant.other.symbol", c["green"]),
        tm_rule("Number", "constant.numeric, constant.language", c["byellow"]),
        tm_rule("Constant", "constant, support.constant", c["byellow"]),
        tm_rule("Keyword", "keyword, storage.type, storage.modifier", c["magenta"]),
        tm_rule("Operator", "keyword.operator, punctuation.separator, punctuation.section", c["fg"]),
        tm_rule("Function", "entity.name.function, support.function", c["blue"]),
        tm_rule("Class", "entity.name.class, entity.name.type, support.class", c["cyan"]),
        tm_rule("Variable", "variable, variable.parameter", c["red"]),
        tm_rule("Tag", "entity.name.tag", c["magenta"]),
        tm_rule("Attribute", "entity.other.attribute-name", c["byellow"]),
        tm_rule("Preprocessor", "meta.preprocessor, keyword.control.import", c["yellow"]),
        tm_rule("Heading", "markup.heading", c["accent"], "bold"),
        tm_rule("Link", "markup.underline.link", c["cyan"], "underline"),
        tm_rule("Inserted", "markup.inserted", c["green"]),
        tm_rule("Deleted", "markup.deleted", c["red"]),
        tm_rule("Changed", "markup.changed", c["byellow"]),
        tm_rule("Invalid", "invalid", c["bred"], "bold"),
    ]
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
            '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
            '<plist version="1.0">\n<dict>\n'
            f'\t<key>name</key>\n\t<string>{name}</string>\n'
            '\t<key>settings</key>\n\t<array>\n' + "".join(rules) + '\t</array>\n'
            f'\t<key>uuid</key>\n\t<string>a0b1e9{"1" if vid == "dark" else "2"}'
            '-0000-4000-8000-b0realis0000</string>\n'
            '\t<key>colorSpaceName</key>\n\t<string>sRGB</string>\n'
            '</dict>\n</plist>\n')


# ---------------------------------------------------------------- tmux -----
def tmux_conf(vid):
    c = pal(vid)
    return f"""# Borealis for tmux ({vid}) — source it from ~/.tmux.conf:
#   source-file ~/.config/borealis/terminal/tmux-{vid}.conf
set -g status-style "bg={c['line']},fg={c['fg']}"
set -g status-left "#[bg={c['accent']},fg={c['bg']},bold] #S #[bg={c['line']},fg={c['accent']}]"
set -g status-left-length 24
set -g status-right "#[fg={c['dim']}]#h #[fg={c['accent']}]%H:%M "
set -g window-status-format " #I #W "
set -g window-status-current-format "#[bg={c['sel']},fg={c['bwhite']},bold] #I #W "
set -g window-status-activity-style "fg={c['byellow']}"
set -g pane-border-style "fg={c['line']}"
set -g pane-active-border-style "fg={c['accent']}"
set -g message-style "bg={c['sel']},fg={c['bwhite']}"
set -g mode-style "bg={c['sel']},fg={c['bwhite']}"
set -g display-panes-colour "{c['dim']}"
set -g display-panes-active-colour "{c['accent']}"
set -g clock-mode-colour "{c['cyan']}"
"""


# ----------------------------------------------------------- LS_COLORS -----
# 256-colour codes keep this readable in any terminal, not just Konsole.
def rgb256(hex_color):
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return f"38;2;{r};{g};{b}"


def dircolors(vid):
    c = pal(vid)
    rows = [
        ("NORMAL", c["fg"], False), ("FILE", c["fg"], False), ("RESET", c["fg"], False),
        ("DIR", c["blue"], True), ("LINK", c["cyan"], False), ("FIFO", c["yellow"], False),
        ("SOCK", c["magenta"], False), ("EXEC", c["green"], True), ("ORPHAN", c["red"], True),
        ("SETUID", c["bred"], True), ("SETGID", c["bred"], True), ("STICKY", c["blue"], True),
    ]
    out = [f"# Borealis LS_COLORS ({vid}) — eval \"$(dircolors -b "
           f"~/.config/borealis/terminal/dircolors-{vid})\""]
    out += [f"{k} {'01;' if bold else ''}{rgb256(v)}" for k, v, bold in rows]
    groups = [
        (c["magenta"], (".tar .tgz .zip .gz .xz .zst .bz2 .7z .rar .deb .rpm .flatpak")),
        (c["byellow"], ".jpg .jpeg .png .gif .bmp .svg .webp .tif .ico .heic"),
        (c["cyan"], ".mp3 .flac .ogg .oga .wav .opus .m4a .mp4 .mkv .webm .mov .avi"),
        (c["green"], ".py .sh .bash .zsh .fish .rb .js .ts .go .rs .c .h .cpp .qml .frag"),
        (c["dim"], ".log .bak .old .tmp .swp .pyc .o .lock"),
        (c["blue"], ".md .rst .txt .pdf .odt .docx .json .yaml .yml .toml .ini .conf"),
    ]
    for color, exts in groups:
        out += [f"{e} {rgb256(color)}" for e in exts.split()]
    return "\n".join(out) + "\n"


# ----------------------------------------------------------------- git -----
def gitconfig(vid):
    c = pal(vid)
    return f"""# Borealis colours for git ({vid}) — use it with:
#   git config --global include.path ~/.config/borealis/terminal/git-{vid}.conf
[color]
\tui = auto
[color "diff"]
\tmeta = "{c['dim']}"
\tfrag = "{c['magenta']}"
\tfunc = "{c['blue']}"
\told = "{c['red']}"
\tnew = "{c['green']}"
\tcommit = "{c['byellow']}"
\twhitespace = "reverse {c['red']}"
[color "status"]
\theader = "{c['dim']}"
\tadded = "{c['green']}"
\tchanged = "{c['byellow']}"
\tuntracked = "{c['red']}"
\tbranch = "{c['accent']} bold"
[color "branch"]
\tcurrent = "{c['accent']} bold"
\tlocal = "{c['fg']}"
\tremote = "{c['cyan']}"
[color "decorate"]
\tbranch = "{c['accent']} bold"
\tremoteBranch = "{c['cyan']}"
\ttag = "{c['byellow']}"
\tHEAD = "{c['magenta']} bold"
"""


# ---------------------------------------------------------------- bash -----
def bash_snippet(vid):
    c = pal(vid)
    fzf = (f"--color=bg+:{c['sel']},fg+:{c['bwhite']},hl:{c['accent']},hl+:{c['bcyan']},"
           f"info:{c['dim']},prompt:{c['accent']},pointer:{c['bcyan']},marker:{c['green']},"
           f"border:{c['line']},header:{c['dim']}")
    return f"""# Borealis for bash ({vid}) — add to ~/.bashrc:
#   source ~/.config/borealis/terminal/borealis-{vid}.bash
[ -r ~/.config/borealis/terminal/dircolors-{vid} ] && \\
    eval "$(dircolors -b ~/.config/borealis/terminal/dircolors-{vid})"
alias ls='ls --color=auto'
alias grep='grep --color=auto'
export BAT_THEME='Borealis {vid.capitalize()}'
export FZF_DEFAULT_OPTS="${{FZF_DEFAULT_OPTS:-}} {fzf}"
# man pages in Borealis colours
export LESS_TERMCAP_md=$'\\e[1;35m' LESS_TERMCAP_us=$'\\e[4;36m' \\
       LESS_TERMCAP_so=$'\\e[1;44;97m' LESS_TERMCAP_se=$'\\e[0m' \\
       LESS_TERMCAP_ue=$'\\e[0m' LESS_TERMCAP_me=$'\\e[0m'

# Prompt: user@host, path, git branch, and a red mark when a command fails.
__borealis_git() {{
    local b
    b=$(GIT_OPTIONAL_LOCKS=0 git symbolic-ref --short HEAD 2>/dev/null) || return
    local dirty=""
    GIT_OPTIONAL_LOCKS=0 git diff --quiet --ignore-submodules HEAD 2>/dev/null || dirty="*"
    printf ' \\001\\e[38;5;245m\\002on \\001\\e[1;35m\\002%s%s' "$b" "$dirty"
}}
__borealis_ps1() {{
    local rc=$?
    local mark='\\[\\e[1;36m\\]❯'
    [ $rc -ne 0 ] && mark='\\[\\e[1;31m\\]❯'
    PS1="\\[\\e[1;34m\\]\\u@\\h \\[\\e[1;36m\\]\\w\\[\\e[0m\\]$(__borealis_git)\\[\\e[0m\\]\\n$mark \\[\\e[0m\\]"
}}
PROMPT_COMMAND=__borealis_ps1
"""


def build(out_root):
    base = os.path.join(out_root, "terminal", "borealis")
    if os.path.exists(base):
        shutil.rmtree(base)
    os.makedirs(base)
    for vid in ("dark", "light"):
        name = f"Borealis {vid.capitalize()}"
        files = {
            f"Borealis {vid.capitalize()}.tmTheme": bat_theme(vid, name),
            f"tmux-{vid}.conf": tmux_conf(vid),
            f"dircolors-{vid}": dircolors(vid),
            f"git-{vid}.conf": gitconfig(vid),
            f"borealis-{vid}.bash": bash_snippet(vid),
        }
        for fn, text in files.items():
            with open(os.path.join(base, fn), "w") as f:
                f.write(text)
    with open(os.path.join(base, "README.md"), "w") as f:
        f.write(README)
    return base


README = """# Borealis on the command line

`install.sh --terminal` copies these into `~/.config/borealis/terminal`, adds the
bat themes, and sources the bash file from `~/.bashrc` (backed up first).

| File | What it is | Use it by hand |
|---|---|---|
| `Borealis Dark.tmTheme` | bat / syntect syntax theme | `mkdir -p ~/.config/bat/themes && cp *.tmTheme ~/.config/bat/themes/ && bat cache --build`, then `export BAT_THEME='Borealis Dark'` |
| `tmux-dark.conf` | tmux status bar and panes | `source-file ~/.config/borealis/terminal/tmux-dark.conf` in `~/.tmux.conf` |
| `dircolors-dark` | `ls` colours | `eval "$(dircolors -b ~/.config/borealis/terminal/dircolors-dark)"` |
| `git-dark.conf` | git diff/status/branch colours | `git config --global include.path ~/.config/borealis/terminal/git-dark.conf` |
| `borealis-dark.bash` | prompt, `LS_COLORS`, `BAT_THEME`, fzf and man-page colours | `source ~/.config/borealis/terminal/borealis-dark.bash` in `~/.bashrc` |

Each file exists in a `-light` version too. The colours are the Konsole scheme's,
so everything matches the terminal you're already in.
"""

if __name__ == "__main__":
    print(build(sys.argv[1]))
