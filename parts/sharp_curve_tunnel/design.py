"""C02-V4: 2x2x2 horizontal right-turn tunnel with a widened central chamber.

C02-V2 passed nominal ball clearance but a real printed ball stalled in the bend.
This revision retains circular ports and the original R16 groove while relieving
the central pinch with a broad, domed turning chamber. Physical retest required.
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

PART_ID = "C02-V4"
SOURCE_CURVE_ID = "C01-V5"
FIT_PROFILE_ID = "duplo-e27-play-v1"
BODY_COURSES = 2
# Inner roof is raised locally, keeping the circular end openings unchanged.
# A mid-bend spherical relief avoids a twisted tight-radius loft and leaves
# 3.4 mm of roof at the highest point.
ROOF_DOME_RADIUS = 10.5
ROOF_DOME_CENTER_Z = 24.5
# 26.5 mm wide central turning room, entirely within the 31.8 mm body.
# Leaves a 2.65 mm exterior wall and >=1.6 mm above the underside receiver.
CHAMBER_RADIUS = 13.25
CHAMBER_CAP_Z = 21.0


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
    """Preserve the circular ports and R16 groove, widen the central turn."""
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
    # The real C02-V2 print jammed despite nominal R16 ball-clearance checks.
    # At 2x2 size a tightly swept torus gives almost no usable lateral freedom.
    # Cut a 26.5 mm-wide room around the turning corner: its flat floor is at
    # the standard 6.35 mm rail datum, with a hemispherical upper roof rather
    # than a large unsupported horizontal bridge. The chamber radius stays
    # 2.65 mm inside each outer face and never reaches either edge opening,
    # so both circular mouths and the receiver remain unchanged.
    if CHAMBER_RADIUS > min(p.width, p.depth) / 2 - DUPLO.roof:
        raise ValueError("Turning chamber would break through an external wall")
    if CHAMBER_CAP_Z + CHAMBER_RADIUS > p.height - DUPLO.roof:
        raise ValueError("Turning chamber would leave an insufficient roof")
    if curve.floor - curve.receiver_depth < DUPLO.roof - 1e-6:
        raise ValueError("Turning chamber would remove the receiver floor")
    chamber_lower = cq.Solid.makeCylinder(
        CHAMBER_RADIUS, CHAMBER_CAP_Z - curve.floor,
        cq.Vector(0, 0, curve.floor))
    chamber_cap = cq.Solid.makeSphere(
        CHAMBER_RADIUS, cq.Vector(0, 0, CHAMBER_CAP_Z),
        angleDegrees1=0, angleDegrees2=90)
    body = body.cut(chamber_lower).cut(chamber_cap).clean()
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
        chamber_floor=shape.isInside(cq.Vector(0,0,curve.floor-.15)),
        chamber_open_at_12_5=not shape.isInside(cq.Vector(0,12.5,20.)),
        chamber_north_wall=shape.isInside(cq.Vector(0,14.2,20.)),
        chamber_east_wall=shape.isInside(cq.Vector(14.2,0,20.)),
        chamber_roof=shape.isInside(cq.Vector(0,0,p.height-1.)),
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
        turning_chamber=dict(
            type="cylindrical_floor_hemispherical_roof",
            radius_mm=CHAMBER_RADIUS,
            diameter_mm=2*CHAMBER_RADIUS,
            dome_equator_z_mm=CHAMBER_CAP_Z,
            lowest_floor_z_mm=curve.floor,
            nominal_min_side_wall_mm=min(p.width,p.depth)/2-CHAMBER_RADIUS,
            physical_rolling_validated=False),
        mesh=mesh, collapsed_stl_triangles_removed=collapsed,
        ball_intersections_mm3=path,
        oversized_ball_intersections_mm3=oversize,
        design=design_manifest(p, channel_standard=BALL_TRACK,
                               finish=ROUNDED_EDGES),
        physical_fit_validated=False,
        physical_rolling_validated=False,
        slicing_validated=False,
        limitations=[
            "C02-V2 physically jammed in the bend; C02-V4 is an unprinted corrective prototype.",
            "A widened room improves geometric freedom, but impact/friction may still stop the ball.",
            "The 26.5 mm chamber is joined to circular mouths; inspect transitions for ledges.",
            "Hemispherical chamber roof and internal floor need support-free slicer inspection.",
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
