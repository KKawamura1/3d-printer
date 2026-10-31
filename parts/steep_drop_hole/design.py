"""S01-V5: enclosed 2x2x3 steep drop tunnel, high west inlet to low east outlet.

The roofed vertical shaft has a printable tapered apex instead of an exposed
opening or a broad horizontal bridge. This is a geometric prototype; ball
dynamics, support-free slicing, fit and child safety are not yet validated.
"""
from dataclasses import asdict, dataclass, replace
from pathlib import Path
import hashlib
import math
import json
import struct

import cadquery as cq

from brickcad.connections import make_studs
from brickcad.marking import engrave
from brickcad.model import brick_from_fit, receiver
from brickcad.ports import Port
from brickcad.standards import BALL_TRACK, DUPLO, ROUNDED_EDGES
from brickcad.verify import VOLUME_TOL, exact_bounds, intersection, mesh_check
from parts.tunnel.e31_fit import add_e31_05_receiver_features

PART_ID = "S01-V5"


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


def rolling_ball_path(d=SteepDrop()):
    """Geometric centreline, not a rigid-body dynamics simulation."""
    lift = ramp_normal_clearance(d)
    landing = (d.low_centre_z +
               d.ramp_grade * (d.ramp_end_x - d.shaft_x) + lift)
    return (
        cq.Vector(-16., 0., d.high_centre_z),
        cq.Vector(d.shaft_x, 0., d.high_centre_z),
        cq.Vector(d.shaft_x, 0., landing),
        cq.Vector(d.ramp_end_x, 0., d.low_centre_z + lift),
        cq.Vector(16., 0., d.low_centre_z),
    )


def ports(d=SteepDrop()):
    """Entry and exit edge datums, separated vertically by one course."""
    return (
        Port("high_west", (-16., 0., d.low_floor + d.drop),
             (-1., 0., 0.), d.section_radius),
        Port("low_east", (16., 0., d.low_floor),
             (1., 0., 0.), d.section_radius),
    )


def build_steep_drop(d=SteepDrop()):
    if d.shaft_radius <= BALL_TRACK.ball_diameter / 2:
        raise ValueError("Shaft must clear the ball diameter")
    if d.shaft_radius >= 15.9 - 1.6:
        raise ValueError("Shaft must leave an external side wall")
    if d.low_floor - d.receiver_depth < 1.6 - 1e-6:
        raise ValueError("A 1.6 mm floor must remain above the underside receiver")

    p = replace(brick_from_fit("duplo-e27-play-v1", nx=2, ny=2, height_units=3),
                tube_radius=6.60)
    cap_start = d.high_centre_z + d.taper_start_above_high_centre
    cap_tip = p.height - d.roof_thickness
    if not d.high_centre_z < cap_start < cap_tip:
        raise ValueError("Taper must start above the high passage and finish under the roof")
    if cap_tip - (d.high_centre_z + d.section_radius) < 1.5:
        raise ValueError("Need overhead clearance above the entrance ball")
    if d.roof_thickness < 1.6:
        raise ValueError("Keep at least 1.6 mm roof material")
    if not 0. < d.ramp_grade <= .7:
        raise ValueError("Run-out grade outside supported steepness")
    if not -15. <= d.ramp_start_x < d.shaft_x < d.ramp_end_x <= 13.:
        raise ValueError("Ramp must start inside high entry and stop before exit")
    if d.ramp_grade * (d.ramp_end_x - d.shaft_x) < 2.:
        raise ValueError("Ramp must provide useful fall after landing")
    # The inclined shelf near the west mouth must remain at least 1 mm
    # BELOW the high entrance floor. A steeper full-length wedge otherwise
    # creates an incoming step and can slow or jam the ball.
    if d.ramp_grade * (d.ramp_end_x - d.ramp_start_x) > d.drop - 1. + 1e-9:
        raise ValueError("Ramp would intrude into high inlet floor")

    outer = (cq.Workplane("XY")
             .box(p.width, p.depth, p.height, centered=(True, True, False))
             .edges("|Z").fillet(ROUNDED_EDGES.corner_radius)
             .edges(">Z").chamfer(.5))
    body = receiver(p, outer, d.receiver_depth, ROUNDED_EDGES.receiver_entry)

    # The vertical chamber terminates below the top roof in a gradual cone.
    # A flat 26 mm ceiling bridge would be hostile to support-free FDM.
    shaft = cq.Solid.makeCylinder(
        d.shaft_radius, cap_start - d.low_floor,
        cq.Vector(d.shaft_x, 0, d.low_floor), cq.Vector(0, 0, 1))
    cap = cq.Solid.makeCone(
        d.shaft_radius, 0., cap_tip - cap_start,
        cq.Vector(d.shaft_x, 0, cap_start), cq.Vector(0, 0, 1))
    high = cq.Solid.makeCylinder(
        d.section_radius, 18., cq.Vector(-18., 0, d.high_centre_z),
        cq.Vector(1, 0, 0))
    low = cq.Solid.makeCylinder(
        d.section_radius, 21., cq.Vector(d.shaft_x, 0, d.low_centre_z),
        cq.Vector(1, 0, 0))
    # Widen the lower passage above the incline: adding the ramp alone
    # would collide with a full-size ball near the old horizontal roof.
    # Preserve the standard circular exit with the original low cylinder.
    path = rolling_ball_path(d)
    start, end = path[2], path[3]
    delta = end.sub(start)
    sloped_bore = cq.Solid.makeCylinder(
        d.section_radius, delta.Length, start, delta.normalized())
    shape = body.cut(shaft).cut(cap).cut(high).cut(low).cut(sloped_bore).val().clean()

    # Fused AFTER the sloped bore to retain the downhill running surface.
    # The wedge stays inside the rounded block exterior and above the
    # underside receiver's 1.6 mm roof.
    left = d.ramp_start_x
    floor = d.low_floor
    ramp = (cq.Workplane("XZ")
            .polyline(((left, floor - .2),
                       (d.ramp_end_x, floor - .2),
                       (d.ramp_end_x, floor),
                       (left, floor + d.ramp_grade * (d.ramp_end_x - left))))
            .close().extrude(14., both=True).val())
    shape = shape.fuse(ramp).clean()
    shape = add_e31_05_receiver_features(shape, p.tubes(), p.tube_radius)
    studs = make_studs(
        p.studs(), p.height, p.stud_radius - p.clearance,
        p.stud_inner_radius, p.stud_height,
        lip_radius=ROUNDED_EDGES.stud_lip_radius)
    shape = cq.Workplane("XY").newObject([shape]).union(studs).val().clean()
    if not shape.isValid() or len(shape.Solids()) != 1:
        raise ValueError("S01-V5 must be a single connected valid solid")
    shape = engrave(shape, PART_ID, x=0., y=-p.depth / 2, z=12.)
    return shape, p


