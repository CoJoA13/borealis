"""Borealis boot splash: a Plymouth 'two-step' theme.

Ink-navy gradient, the Borealis badge + wordmark in the centre (drawn as the
'watermark'), an aurora spinner below it, and matching password-prompt art.
Installed system-wide by install-system.sh (needs root + an initramfs rebuild).
"""
import math
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(__file__))
from render import svg_to_image  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FRAMES = 60          # two-step spreads all throbber frames over a fixed 2 s loop
SPIN = ["#5fe0c8", "#6fcfe0", "#8b9cff", "#9e92ff", "#b18cff"]


def lerp(stops, t):
    t = max(0.0, min(1.0, t)) * (len(stops) - 1)
    i = min(int(t), len(stops) - 2)
    f = t - i
    a = [int(stops[i][k:k + 2], 16) for k in (1, 3, 5)]
    b = [int(stops[i + 1][k:k + 2], 16) for k in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * f) for x, y in zip(a, b))


def spinner_svg(phase, size=40, width=3.6):
    c, r = size / 2, size / 2 - width
    parts = [f'<circle cx="{c}" cy="{c}" r="{r}" fill="none" stroke="#232b40" stroke-width="{width}"/>']
    segs, sweep = 16, 280
    start = -90 + phase * 360
    for i in range(segs):
        a0 = math.radians(start + i * sweep / segs)
        a1 = math.radians(start + (i + 1) * sweep / segs + 0.7)
        op = 0.25 + 0.75 * (i / (segs - 1))
        cap = "round" if i == segs - 1 else "butt"
        parts.append(f'<path d="M{c + r * math.cos(a0):.3f} {c + r * math.sin(a0):.3f} '
                     f'A{r} {r} 0 0 1 {c + r * math.cos(a1):.3f} {c + r * math.sin(a1):.3f}" fill="none" '
                     f'stroke="{lerp(SPIN, i / (segs - 1))}" stroke-opacity="{op:.2f}" '
                     f'stroke-width="{width}" stroke-linecap="{cap}"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
            f'viewBox="0 0 {size} {size}">{"".join(parts)}</svg>')


def watermark_svg():
    """Badge + letter-spaced wordmark, 300x190."""
    logo = open(os.path.join(HERE, "assets", "logo.svg")).read()
    inner = logo[logo.index(">") + 1:logo.rindex("</svg>")]
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="300" height="190" viewBox="0 0 300 190">'
            f'<g transform="translate(102 0) scale(1.5)">{inner}</g>'
            '<text x="150" y="176" text-anchor="middle" fill="#e6e9f2" '
            'font-family="Noto Sans, Cantarell, sans-serif" font-weight="300" font-size="30" '
            'letter-spacing="9">Borealis</text></svg>')


def simple(w, h, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}">{body}</svg>')


FIELD = 'fill="#161b27" stroke="#3a4258" stroke-width="1"'
LOCK_W, ENTRY_W, FIELD_H, FR = 48, 272, 40, 11

