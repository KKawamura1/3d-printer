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


def engrave_trial_west_skirt(shape, label, *, x, y):
    """Engrave an upright 5 mm trial ID on the west face after any mirror."""
    plane = cq.Plane(origin=(x + .4, y, 3.5),
                     xDir=(0, -1, 0), normal=(-1, 0, 0))
    tool = (cq.Workplane(plane)
            .text(label, 5., .45, font="DejaVu Sans",
                  kind="bold", combine=False).val())
    marked = shape.cut(tool).clean()
    if (not marked.isValid() or len(marked.Solids()) != 1
            or shape.Volume() - marked.Volume() < 2):
        raise ValueError(f"Trial mark failed to cut the west skirt: {label}")
    return marked
