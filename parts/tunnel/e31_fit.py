"""E31-05 underside transfer (standalone geometry; historical experiments stay immutable).

Source: experiments/retention_balance_e31/design.py, specimen E31-05.
Applies the E31-05 bead and four split tube slots to the supplied solid.
PR #58 printed B coupons demonstrate a short Z3.50 slot for shallow 4.75 mm
track receivers. Deep ordinary bricks retain the original E31-05 Z4.40 slot.
The original E31 coupon is unchanged. The caller MUST supply the actual
receiver_depth; no implicit rail/brick default is permitted.
Caller must select a tube OD of 13.20 mm (radius 6.60).
"""
import math
import cadquery as cq

BEAD_MINOR_RADIUS = .20
BEAD_Z = 2.25
SLOT_WIDTH = 1.10
SLOT_END_Z = 3.50  # PR58 B: shallow 4.75 mm rail/tunnel receivers
ORIGINAL_E31_SLOT_END_Z = 4.40  # deep ordinary E31-05 bricks
SLOT_END_RADIUS = .65


def slot_end_z_for_receiver_depth(receiver_depth):
    """Deep receivers keep E31-05; shallow track receivers use PR58 B.

    Preserve >=0.60 mm below the receiver ceiling (rounded slot R0.65).
    An explicit receiver depth prevents accidentally applying the shallow
    rail geometry to an ordinary deep brick.
    """
    if not math.isfinite(receiver_depth) or receiver_depth <= 0:
        raise ValueError("receiver_depth must be a finite positive number")
    required_clearance = SLOT_END_RADIUS + 0.60
    if receiver_depth + 1e-6 >= ORIGINAL_E31_SLOT_END_Z + required_clearance:
        return ORIGINAL_E31_SLOT_END_Z
    if receiver_depth + 1e-6 >= SLOT_END_Z + required_clearance:
        return SLOT_END_Z
    raise ValueError("Receiver too shallow for E31 split slots with a 0.60mm roof margin")


def add_e31_05_receiver_features(shape, centres, tube_radius, *, receiver_depth):
    end_z = slot_end_z_for_receiver_depth(receiver_depth)
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
                       .box(4., SLOT_WIDTH, end_z + .1,
                            centered=(True, True, False))
                       .translate((6., 0., -.1)).val())
            rounded_end = cq.Solid.makeCylinder(
                SLOT_END_RADIUS, 4., cq.Vector(4., 0., end_z),
                cq.Vector(1, 0, 0))
            mouth = (cq.Workplane("YZ")
                     .polyline(((-.75, -.1), (.75, -.1),
                                (.55, .80), (-.55, .80)))
                     .close().extrude(4.).translate((4., 0., 0)).val())
            tool = channel.fuse(rounded_end).fuse(mouth)
            tool = tool.rotate((0, 0, 0), (0, 0, 1), angle).translate((x, y, 0))
            result = result.cut(tool)
    return result.clean()
