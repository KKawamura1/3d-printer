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

from brickcad.course_contract import (
    course_fit,
)
from brickcad.course_section_profiles import (
    end_relief_blend, interior_radius_mm, passage_section_wire,
    validate_interior_relief,
)
from brickcad.course_r48_building_blocks import (
    outer_section_wire, sweep_enclosure, place_r48_wire,
)
from brickcad.standards import BALL_TRACK, DUPLO, ROUNDED_EDGES
from brickcad.course_r48_sloped_tunnel import (
    FULL_TUBES as PROVEN_FULL_TUBES,
    CAVITY_DEPTH as PROVEN_RECEIVER_DEPTH,
    open_curve as build_proven_sc02_open_curve,
    add_curve_connections as add_proven_sc02_connections,
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
        validate_interior_relief(
            HALF, extra_radius_mm=self.relief_mm,
            minimum_wall_mm=MIN_RADIAL_SIDEWALL_MM)
        if not self.model_id or len(self.model_id) > 32:
            raise ValueError("Explicit versioned experiment model ID required")

    @property
    def roof_z(self):
        # Identical top-stud plane across each part; 2 units for E01,
        # 3 for SC02. DUPLO studs cannot be placed on a slanted roof.
        return 2 * DUPLO.height + self.drop_mm


@dataclass(frozen=True)
class R48FamilyConfig:
    """One public recipe for R48 open/roofed and level/sloped variants.

    Open curves keep their proven course_loft_family shell; roofed curves
    retain the SC02-derived curved underbody. No successful CAD is rewritten.
    """
    model_id: str
    drop_mm: float
    enclosure: str  # 'open' or 'roofed'
    direction: str = "right"
    relief_mm: float | None = None

    def __post_init__(self):
        if self.enclosure not in ("open", "roofed"):
            raise ValueError("R48 enclosure must be open or roofed")
        if self.direction not in ("right", "left"):
            raise ValueError("R48 direction must be right or left")
        if self.drop_mm not in (0., DUPLO.height):
            raise ValueError("Only level or one-DUPLO-height R48 is supported")
        if not self.model_id or len(self.model_id) > 32:
            raise ValueError("Versioned R48 model ID is required")
        if self.enclosure == "open" and self.relief_mm is not None:
            raise ValueError("Open curves must keep their proven track profile")
        if self.enclosure == "roofed":
            R48PairConfig(self.model_id, self.drop_mm, self.direction,
                          relief_mm=INTERIOR_RADIAL_RELIEF if self.relief_mm is None
                          else self.relief_mm)

    @property
    def roof_z(self):
        """Top of the roof for tunnel variants, before DUPLO studs."""
        if self.enclosure != "roofed":
            raise ValueError("Open R48 rail does not have a roof")
        return 2 * DUPLO.height + self.drop_mm


def build_r48_family(config, *, marked=True):
    """Build four variants through one interface and shared section/path.

    Enclosure-specific outer shells and support booleans remain different
    to preserve historical BRep parity of the proven open and SC02 parts.
    """
    if not isinstance(config, R48FamilyConfig):
        raise TypeError("R48FamilyConfig required")
    if config.enclosure == "roofed":
        return build_r48(R48PairConfig(
            config.model_id, config.drop_mm, config.direction,
            relief_mm=INTERIOR_RADIAL_RELIEF if config.relief_mm is None
            else config.relief_mm), marked=marked)

    from brickcad.course_loft_family import LoftSettings, build_course
    settings = LoftSettings("gentle", config.drop_mm, False,
                            config.direction == "left", "west", 12.)
    shape, fit = build_course(settings,
                              label=config.model_id if marked else None)
    return shape, {
        "model_id": config.model_id,
        "drop_mm": config.drop_mm,
        "enclosure": "open",
        "direction": config.direction,
        "underbody_source": "course_loft_family.build_course",
        "port_contract": port_contract(config.drop_mm),
        "physical_fit_validated": False,
    }


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


def _progress(t):
    length = RADIUS * math.pi / 2
    distance = min(max(0., t), max(0., 1 - t)) * length
    return end_relief_blend(distance, mode="smoothstep-factored")


def _outer_wire(t, config):
    # Do not create a rectangular LEGO box and crop its remnants.
    # Sweep the intended R48 annular envelope directly.
    w = outer_section_wire(
        cq.Workplane("XZ"), inner=INNER, outer=OUTER,
        bottom=BALL_TRACK.floor - .15, top=config.roof_z,
        top_corner_radius=ROUNDED_EDGES.corner_radius)
    return place_r48_wire(w, t)


def _passage_wire(t, config):
    floor = floor_z(t, config.drop_mm)
    progress = _progress(t)
    radius = interior_radius_mm(progress, extra_radius_mm=config.relief_mm)
    roof = floor + 30.3
    wire = passage_section_wire(
        cq.Workplane("XZ"), floor=floor, radius=radius,
        center_x=RADIUS, roof=roof, blend=progress)
    return place_r48_wire(wire, t)


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


def _west_skirt_label_tool(fit, model_id):
    """Keep every 5mm glyph inside the *actual* short west receiver skirt.

    The experimental prefix is preserved in files and reports, but is
    redundant on the physical part: X89-SC02-R10 is nearly 40mm wide,
    whereas this front face is only ~32mm wide. Cutting any part of a glyph
    used to pass the old nonzero-volume test despite visible clipping.
    """
    engraved_id = model_id.removeprefix("X89-")
    plane = cq.Plane(
        origin=(-fit.width / 2 + .4, -16., 2.35),
        xDir=(0, -1, 0), normal=(-1, 0, 0),
    )
    tool = (cq.Workplane(plane)
            .text(engraved_id, 5., .45, font="DejaVu Sans",
                  kind="bold", combine=False).val())
    bounds = tool.BoundingBox()
    # The west end has a 31.9mm-wide low receiver skirt (Y -31.9..0).
    # Keep a margin at both ends, above the bottom edge fillet, and below
    # the original SC02 receiver ceiling at Z=CAVITY_DEPTH (4.75mm).
    if not (-fit.depth / 2 + 1. <= bounds.ymin
            and bounds.ymax <= -1.
            and .4 <= bounds.zmin
            and bounds.zmax <= PROVEN_RECEIVER_DEPTH - .4):
        raise ValueError(
            f"Engraving {engraved_id!r} exceeds the west receiver skirt: "
            f"Y=[{bounds.ymin:.2f},{bounds.ymax:.2f}], "
            f"Z=[{bounds.zmin:.2f},{bounds.zmax:.2f}]")
    return tool


def _west_skirt_mark(shape, fit, model_id):
    tool = _west_skirt_label_tool(fit, model_id)
    marked = shape.cut(tool).clean()
    if (not marked.isValid() or len(marked.Solids()) != 1 or
            shape.Volume() - marked.Volume() < 2):
        raise ValueError("The experimental mark must cut the west skirt")
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
    fit = course_fit(nx=4, ny=4,
                     height_units=2 if config.drop_mm == 0 else 3)
    proven_base, proven_fit = _proven_foundation()
    if (proven_fit.cavity_xy != fit.cavity_xy
            or proven_fit.tube_radius != fit.tube_radius
            or set(PROVEN_FULL_TUBES) != set(complete_tubes(fit))):
        raise ValueError("The production SC02 foundation no longer matches E31-05")

    ts = [-.02] + [i / SAMPLE_STATIONS for i in range(SAMPLE_STATIONS + 1)] + [1.02]
    cover, passage = sweep_enclosure(
        lambda t: _outer_wire(t, config),
        lambda t: _passage_wire(t, config), ts, ruled=True)
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
    shape = add_proven_sc02_connections(
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
