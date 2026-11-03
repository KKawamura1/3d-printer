"""C02R-V1: experimental dome relief preserving C01-V5's successful lower groove.

Unlike the large flat-floor chamber of C02-V4, only a smooth spherical
upper/inner wall relief is subtracted. This is a physical comparison candidate,
not an assertion that the C02-V2 jam mechanism is already proven.
"""
from dataclasses import asdict, replace
from pathlib import Path
import hashlib
import json
import math
import struct

import cadquery as cq

from brickcad.connections import make_studs
from brickcad.model import brick_from_fit, receiver
from brickcad.provenance import design_manifest
from brickcad.standards import BALL_TRACK, DUPLO, ROUNDED_EDGES
from brickcad.verify import exact_bounds, mesh_check, VOLUME_TOL
from parts.sharp_curve.design import SharpCurve, _curve_cut, ball_intersections, ports
from parts.tunnel.e31_fit import add_e31_05_receiver_features

PART_ID = "C02R-V1"
SOURCE_CURVE_ID = "C01-V5"
FIT_PROFILE_ID = "duplo-e27-play-v1"
BODY_COURSES = 2
# Keep the earlier local ceiling dome (C02-V2) and circular mouths.
ROOF_DOME_RADIUS = 10.5
ROOF_DOME_CENTER_Z = 24.5
# Smooth inner-corner relief: z=8.50..35.00, entirely inside the outer walls.
# C01's original channel and bottom at z<=8.50 remain geometrically unchanged.
RELIEF_RADIUS = 13.25
RELIEF_CENTER_Z = 21.75


def _engrave_north(shape, label, width):
    """Keep the mark above the open-rail level and outside the ports."""
    depth = .40
    plane = cq.Plane(origin=(0, width / 2 - depth, 18.0),
                     xDir=(-1, 0, 0), normal=(0, 1, 0))
    tool = cq.Workplane(plane).text(
        label, 2.7, depth + .05, font="DejaVu Sans",
        kind="bold", combine=False).val()
    marked = shape.cut(tool).clean()
    if not marked.isValid() or len(marked.Solids()) != 1:
        raise ValueError("C02R engraving invalidated the tunnel solid")
    if shape.Volume() - marked.Volume() < .2:
        raise ValueError("C02R engraving missed the north wall")
    return marked


def build_relief(curve=SharpCurve(), *, label=PART_ID):
    """Start with C01's toroidal channel, then cut only smooth local roof relief."""
    p = replace(brick_from_fit(FIT_PROFILE_ID, nx=2, ny=2,
                               height_units=BODY_COURSES), tube_radius=6.60)
    outer = (cq.Workplane("XY")
             .box(p.width, p.depth, p.height, centered=(True, True, False))
             .edges("|Z").fillet(ROUNDED_EDGES.corner_radius)
             .edges(">Z").fillet(.5))
    body = receiver(p, outer, curve.receiver_depth, 0).val()
    body = add_e31_05_receiver_features(body, p.tubes(), p.tube_radius)

    # Same R16 groove as C01-V5: west -> south, including the original floor.
    body = body.cut(_curve_cut(curve)).clean().mirror("XZ")
    mid = -16 + curve.turn_radius / math.sqrt(2)
    dome = cq.Solid.makeSphere(
        ROOF_DOME_RADIUS, cq.Vector(mid, mid, ROOF_DOME_CENTER_Z),
        angleDegrees1=-90)
    body = body.cut(dome).clean()

    # Broad but smooth bubble at the INNER corner. No cylindrical flat floor,
    # no abrupt horizontal ledge. It expands near the ball's mid-height,
    # leaving the lower C01 groove available to steer the ball through the bend.
    if RELIEF_RADIUS > p.width / 2 - DUPLO.roof:
        raise ValueError("Relief would open the outer wall")
    if RELIEF_CENTER_Z + RELIEF_RADIUS > p.height - DUPLO.roof:
        raise ValueError("Relief would open the roof")
    if RELIEF_CENTER_Z - RELIEF_RADIUS <= curve.floor:
        raise ValueError("Relief would reach the nominal groove floor")
    bubble = cq.Solid.makeSphere(
        RELIEF_RADIUS, cq.Vector(0, 0, RELIEF_CENTER_Z),
        angleDegrees1=-90)
    body = body.cut(bubble).clean()

    studs = make_studs(p.studs(), p.height, p.stud_radius,
                       p.stud_inner_radius, p.stud_height,
                       ROUNDED_EDGES.stud_lip_radius).val()
    body = body.fuse(studs).clean()
    if not body.isValid() or len(body.Solids()) != 1:
        raise ValueError("C02R must be one connected valid solid")
    return _engrave_north(body, label, p.depth), p


