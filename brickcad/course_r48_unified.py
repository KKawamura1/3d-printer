"""Issue #89: one R48 tunnel design language, varied only by elevation profile.

Experimental engine for X89-E01-U1 (flat) and X89-SC02-U1 (19.2mm slope).
Neither production builders nor any proven STL are modified. Both shapes
are generated from the exact same sweep, shell, windows, E31-05 supports,
full studs and finishing logic. A proof-of-concept, NOT a print-certified part.
"""
from dataclasses import dataclass
from functools import lru_cache
import math

import cadquery as cq

from brickcad.connections import make_studs
from brickcad.course_contract import (
    RECEIVER_DEPTH_MM, add_course_receiver_features, course_fit,
)
from brickcad.course_geometry import smoothstep_fall, smoothstep_rise_factored
from brickcad.standards import BALL_TRACK, DUPLO, ROUNDED_EDGES
from brickcad.course_r48_sloped_tunnel import (
    FULL_TUBES as PROVEN_FULL_TUBES,
    open_curve as build_proven_sc02_open_curve,
    clipped_receivers as add_proven_sc02_partial_receivers,
    roof_studs as add_proven_sc02_roof_studs,
)
from brickcad.r48_path import (
    RADIUS_MM as SHARED_R48_RADIUS, TURN_CENTRE_XY as SHARED_R48_CENTRE,
    ARC_LENGTH_MM, xy_at_s, floor_at_s, grade_at_t,
    horizontal_port_contract,
)

RADIUS = SHARED_R48_RADIUS
CENTRE_XY = SHARED_R48_CENTRE
WIDTH = BALL_TRACK.width
HALF = WIDTH / 2
INNER = RADIUS - HALF
OUTER = RADIUS + HALF
WINDOW_COUNT = 5
WINDOW_WIDTH = 12.0
WINDOW_CUT_DEPTH = 7.0
WINDOW_CORNER_RADIUS = 0.8
WINDOW_MIN_WEB = 2.5
INTERIOR_RADIAL_RELIEF = 1.0  # issue89 tolerance trial; preserve 25.74mm mouth
SAMPLE_STATIONS = 48
TUBE_PROBE_RADIUS = 6.8  # E31 bead OD / 2, not just the bare tube
MIN_RADIAL_SIDEWALL_MM = 1.6


@dataclass(frozen=True)
class R48PairConfig:
    """Shared shape recipe: only drop and handedness vary."""
    model_id: str
    drop_mm: float
    direction: str = "right"
    windows: bool = True
    # Different finished-course widths for paired real rolling experiments.
    # Opening/ports remain unchanged; R10 is the established PR91 default.
    relief_mm: float = INTERIOR_RADIAL_RELIEF

    def __post_init__(self):
        if self.drop_mm not in (0.0, DUPLO.height):
            raise ValueError("Only the flat/one-DUPLO-height R48 comparison is defined")
        if self.direction not in ("right", "left"):
            raise ValueError("Unrecognized handedness")
        if (not isinstance(self.relief_mm, (int, float))
                or not math.isfinite(self.relief_mm)
                or self.relief_mm < 0.
                or HALF - BALL_TRACK.radius - self.relief_mm <
                MIN_RADIAL_SIDEWALL_MM):
            raise ValueError("Relief must be nonnegative and preserve 1.6mm side wall")
        if not self.model_id or len(self.model_id) > 32:
            raise ValueError("Explicit versioned experiment model ID required")

    @property
    def roof_z(self):
        # Identical top-stud plane across each part; 2 units for E01,
        # 3 for SC02. DUPLO studs cannot be placed on a slanted roof.
        return 2 * DUPLO.height + self.drop_mm


def floor_z(t, drop_mm):
    """Shared with the open R48 rails: E01 is constant-z SC02."""
    return floor_at_s(min(1., max(0., t)) * ARC_LENGTH_MM, drop_mm)


def grade(t, drop_mm):
    """Shared positive magnitude of dz/ds for the 48mm radius arc."""
    return grade_at_t(t, drop_mm)


def centreline(t, drop_mm):
    x, y, _, _ = xy_at_s(t * ARC_LENGTH_MM)
    return cq.Vector(x, y, floor_z(t, drop_mm))


def port_contract(drop_mm):
    """Same exact connector coordinates used by open and roofed R48."""
    return horizontal_port_contract(drop_mm)


def _world(wire, t):
    return (wire.rotate((0, 0, 0), (0, 0, 1), -90 + 90 * t)
            .translate((CENTRE_XY[0], CENTRE_XY[1], 0)))


def _progress(t):
    length = RADIUS * math.pi / 2
    distance = min(max(0., t), max(0., 1 - t)) * length
    return min(.995, smoothstep_rise_factored(
        max(0., min(1., (distance - 1.) / 4.))
    ))


