"""Borealis app icons: ink-glass squircles with luminous aurora glyphs.

128x128 canvas; glyphs are bold strokes/fills so they survive 32px.
Only generic apps (no brand logos). Qt-SVG safe: gradients only.
"""

SQUIRCLE = ('<defs>'
            '<linearGradient id="bg" x1="0" y1="6" x2="0" y2="122" gradientUnits="userSpaceOnUse">'
            '<stop offset="0" stop-color="#263058"/><stop offset="1" stop-color="#0f1428"/></linearGradient>'
            '<linearGradient id="g" x1="30" y1="30" x2="98" y2="98" gradientUnits="userSpaceOnUse">'
            '<stop offset="0" stop-color="#5fe0c8"/><stop offset="0.55" stop-color="#8b9cff"/>'
            '<stop offset="1" stop-color="#b18cff"/></linearGradient>'
            '<linearGradient id="shine" x1="0" y1="6" x2="0" y2="64" gradientUnits="userSpaceOnUse">'
            '<stop offset="0" stop-color="#ffffff" stop-opacity="0.10"/>'
            '<stop offset="1" stop-color="#ffffff" stop-opacity="0"/></linearGradient>'
            '</defs>'
            '<rect x="6" y="6" width="116" height="116" rx="30" fill="url(#bg)"/>'
            '<rect x="6" y="6" width="116" height="58" rx="30" fill="url(#shine)"/>'
            '<rect x="7" y="7" width="114" height="114" rx="29" fill="none" stroke="#8b9cff" '
            'stroke-opacity="0.35" stroke-width="2"/>')

S = 'fill="none" stroke="url(#g)" stroke-linecap="round" stroke-linejoin="round"'
SW = 'fill="none" stroke="#f2f4fa" stroke-linecap="round" stroke-linejoin="round"'
F = 'fill="url(#g)"'

