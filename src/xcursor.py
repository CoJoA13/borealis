#!/usr/bin/env python3
"""
xcursor_writer.py - render SVG cursors and write / read X11 Xcursor files.

No xcursorgen, no numpy.  Needs: pycairo + PyGObject with Rsvg 2.0 (librsvg).
Optional: libXcursor.so.1 (only for the independent validation in `check`/`selftest`).

XCURSOR FILE FORMAT (as read by libXcursor file.c and wayland-cursor xcursor.c).
Every integer is a CARD32 stored LITTLE-ENDIAN.

  File header (16 bytes)
    magic    'Xcur'  (bytes 58 63 75 72; == 0x72756358 read as LE uint32)
    header   16      (bytes in file header; readers skip header-16 extra bytes)
    version  0x00010000
    ntoc     number of TOC entries (libXcursor rejects > 0x10000)

  TOC, ntoc x 12 bytes, immediately after the header
    type      0xfffd0002 = image chunk | 0xfffe0001 = comment chunk
    subtype   image: NOMINAL SIZE (e.g. 24)  | comment: 1 copyright, 2 license, 3 other
    position  absolute byte offset of the chunk from start of file

  Image chunk
    header   36      (16 generic chunk-header bytes + 20 image bytes)
    type     0xfffd0002   (must equal TOC type)
    subtype  nominal size (must equal TOC subtype)
    version  1
    width    1..0x7fff
    height   1..0x7fff
    xhot     0..width     (libXcursor rejects xhot > width)
    yhot     0..height
    delay    milliseconds until next frame (animated cursors); ignored for 1 frame
    pixels   width*height CARD32, row-major from top-left, value 0xAARRGGBB with
             PREMULTIPLIED alpha (so LE bytes in memory are B, G, R, A).
             == cairo FORMAT_ARGB32 memory layout on little-endian hosts.

  Comment chunk
    header 20, type 0xfffe0001, subtype 1|2|3, version 1, length, then `length` UTF-8 bytes.

  Animation: several image chunks with the SAME subtype (nominal size); frames play in TOC
  order.  Size selection: the reader picks the nominal size closest to the requested
  XCURSOR_SIZE / cursor size and loads every image chunk with that subtype.

SIZE / HOTSPOT CONVENTION (mirrors KWin's SvgCursorReader and Breeze's own xcursors):
  metadata.json nominal_size N0 describes the SVG canvas (e.g. Breeze: 32x32 canvas, N0=24).
  For a target nominal size N:  scale = N / N0
     image  = round(svg_w*scale) x round(svg_h*scale)   (Breeze: 24 -> 32x32, 48 -> 64x64)
     hotspot = floor(hotspot_svg * scale)              (Breeze xcursors truncate; KWin rounds)
"""
from __future__ import annotations

import argparse
import ctypes
import ctypes.util
import json
import math
import os
import struct
import sys
from array import array
from dataclasses import dataclass, field

XCURSOR_MAGIC = b"Xcur"
XCURSOR_FILE_VERSION = 0x00010000
XCURSOR_FILE_HEADER_LEN = 16
XCURSOR_TOC_LEN = 12
XCURSOR_IMAGE_TYPE = 0xFFFD0002
XCURSOR_IMAGE_VERSION = 1
XCURSOR_IMAGE_HEADER_LEN = 36
XCURSOR_IMAGE_MAX_SIZE = 0x7FFF
XCURSOR_COMMENT_TYPE = 0xFFFE0001
XCURSOR_COMMENT_VERSION = 1
XCURSOR_COMMENT_HEADER_LEN = 20
COMMENT_COPYRIGHT, COMMENT_LICENSE, COMMENT_OTHER = 1, 2, 3

DEFAULT_SIZES = (24, 32, 48, 64, 72, 96)


@dataclass
class XcursorImage:
    size: int            # nominal size (TOC subtype)
    width: int
    height: int
    xhot: int
    yhot: int
    delay: int           # ms
    pixels: bytes        # width*height*4 bytes: little-endian premultiplied ARGB32 (B,G,R,A)

    def __post_init__(self):
        if not (1 <= self.width <= XCURSOR_IMAGE_MAX_SIZE and 1 <= self.height <= XCURSOR_IMAGE_MAX_SIZE):
            raise ValueError(f"bad image size {self.width}x{self.height}")
        if not (0 <= self.xhot <= self.width and 0 <= self.yhot <= self.height):
            raise ValueError(f"hotspot ({self.xhot},{self.yhot}) outside {self.width}x{self.height}")
        if len(self.pixels) != self.width * self.height * 4:
            raise ValueError("pixel buffer length != width*height*4")


