"""S02-V8: enclosed 2x2x3 sharp-right-turn steep drop tunnel.

Uses PR36's west-to-south port arrangement and PR38 S01-V5's roofed steep
drop with a 0.65 southward exit ramp. Because a complete R16 arc cannot
coexist with the shaft inside 2x2, the lower turn is a descending straight
run-out, not a true R16 curve. Physical rolling/slicing remain untested.
"""
from dataclasses import asdict, replace, dataclass
from pathlib import Path
import hashlib
import math
import json
import struct

import cadquery as cq

from brickcad.connections import make_studs
from brickcad.model import brick_from_fit, receiver
from brickcad.ports import Port
from brickcad.standards import BALL_TRACK, DUPLO, ROUNDED_EDGES
from brickcad.verify import exact_bounds, intersection, mesh_check, VOLUME_TOL
@dataclass(frozen=True)
class SharpCurve:
    floor: float = BALL_TRACK.floor
    section_radius: float = BALL_TRACK.radius

@dataclass(frozen=True)
class SteepDrop:
    low_floor: float = BALL_TRACK.floor
    drop: float = DUPLO.height
    section_radius: float = BALL_TRACK.radius
    shaft_radius: float = 13.15
    shaft_x: float = -2.0
    receiver_depth: float = 4.75
    taper_start_above_high_centre: float = 5.0
    roof_thickness: float = 1.8
    ramp_grade: float = 0.65  # 33 degrees, near max with upper inlet preserved
    ramp_start_x: float = -15.0  # run-out shelf begins just inside high mouth
    ramp_end_x: float = 13.0  # 3 mm of level exit, unchanged outlet port

    @property
    def low_centre_z(self):
        return self.low_floor + self.section_radius

    @property
    def high_centre_z(self):
        return self.low_centre_z + self.drop


def ramp_normal_clearance(d=SteepDrop()):
    """Extra centre height above a slanted floor for a full-size ball."""
    radius = BALL_TRACK.ball_diameter / 2
    return radius * (math.sqrt(1. + d.ramp_grade ** 2) - 1.)


from parts.tunnel.e31_fit import add_e31_05_receiver_features

PART_ID = "S03-V2"
SOURCE_CURVE_ID = "C01-V5"
SOURCE_DROP_ID = "S01-V5"
SHAFT_X = 0.0
# Preserve the south exit direction without opening an unwanted low west port.


def ports(d=SteepDrop(shaft_x=SHAFT_X)):
    return (
        Port("high_west", (-16., 0., d.low_floor + d.drop),
             (-1., 0., 0.), d.section_radius),
        Port("low_north", (0., 16., d.low_floor),
             (0., 1., 0.), d.section_radius),
    )


def _engrave_north(shape, label, width):
    plane = cq.Plane(origin=(0., -width / 2 + .4, 18.),
                     xDir=(1, 0, 0), normal=(0, -1, 0))
    text_tool = cq.Workplane(plane).text(
        label, 2.7, .45, font="DejaVu Sans",
        kind="bold", combine=False).val()
    result = shape.cut(text_tool).clean()
    if not result.isValid() or len(result.Solids()) != 1:
        raise ValueError("Engraving invalidated S02")
    if shape.Volume() - result.Volume() < .2:
        raise ValueError("S02 revision did not intersect north face")
    return result