GLYPHS = {
    "files": f'<path {F} d="M34 42 a6 6 0 0 1 6 -6 h17 l7 8 h24 a6 6 0 0 1 6 6 v36 a6 6 0 0 1 -6 6 h-48 '
             f'a6 6 0 0 1 -6 -6 z"/>'
             '<path fill="#f2f4fa" fill-opacity="0.22" d="M34 56 h60 v30 a6 6 0 0 1 -6 6 h-48 a6 6 0 0 1 -6 -6 z"/>',
    "terminal": f'<path {S} stroke-width="9" d="M38 46 L56 64 L38 82"/>'
                f'<path {S} stroke-width="9" d="M64 84 H90"/>',
    "settings": f'<path {SW} stroke-opacity="0.35" stroke-width="6" d="M34 44 H94 M34 64 H94 M34 84 H94"/>'
                f'<circle {F} cx="76" cy="44" r="9"/><circle {F} cx="50" cy="64" r="9"/>'
                f'<circle {F} cx="82" cy="84" r="9"/>',
    "software": f'<rect {F} x="36" y="36" width="24" height="24" rx="7"/>'
                f'<rect {F} x="68" y="36" width="24" height="24" rx="7"/>'
                f'<rect {F} x="36" y="68" width="24" height="24" rx="7"/>'
                f'<rect {S} stroke-width="5" x="70.5" y="70.5" width="19" height="19" rx="5.5"/>'
                f'<path {SW} stroke-width="5" d="M80 74 V86 M74 80 H86"/>',
    "editor": f'<rect {S} stroke-width="7" x="40" y="32" width="48" height="64" rx="8"/>'
              f'<path {SW} stroke-opacity="0.75" stroke-width="6" d="M52 50 H76 M52 64 H76 M52 78 H68"/>',
    "trash": f'<path {S} stroke-width="8" d="M38 42 H90"/><path {S} stroke-width="6" d="M56 42 V36 H72 V42"/>'
             f'<path {S} stroke-width="8" d="M44 52 L48 90 a6 6 0 0 0 6 5 h20 a6 6 0 0 0 6 -5 L84 52"/>'
             f'<path {SW} stroke-opacity="0.45" stroke-width="5" d="M58 60 V86 M70 60 V86"/>',
    "trash-full": f'<path fill="url(#g)" fill-opacity="0.35" d="M44 52 L48 90 a6 6 0 0 0 6 5 h20 '
                  f'a6 6 0 0 0 6 -5 L84 52 z"/>'
                  f'<path {S} stroke-width="8" d="M38 42 H90"/><path {S} stroke-width="6" d="M56 42 V36 H72 V42"/>'
                  f'<path {S} stroke-width="8" d="M44 52 L48 90 a6 6 0 0 0 6 5 h20 a6 6 0 0 0 6 -5 L84 52"/>'
                  f'<path {SW} stroke-opacity="0.6" stroke-width="5" d="M58 60 V86 M70 60 V86"/>',
    "screenshot": f'<path {S} stroke-width="7" d="M36 52 V42 a6 6 0 0 1 6 -6 H52 M76 36 H86 a6 6 0 0 1 6 6 '
                  f'V52 M92 76 V86 a6 6 0 0 1 -6 6 H76 M52 92 H42 a6 6 0 0 1 -6 -6 V76"/>'
                  f'<circle {F} cx="64" cy="64" r="11"/>',
    "images": f'<rect {S} stroke-width="7" x="34" y="38" width="60" height="52" rx="9"/>'
              f'<path {F} d="M40 84 L56 64 L67 76 L75 68 L88 84 z"/>'
              '<circle fill="#f2f4fa" fill-opacity="0.85" cx="76" cy="54" r="6"/>',
    "documents": f'<path {S} stroke-width="7" d="M42 94 V40 a6 6 0 0 1 6 -6 H72 L86 48 V62"/>'
                 f'<circle {S} stroke-width="7" cx="72" cy="74" r="12"/>'
                 f'<path {S} stroke-width="8" d="M81 83 L92 94"/>',
    "calculator": f'<rect {S} stroke-width="6" x="40" y="30" width="48" height="68" rx="9"/>'
                  f'<rect {F} x="48" y="39" width="32" height="13" rx="3"/>'
                  + "".join(f'<circle fill="#f2f4fa" fill-opacity="0.8" cx="{x}" cy="{y}" r="4"/>'
                            for y in (64, 76, 88) for x in (53, 64, 75)),
    "monitor": f'<path {S} stroke-width="7" d="M30 68 H46 L55 48 L68 86 L77 60 L83 68 H98"/>',
    "archive": f'<rect {F} x="32" y="36" width="64" height="14" rx="5"/>'
               f'<path {S} stroke-width="7" d="M38 54 V86 a6 6 0 0 0 6 6 H84 a6 6 0 0 0 6 -6 V54"/>'
               f'<path {SW} stroke-opacity="0.75" stroke-width="5" stroke-dasharray="4 4" d="M64 52 V74"/>'
               '<rect fill="#f2f4fa" fill-opacity="0.85" x="59" y="74" width="10" height="9" rx="2.5"/>',
    "music": f'<path {S} stroke-width="7" d="M76 82 V36 C 86 38, 94 44, 92 58"/>'
             f'<ellipse {F} cx="63" cy="82" rx="14" ry="11"/>',
    "video": f'<rect fill="url(#g)" fill-opacity="0.22" x="32" y="40" width="64" height="48" rx="10"/>'
             f'<rect {S} stroke-width="7" x="32" y="40" width="64" height="48" rx="10"/>'
             '<path fill="#f2f4fa" d="M57 52 L79 64 L57 76 z"/>',
    "info": f'<circle {S} stroke-width="7" cx="64" cy="64" r="28"/>'
            '<circle fill="#f2f4fa" cx="64" cy="50" r="5"/>'
            f'<path {SW} stroke-width="8" d="M64 62 V80"/>',
    "disk": f'<circle {S} stroke-width="13" cx="64" cy="64" r="24"/>'
            '<path fill="none" stroke="#f2f4fa" stroke-opacity="0.75" stroke-width="13" '
            'd="M64 40 A24 24 0 0 1 86.5 56"/>',
    "phone": f'<rect {S} stroke-width="7" x="46" y="32" width="36" height="64" rx="9"/>'
             f'<path {SW} stroke-opacity="0.75" stroke-width="5" d="M58 42 H70"/>'
             f'<circle {F} cx="64" cy="84" r="4.5"/>',
    "search": f'<circle {S} stroke-width="9" cx="58" cy="58" r="19"/>'
              f'<path {S} stroke-width="11" d="M73 73 L90 90"/>',
}

# glyph -> icon names it answers to (desktop Icon= values + generic names)
NAMES = {
    "files": ["org.kde.dolphin", "system-file-manager", "dolphin"],
    "terminal": ["utilities-terminal", "org.kde.konsole", "konsole", "terminal"],
    "settings": ["preferences-system", "systemsettings", "org.kde.systemsettings"],
    "software": ["plasmadiscover", "org.kde.discover", "system-software-install"],
    "editor": ["kwrite", "org.kde.kwrite", "kate", "org.kde.kate", "accessories-text-editor",
               "text-editor"],
    "trash": ["user-trash", "trashcan_empty"],
    "trash-full": ["user-trash-full", "trashcan_full"],
    "screenshot": ["spectacle", "org.kde.spectacle", "applets-screenshooter", "accessories-screenshot"],
    "images": ["gwenview", "org.kde.gwenview"],
    "documents": ["okular", "org.kde.okular"],
    "calculator": ["accessories-calculator", "org.kde.kcalc", "kcalc"],
    "monitor": ["utilities-system-monitor", "org.kde.plasma-systemmonitor", "ksysguard",
                "org.kde.ksysguard"],
    "archive": ["ark", "org.kde.ark", "utilities-file-archiver"],
    "music": ["elisa", "org.kde.elisa"],
    "video": ["dragonplayer", "org.kde.dragonplayer", "haruna", "org.kde.haruna"],
    "info": ["hwinfo", "org.kde.kinfocenter"],
    "disk": ["filelight", "org.kde.filelight", "org.gnome.baobab", "baobab"],
    "phone": ["kdeconnect", "org.kde.kdeconnect.app"],
    "search": ["kfind", "org.kde.kfind"],
}


def icon_svg(glyph):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128">'
            f'{SQUIRCLE}{GLYPHS[glyph]}</svg>')
