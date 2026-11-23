"""GW02-V10: split the V4 rotor for print-flat front/back shells.

The V4 ball path and impact stop are unchanged. Split-face printing exposes
both half-channel interiors so any slicer support can be removed before
assembly. This is a CAD test prototype, not a physical motion validation.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import cadquery as cq
from brickcad.verify import mesh_check
from experiments.gravity_wheel_g02 import open_cup_v4 as v4

VERSION = "GW02-V10"
JOIN_POINTS = ((6., 0.), (-6., 0.), (0., 6.), (0., -6.))
HOLE_R = 1.55
PIN_R = 1.42
HOLE_DEPTH = 6.0
PIN_LENGTH = 11.5


def reinforced_rotor_local():
    """Mirror V4's rear side ribs to the front so BOTH halves are connected.

    Clip new ribs with the ball channel bores before fusing; otherwise they
    would extend into the running volume and jam the ball.
    """
    original = v4.rotor_local()
    # Previously, the ribs first appeared at |Y|=11 mm, leaving a ~3 mm
    # gap above the Y=+/-8 mm spokes. The V9 slicer traced ~20 mm of
    # unsupported extrusion at print Z=11.2 mm. Connect the whole rib
    # cross-section from the split face to |Y|=18 mm instead.
    rib = (cq.Workplane("XZ")
           .polyline([(-4, -2), (4, -2), (15, 35), (4, 35)])
           .close().extrude(18, both=True).val())
    bore = v4.cup_bore_local()
    rib = rib.cut(bore).cut(v4.rotate(bore, 180))
    reinforced = original.fuse(rib).fuse(v4.rotate(rib, 180))
    # V6's ribs started ~11 mm above the print plane, forming long unsupported
    # bridges. This narrow web connects the hub to each cup at *every* layer
    # from the split plane through 12 mm, before the existing side ribs start.
    # It follows the outside of the cup, and never obstructs the ball bore.
    web = (cq.Workplane("XZ")
           .polyline([(-7, 5), (-4, 4), (-11, 36), (-14, 36)])
           .close().extrude(12, both=True).val())
    web = web.cut(bore).cut(v4.rotate(bore, 180))
    return reinforced.fuse(web).fuse(v4.rotate(web, 180)).clean()


def rotor_halves_local():
    original = reinforced_rotor_local()
    negative = original.intersect(v4.box(200, 100, 200, 0, -50, 0))
    positive = original.intersect(v4.box(200, 100, 200, 0, 50, 0))
    for x, z in JOIN_POINTS:
        negative = negative.cut(v4.cyl(HOLE_R, HOLE_DEPTH,
                                       (x, 0, z), (0, -1, 0)))
        positive = positive.cut(v4.cyl(HOLE_R, HOLE_DEPTH,
                                       (x, 0, z), (0, 1, 0)))
    return negative.clean(), positive.clean()


def joiner_local(x=6., z=0.):
    return v4.cyl(PIN_R, PIN_LENGTH, (x, -PIN_LENGTH / 2, z))


def build_parts():
    front, back = rotor_halves_local()
    previous = v4.build_parts()
    return {
        "rotor_front": v4.world(front),
        "rotor_back": v4.world(back),
        "rotor_joiner": v4.world(joiner_local()),
        "stand_front": previous["stand_front"],
        "stand_back_stop": previous["stand_back_stop"],
        "axle": previous["axle"],
        "stop_pin": previous["stop_pin"],
    }


def sacrificial_stop_support_local():
    """Support striker from the first printed layer; break it away before use.

    This temporary support is NOT part of the assembled running geometry.
    The stop lug starts at Y=12 mm and otherwise appears in midair.
    """
    stem = v4.cyl(2.5, 11.7, (0, 0, v4.STOP_R))
    weak_neck = v4.cyl(1.15, 0.65, (0, 11.6, v4.STOP_R))
    return stem.fuse(weak_neck).clean()


# The original V9 G-code develops 20 mm midair bridges at layer Z=11.2.
# Each sacrificial post begins on the split face (bed-facing during printing)
# and ends with a weak neck just inside the previously unsupported roof.
# Their positions were chosen from the actual G-code unsupported footprints.
ROOF_SUPPORT_POINTS = (
    (26.5, 19.1),
    (18.1, 20.5),
    (-26.5, -19.1),
    (-18.1, -20.5),
)


def sacrificial_roof_support_local(side):
    """Four tiny REMOVE-BEFORE-ASSEMBLY posts below the long relief roofs.

    These are print-only, not included in the actual moving assembly.
    The posts are accessible from the rotor's split face after printing.
    """
    if side not in (-1, 1):
        raise ValueError(f"side must be -1 or +1, got {side}")
    posts = []
    for x, z in ROOF_SUPPORT_POINTS:
        foot = v4.cyl(2.35, .65, (x, 0, z), (0, side, 0))
        stem = v4.cyl(1.5, 10.75, (x, 0, z), (0, side, 0))
        neck = v4.cyl(.8, .65, (x, side * 10.7, z),
                      (0, side, 0))
        posts.append(foot.fuse(stem).fuse(neck))
    return cq.Compound.makeCompound(posts)


def orient_for_print(name, shape):
    if name == "rotor_front":
        deg = -90
    elif name in ("rotor_back", "rotor_joiner"):
        deg = 90
    else:
        return v4.orient_for_print(name, shape)
    # Removable posts below the side-relief roofs; the original V9 geometry
    # left unsupported spans as large as 19.7 mm at print Z=11.2 mm.
    side = -1 if name == "rotor_front" else 1
    shape = shape.fuse(v4.world(sacrificial_roof_support_local(side)))
    if name == "rotor_back":
        # Separate print-only support for the stop lug.
        shape = shape.fuse(v4.world(sacrificial_stop_support_local()))
    shape = shape.clean()
    rotated = shape.rotate((0, 0, 0), (1, 0, 0), deg)
    b = rotated.BoundingBox()
    return rotated.translate((-(b.xmin + b.xmax) / 2,
                              -(b.ymin + b.ymax) / 2, -b.zmin))


# Coordinates in millimetres on one 180 x 180 mm A1 mini build plate.
# The pin master is duplicated 4 times to make 10 independent pieces.
PRINT_PLATE_COORDS = {
    "rotor_front": (-44.0, -24.0),
    "rotor_back": (44.0, -24.0),
    "stand_front": (-60.0, 62.0),
    "stand_back_stop": (-10.0, 62.0),
    "axle": (32.0, 55.0),
    "stop_pin": (62.0, 55.0),
    "rotor_joiner_1": (29.0, 75.0),
    "rotor_joiner_2": (40.0, 75.0),
    "rotor_joiner_3": (51.0, 75.0),
    "rotor_joiner_4": (62.0, 75.0),
}


def plate_parts(printables):
    """Ten independent on-bed solids in a SINGLE STL, not a fused model."""
    result = {}
    for name, (x, y) in PRINT_PLATE_COORDS.items():
        source = "rotor_joiner" if name.startswith("rotor_joiner_") else name
        result[name] = printables[source].translate((x, y, 0))
    return result


def plate_checks(parts):
    """Detect plate overflow, floating objects, XY collisions and spacing."""
    checks = {}
    for name, shape in parts.items():
        b = shape.BoundingBox()
        checks[f"plate_on_bed_{name}"] = abs(b.zmin) < .01
        checks[f"plate_bounds_{name}"] = (min(b.xmin, b.ymin) >= -85
                                          and max(b.xmax, b.ymax) <= 85)
    names = list(parts)
    for i, name in enumerate(names):
        a = parts[name].BoundingBox()
        for other in names[i+1:]:
            b = parts[other].BoundingBox()
            dx = max(a.xmin - b.xmax, b.xmin - a.xmax, 0)
            dy = max(a.ymin - b.ymax, b.ymin - a.ymax, 0)
            checks[f"plate_gap_{name}_{other}"] = max(dx, dy) >= 4.0
    return checks


def static_checks(parts):
    checks = {"v4_" + name: ok for name, ok in
              v4.static_checks(v4.build_parts()).items()}
    front, back = rotor_halves_local()
    original = reinforced_rotor_local()
    union = front.fuse(back)
    removed = original.cut(union).Volume()
    checks.update({
        "seven_printable_parts": len(parts) == 7,
        "rotor_halves_single_valid_solids": all(
            s.isValid() and len(s.Solids()) == 1 for s in (front, back)),
        "joiner_one_valid_solid": joiner_local().isValid()
            and len(joiner_local().Solids()) == 1,
        "halves_do_not_overlap": front.intersect(back).Volume() < .05,
        "split_did_not_add_geometry": union.cut(original).Volume() < .05,
        "only_dowel_sockets_removed": 200 < removed < 450,
        "ball_clearance_retained": union.intersect(v4.ball_local()).Volume() < .1,
        "front_bracing_is_ball_clear": reinforced_rotor_local().intersect(v4.ball_local()).Volume() < .1,
        "reinforcement_is_contiguous": len(reinforced_rotor_local().Solids()) == 1,
        "no_unsupported_midair_connection": all(
            len(reinforced_rotor_local().intersect(
                v4.box(200, .2, 200, 0, side * y, 0)).Solids()) == 1
            for side in (-1, 1) for y in (.2, 3, 7, 10, 11, 11.8)),
        "pin_inside_hub_not_axle": all(
            math.hypot(x, z) - HOLE_R > v4.BORE_R + 1
            and math.hypot(x, z) + HOLE_R < v4.ROTOR_HUB_R - .7
            for x, z in JOIN_POINTS),
        "dowel_clearance": PIN_R < HOLE_R and PIN_LENGTH < 2 * HOLE_DEPTH,
    })
    for x, z in JOIN_POINTS:
        pin = joiner_local(x, z)
        checks[f"dowel_clear_{x}_{z}"] = (
            pin.intersect(front).Volume() < .05
            and pin.intersect(back).Volume() < .05)
    printables = {name: orient_for_print(name, sh) for name, sh in parts.items()}
    checks["breakaway_stop_support_print_only"] = (
        printables["rotor_back"].Volume() > parts["rotor_back"].Volume() + 100)
    checks["breakaway_roof_posts_print_only"] = all(
        printables[name].Volume() > parts[name].Volume() + 300
        and len(printables[name].Solids()) == 1
        for name in ("rotor_front", "rotor_back"))
    checks.update(plate_checks(plate_parts(printables)))
    checks["plate_has_ten_independent_parts"] = len(plate_parts(printables)) == 10
    for name, shape in parts.items():
        pose = v4.print_pose_report(printables[name])
        checks[f"on_plate_{name}"] = abs(pose["min_z_mm"]) < .01
        checks[f"bed_contact_{name}"] = pose["bed_contact_faces_mm2"] > (
            150 if name in ("rotor_front", "rotor_back") else 1)
        checks[f"fits_a1_mini_{name}"] = (
            pose["x_span_mm"] <= 180 and pose["y_span_mm"] <= 180)
    return checks


def assembly_step():
    parts = build_parts()
    return cq.Compound.makeCompound([
        parts["rotor_front"], parts["rotor_back"],
        *(v4.world(joiner_local(x, z)) for x, z in JOIN_POINTS),
        parts["stand_front"], parts["stand_back_stop"],
        parts["axle"], parts["stop_pin"],
    ])


def export(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    parts = build_parts()
    checks = static_checks(parts)
    poses, meshes = {}, {}
    for name, shape in parts.items():
        printable = orient_for_print(name, shape)
        poses[name] = v4.print_pose_report(printable)
        path = out / f"{name}.stl"
        cq.exporters.export(printable, str(path), tolerance=.07,
                            angularTolerance=.2)
        meshes[name] = mesh_check(path)
        checks[f"mesh_{name}"] = bool(meshes[name]["passed"])
        checks[f"mesh_on_plate_{name}"] = (
            abs(meshes[name]["bounds_mm"][0][2]) < .08)
    plate = cq.Compound.makeCompound(list(plate_parts(
        {name: orient_for_print(name, shape) for name, shape in parts.items()}
    ).values()))
    plate_file = out / "print_plate.stl"
    cq.exporters.export(plate, str(plate_file), tolerance=.07,
                        angularTolerance=.2)
    plate_mesh = mesh_check(plate_file)
    checks["print_plate_mesh"] = bool(plate_mesh["passed"])
    checks["print_plate_mesh_on_bed"] = abs(plate_mesh["bounds_mm"][0][2]) < .08
    cq.exporters.export(assembly_step(), str(out / "assembly.step"))
    report = {
        "model_id": VERSION,
        "passed": all(checks.values()),
        "checks": checks,
        "mesh": {"passed": all(m["passed"] for m in meshes.values())},
        "meshes": meshes,
        "print_poses": poses,
        "print_plate": {
            "file": "print_plate.stl",
            "independent_printed_pieces": 10,
            "positions_mm": PRINT_PLATE_COORDS,
            "mesh": plate_mesh,
            "sacrificial_stop_support": "SNAP OFF before assembling the rotor",
        },
        "rotor_joiner_copies": 4,
        "added_reinforcement": "mirrored V4 side braces and continuous printable-plane webs, both clipped outside the ball passages",
        "assembly_coordinate_system": "original V4 world space",
        "slicer_validated": False,
        "physical_fit_validated": False,
        "gravity_motion_validated": False,
        "impact_release_validated": False,
        "warning": "A PRINT-ONLY sacrificial stem supports the stop lug. "
                   "Remove it completely before assembly; verify the ball path. "
                   "Actual Bambu Studio slicing and physical tests remain pending. "
                   "Adult bench trial only.",
    }
    (out / "report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(VERSION, "PASS" if report["passed"] else "FAIL",
          [name for name, ok in checks.items() if not ok], flush=True)
    if not report["passed"]:
        raise ValueError("GW02-V10 model or STL verification failed")
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="build/gravity-wheel-g02-v10")
    export(ap.parse_args().out)