def _outer_wire(t, config):
    # Do not create a rectangular LEGO box and crop its remnants.
    # Sweep the intended R48 annular envelope directly.
    w = cq.Workplane("XZ").polyline((
        (INNER, BALL_TRACK.floor - .15), (OUTER, BALL_TRACK.floor - .15),
        (OUTER, config.roof_z), (INNER, config.roof_z)
    )).close().val()
    top = [v for v in w.Vertices()
           if v.Center().z > config.roof_z - .01]
    w = w.fillet2D(ROUNDED_EDGES.corner_radius, top)
    return _world(w, t)


def _passage_wire(t, config):
    floor = floor_z(t, config.drop_mm)
    progress = _progress(t)
    # Same radial relief at identical stations for both configurations.
    # Identical fixed OEM openings, while the interior expands by the
    # specimen-specific amount (0.4mm or 1.0mm for the controlled trial).
    radius = BALL_TRACK.radius + config.relief_mm * progress
    centre = floor + radius
    a = radius / math.sqrt(2)
    roof = floor + 30.3
    bridge = centre + math.sqrt(2) * radius - roof

    def mix(circle, high):
        return circle * (1 - progress) + high * progress

    end = (mix(radius * math.cos(math.radians(75)), bridge),
           mix(centre + radius * math.sin(math.radians(75)), roof))
    mid = (mix(radius * .5, (a + bridge) / 2),
           mix(centre + radius * math.sqrt(3) / 2,
               (centre + a + roof) / 2))
    apex = (0, mix(centre + radius, roof))
    w = (cq.Workplane("XZ")
         .moveTo(RADIUS - a, centre + a)
         .threePointArc((RADIUS, floor), (RADIUS + a, centre + a))
         .threePointArc((RADIUS + mid[0], mid[1]),
                        (RADIUS + end[0], end[1]))
         .threePointArc((RADIUS + apex[0], apex[1]),
                        (RADIUS - end[0], end[1]))
         .threePointArc((RADIUS - mid[0], mid[1]),
                        (RADIUS - a, centre + a))
         .close().val())
    return _world(w, t)


def _entire_disk_inside_outline(x, y, radius, margin=0.):
    """Select complete supports by design; NEVER clip their circles into fins."""
    for i in range(96):
        a = math.tau * i / 96
        sx = x + radius * math.cos(a)
        sy = y + radius * math.sin(a)
        distance = math.hypot(sx - CENTRE_XY[0], sy - CENTRE_XY[1])
        if (distance < INNER + margin or distance > OUTER - margin or
                abs(sx) > 31.9 - margin or abs(sy) > 31.9 - margin):
            return False
    return True


def _window_cutters(config):
    """Rounded pentagonal windows on the outside only; no concave apertures."""
    arc = OUTER * math.pi / 2
    gap = (arc - WINDOW_COUNT * WINDOW_WIDTH) / (WINDOW_COUNT + 1)
    if gap < WINDOW_MIN_WEB:
        raise ValueError("Insufficient facade posts")

    for i in range(WINDOW_COUNT):
        s = gap + WINDOW_WIDTH / 2 + i * (WINDOW_WIDTH + gap)
        t = s / arc
        angle = -math.pi / 2 + t * math.pi / 2
        rx, ry = math.cos(angle), math.sin(angle)
        tangent = (-ry, rx, 0)
        plane = cq.Plane(
            origin=(CENTRE_XY[0] + (OUTER + 1.1) * rx,
                    CENTRE_XY[1] + (OUTER + 1.1) * ry, 0),
            xDir=tangent, normal=(rx, ry, 0),
        )
        # Each opening follows the local sloping floor, not a fixed world Z.
        z = lambda u: floor_z(t + u / arc, config.drop_mm)
        half = WINDOW_WIDTH / 2
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
        wire = wire.fillet2D(
            WINDOW_CORNER_RADIUS, list(wire.Vertices())
        )
        yield cq.Solid.extrudeLinear(
            wire, [], cq.Vector(-rx * WINDOW_CUT_DEPTH,
                                -ry * WINDOW_CUT_DEPTH, 0)
        )


def complete_studs(fit):
    return tuple((x, y) for x, y in fit.studs()
                 if _entire_disk_inside_outline(
                     x, y, fit.stud_radius - fit.clearance, .7))


def complete_tubes(fit):
    return tuple((x, y) for x, y in fit.tubes()
                 if _entire_disk_inside_outline(
                     x, y, TUBE_PROBE_RADIUS))



@lru_cache(maxsize=1)
def _proven_foundation():
    """Retain the actual SC02 underbody rather than reconstruct its receiver.

    This comes directly from the historical SC02 curve's build path. It
    includes its *print-tested floor*, the 4.75mm receiver, three tube walls,
    and the curved end-skirt. The same foundation is used for E01 and SC02.
    Keep its original CAD unchanged; attach roof/track variants above it.
    """
    return build_proven_sc02_open_curve()