@dataclass
class XcursorComment:
    subtype: int
    text: str


@dataclass
class XcursorFile:
    version: int
    images: list = field(default_factory=list)
    comments: list = field(default_factory=list)


# --------------------------------------------------------------------------------------------
# writing / reading
# --------------------------------------------------------------------------------------------
def write_xcursor(path: str, images: list[XcursorImage], comments: list[XcursorComment] = ()) -> None:
    """Write an Xcursor file. Order of `images` is preserved (= animation order per size)."""
    if not images:
        raise ValueError("need at least one image")
    chunks = []  # (type, subtype, bytes)
    for c in comments:
        data = c.text.encode("utf-8")
        chunks.append((XCURSOR_COMMENT_TYPE, c.subtype,
                       struct.pack("<5I", XCURSOR_COMMENT_HEADER_LEN, XCURSOR_COMMENT_TYPE, c.subtype,
                                   XCURSOR_COMMENT_VERSION, len(data)) + data))
    for im in images:
        hdr = struct.pack("<9I", XCURSOR_IMAGE_HEADER_LEN, XCURSOR_IMAGE_TYPE, im.size, XCURSOR_IMAGE_VERSION,
                          im.width, im.height, im.xhot, im.yhot, im.delay)
        chunks.append((XCURSOR_IMAGE_TYPE, im.size, hdr + im.pixels))
    ntoc = len(chunks)
    pos = XCURSOR_FILE_HEADER_LEN + ntoc * XCURSOR_TOC_LEN
    out = bytearray(struct.pack("<4sIII", XCURSOR_MAGIC, XCURSOR_FILE_HEADER_LEN, XCURSOR_FILE_VERSION, ntoc))
    for typ, sub, blob in chunks:
        out += struct.pack("<3I", typ, sub, pos)
        pos += len(blob)
    for _, _, blob in chunks:
        out += blob
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(out)
    os.replace(tmp, path)


def read_xcursor(path: str) -> XcursorFile:
    """Parse + validate like libXcursor (raises ValueError on anything libXcursor would reject)."""
    b = open(path, "rb").read()
    if len(b) < 16:
        raise ValueError("file too short")
    magic, header, version, ntoc = struct.unpack_from("<4sIII", b, 0)
    if magic != XCURSOR_MAGIC:
        raise ValueError(f"bad magic {magic!r}")
    if header < XCURSOR_FILE_HEADER_LEN:
        raise ValueError("file header too short")
    if ntoc > 0x10000:
        raise ValueError("ntoc too large")
    res = XcursorFile(version=version)
    for i in range(ntoc):
        typ, sub, pos = struct.unpack_from("<3I", b, header + i * XCURSOR_TOC_LEN)
        chdr, ctyp, csub, cver = struct.unpack_from("<4I", b, pos)
        if ctyp != typ or csub != sub:
            raise ValueError(f"TOC entry {i}: chunk type/subtype mismatch")
        if typ == XCURSOR_IMAGE_TYPE:
            if chdr < XCURSOR_IMAGE_HEADER_LEN:
                raise ValueError("image chunk header too short")
            w, h, xh, yh, delay = struct.unpack_from("<5I", b, pos + 16)
            start = pos + chdr
            pix = b[start:start + w * h * 4]
            if len(pix) != w * h * 4:
                raise ValueError("truncated pixel data")
            res.images.append(XcursorImage(sub, w, h, xh, yh, delay, bytes(pix)))
        elif typ == XCURSOR_COMMENT_TYPE:
            (length,) = struct.unpack_from("<I", b, pos + 16)
            start = pos + chdr
            res.comments.append(XcursorComment(sub, b[start:start + length].decode("utf-8", "replace")))
    return res


def best_size(xc: XcursorFile, requested: int) -> int:
    """libXcursor _XcursorFindBestSize: nominal size with the smallest |size-requested| (first wins)."""
    best, bestd = 0, None
    for im in xc.images:
        d = abs(im.size - requested)
        if bestd is None or d < bestd:
            best, bestd = im.size, d
    return best


# --------------------------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------------------------
def _rsvg():
    import gi
    gi.require_version("Rsvg", "2.0")
    from gi.repository import Rsvg
    return Rsvg


