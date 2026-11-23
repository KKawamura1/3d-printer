"""Four 4×2 sharp-curve geometries, finished in both handednesses."""
import math
from dataclasses import dataclass
from itertools import product

import cadquery as cq

from brickcad.course_finish import (
    WINDOW_WIDTH_MM, engrave_trial_west_skirt, rounded_side_window,
)
from brickcad.course_loft_family import (
    CHANNEL_HALF_WIDTH, LoftSettings, build_course, height, xy,
)
from brickcad.standards import BALL_TRACK, DUPLO


@dataclass(frozen=True)
class Specimen:
    id: str
    drop_mm: float
    tunnel: bool
    left: bool

    @property
    def settings(self):
        return LoftSettings("sharp", self.drop_mm, self.tunnel, False, "south", 12.)


# Only one-DUPLO-height downhill variants are needed. Retain the
# historical X4A-05..08 IDs; X4A-01..04 (level 4×2) are retired.
# Both directions enter from the west.
SPECIMENS = tuple(
    Specimen(f"X4A-{index:02}", DUPLO.height, tunnel, left)
    for index, (tunnel, left) in enumerate(
        product((False, True), (False, True)), 5
    )
)


# Window centres are specified along the ACTUAL OUTER WALL, not the R16
# track centreline. This prevents the bend from looking like a huge gap.
# Two straight + two curved openings; 12mm windows leave >=3mm webs.
OUTER_WALL_WINDOW_CENTRES_MM = (9., 25., 43., 61.)
WINDOW_EDGE_MARGIN_MM = 3.
WINDOW_MIN_WEB_MM = 3.


def window_stations(settings):
    """Centreline stations of equally distributed OUTER-wall windows.

    Arc distance scales by R/(R + channel half-width); that same factor
    converts each curved-window cutter width to true outside-wall width.
    Keep a gap at the straight-to-arc junction, so a planar cutter cannot
    accidentally shear both wall types.
    """
    if settings.route != "sharp":
        raise ValueError("The 4x2 external-wall window plan requires R16")
    outer_radius = settings.radius + CHANNEL_HALF_WIDTH
    total_outer_length = 32. + math.pi * outer_radius / 2.
    half_width = WINDOW_WIDTH_MM / 2.
    centres = OUTER_WALL_WINDOW_CENTRES_MM
    if (centres[0] - half_width < WINDOW_EDGE_MARGIN_MM or
            total_outer_length - centres[-1] - half_width <
            WINDOW_EDGE_MARGIN_MM):
        raise ValueError("Window plan interferes with an entrance/exit port")
    if any(b - a - 2*half_width < WINDOW_MIN_WEB_MM
           for a, b in zip(centres, centres[1:])):
        raise ValueError("Window plan has insufficient intervening wall")
    if any(abs(c - 32.) - half_width < 1. for c in centres):
        raise ValueError("Window cutter must not straddle the turn junction")
    return tuple(
        outer if outer <= 32.
        else 32. + (outer - 32.) * settings.radius / outer_radius
        for outer in centres
    )


def cut_windows(body, settings):
    volumes = []
    for s in window_stations(settings):
        x, y, tx, ty = xy(s, settings)
        nx, ny = -ty, tx
        stand_off = CHANNEL_HALF_WIDTH + 1.1
        plane = cq.Plane(origin=(x + stand_off * nx, y + stand_off * ny, 0),
                         xDir=(-tx, -ty, 0), normal=(nx, ny, 0))
        # On the curve the window width is measured at the outside wall.
        scale = settings.radius / (settings.radius + CHANNEL_HALF_WIDTH) if s > 32. else 1.
        tool = rounded_side_window(
            plane, lambda u: height(s - u * scale, settings), cq.Vector(-nx, -ny, 0)
        )
        result = body.cut(tool).clean()
        removed = body.Volume() - result.Volume()
        z = height(s, settings) + BALL_TRACK.radius
        # Confirm the cut opened the wall all the way to the guide. Check
        # the same points before and after so a cutter missing the wall fails.
        probes = [cq.Vector(x + nx * d, y + ny * d, z) for d in (14.5, 15., 15.6)]
        if (removed < 50 or not result.isValid() or len(result.Solids()) != 1
                or not all(body.isInside(p) and not result.isInside(p) for p in probes)):
            raise ValueError(f"Window did not open the exterior wall at station {s:.2f}: {removed:.2f} mm³")
        volumes.append(removed)
        body = result
    return body, volumes


def build_base(settings):
    """Use the production SD01/SD03 pipeline for all four bases."""
    bare, fit = build_course(settings)
    if settings.tunnel:
        windowed, windows = cut_windows(bare, settings)
    else:
        windowed, windows = bare, []
    return bare, windowed, fit, windows


def orient_body(shape, specimen):
    return shape.mirror("XZ") if specimen.left else shape


def mark_body(shape, specimen, fit):
    return engrave_trial_west_skirt(shape, specimen.id, x=-fit.width / 2, y=0.)
