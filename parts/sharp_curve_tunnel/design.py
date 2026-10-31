"""C02-V2: enclosed 2x2x2 R16 right-angle tunnel companion to C01-V2.

The running surface is the same quarter-torus as C01-V2. A second DUPLO
course provides a real ceiling and supports all four top studs.
CAD clearance is not evidence that a ball will carry momentum through R16.
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

PART_ID = "C02-V2"
SOURCE_CURVE_ID = "C01-V2"
FIT_PROFILE_ID = "duplo-e27-play-v1"
BODY_COURSES = 2
# Inner roof is raised locally, keeping the circular end openings unchanged.
# A mid-bend spherical relief avoids a twisted tight-radius loft and leaves
# 3.4 mm of roof at the highest point.
ROOF_DOME_RADIUS = 10.5
ROOF_DOME_CENTER_Z = 24.5


def _engrave_north(shape, label, width):
    """Engrave the north face, away from both tunnel openings and the studs."""
    depth = .40
    plane = cq.Plane(origin=(0, width/2-depth, 18.0),
                     xDir=(-1, 0, 0), normal=(0, 1, 0))
    tool = cq.Workplane(plane).text(
        label, 2.7, depth+.05, font="DejaVu Sans",
        kind="bold", combine=False).val()
    marked = shape.cut(tool).clean()
    if not marked.isValid() or len(marked.Solids()) != 1:
        raise ValueError("C02 engraving invalidated the tunnel solid")
    if shape.Volume()-marked.Volume() < .2:
        raise ValueError("C02 engraving did not touch the north wall")
    return marked


def build_tunnel(curve=SharpCurve(), *, label=PART_ID):
    """Same west-to-south R16 channel as C01; add roof, not a new rail profile."""
    p = replace(brick_from_fit(FIT_PROFILE_ID, nx=2, ny=2,
                               height_units=BODY_COURSES), tube_radius=6.60)
    outer = (cq.Workplane("XY")
             .box(p.width, p.depth, p.height, centered=(True,True,False))
             .edges("|Z").fillet(ROUNDED_EDGES.corner_radius)
             .edges(">Z").fillet(.5))
    body = receiver(p, outer, curve.receiver_depth, 0).val()
    body = add_e31_05_receiver_features(body, p.tubes(), p.tube_radius)
    # C01's toroidal cut initially travels west -> north; reflect it to
    # west -> south. Its circular mouths match the open rail exactly.
    body = body.cut(_curve_cut(curve)).clean().mirror("XZ")
    mid_x = -16+curve.turn_radius/math.sqrt(2)
    dome = cq.Solid.makeSphere(
        ROOF_DOME_RADIUS, cq.Vector(mid_x, mid_x, ROOF_DOME_CENTER_Z),
        angleDegrees1=-90)
    # The spherical cap intersects the torus only inside the bend.
    # At the west/south mouths the original circular profile is untouched.
    body = body.cut(dome).clean()
    studs = make_studs(p.studs(), p.height, p.stud_radius,
                       p.stud_inner_radius, p.stud_height,
                       ROUNDED_EDGES.stud_lip_radius).val()
    body = body.fuse(studs).clean()
    if not body.isValid() or len(body.Solids()) != 1:
        raise ValueError("C02 tunnel must be one connected valid solid")
    return _engrave_north(body, label, p.depth), p


def export(out=Path("build/sharp-curve-tunnel")):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    curve = SharpCurve()
    shape, p = build_tunnel(curve)
    stl = out / "brick.stl"
    cq.exporters.export(shape, str(stl), tolerance=.01, angularTolerance=.1)

    # As in C01-V2, drop only float32 triangles collapsed during STL export.
    raw = stl.read_bytes()
    triangles = []
    count = struct.unpack_from("<I", raw, 80)[0]
    for i in range(count):
        triangle = raw[84+50*i:134+50*i]
        coords = struct.unpack("<12fH", triangle)[3:12]
        if len({tuple(coords[j:j+3]) for j in (0,3,6)}) == 3:
            triangles.append(triangle)
    collapsed = count-len(triangles)
    if collapsed:
        stl.write_bytes(raw[:80]+struct.pack("<I",len(triangles))+b"".join(triangles))

    mesh = mesh_check(stl)
    path = ball_intersections(shape, curve, samples=19)
    oversize = ball_intersections(shape, curve, diameter=28., samples=5)
    bounds = exact_bounds(shape)
    ceiling_z = max(curve.floor+2*curve.section_radius,
                    ROOF_DOME_CENTER_Z+ROOF_DOME_RADIUS)
    mid_xy = -16+curve.turn_radius/math.sqrt(2)
    checks = dict(
        valid_brep=shape.isValid(),
        one_solid=len(shape.Solids())==1,
        body_grid=all(abs(a-b)<1e-5 for a,b in zip(bounds,(31.8,31.8,42.9))),
        mesh=mesh["passed"],
        mesh_volume=abs(mesh["signed_volume_mm3"]-shape.Volume())/shape.Volume()<.001,
        ball_path_clear=max(path)<VOLUME_TOL,
        oversized_ball_blocked=max(oversize)>VOLUME_TOL,
        receiver_tube_hole=not shape.isInside(cq.Vector(0,0,1)),
        receiver_tube_wall=shape.isInside(cq.Vector(4,4,1)),
        all_stud_floors=all(shape.isInside(cq.Vector(x,y,p.height-.1))
                             for x,y in p.studs()),
        studs_hollow=all(not shape.isInside(cq.Vector(x,y,p.height+2.))
                          for x,y in p.studs()),
        studs_walls=all(shape.isInside(cq.Vector(x+4.,y,p.height+2.))
                         for x,y in p.studs()),
        roof_present=shape.isInside(cq.Vector(mid_xy,mid_xy,p.height-1.)),
        inner_roof_raised=not shape.isInside(cq.Vector(mid_xy,mid_xy,34.)),
        roof_solid_above_dome=shape.isInside(cq.Vector(mid_xy,mid_xy,36.)),
        west_mouth_circular=shape.isInside(cq.Vector(-15.8,0,33.)),
        south_mouth_circular=shape.isInside(cq.Vector(0,-15.8,33.)),
        roof_min_thickness=p.height-ceiling_z>=DUPLO.roof,
        curve_floor=shape.isInside(cq.Vector(
            -16+curve.turn_radius/math.sqrt(2),
            -16+curve.turn_radius/math.sqrt(2), curve.floor-.15)),
    )
    report = dict(
        schema_version=1, kind="duplo-sharp-curve-tunnel",
        part_id=PART_ID, source_curve_id=SOURCE_CURVE_ID,
        passed=all(checks.values()), checks=checks,
        geometry=dict(bounds_mm=bounds, volume_mm3=shape.Volume(),
                      parameters=asdict(p)),
        curve=asdict(curve), ports=[asdict(x) for x in ports(curve)],
        roof=dict(style="circular_mouth_raised_center_dome",
                  minimum_thickness_mm=p.height-ceiling_z,
                  ceiling_max_z_mm=ceiling_z,
                  dome_radius_mm=ROOF_DOME_RADIUS,
                  dome_center_z_mm=ROOF_DOME_CENTER_Z,
                  all_four_studs=True),
        mesh=mesh, collapsed_stl_triangles_removed=collapsed,
        ball_intersections_mm3=path,
        oversized_ball_intersections_mm3=oversize,
        design=design_manifest(p, channel_standard=BALL_TRACK,
                               finish=ROUNDED_EDGES),
        physical_fit_validated=False,
        physical_rolling_validated=False,
        slicing_validated=False,
        limitations=[
            "Very tight R16 curve: a collision-free ball may still stop or jam.",
            "Circular mouths, with a spherical roof relief near the middle of the bend.",
            "Roof and underside bridge/overhang require Bambu Studio slicing.",
            "E31-05 receiver is a transferred trial, not physically verified here.",
            "Static sphere samples and manifold STL do not prove rolling.",
        ],
        files={"brick.stl":hashlib.sha256(stl.read_bytes()).hexdigest()},
    )
    (out/"report.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print(PART_ID,"PASS" if report["passed"] else "FAIL",checks,flush=True)
    if not report["passed"]:
        raise RuntimeError("C02 tunnel geometry validation failed")
    return report


if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",type=Path,default=Path("build/sharp-curve-tunnel"))
    export(parser.parse_args().out)