def svg_intrinsic_size(svg_path: str) -> tuple[float, float]:
    Rsvg = _rsvg()
    h = Rsvg.Handle.new_from_file(svg_path)
    ok, w, hh = h.get_intrinsic_size_in_pixels()
    if ok and w > 0 and hh > 0:
        return float(w), float(hh)
    has_w, _w, has_h, _h, has_vb, vb = h.get_intrinsic_dimensions()
    if has_vb:
        return float(vb.width), float(vb.height)
    raise ValueError(f"{svg_path}: no width/height and no viewBox")


def render_svg_surface(svg_path: str, width: int, height: int):
    """Render the whole SVG document scaled (non-uniformly if needed) into a width x height
    cairo ARGB32 (premultiplied) surface."""
    import cairo
    Rsvg = _rsvg()
    iw, ih = svg_intrinsic_size(svg_path)
    handle = Rsvg.Handle.new_from_file(svg_path)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    ctx = cairo.Context(surf)
    ctx.scale(width / iw, height / ih)
    vp = Rsvg.Rectangle()
    vp.x, vp.y, vp.width, vp.height = 0, 0, iw, ih
    handle.render_document(ctx, vp)
    surf.flush()
    return surf


def surface_to_xcursor_pixels(surf) -> bytes:
    """cairo ARGB32 (native-endian premultiplied) -> Xcursor pixel bytes (LE premultiplied ARGB)."""
    w, h, stride = surf.get_width(), surf.get_height(), surf.get_stride()
    data = bytes(surf.get_data())
    rows = b"".join(data[y * stride:y * stride + w * 4] for y in range(h))
    if sys.byteorder == "big":  # cairo is native-endian; Xcursor is little-endian
        a = array("I", rows)
        a.byteswap()
        rows = a.tobytes()
    return rows


def png_to_xcursor_pixels(png_path: str) -> tuple[int, int, bytes]:
    """Load a PNG (straight alpha) via cairo, which premultiplies for us."""
    import cairo
    surf = cairo.ImageSurface.create_from_png(png_path)
    if surf.get_format() != cairo.FORMAT_ARGB32:
        s2 = cairo.ImageSurface(cairo.FORMAT_ARGB32, surf.get_width(), surf.get_height())
        c = cairo.Context(s2)
        c.set_source_surface(surf)
        c.paint()
        surf = s2
    return surf.get_width(), surf.get_height(), surface_to_xcursor_pixels(surf)


def xcursor_image_to_png(im: XcursorImage, png_path: str) -> None:
    import cairo
    px = im.pixels
    if sys.byteorder == "big":
        a = array("I", px)
        a.byteswap()
        px = a.tobytes()
    stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_ARGB32, im.width)
    buf = bytearray(stride * im.height)
    for y in range(im.height):
        buf[y * stride:y * stride + im.width * 4] = px[y * im.width * 4:(y + 1) * im.width * 4]
    surf = cairo.ImageSurface.create_for_data(buf, cairo.FORMAT_ARGB32, im.width, im.height, stride)
    surf.write_to_png(png_path)


# --------------------------------------------------------------------------------------------
# high level builders
# --------------------------------------------------------------------------------------------
@dataclass
class Frame:
    svg: str              # path to the SVG file
    hotspot_x: float      # in SVG canvas units
    hotspot_y: float
    nominal_size: float   # nominal size the SVG canvas represents (Breeze: 24 for a 32x32 canvas)
    delay: int = 0        # ms (animated cursors only)


def load_scalable_dir(path: str) -> list[Frame]:
    """Read a KWin cursors_scalable/<name>/ directory (metadata.json + svgs)."""
    with open(os.path.join(path, "metadata.json")) as f:
        meta = json.load(f)
    if not isinstance(meta, list) or not meta:
        raise ValueError("metadata.json must be a non-empty JSON array")
    frames = []
    for e in meta:
        for k in ("filename", "hotspot_x", "hotspot_y", "nominal_size"):
            if k not in e:
                raise ValueError(f"metadata entry missing {k!r} (KWin rejects the whole cursor)")
        frames.append(Frame(os.path.join(path, e["filename"]), float(e["hotspot_x"]), float(e["hotspot_y"]),
                            float(e["nominal_size"]), int(e.get("delay", 0))))
    return frames