def _west_skirt_mark(shape, fit, model_id):
    # At Z=3.5 the west entrance has a continuous 4.75mm receiver sidewall.
    # Size 5.0mm is deliberately larger than the historical 3mm. Only the
    # ID on a new experiment is touched, never the locked production contract.
    plane = cq.Plane(
        origin=(-fit.width / 2 + .4, -16., 3.5),
        xDir=(0, -1, 0), normal=(-1, 0, 0),
    )
    tool = (cq.Workplane(plane)
            .text(model_id, 5., .45, font="DejaVu Sans",
                  kind="bold", combine=False).val())
    marked = shape.cut(tool).clean()
    if (not marked.isValid() or len(marked.Solids()) != 1 or
            shape.Volume() - marked.Volume() < 2):
        raise ValueError("The entire experimental mark must cut the west skirt")
    return marked


def build_r48(config, *, marked=True):
    """Re-use SC02's curved, printable foundation for both roofed R48 tracks.

    The underbody, receiver posts, tube cuts, and roof stud construction are
    all the original `course_r48_sloped_tunnel` operations. We change only
    the profile (flat/sloped), bore relief, windows and the test engraving.
    In particular, DO NOT cut a new rectangular receiver pocket into a
    swept annulus: that introduced PR91's catastrophic Z=4.75mm bridge.
    """
    if not isinstance(config, R48PairConfig):
        raise TypeError("R48PairConfig required")
    nominal_min_wall = HALF - BALL_TRACK.radius - config.relief_mm
    if nominal_min_wall < MIN_RADIAL_SIDEWALL_MM:
        raise ValueError(f"Radial sidewall too thin: {nominal_min_wall:.3f}mm")

    fit = course_fit(nx=4, ny=4,
                     height_units=2 if config.drop_mm == 0 else 3)
    proven_base, proven_fit = _proven_foundation()
    if (proven_fit.cavity_xy != fit.cavity_xy
            or proven_fit.tube_radius != fit.tube_radius
            or set(PROVEN_FULL_TUBES) != set(complete_tubes(fit))):
        raise ValueError("The production SC02 foundation no longer matches E31-05")

    ts = [-.02] + [i / SAMPLE_STATIONS for i in range(SAMPLE_STATIONS + 1)] + [1.02]
    cover = cq.Solid.makeLoft([_outer_wire(t, config) for t in ts], ruled=True)
    passage = cq.Solid.makeLoft(
        [_passage_wire(t, config) for t in ts], ruled=True)
    bed_envelope = cq.Workplane("XY").box(
        fit.width, fit.depth, 100,
        centered=(True, True, False)).val()

    # The roof is above Z=6.20, and overlaps the real printed SC02 base.
    # Nothing below the original lower socket is replaced with a new bridge.
    # Importantly the proven base remains continuous under both flat/sloped
    # track profiles, while passage cuts only start at the Z>=6.35 track floor.
    shape = proven_base.fuse(cover.intersect(bed_envelope)).clean()
    shape = shape.cut(passage).clean()

    # Keep SC02's clipped partial tube supports, its 3 complete E31-05
    # tubes, bead and slit geometry, and its actual clipped roof studs.
    shape = add_proven_sc02_partial_receivers(shape, proven_fit)
    shape = add_course_receiver_features(
        shape, PROVEN_FULL_TUBES, proven_fit.tube_radius,
        receiver_depth=RECEIVER_DEPTH_MM)
    shape = add_proven_sc02_roof_studs(
        shape, proven_fit, top_z=config.roof_z)

    window_volumes = []
    if config.windows:
        for cutter in _window_cutters(config):
            before = shape.Volume()
            shape = shape.cut(cutter).clean()
            removed = before - shape.Volume()
            if removed < 50 or not shape.isValid() or len(shape.Solids()) != 1:
                raise ValueError("One of the 5 windows failed to open the outer wall")
            window_volumes.append(removed)

    if config.direction == "left":
        shape = shape.mirror("XZ")
    if marked:
        if config.direction == "left":
            raise ValueError("Left-hand mark placement is not yet validated")
        shape = _west_skirt_mark(shape, fit, config.model_id)
    if not shape.isValid() or len(shape.Solids()) != 1:
        raise ValueError("R48 output must be a valid, single connected solid")

    # The seven entire studs from the footprint are among the original
    # clipped-stud array; this is not a claim that *only* seven studs exist.
    entire_studs = complete_studs(fit)
    return shape, {
        "model_id": config.model_id,
        "drop_mm": config.drop_mm,
        "direction": config.direction,
        "roof_z_mm": config.roof_z,
        "top_studs": list(entire_studs),
        "roof_stud_method": "course_r48_sloped_tunnel.roof_studs (full + clipped)",
        "complete_e31_tubes": list(PROVEN_FULL_TUBES),
        "partial_e31_tubes": 4,
        "underbody_source": "course_r48_sloped_tunnel.open_curve",
        "receiver_method": "course_r48_sloped_tunnel.clipped_receivers",
        "window_cut_volumes_mm3": window_volumes,
        "port_contract": port_contract(config.drop_mm),
        "ball_diameter_mm": BALL_TRACK.ball_diameter,
        "interior_radial_relief_mm": config.relief_mm,
        "radial_relief_at_ports_mm": 0.,
    }
