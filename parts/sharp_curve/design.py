"""C01-V2: right-hand open 90-degree DUPLO curve, 2x2 by one course.

The rolling centreline is a R16 quarter-circle, west entry to south exit.
Static sphere clearance does not establish reliable rolling at this tight radius.
"""
from dataclasses import asdict, dataclass, replace
from pathlib import Path
import hashlib
import json
import math
import struct

import cadquery as cq

from brickcad.connections import make_studs
from brickcad.model import brick_from_fit, receiver
from brickcad.ports import Port
from brickcad.provenance import design_manifest
from brickcad.standards import BALL_TRACK, DUPLO, ROUNDED_EDGES
from brickcad.verify import exact_bounds, intersection, mesh_check, VOLUME_TOL
from parts.tunnel.e31_fit import add_e31_05_receiver_features

PART_ID = "C01-V2"
FIT_PROFILE_ID = "duplo-e27-play-v1"


@dataclass(frozen=True)
class SharpCurve:
    turn_radius: float = DUPLO.pitch
    floor: float = BALL_TRACK.floor
    section_radius: float = BALL_TRACK.radius
    ball_diameter: float = BALL_TRACK.ball_diameter
    receiver_depth: float = 4.75
    numerical_lift: float = 0.05

    def __post_init__(self):
        if abs(self.turn_radius - DUPLO.pitch) > 1e-6:
            raise ValueError("C01-V2 is a 2x2 R16 curve")
        if self.section_radius >= self.turn_radius - 1.6:
            raise ValueError("No space remains for the inside corner")
        if self.floor - self.receiver_depth < 1.6 - 1e-6:
            raise ValueError("Receiver must leave a 1.6 mm floor")
        if self.ball_diameter <= 0 or self.ball_diameter / 2 >= self.section_radius:
            raise ValueError("Ball must fit inside the section")


def ports(curve=SharpCurve()):
    """Datums on grid boundary, entering west and leaving south (right turn)."""
    return (
        Port("west", (-16., 0., curve.floor), (-1., 0., 0.), curve.section_radius),
        Port("south", (0., -16., curve.floor), (0., -1., 0.), curve.section_radius),
    )


def ball_position(degrees, curve=SharpCurve(), diameter=None):
    """Degrees run from +90 (west) to zero (south) about (-16,-16)."""
    a = math.radians(degrees)
    r = curve.ball_diameter if diameter is None else diameter
    return cq.Vector(-16 + curve.turn_radius * math.cos(a),
                     -16 + curve.turn_radius * math.sin(a),
                     curve.floor + r/2 + curve.numerical_lift)


def ball_intersections(shape, curve=SharpCurve(), *, diameter=None, samples=19):
    if samples < 2:
        raise ValueError("At least two sampling positions are required")
    d = curve.ball_diameter if diameter is None else diameter
    if d <= 0:
        raise ValueError("Ball diameter must be positive")
    return [
        intersection(shape, cq.Solid.makeSphere(
            d/2, ball_position(90*i/(samples-1), curve, d),
            angleDegrees1=-90))
        for i in range(samples)
    ]


def _curve_cut(curve):
    """Exact quarter-torus cut. The nominal ends are 0.1 mm outside the body.

    Do not overlap tangent cylinders: their BRep seams produced open STL edges.
    The section and floor exactly match the existing straight-track standard.
    """
    torus = (cq.Workplane("XZ")
             .moveTo(curve.turn_radius, curve.floor + curve.section_radius)
             .circle(curve.section_radius)
             .revolve(90, (0, 0), (0, 1)).val()
             .rotate((0, 0, 0), (0, 0, 1), -90)
             .translate((-16, 16, 0)))
    return torus


def _engrave_north(shape, label, width):
    """Place revision text on the non-running north face, below the top."""
    depth = 0.4
    plane = cq.Plane(origin=(0, width/2 - depth, 11.5),
                     xDir=(-1, 0, 0), normal=(0, 1, 0))
    tool = (cq.Workplane(plane).text(label, 2.7, depth + .05,
                                    font="DejaVu Sans", kind="bold",
                                    combine=False).val())
    marked = shape.cut(tool).clean()
    if not marked.isValid() or len(marked.Solids()) != 1:
        raise ValueError("Engraving invalidated curve geometry")
    if shape.Volume() - marked.Volume() < 0.2:
        raise ValueError("Engraved revision did not intersect the north wall")
    return marked