def build_images(frames: list[Frame], sizes=DEFAULT_SIZES, png_dir: str | None = None,
                 png_prefix: str = "cursor", hotspot_rounding=math.floor,
                 canvas: str = "scaled") -> list[XcursorImage]:
    """Render every frame at every nominal size.

    canvas="scaled"  : image = SVG canvas * (N / nominal_size)  (Breeze/KWin convention)
    canvas="nominal" : image = N x N (whole SVG squeezed into the nominal size)
    """
    images = []
    for n in sorted(set(int(s) for s in sizes)):
        for idx, fr in enumerate(frames):
            iw, ih = svg_intrinsic_size(fr.svg)
            if canvas == "scaled":
                scale = n / fr.nominal_size
                w, h = max(1, round(iw * scale)), max(1, round(ih * scale))
                sx, sy = w / iw, h / ih
            elif canvas == "nominal":
                w = h = n
                sx, sy = n / iw, n / ih
            else:
                raise ValueError(canvas)
            surf = render_svg_surface(fr.svg, w, h)
            xh = min(max(int(hotspot_rounding(fr.hotspot_x * sx)), 0), w - 1)
            yh = min(max(int(hotspot_rounding(fr.hotspot_y * sy)), 0), h - 1)
            delay = fr.delay if len(frames) > 1 else (fr.delay or 50)
            if png_dir:
                os.makedirs(png_dir, exist_ok=True)
                suffix = f"_{idx + 1:02d}" if len(frames) > 1 else ""
                surf.write_to_png(os.path.join(png_dir, f"{png_prefix}_{n}{suffix}.png"))
            images.append(XcursorImage(n, w, h, xh, yh, delay, surface_to_xcursor_pixels(surf)))
    return images


def svg_to_xcursor(svg_path: str, out_path: str, hotspot: tuple[float, float], nominal_size: float,
                   sizes=DEFAULT_SIZES, png_dir: str | None = None, canvas: str = "scaled") -> list[XcursorImage]:
    """Single static SVG -> Xcursor file (hotspot in SVG canvas units)."""
    frames = [Frame(svg_path, hotspot[0], hotspot[1], nominal_size, 0)]
    ims = build_images(frames, sizes, png_dir, os.path.basename(out_path), canvas=canvas)
    write_xcursor(out_path, ims)
    return ims


def scalable_to_xcursor(scalable_dir: str, out_path: str, sizes=DEFAULT_SIZES, png_dir: str | None = None,
                        canvas: str = "scaled") -> list[XcursorImage]:
    """cursors_scalable/<name>/ (static or animated) -> cursors/<name> Xcursor file."""
    frames = load_scalable_dir(scalable_dir)
    ims = build_images(frames, sizes, png_dir, os.path.basename(out_path), canvas=canvas)
    write_xcursor(out_path, ims)
    return ims


def make_alias_symlinks(directory: str, aliases: dict[str, list[str]], overwrite=False) -> list[str]:
    """Create relative same-directory symlinks alias -> real (NO CHAINS: KWin resolves only
    one readlink level and only against already-registered names). Works for cursors/
    (files) and cursors_scalable/ (directories). Returns created link names."""
    made = []
    for real, links in aliases.items():
        if not os.path.exists(os.path.join(directory, real)):
            continue
        for ln in links:
            p = os.path.join(directory, ln)
            if os.path.lexists(p):
                if not overwrite:
                    continue
                os.remove(p)
            os.symlink(real, p)
            made.append(ln)
    return made