def sampled_ball_collisions(shape, d=SteepDrop()):
    """Sample the descending full-ball centreline at each turn and ramp."""
    radius = BALL_TRACK.ball_diameter / 2
    path = rolling_ball_path(d)
    centres = []
    for start, end in zip(path, path[1:]):
        centres.extend(start.add(end.sub(start).multiply(i / 12.))
                       for i in range(13))
    return [intersection(shape, cq.Solid.makeSphere(
        radius, centre, angleDegrees1=-90)) for centre in centres]


def continuous_ball_path_intersections(shape, d=SteepDrop()):
    """Rigid swept-ball clearance only, not real rolling dynamics."""
    radius = BALL_TRACK.ball_diameter / 2
    path = rolling_ball_path(d)
    volumes = []
    for start, end in zip(path, path[1:]):
        delta = end.sub(start)
        swept_cylinder = cq.Solid.makeCylinder(
            radius, delta.Length, start, delta.normalized())
        volumes.append(intersection(shape, swept_cylinder))
    for centre in path:
        volumes.append(intersection(shape, cq.Solid.makeSphere(
            radius, centre, angleDegrees1=-90)))
    return volumes


def export(out=Path("build/steep-drop-hole")):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    d = SteepDrop()
    shape, p = build_steep_drop(d)
    stl = out / "brick.stl"
    cq.exporters.export(shape, str(stl), tolerance=.03, angularTolerance=.2)

    # Remove float32-collapsed facets (as in the maintained tunnel exporter).
    raw = stl.read_bytes()
    triangles = []
    for i in range(struct.unpack_from("<I", raw, 80)[0]):
        tri = raw[84 + 50 * i:134 + 50 * i]
        vertex_data = struct.unpack("<12fH", tri)[3:12]
        if len({tuple(vertex_data[k:k + 3]) for k in (0, 3, 6)}) == 3:
            triangles.append(tri)
    stl.write_bytes(raw[:80] + struct.pack("<I", len(triangles)) +
                    b"".join(triangles))

    cq.exporters.export(shape, str(out / "brick.step"))
    mesh = mesh_check(stl)
    collisions = sampled_ball_collisions(shape, d)
    sweeps = continuous_ball_path_intersections(shape, d)
    bounds = exact_bounds(shape)
    checks = {
        "single_valid_solid": shape.isValid() and len(shape.Solids()) == 1,
        "size_2x2x3_with_studs": all(abs(a - b) < .01 for a, b in
                                  zip(bounds, (31.8, 31.8, p.height + p.stud_height))),
        "watertight_mesh": mesh["passed"],
        "sampled_ball_clear": max(collisions) < VOLUME_TOL,
        "continuous_ball_path_clear": max(sweeps) < VOLUME_TOL,
        "bottom_floor_present": shape.isInside(cq.Vector(0, 0, 6.2)),
        "downhill_ramp_present": (shape.isInside(cq.Vector(
            d.shaft_x, 0, d.low_floor + 1.)) and
            not shape.isInside(cq.Vector(
                d.shaft_x, 0, d.low_floor +
                d.ramp_grade * (d.ramp_end_x - d.shaft_x) + 1.))),
        "inlet_floor_preserved": d.drop - d.ramp_grade * (
            d.ramp_end_x - d.ramp_start_x) >= 1. - 1e-9,
        "ramp_reaches_exit_floor": not shape.isInside(cq.Vector(
            d.ramp_end_x, 0, d.low_floor + .2)),
        "enclosed_roof": shape.isInside(cq.Vector(
            d.shaft_x, 0, p.height - .1)),
        "four_top_stud_walls": all(shape.isInside(cq.Vector(
            x + 3.9, y, p.height + 1.)) for x, y in p.studs()),
        "receiver_central_bore": not shape.isInside(cq.Vector(0, 0, 1.)),
        "receiver_tube_wall": shape.isInside(cq.Vector(3.89, 3.89, 1.)),
        "high_mouth_below_roof": d.high_centre_z + d.section_radius <
                                  p.height - d.roof_thickness,
        "two_ports_one_course_apart": abs(
            ports(d)[0].floor_xyz_mm[2] - ports(d)[1].floor_xyz_mm[2] -
            DUPLO.height) < 1e-6,
    }
    report = {
        "part_id": PART_ID,
        "passed": all(checks.values()),
        "shape": "enclosed steep drop tunnel with sloped run-out to low east outlet",
        "parameters": asdict(d),
        "bounds_mm": bounds,
        "checks": checks,
        "mesh": mesh,
        "ball_intersections_mm3": collisions,
        "continuous_path_intersections_mm3": sweeps,
        "ramp_rise_at_landing_mm": d.ramp_grade * (d.ramp_end_x - d.shaft_x),
        "inlet_ramp_floor_margin_mm": d.drop - d.ramp_grade *
                                     (d.ramp_end_x - d.ramp_start_x),
        "ramp_angle_deg": math.degrees(math.atan(d.ramp_grade)),
        "centreline_points_mm": [p.toTuple() for p in rolling_ball_path(d)],
        "taper_start_z_mm": d.high_centre_z + d.taper_start_above_high_centre,
        "taper_tip_z_mm": p.height - d.roof_thickness,
        "ports": [asdict(port) for port in ports(d)],
        "fit_profile_id": p.fit_profile_id,
        "e31_05_receiver": {"tube_od_mm": 13.2, "bead_radius_mm": .2,
                            "split_slots": 4},
        "top_studs": 4,
        "top_duplo_stackable_geometrically": True,
        "physical_fit_validated": False,
        "physical_rolling_validated": False,
        "support_free_slicing_validated": False,
        "limitations": [
            "Tapered roof and circular entrance need slicer confirmation without supports.",
            "The inclined floor biases rolling toward the outlet, but physical rolling is untested.",
            "Swept-volume clearance cannot prove impact or rolling dynamics.",
            "Entrance and exit edge finish and child safety need inspection.",
            "E31-05 underside and top studs are not physically validated on this shape.",
        ],
        "sha256_stl": hashlib.sha256(stl.read_bytes()).hexdigest(),
    }
    (out / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(PART_ID, "PASS" if report["passed"] else "FAIL",
          checks, flush=True)
    if not report["passed"]:
        raise RuntimeError("S01-V5 geometry verification failed")
    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path,
                        default=Path("build/steep-drop-hole"))
    export(parser.parse_args().out)
