"""Shared channel cross-sections for open and roofed ball courses.

This module owns only the actual passage wire. The outer shell, roof, windows,
engraving and DUPLO supports remain enclosure-specific. In particular, the
historical calculation order and arc construction are deliberately retained:
moving proven parts to this function must not alter their BRep.
"""
import math


def passage_section_wire(workplane, *, floor, radius, center_x=0.,
                         roof=None, blend=0., open_top=95.):
    """Return a CadQuery wire using the same lower semicircle in both modes.

    roof=None: open trough, with high cutter walls (not a printed roof).
    roof=<z>: circular mouths blending to the proven pointed tunnel ceiling.
    Coordinates are in the supplied workplane's local XY plane.
    """
    centre = floor + radius
    if roof is None:
        return (workplane.moveTo(center_x-radius, centre)
                .threePointArc((center_x, floor),
                               (center_x+radius, centre))
                .lineTo(center_x+radius, open_top)
                .lineTo(center_x-radius, open_top).close().val())

    a = radius / math.sqrt(2)
    bridge = centre + math.sqrt(2) * radius - roof

    def mix(circle, pointed):
        return circle * (1 - blend) + pointed * blend

    end = (mix(radius * math.cos(math.radians(75)), bridge),
           mix(centre + radius * math.sin(math.radians(75)), roof))
    mid = (mix(radius * .5, (a + bridge) / 2),
           mix(centre + radius * math.sqrt(3) / 2,
               (centre + a + roof) / 2))
    apex = (0, mix(centre + radius, roof))
    return (workplane.moveTo(center_x-a, centre+a)
            .threePointArc((center_x, floor), (center_x+a, centre+a))
            .threePointArc((center_x+mid[0], mid[1]),
                           (center_x+end[0], end[1]))
            .threePointArc((center_x+apex[0], apex[1]),
                           (center_x-end[0], end[1]))
            .threePointArc((center_x-mid[0], mid[1]),
                           (center_x-a, centre+a))
            .close().val())