# two-step draws lock.png flush against the left of entry.png, so the lock is
# drawn as the rounded left cap of one input field and entry.png as the rest
ART = {
    "lock.png": (LOCK_W, FIELD_H,
                 f'<path d="M{LOCK_W} 0.5 H{FR + 0.5} A{FR} {FR} 0 0 0 0.5 {FR + 0.5} V{FIELD_H - FR - 0.5} '
                 f'A{FR} {FR} 0 0 0 {FR + 0.5} {FIELD_H - 0.5} H{LOCK_W}" {FIELD}/>'
                 '<g transform="translate(15 10)">'
                 '<path d="M5 9 V6.5 a4 4 0 0 1 8 0 V9" fill="none" stroke="#8b9cff" '
                 'stroke-width="2" stroke-linecap="round"/>'
                 '<rect x="2" y="9" width="14" height="11" rx="3" fill="#8b9cff"/>'
                 '<circle cx="9" cy="14.5" r="1.6" fill="#0b0f19"/></g>'),
    "entry.png": (ENTRY_W, FIELD_H,
                  f'<path d="M0 0.5 H{ENTRY_W - FR - 0.5} A{FR} {FR} 0 0 1 {ENTRY_W - 0.5} {FR + 0.5} '
                  f'V{FIELD_H - FR - 0.5} A{FR} {FR} 0 0 1 {ENTRY_W - FR - 0.5} {FIELD_H - 0.5} H0" {FIELD}/>'),
    "bullet.png": (12, 12, '<circle cx="6" cy="6" r="4" fill="#e6e9f2"/>'),
    "capslock.png": (24, 24, '<path d="M12 4 L20 13 H15.5 V17 H8.5 V13 H4 Z" fill="none" stroke="#ffc46b" '
                             'stroke-width="2" stroke-linejoin="round"/>'
                             '<rect x="8.5" y="19" width="7" height="2.2" rx="1.1" fill="#ffc46b"/>'),
    "keyboard.png": (28, 20, '<rect x="1" y="2" width="26" height="16" rx="4" fill="none" stroke="#8f97ab" '
                             'stroke-width="2"/>'
                             + "".join(f'<rect x="{5 + 4.5 * i}" y="6.5" width="2.5" height="2.5" rx="0.6" '
                                       f'fill="#8f97ab"/>' for i in range(5))
                             + '<rect x="8" y="12" width="12" height="2.5" rx="1" fill="#8f97ab"/>'),
}


def plymouth_file(imagedir):
    return f"""[Plymouth Theme]
Name=Borealis
Description=Aurora boot splash from the Borealis KDE theme
ModuleName=two-step

[two-step]
Font=Noto Sans 12
TitleFont=Noto Sans 24
ImageDir={imagedir}
DialogHorizontalAlignment=.5
DialogVerticalAlignment=.62
TitleHorizontalAlignment=.5
TitleVerticalAlignment=.24
HorizontalAlignment=.5
VerticalAlignment=.61
WatermarkHorizontalAlignment=.5
WatermarkVerticalAlignment=.42
Transition=none
TransitionDuration=0.0
BackgroundStartColor=0x0b0f19
BackgroundEndColor=0x111a2e
ProgressBarBackgroundColor=0x2a3246
ProgressBarForegroundColor=0x8b9cff
MessageBelowAnimation=true
ShowAnimationPercent=1.0

[boot-up]
UseEndAnimation=false

[shutdown]
UseEndAnimation=false

[reboot]
UseEndAnimation=false

[updates]
SuppressMessages=true
ProgressBarShowPercentComplete=true
UseProgressBar=true
Title=Installing updates…
SubTitle=Please keep your computer on

[system-upgrade]
SuppressMessages=true
ProgressBarShowPercentComplete=true
UseProgressBar=true
Title=Upgrading the system…
SubTitle=Please keep your computer on

[firmware-upgrade]
SuppressMessages=true
ProgressBarShowPercentComplete=true
UseProgressBar=true
Title=Upgrading firmware…
SubTitle=Please keep your computer on

[system-reset]
SuppressMessages=true
ProgressBarShowPercentComplete=true
UseProgressBar=true
Title=Resetting the system…
SubTitle=Please keep your computer on
"""


def build(out_root):
    base = os.path.join(out_root, "plymouth", "themes", "borealis")
    if os.path.exists(base):
        shutil.rmtree(base)
    os.makedirs(base)
    for i in range(FRAMES):
        svg_to_image(spinner_svg(i / FRAMES), 40, 40).save(os.path.join(base, f"throbber-{i + 1:04d}.png"))
    svg_to_image(watermark_svg(), 300, 190).save(os.path.join(base, "watermark.png"))
    for name, (w, h, body) in ART.items():
        svg_to_image(simple(w, h, body), w, h).save(os.path.join(base, name))
    with open(os.path.join(base, "borealis.plymouth"), "w") as f:
        f.write(plymouth_file("/usr/share/plymouth/themes/borealis"))
    return base


if __name__ == "__main__":
    print(build(sys.argv[1]))