def build_curve(curve=SharpCurve(), *, label=PART_ID):
    p = replace(brick_from_fit(FIT_PROFILE_ID, nx=2, ny=2, height_units=1),
                tube_radius=6.60)
    outer = (cq.Workplane("XY")
             .box(p.width, p.depth, p.height, centered=(True, True, False))
             .edges("|Z").fillet(ROUNDED_EDGES.corner_radius)
             .edges(">Z").fillet(.5))
    body = receiver(p, outer, curve.receiver_depth, 0).val()
    body = add_e31_05_receiver_features(body, p.tubes(), p.tube_radius)

    # Build west -> north then reflect across XZ to give west -> south/right.
    body = body.cut(_curve_cut(curve)).clean()

    # Only one stud remains outside the complete ball envelope. Do not populate
    # the other three studs: doing so blocks a 24.26 mm ball in this footprint.
    stud = make_studs([(8., -8.)], p.height, p.stud_radius,
                      p.stud_inner_radius, p.stud_height,
                      ROUNDED_EDGES.stud_lip_radius).val()
    body = body.fuse(stud).clean().mirror("XZ")
    if not body.isValid() or len(body.Solids()) != 1:
        raise ValueError("Sharp curve must be one connected valid solid")
    return _engrave_north(body, label, p.depth), p


def export(out=Path("build/sharp-curve")):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    curve = SharpCurve()
    shape, p = build_curve(curve)
    stl = out / "brick.stl"
    cq.exporters.export(shape, str(stl), tolerance=.01, angularTolerance=.1)

    # Remove only triangles that have exactly collapsed after float32 export.
    raw = stl.read_bytes()
    kept = []
    count = struct.unpack_from("<I", raw, 80)[0]
    for i in range(count):
        triangle = raw[84+50*i:134+50*i]
        coords = struct.unpack("<12fH", triangle)[3:12]
        if len({tuple(coords[j:j+3]) for j in (0, 3, 6)}) == 3:
            kept.append(triangle)
    if len(kept) != count:
        stl.write_bytes(raw[:80] + struct.pack("<I", len(kept)) + b"".join(kept))

    mesh = mesh_check(stl)
    intersections = ball_intersections(shape, curve, samples=19)
    too_large = ball_intersections(shape, curve, diameter=28., samples=5)
    bounds = exact_bounds(shape)
    checks = dict(
        valid_brep=shape.isValid(),
        one_solid=len(shape.Solids()) == 1,
        body_grid=all(abs(a-b)<1e-5 for a,b in
                      zip(bounds, (31.8, 31.8, 23.7))),
        mesh=mesh["passed"],
        mesh_volume=abs(mesh["signed_volume_mm3"]-shape.Volume())/shape.Volume() < .001,
        ball_path_clear=max(intersections) < VOLUME_TOL,
        oversized_ball_blocked=max(too_large) > VOLUME_TOL,
        receiver_tube_hole=not shape.isInside(cq.Vector(0,0,1)),
        receiver_tube_wall=shape.isInside(cq.Vector(4.,4.,1)),
        stud_hollow=not shape.isInside(cq.Vector(8,8,22)),
        stud_wall=shape.isInside(cq.Vector(12.,8,22)),
        curve_floor=shape.isInside(cq.Vector(
            -16+curve.turn_radius/math.sqrt(2),
            -16+curve.turn_radius/math.sqrt(2), curve.floor-.15)),
    )
    report = dict(
        schema_version=1, kind="duplo-sharp-curve",
        part_id=PART_ID, passed=all(checks.values()),
        checks=checks, geometry=dict(bounds_mm=bounds,
                                     volume_mm3=shape.Volume(),
                                     parameters=asdict(p)),
        curve=asdict(curve), ports=[asdict(x) for x in ports(curve)],
        studs_retained=[(8.,8.)],
        mesh=mesh,
        ball_intersections_mm3=intersections,
        oversized_ball_intersections_mm3=too_large,
        design=design_manifest(p, channel_standard=BALL_TRACK,
                               finish=ROUNDED_EDGES),
        physical_fit_validated=False,
        physical_rolling_validated=False,
        limitations=[
            "R16 is a tight 90-degree turn: momentum/friction and ball exit speed are untested.",
            "One upper stud only; the other three would obstruct the ball passage.",
            "E31-05 receiver is transferred from a 2x2 coupon, not tested on this curve.",
            "No slicer or bridge/overhang inspection has been performed.",
            "Static sphere samples and a manifold mesh do not prove physical rolling.",
        ],
        files={"brick.stl": hashlib.sha256(stl.read_bytes()).hexdigest()},
    )
    (out / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(PART_ID, "PASS" if report["passed"] else "FAIL", checks, flush=True)
    if not report["passed"]:
        raise RuntimeError("Sharp curve geometric verification failed")
    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("build/sharp-curve"))
    export(parser.parse_args().out)
