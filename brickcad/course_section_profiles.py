"""Shared channel cross-sections for open and roofed ball courses.

This module owns only the actual passage wire. The outer shell, roof, windows,
engraving and DUPLO supports remain enclosure-specific. In particular, the
historical calculation order and arc construction are deliberately retained:
moving proven parts to this function must not alter their BRep.
"""
import math

from brickcad.course_geometry import (
    smoothstep_rise_expanded, smoothstep_rise_factored,
)
from brickcad.standards import BALL_TRACK

# Preserve the arithmetic order of the legacy CADs. Merely replacing the
# factored smoothstep with its expanded algebraic twin can change a BRep.
def end_relief_blend(distance_mm, *, mode):
    """Fraction of extra passage radius reached from the nearest mouth.

    Both PR91 R48 and PR94 R16 retain their own geometry-specific ramp mode.
    An exact zero at the mouth retains the 25.74mm mating opening.
    """
    if mode == "linear":
        return min(1., distance_mm / 5.)
    u = max(0., min(1., (distance_mm - 1.) / 4.))
    if mode == "smoothstep-expanded":
        return min(.995, smoothstep_rise_expanded(u))
    if mode == "smoothstep-factored":
        return min(.995, smoothstep_rise_factored(u))
    raise ValueError(f"Unknown passage-relief transition: {mode}")


def interior_radius_mm(blend, *, extra_radius_mm):
    """Shared lower-arc radius, with nominal BALL_TRACK mouth at blend=0."""
    return BALL_TRACK.radius + extra_radius_mm * blend


def validate_interior_relief(half_body_width_mm, *, extra_radius_mm,
                             minimum_wall_mm=1.6):
    """Reject a nominal interior enlargement that leaves too little sidewall."""
    if (not isinstance(extra_radius_mm, (int, float))
            or not math.isfinite(extra_radius_mm)
            or extra_radius_mm < 0.
            or half_body_width_mm - BALL_TRACK.radius - extra_radius_mm
            < minimum_wall_mm):
        raise ValueError("Relief must be nonnegative and preserve 1.6mm side wall")
    return extra_radius_mm



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
