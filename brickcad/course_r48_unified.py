"""Issue #89: one R48 tunnel design language, varied only by elevation profile.

Experimental engine for X89-E01-U1 (flat) and X89-SC02-U1 (19.2mm slope).
Neither production builders nor any proven STL are modified. Both shapes
are generated from the exact same sweep, shell, windows, E31-05 supports,
full studs and finishing logic. A proof-of-concept, NOT a print-certified part.
"""
from dataclasses import dataclass
import math

import cadquery as cq

from brickcad.connections import make_studs
from brickcad.course_contract import (
    RECEIVER_DEPTH_MM, add_course_receiver_features, course_fit,
)
from brickcad.course_geometry import smoothstep_fall, smoothstep_rise_factored
from brickcad.standards import BALL_TRACK, DUPLO, ROUNDED_EDGES

RADIUS = 48.0
CENTRE_XY = (-32.0, 32.0)
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

    def __post_init__(self):
        if self.drop_mm not in (0.0, DUPLO.height):
            raise ValueError("Only the flat/one-DUPLO-height R48 comparison is defined")
        if self.direction not in ("right", "left"):
            raise ValueError("Unrecognized handedness")
        if not self.model_id or len(self.model_id) > 32:
            raise ValueError("Explicit versioned experiment model ID required")

    @property
    def roof_z(self):
        # Identical top-stud plane across each part; 2 units for E01,
        # 3 for SC02. DUPLO studs cannot be placed on a slanted roof.
        return 2 * DUPLO.height + self.drop_mm


def floor_z(t, drop_mm):
    """Slope is the only geometric variation; E01 is constant-z SC02."""
    t = min(1., max(0., t))
    return BALL_TRACK.floor + drop_mm * smoothstep_fall(t)


def grade(t, drop_mm):
    """Magnitude of dz/ds for the 48mm radius arc."""
    t = min(1., max(0., t))
    return drop_mm * 6 * t * (1 - t) / (RADIUS * math.pi / 2)


def centreline(t, drop_mm):
    a = math.radians(-90 + 90 * t)
    return cq.Vector(
        CENTRE_XY[0] + RADIUS * math.cos(a),
        CENTRE_XY[1] + RADIUS * math.sin(a),
        floor_z(t, drop_mm),
    )


def port_contract(drop_mm):
    """The physical OEM port radius/position is *never* expanded."""
    return {
        "west": ((-32., -16., BALL_TRACK.floor + drop_mm),
                 (-1., 0., 0.), BALL_TRACK.radius),
        "north": ((16., 32., BALL_TRACK.floor),
                  (0., 1., 0.), BALL_TRACK.radius),
        "opening_diameter_mm": BALL_TRACK.opening,
    }


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
        (INNER, 0), (OUTER, 0),
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
    # 0 at physical ports, up to +1.0mm internally; important for sloped
    # rigid-ball clearance, where the grade increases sphere sweep extent.
    radius = BALL_TRACK.radius + INTERIOR_RADIAL_RELIEF * progress
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
    """Common CAD construction for both E01 and SC02; no old BRep cropping."""
    if not isinstance(config, R48PairConfig):
        raise TypeError("R48PairConfig required")
    nominal_min_wall = HALF - BALL_TRACK.radius - INTERIOR_RADIAL_RELIEF
    if nominal_min_wall < MIN_RADIAL_SIDEWALL_MM:
        raise ValueError(f"Radial sidewall too thin: {nominal_min_wall:.3f}mm")
    fit = course_fit(
        nx=4, ny=4,
        height_units=2 if config.drop_mm == 0 else 3,
    )
    ts = [-.02] + [i / SAMPLE_STATIONS for i in range(SAMPLE_STATIONS + 1)] + [1.02]
    exterior = cq.Solid.makeLoft(
        [_outer_wire(t, config) for t in ts], ruled=True)
    passage = cq.Solid.makeLoft(
        [_passage_wire(t, config) for t in ts], ruled=True)
    bounding_box = (cq.Workplane("XY")
                    .box(fit.width, fit.depth, 100,
                         centered=(True, True, False)).val())
    shape = exterior.intersect(bounding_box).clean()

    # Round the physical exterior's *bottom* perimeter before creating ports,
    # window openings or socket features (otherwise fillet will cross slots).
    bottom = [e for e in shape.Edges()
              if abs(e.BoundingBox().zmin) < 1e-5 and
              abs(e.BoundingBox().zmax) < 1e-5]
    if not bottom:
        raise ValueError("No bottom outline available to round")
    shape = shape.fillet(.55, bottom).clean()

    shape = shape.cut(passage).clean()
    cavity = (cq.Workplane("XY")
              .box(*fit.cavity_xy, RECEIVER_DEPTH_MM,
                   centered=(True, True, False)).val())
    shape = shape.cut(cavity).clean()

    # Three deliberately complete supports instead of old clipped tube fins.
    tubes = complete_tubes(fit)
    if set(tubes) != {(-16., -16.), (0., 0.), (16., 16.)}:
        raise ValueError(f"Unexpected complete E31-05 support layout: {tubes}")
    for x, y in tubes:
        ring = (cq.Workplane("XY", origin=(x, y, 0))
                .circle(fit.tube_radius).circle(fit.tube_inner_radius)
                .extrude(RECEIVER_DEPTH_MM).val())
        shape = shape.fuse(ring).clean()
    shape = add_course_receiver_features(
        shape, tubes, fit.tube_radius, receiver_depth=RECEIVER_DEPTH_MM
    )

    # Seven *whole* studs; do not crop a 16-stud rectangular array.
    studs = complete_studs(fit)
    if len(studs) != 7:
        raise ValueError(f"Unexpected whole-stud count: {len(studs)}")
    for x, y in studs:
        stud = make_studs(
            [(x, y)], config.roof_z - .15,
            fit.stud_radius - fit.clearance,
            fit.stud_inner_radius, fit.stud_height + .15,
            ROUNDED_EDGES.stud_lip_radius
        ).val()
        shape = shape.fuse(stud).clean()

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
        # On left-hand specimens the mirrored west-skirt location changes
        # from Y=-16 to +16. Mirror finished geometry before adding legible ID.
        if config.direction == "left":
            # Mirror the engraving placement, not the actual letters.
            raise ValueError("Left-hand mark placement is not yet validated")
        shape = _west_skirt_mark(shape, fit, config.model_id)
    if not shape.isValid() or len(shape.Solids()) != 1:
        raise ValueError("R48 output must be a valid, single connected solid")
    return shape, {
        "model_id": config.model_id,
        "drop_mm": config.drop_mm,
        "direction": config.direction,
        "roof_z_mm": config.roof_z,
        "top_studs": list(studs),
        "complete_e31_tubes": list(tubes),
        "window_cut_volumes_mm3": window_volumes,
        "port_contract": port_contract(config.drop_mm),
        "ball_diameter_mm": BALL_TRACK.ball_diameter,
        "interior_radial_relief_mm": INTERIOR_RADIAL_RELIEF,
        "radial_relief_at_ports_mm": 0.,
    }
