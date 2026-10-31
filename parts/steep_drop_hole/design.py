"""S01-V2: enclosed 2x2x3 steep drop tunnel, high west inlet to low east outlet.

The roofed vertical shaft has a printable tapered apex instead of an exposed
opening or a broad horizontal bridge. This is a geometric prototype; ball
dynamics, support-free slicing, fit and child safety are not yet validated.
"""
from dataclasses import asdict, dataclass, replace
from pathlib import Path
import hashlib
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

PART_ID = "S01-V2"


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

    @property
    def low_centre_z(self):
        return self.low_floor + self.section_radius

    @property
    def high_centre_z(self):
        return self.low_centre_z + self.drop


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
    shape = body.cut(shaft).cut(cap).cut(high).cut(low).val().clean()
    shape = add_e31_05_receiver_features(shape, p.tubes(), p.tube_radius)
    studs = make_studs(
        p.studs(), p.height, p.stud_radius - p.clearance,
        p.stud_inner_radius, p.stud_height,
        lip_radius=ROUNDED_EDGES.stud_lip_radius)
    shape = cq.Workplane("XY").newObject([shape]).union(studs).val().clean()
    if not shape.isValid() or len(shape.Solids()) != 1:
        raise ValueError("S01-V2 must be a single connected valid solid")
    shape = engrave(shape, PART_ID, x=0., y=-p.depth / 2, z=12.)
    return shape, p


def sampled_ball_collisions(shape, d=SteepDrop()):
    """Discrete full-ball clearance samples, not a rolling dynamics simulation."""
    radius = BALL_TRACK.ball_diameter / 2
    centres = []
    centres.extend(cq.Vector(x, 0, d.high_centre_z)
                   for x in (-16., -12., -8., -4., d.shaft_x))
    centres.extend(cq.Vector(d.shaft_x, 0, z)
                   for z in (d.high_centre_z - 4., d.high_centre_z - 8.,
                             d.high_centre_z - 12., d.low_centre_z))
    centres.extend(cq.Vector(x, 0, d.low_centre_z)
                   for x in (-1., 0., 3., 8., 13., 16.))
    return [intersection(shape, cq.Solid.makeSphere(
        radius, center, angleDegrees1=-90)) for center in centres]


def continuous_ball_path_intersections(shape, d=SteepDrop()):
    """Rigid swept-ball clearance along the piecewise straight path; no dynamics."""
    r = BALL_TRACK.ball_diameter / 2
    high_z, low_z = d.high_centre_z, d.low_centre_z
    segments = (
        (cq.Vector(-16., 0, high_z), cq.Vector(d.shaft_x, 0, high_z)),
        (cq.Vector(d.shaft_x, 0, high_z), cq.Vector(d.shaft_x, 0, low_z)),
        (cq.Vector(d.shaft_x, 0, low_z), cq.Vector(16., 0, low_z)),
    )
    volumes = []
    for start, end in segments:
        delta = end.sub(start)
        swept_cylinder = cq.Solid.makeCylinder(r, delta.Length, start, delta.normalized())
        volumes.append(intersection(shape, swept_cylinder))
    for centre in (segments[0][0], segments[0][1], segments[1][1], segments[2][1]):
        volumes.append(intersection(shape, cq.Solid.makeSphere(
            r, centre, angleDegrees1=-90)))
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
        "shape": "enclosed steep drop tunnel; west upper inlet, east lower outlet",
        "parameters": asdict(d),
        "bounds_mm": bounds,
        "checks": checks,
        "mesh": mesh,
        "ball_intersections_mm3": collisions,
        "continuous_path_intersections_mm3": sweeps,
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
            "A falling ball may stall in the lower chamber: no physical dynamics test.",
            "Piecewise swept-volume clearance does not prove the ball will turn or roll.",
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
        raise RuntimeError("S01-V1 geometry verification failed")
    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path,
                        default=Path("build/steep-drop-hole"))
    export(parser.parse_args().out)
