#!/usr/bin/env python3
"""Draw what the GRUB menu will look like, without rebooting.

    tools/grub_mock.py [build/share/grub/themes/borealis] -o out.png

Reads theme.txt for the colours and geometry it understands (background,
title, boot_menu box, the selected-item pixmap and the progress bar) and
composes a 1920x1200 preview. GRUB itself is the authority; this is a sketch
that catches the obvious mistakes.
"""
import argparse
import os
import re

from PIL import Image, ImageDraw, ImageFont

ENTRIES = ["Fedora Linux (7.2.4-200.fc44.x86_64) 44 (KDE Plasma)",
           "Fedora Linux (7.1.13-200.fc44.x86_64) 44 (KDE Plasma)",
           "UEFI Firmware Settings"]


def parse(theme):
    text = open(theme).read()
    top = dict(re.findall(r'^([\w-]+):\s*"?([^"\n]+)"?', text, re.M))
    menu = re.search(r"\+ boot_menu \{(.*?)\n\}", text, re.S)
    menu = dict(re.findall(r"(\w+)\s*=\s*\"?([^\"\n]+)\"?", menu.group(1))) if menu else {}
    labels = [dict(re.findall(r"(\w+)\s*=\s*\"?([^\"\n]+)\"?", m))
              for m in re.findall(r"\+ label \{(.*?)\n\}", text, re.S)]
    return top, menu, labels


def pct(value, total):
    value = str(value).strip()
    return int(total * float(value.rstrip("%")) / 100) if value.endswith("%") else int(float(value))


def font(size):
    for f in ("/usr/share/fonts/rsms-inter-fonts/Inter-Regular.ttf",
              "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf"):
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("theme_dir", nargs="?", default="build/share/grub/themes/borealis")
    ap.add_argument("-o", "--output", default="grub-preview.png")
    ap.add_argument("--size", default="1920x1200")
    a = ap.parse_args()
    W, H = (int(x) for x in a.size.split("x"))
    top, menu, labels = parse(os.path.join(a.theme_dir, "theme.txt"))

    img = Image.open(os.path.join(a.theme_dir, top.get("desktop-image", "background.png")))
    img = img.convert("RGB").resize((W, H), Image.LANCZOS)
    d = ImageDraw.Draw(img)

    for lab in labels:
        if lab.get("id") == "__timeout__":
            lab = dict(lab, text=lab.get("text", "").replace("%d", "5"))
        size = int((lab.get("font", "x 20").split() or ["20"])[-1])
        f = font(size)
        y = pct(lab.get("top", 0), H)
        d.text((W / 2, y), lab.get("text", ""), font=f, fill=lab.get("color", "#ffffff"), anchor="ma")

    mleft, mtop = pct(menu.get("left", 0), W), pct(menu.get("top", 0), H)
    mwidth = pct(menu.get("width", "50%"), W)
    ih, isp = int(menu.get("item_height", 40)), int(menu.get("item_spacing", 6))
    pad = int(menu.get("item_padding", 12))
    f = font(int(menu.get("item_font", "x 20").split()[-1]))
    sel = Image.open(os.path.join(a.theme_dir, "select_c.png")).convert("RGBA")
    for i, entry in enumerate(ENTRIES):
        y = mtop + i * (ih + isp)
        if i == 0:      # GRUB highlights the default entry
            bar = Image.new("RGBA", (mwidth, ih), (0, 0, 0, 0))
            bd = ImageDraw.Draw(bar)
            bd.rounded_rectangle([0, 0, mwidth - 1, ih - 1], radius=10,
                                 fill=sel.getpixel((0, 0)), outline=sel.getpixel((0, 0))[:3] + (255,),
                                 width=2)
            img.paste(bar, (mleft, y), bar)
        color = menu.get("selected_item_color" if i == 0 else "item_color", "#ffffff")
        d.text((mleft + pad, y + ih / 2), entry, font=f, fill=color, anchor="lm")

    bar = re.search(r"\+ progress_bar \{(.*?)\n\}", open(os.path.join(a.theme_dir, "theme.txt")).read(), re.S)
    if bar:
        b = dict(re.findall(r"(\w+)\s*=\s*\"?([^\"\n]+)\"?", bar.group(1)))
        x, y = pct(b.get("left", 0), W), pct(b.get("top", 0), H)
        w, h = pct(b.get("width", "30%"), W), int(b.get("height", 6))
        track = Image.open(os.path.join(a.theme_dir, "track_c.png")).convert("RGBA").getpixel((0, 0))
        fill = Image.open(os.path.join(a.theme_dir, "fill_c.png")).convert("RGBA").getpixel((0, 0))
        d.rounded_rectangle([x, y, x + w, y + h], radius=h // 2, fill=track)
        d.rounded_rectangle([x, y, x + int(w * 0.6), y + h], radius=h // 2, fill=fill)

    img.save(a.output)
    print(a.output)


if __name__ == "__main__":
    main()
