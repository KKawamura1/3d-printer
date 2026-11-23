"""Shared trial engraving and rounded side openings for ball courses."""
import cadquery as cq

WINDOW_WIDTH_MM = 12.
WINDOW_CORNER_RADIUS_MM = .8
WINDOW_CUT_DEPTH_MM = 7.


def rounded_side_window(plane, floor_at_offset, inward):
    """Cut a PR91 window profile that follows the local running-floor height."""
    half = WINDOW_WIDTH_MM / 2
    z = floor_at_offset
    points = (
        (-half, z(-half) + 7),
        (half, z(half) + 7),
        (half, z(half) + 17),
        (half - 1.5, z(half - 1.5) + 20),
        (0, z(0) + 22),
        (-half + 1.5, z(-half + 1.5) + 20),
        (-half, z(-half) + 17),
    )
    wire = cq.Workplane(plane).polyline(points).close().val()
    wire = wire.fillet2D(WINDOW_CORNER_RADIUS_MM, list(wire.Vertices()))
    return cq.Solid.extrudeLinear(wire, [], inward.multiply(WINDOW_CUT_DEPTH_MM))


def west_skirt_label_tool(label, *, x, y, face_width_mm=31.8):
    """Return the full 5mm cutter only if every glyph fits the receiver skirt.

    Replacing the earlier 'any material removed' check prevents clipped
    lettering, as seen on the PR91 physical print. Coordinates are in mm.
    """
    plane = cq.Plane(origin=(x + .4, y, 2.35),
                     xDir=(0, -1, 0), normal=(-1, 0, 0))
    tool = (cq.Workplane(plane)
            .text(label, 5., .45, font="DejaVu Sans",
                  kind="bold", combine=False).val())
    bounds = tool.BoundingBox()
    margin = 1.
    if not (y - face_width_mm / 2 + margin <= bounds.ymin
            and bounds.ymax <= y + face_width_mm / 2 - margin
            and .4 <= bounds.zmin and bounds.zmax <= 4.75 - .4):
        raise ValueError(
            f"Engraving {label!r} exceeds the west receiver skirt: "
            f"Y=[{bounds.ymin:.2f},{bounds.ymax:.2f}], "
            f"Z=[{bounds.zmin:.2f},{bounds.zmax:.2f}]")
    return tool


def engrave_trial_west_skirt(shape, label, *, x, y, face_width_mm=31.8):
    """Cut an upright, fully contained trial ID after mirroring."""
    tool = west_skirt_label_tool(label, x=x, y=y,
                                 face_width_mm=face_width_mm)
    marked = shape.cut(tool).clean()
    if (not marked.isValid() or len(marked.Solids()) != 1
            or shape.Volume() - marked.Volume() < 2):
        raise ValueError(f"Trial mark failed to cut the west skirt: {label}")
    return marked
