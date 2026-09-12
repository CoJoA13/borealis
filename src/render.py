"""SVG -> PNG rendering with librsvg (gi) + cairo, and small preview helpers."""
import gi

gi.require_version("Rsvg", "2.0")
from gi.repository import Rsvg  # noqa: E402
import cairo  # noqa: E402
from PIL import Image  # noqa: E402


def svg_to_surface(svg, width, height, element=None, stylesheet=None):
    """Render SVG text (or bytes) into an ARGB32 surface of width x height.

    element: optional '#id' to render only that element, scaled to the size.
    stylesheet: optional CSS injected before rendering (e.g. to resolve
    ColorScheme-* classes for previews).
    """
    data = svg.encode() if isinstance(svg, str) else svg
    handle = Rsvg.Handle.new_from_data(data)
    if stylesheet:
        handle.set_stylesheet(stylesheet.encode())
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    ctx = cairo.Context(surf)
    vp = Rsvg.Rectangle()
    vp.x, vp.y, vp.width, vp.height = 0, 0, width, height
    if element:
        handle.render_element(ctx, element, vp)
    else:
        handle.render_document(ctx, vp)
    surf.flush()
    return surf


def surface_to_image(surf):
    return Image.frombuffer("RGBA", (surf.get_width(), surf.get_height()),
                            bytes(surf.get_data()), "raw", "BGRa",
                            surf.get_stride(), 1).copy()


def svg_to_image(svg, width, height, element=None, stylesheet=None):
    return surface_to_image(svg_to_surface(svg, width, height, element, stylesheet))


def svg_to_png(svg, path, width, height, element=None, stylesheet=None):
    svg_to_surface(svg, width, height, element, stylesheet).write_to_png(path)


def element_ids(svg):
    import xml.etree.ElementTree as ET
    root = ET.fromstring(svg.encode() if isinstance(svg, str) else svg)
    return [e.get("id") for e in root.iter() if e.get("id")]