def build_tunnel(d=SteepDrop(shaft_x=SHAFT_X), curve=SharpCurve(),
                 *, label=PART_ID):
    if d.low_floor != curve.floor or d.section_radius != curve.section_radius:
        raise ValueError("Curve and drop channel datums must match")
    if abs(d.drop - DUPLO.height) > 1e-6:
        raise ValueError("S02 uses exactly one DUPLO course of drop")
    if d.shaft_radius <= BALL_TRACK.ball_diameter / 2:
        raise ValueError("Shaft too narrow for the ball")
    if not .0 < d.ramp_grade <= .7 or d.ramp_end_x != 13.:
        raise ValueError("S02-V8 requires a supported S01-V5 steep exit")
    if abs(d.ramp_grade - .65) > 1e-8:
        raise ValueError("S02-V8 must use the S01-V5 33-degree ramp")
    if not -15. <= d.ramp_start_x < d.shaft_x < d.ramp_end_x:
        raise ValueError("Ramp start must precede the landing and exit")
    if d.ramp_grade * (d.ramp_end_x - d.ramp_start_x) > d.drop - 1. + 1e-9:
        raise ValueError("Ramp must preserve at least 1mm below the high entry floor")
    if d.low_floor - d.receiver_depth < 1.6 - 1e-6:
        raise ValueError("Underside receiver leaves insufficient floor")
    p = replace(brick_from_fit("duplo-e27-play-v1", nx=2, ny=2,
                               height_units=3), tube_radius=6.60)

    cap_start = d.high_centre_z + d.taper_start_above_high_centre
    cap_tip = p.height - d.roof_thickness
    if cap_tip - (d.high_centre_z + d.section_radius) < 1.5:
        raise ValueError("High passage needs roof clearance")
    if d.roof_thickness < 1.6:
        raise ValueError("Roof too thin")

    outer = (cq.Workplane("XY")
             .box(p.width, p.depth, p.height, centered=(True, True, False))
             .edges("|Z").fillet(ROUNDED_EDGES.corner_radius)
             .edges(">Z").chamfer(.5))
    body = receiver(p, outer, d.receiver_depth,
                    ROUNDED_EDGES.receiver_entry).val()

    shaft = cq.Solid.makeCylinder(
        d.shaft_radius, cap_start - d.low_floor,
        cq.Vector(d.shaft_x, 0., d.low_floor), cq.Vector(0., 0., 1.))
    cone = cq.Solid.makeCone(
        d.shaft_radius, 0., cap_tip - cap_start,
        cq.Vector(d.shaft_x, 0., cap_start), cq.Vector(0., 0., 1.))
    high = cq.Solid.makeCylinder(
        d.section_radius, 18., cq.Vector(-18., 0., d.high_centre_z),
        cq.Vector(1., 0., 0.))
    south = cq.Solid.makeCylinder(
        d.section_radius, 18., cq.Vector(0., -18., d.low_centre_z),
        cq.Vector(0., 1., 0.))

    # The PR36 right-turn direction is combined with PR38's roofed shaft.
    # Its full R16 toroidal bore cannot be inserted into this 2x2 chamber:
    # it creates an unintended low west opening and non-manifold STL seams.
    # A steep 0.65 south-facing run-out ramp makes the lower 90-degree turn instead.
    lift = ramp_normal_clearance(d)
    landing_z = d.low_centre_z + d.ramp_grade * d.ramp_end_x + lift
    start = cq.Vector(0., 0., landing_z)
    end = cq.Vector(0., -d.ramp_end_x, d.low_centre_z + lift)
    segment = end.sub(start)
    sloped_bore = cq.Solid.makeCylinder(
        d.section_radius, segment.Length, start, segment.normalized())
    shape = (body.cut(shaft).cut(cone).cut(high).cut(south)
             .cut(sloped_bore).clean())

    # Rotate S01-V5's inclined landing shelf toward south (negative Y).
    # Y increases toward the closed north face; exit is south/negative Y.
    north_start = -d.ramp_start_x
    ramp = (cq.Workplane("YZ")
            .polyline(((north_start, d.low_floor - .2),
                       (-d.ramp_end_x, d.low_floor - .2),
                       (-d.ramp_end_x, d.low_floor),
                       (north_start, d.low_floor +
                        d.ramp_grade * (d.ramp_end_x - d.ramp_start_x))))
            .close().extrude(14., both=True).val())
    shape = shape.fuse(ramp).clean()
    shape = add_e31_05_receiver_features(shape, p.tubes(), p.tube_radius)
    studs = make_studs(
        p.studs(), p.height, p.stud_radius - p.clearance,
        p.stud_inner_radius, p.stud_height,
        lip_radius=ROUNDED_EDGES.stud_lip_radius).val()
    shape = shape.fuse(studs).clean()
    if not shape.isValid() or len(shape.Solids()) != 1:
        raise ValueError("S02 needs one connected, valid solid")
    return _engrave_north(shape.mirror("XZ"), label, p.depth), p