# Breeze 6.7.5 alias map, flattened so every alias points straight at a real file.
BREEZE_ALIASES: dict[str, list[str]] = {
    "alias": ["3085a0e285430894940527032f8b26df", "640fb0e74195791501fd1ed57b41487f",
              "a2a266d0498c3104214a47bd64ab0fc8", "link"],
    "cell": ["plus"],
    "col-resize": ["split_h"],
    "copy": ["1081e37283d90000800003c07f3ef6bf", "6407b0e94181790501fd1e167b474872",
             "b66166c04f8c3109214a4fbd64a50fc8", "dnd-copy"],
    "crosshair": ["cross", "tcross"],
    "default": ["arrow", "left_ptr", "size-bdiag", "size-fdiag", "size-hor", "size-ver", "top_left_arrow"],
    "dnd-move": ["4498f0e0c1937ffe01fd06f973665830", "9081237383d90e509aa00f00170e968f", "closedhand",
                 "dnd-none", "fcf21c00b30f7e3f83fe0dfd12e71cff", "grabbing", "move"],
    "fleur": ["size_all"],
    "help": ["5c6cd98b3f3ebcb1f9c7f1c204630408", "d9ce0ab605698f320427677b458ad60b", "left_ptr_help",
             "question_arrow", "whats_this"],
    "no-drop": ["forbidden"],
    "not-allowed": ["03b6e0fcb3499374a867c041f52298f0", "circle", "crossed_circle"],
    "openhand": ["grab"],
    "pointer": ["9d800788f1b08800ae810202380a0822", "e29285e634086352946a0e7090d73106", "hand1", "hand2",
                "pointing_hand"],
    "progress": ["00000000000000020006000e7e9ffc3f", "08e8e1c95fe2fc01f976f1e063a24ccd",
                 "3ecb610c1bf2410f44200f48c40d3599", "half-busy", "left_ptr_watch"],
    "row-resize": ["split_v"],
    "size_bdiag": ["ne-resize", "nesw-resize", "sw-resize"],
    "size_fdiag": ["nw-resize", "nwse-resize", "se-resize"],
    "size_hor": ["e-resize", "ew-resize", "h_double_arrow", "sb_h_double_arrow", "w-resize"],
    "size_ver": ["00008160000006810000408080010102", "n-resize", "ns-resize", "s-resize", "sb_v_double_arrow",
                 "v_double_arrow"],
    "text": ["ibeam", "xterm"],
    "wait": ["watch"],
}
# The 47 real cursors Breeze ships (each needs cursors/<name> + cursors_scalable/<name>/):
BREEZE_REAL = ["alias", "all-scroll", "bottom_left_corner", "bottom_right_corner", "bottom_side", "cell",
               "center_ptr", "col-resize", "color-picker", "context-menu", "copy", "crosshair", "default",
               "dnd-move", "dnd-no-drop", "down-arrow", "draft", "fleur", "help", "left-arrow", "left_side",
               "no-drop", "not-allowed", "openhand", "pencil", "pirate", "pointer", "progress", "right-arrow",
               "right_ptr", "right_side", "row-resize", "size_bdiag", "size_fdiag", "size_hor", "size_ver",
               "text", "top_left_corner", "top_right_corner", "top_side", "up-arrow", "vertical-text", "wait",
               "wayland-cursor", "x-cursor", "zoom-in", "zoom-out"]


# --------------------------------------------------------------------------------------------
# independent validation with the real libXcursor (ctypes)
# --------------------------------------------------------------------------------------------
class _XcImage(ctypes.Structure):
    _fields_ = [("version", ctypes.c_uint32), ("size", ctypes.c_uint32), ("width", ctypes.c_uint32),
                ("height", ctypes.c_uint32), ("xhot", ctypes.c_uint32), ("yhot", ctypes.c_uint32),
                ("delay", ctypes.c_uint32), ("pixels", ctypes.POINTER(ctypes.c_uint32))]


class _XcImages(ctypes.Structure):
    _fields_ = [("nimage", ctypes.c_int), ("images", ctypes.POINTER(ctypes.POINTER(_XcImage))),
                ("name", ctypes.c_char_p)]


def libxcursor_load(path: str, size: int):
    """Load with libXcursor's XcursorFilenameLoadImages(); returns list of dicts or raises."""
    name = ctypes.util.find_library("Xcursor") or "libXcursor.so.1"
    lib = ctypes.CDLL(name)
    lib.XcursorFilenameLoadImages.restype = ctypes.POINTER(_XcImages)
    lib.XcursorFilenameLoadImages.argtypes = [ctypes.c_char_p, ctypes.c_int]
    lib.XcursorImagesDestroy.argtypes = [ctypes.POINTER(_XcImages)]
    p = lib.XcursorFilenameLoadImages(path.encode(), size)
    if not p:
        raise ValueError(f"libXcursor rejected {path}")
    out = []
    for i in range(p.contents.nimage):
        im = p.contents.images[i].contents
        out.append(dict(size=im.size, width=im.width, height=im.height, xhot=im.xhot, yhot=im.yhot,
                        delay=im.delay, first_pixel=hex(im.pixels[0]) if im.width else None))
    lib.XcursorImagesDestroy(p)
    return out


# --------------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------------
def _dump(path):
    xc = read_xcursor(path)
    print(f"{path}: version=0x{xc.version:08x} images={len(xc.images)} comments={len(xc.comments)}")
    by = {}
    for im in xc.images:
        by.setdefault(im.size, []).append(im)
    for s in sorted(by):
        im = by[s][0]
        print(f"  nominal {s:3d}: frames={len(by[s]):2d} {im.width}x{im.height} hot=({im.xhot},{im.yhot}) delay={im.delay}ms")
    for c in xc.comments:
        print(f"  comment[{c.subtype}]: {c.text!r}")


