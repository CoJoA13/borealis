# Borealis — KDE Store listing kit

Everything needed to publish Borealis on [store.kde.org](https://store.kde.org).
Build the archives with:

```bash
./build.py && tools/package.py      # → dist/*.tar.gz + dist/SHA256SUMS
```

## Suggested listings

Publish the pieces first, then the two Global Themes that depend on them.

| Archive (dist/) | Store category | Title |
|---|---|---|
| `Borealis-plasma-style-*.tar.gz` | Plasma Themes | Borealis |
| `Borealis-color-schemes-*.tar.gz` | Plasma Color Schemes | Borealis Dark & Light |
| `Borealis-Dark-aurorae-*.tar.gz`, `Borealis-Light-aurorae-*.tar.gz` | Plasma Window Decorations | Borealis (Dark / Light) |
| `Borealis-Snow-cursors-*.tar.gz`, `Borealis-Ink-cursors-*.tar.gz` | Cursors | Borealis Snow / Ink |
| `Borealis-icons-*.tar.gz` | Full Icon Themes | Borealis icons (requires Tela) |
| `Borealis-wallpaper-*.tar.gz` | Wallpapers KDE Plasma | Borealis — aurora night & dawn |
| `Borealis-Aurora-animated-wallpaper-*.tar.gz` | Plasma 6 Wallpaper Plugins | Borealis Aurora (animated) |
| `Borealis-sound-theme-*.tar.gz` | System Sounds | Borealis chimes |
| `Borealis-konsole-*.tar.gz` | Konsole Color Schemes | Borealis |
| `Borealis-kate-*.tar.gz` | Kate/KWrite Color Schemes | Borealis |
| `Borealis-plymouth-*.tar.gz` | Plymouth Themes | Borealis boot splash |
| `Borealis-Dark-global-theme-*.tar.gz` | Global Themes (Plasma 6) | Borealis Dark |
| `Borealis-Light-global-theme-*.tar.gz` | Global Themes (Plasma 6) | Borealis Light |

After the component listings exist, add their store IDs to each Global Theme's
`metadata.json` so "Get New…" installs everything in one go:

```json
"X-KPackage-Dependencies": [
    "kns://plasma-themes.knsrc/api.kde-look.org/<id>",
    "kns://colorschemes.knsrc/api.kde-look.org/<id>",
    "kns://aurorae.knsrc/api.kde-look.org/<id>",
    "kns://xcursor.knsrc/api.kde-look.org/<id>",
    "kns://icons.knsrc/api.kde-look.org/<id>",
    "kns://wallpaper.knsrc/api.kde-look.org/<id>"
]
```

Screenshots: `docs/preview-dark.jpg`, `docs/preview-light.jpg`, `docs/switcher-dark.jpg`,
`docs/splash.jpg`, `docs/editor-dark.jpg`, `docs/gtk.jpg` (all rendered from the real theme).

## Description (Global Theme)

**Borealis** — aurora over the mountains for Plasma 6.

A calm, frosted theme in two moods that switch with Plasma's day/night setting:
**Borealis Dark** (ink-navy night) and **Borealis Light** (polar dawn), both with
periwinkle and aurora-teal accents.

- Frosted Plasma Style with 12 px corners, pill-shaped task indicators and an aurora progress bar
- Window decorations with teal · periwinkle · rose pill buttons
- Procedural aurora wallpaper (night + dawn) and an optional **animated** version for desktop and lock screen
- Snow and Ink SVG cursors, gradient folders and matching app icons (on top of Tela)
- Splash screen, soft chime sound theme, Konsole and Kate schemes, GTK4/libadwaita colors
- Readable by design: every text color meets WCAG AA (4.5:1)

Tested on Fedora 44 with Plasma 6.7. Fonts: Inter + JetBrains Mono (optional,
`sudo dnf install rsms-inter-fonts jetbrains-mono-fonts`).

License: GPL-3.0-or-later. Folder shapes derived from the Tela icon theme (GPL-3.0).