def export(out=Path("build/c02-upper-relief")):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    curve = SharpCurve()
    shape, p = build_relief(curve)
    stl = out / "brick.stl"
    cq.exporters.export(shape, str(stl), tolerance=.01, angularTolerance=.1)

    # STL uses float32 vertices; remove only truly collapsed export facets.
    raw = stl.read_bytes()
    count = struct.unpack_from("<I", raw, 80)[0]
    kept = []
    for i in range(count):
        tri = raw[84 + 50 * i:134 + 50 * i]
        coords = struct.unpack("<12fH", tri)[3:12]
        if len({tuple(coords[j:j+3]) for j in (0, 3, 6)}) == 3:
            kept.append(tri)
    collapsed = count - len(kept)
    if collapsed:
        stl.write_bytes(raw[:80] + struct.pack("<I", len(kept)) + b"".join(kept))

    mesh = mesh_check(stl)
    path = ball_intersections(shape, curve, samples=19)
    oversize = ball_intersections(shape, curve, diameter=28., samples=5)
    mid = -16 + curve.turn_radius / math.sqrt(2)
    checks = dict(
        valid_brep=shape.isValid(),
        one_solid=len(shape.Solids()) == 1,
        grid=all(abs(a-b) < 1e-5 for a, b in
                 zip(exact_bounds(shape), (31.8, 31.8, 42.9))),
        mesh=mesh["passed"],
        mesh_volume=abs(mesh["signed_volume_mm3"]-shape.Volume())/shape.Volume() < .001,
        ball_path_clear=max(path) < VOLUME_TOL,
        oversized_ball_blocked=max(oversize) > VOLUME_TOL,
        receiver_hole=not shape.isInside(cq.Vector(0, 0, 1)),
        receiver_wall=shape.isInside(cq.Vector(4, 4, 1)),
        all_studs=all(shape.isInside(cq.Vector(x + 4., y, p.height + 2.))
                      for x, y in p.studs()),
        original_floor=shape.isInside(cq.Vector(mid, mid, curve.floor-.15)),
        original_floor_open=not shape.isInside(cq.Vector(mid, mid, curve.floor+.15)),
        inner_relief=not shape.isInside(cq.Vector(0, 12.5, 20.)),
        wall_north=shape.isInside(cq.Vector(0, 14.2, 20.)),
        wall_east=shape.isInside(cq.Vector(14.2, 0, 20.)),
        roof_north=shape.isInside(cq.Vector(-15.8, 0, 33.)),
        roof_south=shape.isInside(cq.Vector(0, -15.8, 33.)),
        roof_above_dome=shape.isInside(cq.Vector(mid, mid, 36.)),
        roof_above_relief=shape.isInside(cq.Vector(0, 0, 37.4)),
        relief_not_at_floor=shape.isInside(cq.Vector(0, 0, 7.)),
    )
    report = dict(
        schema_version=1, kind="duplo-c02-upper-inner-relief-experiment",
        part_id=PART_ID, source_curve_id=SOURCE_CURVE_ID,
        passed=all(checks.values()), checks=checks,
        geometry=dict(bounds_mm=exact_bounds(shape), volume_mm3=shape.Volume(),
                      parameters=asdict(p)),
        curve=asdict(curve), ports=[asdict(x) for x in ports(curve)],
        relief=dict(type="spherical_inner_corner", radius_mm=RELIEF_RADIUS,
                    center_xyz_mm=[0, 0, RELIEF_CENTER_Z],
                    bottom_z_mm=RELIEF_CENTER_Z-RELIEF_RADIUS,
                    top_z_mm=RELIEF_CENTER_Z+RELIEF_RADIUS,
                    floor_is_flat=False),
        mesh=mesh, collapsed_stl_triangles_removed=collapsed,
        ball_intersections_mm3=path,
        oversized_ball_intersections_mm3=oversize,
        design=design_manifest(p, channel_standard=BALL_TRACK,
                               finish=ROUNDED_EDGES),
        physical_fit_validated=False, physical_rolling_validated=False,
        slicing_validated=False,
        limitations=[
            "C01-V5 rolled well; C02-V2 physically jammed; the cause is not proven.",
            "This preserves the open groove bottom; a spherical inner relief is experimental.",
            "Spherical roof and remaining overhang require Bambu Studio inspection.",
            "Nominal sphere checks do not guarantee motion, speed or print tolerances.",
            "E31-05 receiver has not been retested for this geometry."
        ],
        files={"brick.stl": hashlib.sha256(stl.read_bytes()).hexdigest()},
    )
    (out / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(PART_ID, "PASS" if report["passed"] else "FAIL", checks, flush=True)
    if not report["passed"]:
        raise RuntimeError("C02R geometry validation failed")
    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("build/c02-upper-relief"))
    export(parser.parse_args().out)
