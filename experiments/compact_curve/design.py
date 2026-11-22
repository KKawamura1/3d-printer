"""Four 4×2 sharp-curve geometries, finished in both handednesses."""
import math
from dataclasses import dataclass
from itertools import product

import cadquery as cq

from brickcad.course_finish import engrave_trial_west_skirt, rounded_side_window
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


# Rows: horizontal open, horizontal tunnel, sloped open, sloped tunnel.
# Each row is right and left. Both sides start at the west mouth.
SPECIMENS = tuple(
    Specimen(f"X4A-{index:02}", drop_mm, tunnel, left)
    for index, (drop_mm, tunnel, left) in enumerate(
        product((0., DUPLO.height), (False, True), (False, True)), 1
    )
)


def window_stations(settings):
    # Two straight windows with 3 mm between them, then one at the arc apex.
    return (9., 24., 32. + settings.radius * math.pi / 4)


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