def _selftest(workdir):
    import subprocess
    os.makedirs(workdir, exist_ok=True)
    src = "/usr/share/icons/breeze_cursors/cursors_scalable"
    ok = True
    for name in ("default", "pointer", "wait"):
        out = os.path.join(workdir, name)
        ims = scalable_to_xcursor(os.path.join(src, name), out, DEFAULT_SIZES,
                                  png_dir=os.path.join(workdir, "png"))
        back = read_xcursor(out)
        assert len(back.images) == len(ims), "image count mismatch"
        for a, b in zip(ims, back.images):
            assert (a.size, a.width, a.height, a.xhot, a.yhot, a.delay, a.pixels) == \
                   (b.size, b.width, b.height, b.xhot, b.yhot, b.delay, b.pixels), "round-trip mismatch"
        print("wrote + re-read OK:", out)
        _dump(out)
        print("  file(1):", subprocess.run(["file", "-b", out], capture_output=True, text=True).stdout.strip())
        for req in (24, 40, 96):
            try:
                got = libxcursor_load(out, req)
                print(f"  libXcursor XcursorFilenameLoadImages(size={req}): {len(got)} image(s), "
                      f"nominal={got[0]['size']} {got[0]['width']}x{got[0]['height']} "
                      f"hot=({got[0]['xhot']},{got[0]['yhot']}) delay={got[0]['delay']}")
            except OSError as e:
                print("  libXcursor not available:", e)
                break
        # compare against the shipped Breeze xcursor at nominal 24
        ref = read_xcursor(os.path.join("/usr/share/icons/breeze_cursors/cursors", name))
        r24 = [i for i in ref.images if i.size == 24][0]
        m24 = [i for i in back.images if i.size == 24][0]
        geom_same = (r24.width, r24.height, r24.xhot, r24.yhot) == (m24.width, m24.height, m24.xhot, m24.yhot)
        diff = sum(abs(x - y) for x, y in zip(r24.pixels[3::4], m24.pixels[3::4])) / (r24.width * r24.height)
        print(f"  vs system breeze '{name}' @24: geometry+hotspot identical={geom_same}, "
              f"mean |alpha diff| per pixel={diff:.2f}/255")
        ok &= geom_same
    print("SELFTEST", "PASSED" if ok else "FAILED")
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("svg", help="static SVG -> xcursor")
    a.add_argument("svg"); a.add_argument("out")
    a.add_argument("--hotspot", nargs=2, type=float, required=True, metavar=("X", "Y"),
                   help="hotspot in SVG canvas units")
    a.add_argument("--nominal", type=float, default=None,
                   help="nominal size the SVG canvas represents (default: SVG width => image==nominal)")
    a.add_argument("--sizes", type=int, nargs="+", default=list(DEFAULT_SIZES))
    a.add_argument("--png-dir")
    b = sub.add_parser("scalable", help="cursors_scalable/<name>/ (metadata.json) -> xcursor")
    b.add_argument("dir"); b.add_argument("out")
    b.add_argument("--sizes", type=int, nargs="+", default=list(DEFAULT_SIZES))
    b.add_argument("--png-dir")
    c = sub.add_parser("dump", help="print xcursor structure")
    c.add_argument("files", nargs="+")
    d = sub.add_parser("check", help="validate with libXcursor at a requested size")
    d.add_argument("file"); d.add_argument("--size", type=int, default=24)
    e = sub.add_parser("selftest", help="render Breeze default/pointer/wait, write, re-read, validate")
    e.add_argument("--workdir", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "xcursor-test"))
    args = ap.parse_args(argv)
    if args.cmd == "svg":
        nominal = args.nominal or svg_intrinsic_size(args.svg)[0]
        svg_to_xcursor(args.svg, args.out, tuple(args.hotspot), nominal, args.sizes, args.png_dir)
        _dump(args.out)
    elif args.cmd == "scalable":
        scalable_to_xcursor(args.dir, args.out, args.sizes, args.png_dir)
        _dump(args.out)
    elif args.cmd == "dump":
        for f in args.files:
            _dump(f)
    elif args.cmd == "check":
        for r in libxcursor_load(args.file, args.size):
            print(r)
    elif args.cmd == "selftest":
        return _selftest(args.workdir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
