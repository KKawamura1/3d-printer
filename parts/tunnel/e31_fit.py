"""E31-05 underside transfer (standalone geometry; historical experiments stay immutable).

Source: experiments/retention_balance_e31/design.py, specimen E31-05.
Only applies a bead and four split tube slots to the supplied solid.
Caller must select a tube OD of 13.20 mm (radius 6.60).
"""
import cadquery as cq

BEAD_MINOR_RADIUS = .20
BEAD_Z = 2.25
SLOT_WIDTH = 1.10
SLOT_END_Z = 4.40
SLOT_END_RADIUS = .65


def add_e31_05_receiver_features(shape, centres, tube_radius):
    if abs(tube_radius - 6.60) > 1e-6:
        raise ValueError("E31-05 requires nominal tube radius 6.60 mm")
    result = shape
    for x, y in centres:
        ring = cq.Solid.makeTorus(tube_radius, BEAD_MINOR_RADIUS,
                                  cq.Vector(x, y, BEAD_Z), cq.Vector(0, 0, 1))
        result = result.fuse(ring)
    result = result.clean()
    for x, y in centres:
        for angle in (0, 90, 180, 270):
            channel = (cq.Workplane("XY")
                       .box(4., SLOT_WIDTH, SLOT_END_Z + .1,
                            centered=(True, True, False))
                       .translate((6., 0., -.1)).val())
            rounded_end = cq.Solid.makeCylinder(
                SLOT_END_RADIUS, 4., cq.Vector(4., 0., SLOT_END_Z),
                cq.Vector(1, 0, 0))
            mouth = (cq.Workplane("YZ")
                     .polyline(((-.75, -.1), (.75, -.1),
                                (.55, .80), (-.55, .80)))
                     .close().extrude(4.).translate((4., 0., 0)).val())
            tool = channel.fuse(rounded_end).fuse(mouth)
            tool = tool.rotate((0, 0, 0), (0, 0, 1), angle).translate((x, y, 0))
            result = result.cut(tool)
    return result.clean()