def _path_centres(d):
    """Upper west inlet, vertical shaft, sloped south run-out, low south exit."""
    lift = ramp_normal_clearance(d)
    landing_z = d.low_centre_z + d.ramp_grade * d.ramp_end_x + lift
    return (
        cq.Vector(-16., 0., d.high_centre_z),
        cq.Vector(0., 0., d.high_centre_z),
        cq.Vector(0., 0., landing_z),
        cq.Vector(0., d.ramp_end_x, d.low_centre_z + lift),
        cq.Vector(0., 16., d.low_centre_z),
    )


def ball_path_collisions(shape, d=SteepDrop(shaft_x=SHAFT_X)):
    """Full sphere samples along the descending exit path."""
    r = BALL_TRACK.ball_diameter / 2
    points = _path_centres(d)
    centres = []
    for a, b in zip(points, points[1:]):
        for i in range(6):
            t = i / 5
            centres.append(a.add(b.sub(a).multiply(t)))
    return [intersection(shape, cq.Solid.makeSphere(
        r, c, angleDegrees1=-90)) for c in centres]


def swept_ball_path_collisions(shape, d=SteepDrop(shaft_x=SHAFT_X)):
    """Continuous capsules along linearized ramp and drop segments."""
    r = BALL_TRACK.ball_diameter / 2
    points = _path_centres(d)
    swept = []
    for a, b in zip(points, points[1:]):
        v = b.sub(a)
        swept.append(intersection(shape, cq.Solid.makeCylinder(
            r, v.Length, a, v.normalized())))
        swept.append(intersection(shape, cq.Solid.makeSphere(
            r, a, angleDegrees1=-90)))
    swept.append(intersection(shape, cq.Solid.makeSphere(
        r, points[-1], angleDegrees1=-90)))
    return swept


def _remove_collapsed_triangles(stl):
    raw = stl.read_bytes()
    kept = []
    count = struct.unpack_from("<I", raw, 80)[0]
    for i in range(count):
        tri = raw[84 + 50*i:134 + 50*i]
        coords = struct.unpack("<12fH", tri)[3:12]
        if len({tuple(coords[j:j+3]) for j in (0, 3, 6)}) == 3:
            kept.append(tri)
    if len(kept) != count:
        stl.write_bytes(raw[:80] + struct.pack("<I", len(kept))
                        + b"".join(kept))
    return count - len(kept)


