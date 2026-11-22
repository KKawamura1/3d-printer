"""The shared R48 path and height contract for open and roofed DUPLO curves.

Unlike the historic CAD engines, this module contains *no shell, window,
support or engraving* decisions. Those belong to separate enclosure adapters.

Inputs/outputs are mm. The evaluation order of xy_at_s() and floor_at_s()
is deliberately identical to the proven open-course loft engine, avoiding
silent numerical CAD parity drift for GC01/SC03/SC05.
"""
import math

from brickcad.course_geometry import smoothstep_fall
from brickcad.standards import BALL_TRACK, DUPLO

RADIUS_MM = 48.
TURN_CENTRE_XY = (-32., 32.)
ARC_LENGTH_MM = math.pi * RADIUS_MM / 2


def xy_at_s(s):
    """(x,y,tx,ty) on the original quarter-circle, s in arc-length mm."""
    a = -math.pi / 2 + s / RADIUS_MM
    return (TURN_CENTRE_XY[0] + RADIUS_MM * math.cos(a),
            TURN_CENTRE_XY[1] + RADIUS_MM * math.sin(a),
            -math.sin(a), math.cos(a))


def floor_at_s(s, drop_mm):
    """Original smoothstep grade. 0 means horizontal; positive descends."""
    t = max(0., min(1., s / ARC_LENGTH_MM))
    return BALL_TRACK.floor + drop_mm * smoothstep_fall(t)


def grade_at_t(t, drop_mm):
    """Positive magnitude of dz/ds. Zero at physical mouth planes."""
    t = max(0., min(1., t))
    return drop_mm * 6 * t * (1 - t) / ARC_LENGTH_MM


def horizontal_port_contract(drop_mm):
    """Numerically exact physical connector coordinates, not rounded cos()."""
    return {
        "west": ((-32., -16., BALL_TRACK.floor + drop_mm),
                 (-1., 0., 0.), BALL_TRACK.radius),
        "north": ((16., 32., BALL_TRACK.floor),
                  (0., 1., 0.), BALL_TRACK.radius),
        "opening_diameter_mm": BALL_TRACK.opening,
    }


def validate_profile(drop_mm):
    """Define the only two established R48 vertical profiles."""
    if drop_mm not in (0., DUPLO.height):
        raise ValueError("R48 currently supports 0 or 19.2mm descent")
    return drop_mm
