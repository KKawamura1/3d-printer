"""S01-V1: compact 2x2x2 open-top steep drop-hole, from a high west inlet to a low east outlet.

This is deliberately NOT a sealed tunnel: the high mouth of a 24.26 mm
ball exceeds a two-course body, so the shaft opens through the upper face.
The top has no studs and is not a stackable DUPLO connection.
Physical rolling, clutch strength, slicing and child safety are unverified.
"""
from dataclasses import asdict, dataclass, replace
from pathlib import Path
import hashlib
import json
import struct

import cadquery as cq

from brickcad.marking import engrave
from brickcad.model import brick_from_fit, receiver
from brickcad.ports import Port
from brickcad.standards import BALL_TRACK, DUPLO, ROUNDED_EDGES
from brickcad.verify import VOLUME_TOL, exact_bounds, intersection, mesh_check
from parts.tunnel.e31_fit import add_e31_05_receiver_features

PART_ID = "S01-V1"


@dataclass(frozen=True)
class SteepDrop:
    low_floor: float = BALL_TRACK.floor
    drop: float = DUPLO.height
    section_radius: float = BALL_TRACK.radius
    shaft_radius: float = 13.15
    shaft_x: float = -2.0
    receiver_depth: float = 4.75

    @property
    def low_centre_z(self):
        return self.low_floor + self.section_radius

    @property
    def high_centre_z(self):
        return self.low_centre_z + self.drop


def ports(d=SteepDrop()):
    """Virtual edge datums; the west mouth is open above the roof."""
    return (
        Port("high_west_open", (-16., 0., d.low_floor + d.drop),
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

    p = replace(brick_from_fit("duplo-e27-play-v1", nx=2, ny=2, height_units=2),
                tube_radius=6.60)
    outer = (cq.Workplane("XY")
             .box(p.width, p.depth, p.height, centered=(True, True, False))
             .edges("|Z").fillet(ROUNDED_EDGES.corner_radius)
             .edges(">Z").chamfer(.5))
    body = receiver(p, outer, d.receiver_depth, ROUNDED_EDGES.receiver_entry)

    # A generous upright drop chamber connects two short horizontal mouth cuts.
    # Tools deliberately overrun the physical side/top faces to open the passages.
    shaft = cq.Solid.makeCylinder(
        d.shaft_radius, p.height + 11., cq.Vector(d.shaft_x, 0, d.low_floor),
        cq.Vector(0, 0, 1))
    high = cq.Solid.makeCylinder(
        d.section_radius, 18., cq.Vector(-18., 0, d.high_centre_z),
        cq.Vector(1, 0, 0))
    low = cq.Solid.makeCylinder(
        d.section_radius, 21., cq.Vector(d.shaft_x, 0, d.low_centre_z),
        cq.Vector(1, 0, 0))
    # No top studs: a stud crossing this upper opening would obstruct a ball.
    shape = body.cut(shaft).cut(high).cut(low).val().clean()
    shape = add_e31_05_receiver_features(shape, p.tubes(), p.tube_radius)
    if not shape.isValid() or len(shape.Solids()) != 1:
        raise ValueError("S01-V1 must be a single connected valid solid")
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
    bounds = exact_bounds(shape)
    checks = {
        "single_valid_solid": shape.isValid() and len(shape.Solids()) == 1,
        "size_2x2x2": all(abs(a - b) < .01 for a, b in
                         zip(bounds, (31.8, 31.8, 38.4))),
        "watertight_mesh": mesh["passed"],
        "sampled_ball_clear": max(collisions) < VOLUME_TOL,
        "bottom_floor_present": shape.isInside(cq.Vector(0, 0, 6.2)),
        "drop_shaft_open_at_top": not shape.isInside(cq.Vector(
            d.shaft_x, 0, p.height - .1)),
        "receiver_central_bore": not shape.isInside(cq.Vector(0, 0, 1.)),
        "receiver_tube_wall": shape.isInside(cq.Vector(5.4, 0, 1.)),
        "high_mouth_overflows_top": d.high_centre_z + d.section_radius > p.height,
        "two_ports_one_course_apart": abs(
            ports(d)[0].floor_xyz_mm[2] - ports(d)[1].floor_xyz_mm[2] -
            DUPLO.height) < 1e-6,
    }
    report = {
        "part_id": PART_ID,
        "passed": all(checks.values()),
        "shape": "open-top steep drop hole; west upper inlet, east lower outlet",
        "parameters": asdict(d),
        "bounds_mm": bounds,
        "checks": checks,
        "mesh": mesh,
        "ball_intersections_mm3": collisions,
        "ports": [asdict(port) for port in ports(d)],
        "fit_profile_id": p.fit_profile_id,
        "e31_05_receiver": {"tube_od_mm": 13.2, "bead_radius_mm": .2,
                            "split_slots": 4},
        "top_studs": 0,
        "top_duplo_stackable": False,
        "physical_fit_validated": False,
        "physical_rolling_validated": False,
        "support_free_slicing_validated": False,
        "limitations": [
            "Open-top shaft is unavoidable with a 2x2x2 high entrance; no top studs.",
            "A falling ball may stall in the lower chamber: no physical dynamics test.",
            "Finite ball positions are not a continuous swept-volume proof.",
            "Rounded vertical rim/mouth safety and support-free slicing need inspection.",
            "E31-05 on this two-course shape is an unvalidated transfer.",
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