def export(out=Path("build/steep-sharp-curve-tunnel")):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    d = SteepDrop(shaft_x=SHAFT_X)
    shape, p = build_tunnel(d)
    stl = out / "brick.stl"
    cq.exporters.export(shape, str(stl), tolerance=.01,
                        angularTolerance=.1)
    removed = _remove_collapsed_triangles(stl)
    mesh = mesh_check(stl)
    print("S02 STL mesh:", mesh, flush=True)
    samples = ball_path_collisions(shape, d)
    sweeps = swept_ball_path_collisions(shape, d)
    bounds = exact_bounds(shape)
    checks = dict(
        single_valid_solid=shape.isValid() and len(shape.Solids()) == 1,
        bounds_2x2x3=all(abs(a - b) < .01
                           for a, b in zip(bounds, (31.8, 31.8, 62.1))),
        watertight_mesh=mesh["passed"],
        sampled_ball_clear=max(samples) < VOLUME_TOL,
        continuous_ball_path_clear=max(sweeps) < VOLUME_TOL,
        lower_west_wall_closed=shape.isInside(
            cq.Vector(-15.7, 0., d.low_centre_z)),
        roof_present=shape.isInside(cq.Vector(0., 0., p.height - .1)),
        lower_floor_present=shape.isInside(cq.Vector(0., 0., 6.2)),
        receiver_bore_open=not shape.isInside(cq.Vector(0., 0., 1.)),
        receiver_wall_present=shape.isInside(cq.Vector(3.89, 3.89, 1.)),
        four_upper_studs=all(shape.isInside(
            cq.Vector(x + 3.9, y, p.height + 1.))
            for x, y in p.studs()),
        one_course_drop=(abs(ports(d)[0].floor_xyz_mm[2]
                             - ports(d)[1].floor_xyz_mm[2]
                             - DUPLO.height) < 1e-6),
        ramp_grade_matches_s01_v5=abs(d.ramp_grade - .65) < 1e-8,
        landing_to_runout_drop=abs(
            d.ramp_grade * (d.ramp_end_x - d.shaft_x) - 8.45) < 1e-7,
        high_inlet_floor_margin=(
            d.drop - d.ramp_grade * (d.ramp_end_x - d.ramp_start_x) >= 1. - 1e-8),
        downhill_floor_at_landing=shape.isInside(
            cq.Vector(0., 0., d.low_floor + 1.)),
        downhill_headroom_at_landing=not shape.isInside(cq.Vector(
            0., 0., d.low_floor + d.ramp_grade * d.ramp_end_x + 1.)),
        exit_floor_clear=not shape.isInside(
            cq.Vector(0., d.ramp_end_x, d.low_floor + .2)),
    )
    report = dict(
        part_id=PART_ID, sources=[SOURCE_CURVE_ID, SOURCE_DROP_ID],
        passed=all(checks.values()), checks=checks,
        description="2x2x3 roofed high west -> low north 90-degree drop",
        parameters=asdict(d), bounds_mm=bounds,
        ports=[asdict(port) for port in ports(d)],
        left_turn=dict(source=SOURCE_CURVE_ID,
                        direction="west-high-to-north-low",
                        full_R16_arc=False,
                        grade=d.ramp_grade,
                        ramp_angle_deg=math.degrees(math.atan(d.ramp_grade)),
                        landing_to_runout_drop_mm=d.ramp_grade * (d.ramp_end_x - d.shaft_x),
                        inlet_floor_margin_mm=d.drop - d.ramp_grade * (
                            d.ramp_end_x - d.ramp_start_x),
                        ramp_end_south_mm=d.ramp_end_x),
        mesh=mesh, collapsed_facets_removed=removed,
        ball_samples_mm3=samples, ball_sweep_mm3=sweeps,
        sha256_stl=hashlib.sha256(stl.read_bytes()).hexdigest(),
        physical_rolling_validated=False,
        support_free_slicing_validated=False,
        physical_fit_validated=False,
        limitations=[
            "The drop chamber and 33-degree south run-out are connected and fully roofed.",
            "The south-directed sloping exit turns 90 degrees; it is not a complete R16 circular arc.",
            "Swept spheres prove only geometric clearance, not spontaneous exit after the fall.",
            "Tapered roof, underside, E31-05 and stud overhangs require physical/slicer checks.",
        ])
    (out / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    from brickcad.render import viewer
    viewer_report={**report,'geometry':dict(bounds_mm=exact_bounds(shape),parameters=asdict(p)),
                   'fit':dict(insertion=[],poses=[])}
    for name,dx,angle in [('aligned',0,0),('cross_90',0,90),('half_pitch_negative_control',8,0)]:
        upper=shape.rotate((0,0,0),(0,0,1),angle).translate((dx,0,p.height))
        overlap=intersection(shape,upper)
        row=dict(name=name,xyz_mm=[dx,0,p.height],rotation_deg=angle,intersection_mm3=overlap,collision=overlap>VOLUME_TOL)
        if name=='aligned':viewer_report['fit']['insertion'].append(dict(row,pair='printed/printed',lift_mm=0))
        else:viewer_report['fit']['poses'].append(row)
    viewer(shape.copy(mesh=False),p,viewer_report,out)
    cq.exporters.export(shape,str(out/'brick.step'))
    print(PART_ID, "PASS" if report["passed"] else "FAIL", checks, flush=True)
    if not report["passed"]:
        raise RuntimeError("S02 CAD verification failed")
    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path,
                        default=Path("build/steep-sharp-curve-tunnel"))
    export(parser.parse_args().out)
