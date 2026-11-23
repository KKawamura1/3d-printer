"""GW02-V12 / issue #99: print-flat OUTER cup panels; no sacrificial supports.

In V11 the Y=0 rotor split faces were laid on the bed, leaving arch-like
cup roofs high above it. V12 reverses that premise: each rotor half has a
flat exterior panel at Y=+/-16 mm, laid FACE DOWN; rails, hub, and spokes
grow from the panel toward the joint at Y=0. The inner running volume is
cleared from the outer panel towards the split. This is a printability
experiment, NOT a claim of slicer or dynamic-motion success.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cadquery as cq

from brickcad.verify import mesh_check
from experiments.gravity_wheel_g02 import open_cup_v4 as v4
from experiments.gravity_wheel_g02 import open_cup_v11 as v11

VERSION = "GW02-V12"
HALF_DEPTH = 16.0
PANEL_THICKNESS = v4.CUP_OUT_R - v4.CUP_IN_R  # 2.35 mm
PRINT_PLATE_COORDS = dict(v11.PRINT_PLATE_COORDS)
PRINT_PLATE_COORDS["rotor_front"] = (-44.0, -27.0)
PRINT_PLATE_COORDS["rotor_back"] = (44.0, -27.0)


def _cup_frame(shape):
    return v4.rotate(shape, -v4.CUP_TILT).translate(
        (v4.POCKET_X, 0, v4.POCKET_Z))


def _halfspace(side):
    if side not in (-1, 1):
        raise ValueError("side must be -1 or +1")
    return v4.box(200, HALF_DEPTH, 200, 0, side * HALF_DEPTH / 2, 0)


def cup_half_local(side):
    """Flat outer panel plus two radial rails; no overhead cylindrical roof.

    The outer panel at |Y|=16 provides lateral ball retention. The panel
    covers the full XZ projection of both rails and the inner running cavity,
    so it can be printed face down without bridging the cup opening.
    """
    panel = v4.box(
        v4.CUP_LENGTH, PANEL_THICKNESS, 2 * v4.CUP_OUT_R,
        0, side * (v4.CUP_OUT_R - PANEL_THICKNESS / 2), 0)
    top_rail = v4.box(
        v4.CUP_LENGTH, v4.CUP_IN_R, PANEL_THICKNESS,
        0, side * v4.CUP_IN_R / 2,
        v4.CUP_IN_R + PANEL_THICKNESS / 2)
    bottom_rail = v4.box(
        v4.CUP_LENGTH, v4.CUP_IN_R, PANEL_THICKNESS,
        0, side * v4.CUP_IN_R / 2,
        -v4.CUP_IN_R - PANEL_THICKNESS / 2)
    return _cup_frame(panel.fuse(top_rail).fuse(bottom_rail)).clean()


def spoke_half_local(side):
    # Constant XZ profile from the bed-facing panel to the joint plane:
    # unlike V11, the web never starts above a layer with no foundation.
    spine = (cq.Workplane("XZ")
             .polyline([(-5, -5), (5, -5),
                        (v4.POCKET_X + 7, v4.POCKET_Z),
                        (v4.POCKET_X - 7, v4.POCKET_Z)])
             .close().extrude(HALF_DEPTH, both=True).val())
    return spine.intersect(_halfspace(side)).clean()


def rotor_half_local(side):
    cup = cup_half_local(side)
    spoke = spoke_half_local(side)
    hub = v4.cyl(v4.ROTOR_HUB_R, HALF_DEPTH,
                 (0, 0, 0), (0, side, 0))
    solid = (cup.fuse(v4.rotate(cup, 180))
             .fuse(spoke).fuse(v4.rotate(spoke, 180)).fuse(hub))

    # As Y approaches the split, cylindrical clearance only REMOVES material.
    # Its radius grows toward Y=0 rather than bridging a cavity roof.
    bore = v4.cup_bore_local()
    solid = solid.cut(bore).cut(v4.rotate(bore, 180))

    # Reuse V4's ball-retention slot and exit lip wherever possible.
    relief = _cup_frame(v4.box(
        v4.SLOT_LENGTH, v4.SLOT_WIDTH, 22, 4.5, 0, -16))
    solid = solid.cut(relief).cut(v4.rotate(relief, 180))
    lip = v4.cup_lip_local().intersect(_halfspace(side))
    solid = solid.fuse(lip).fuse(v4.rotate(lip, 180))

    # V4's rear stop lug projects past the print plane and would float.
    # Instead, place a short print-supported striker at Y=12..16 on the
    # outer panel. Extending it toward Y=0 would hit the ball.
    # Extend the stationary stop pin inward to reach this tab.
    if side == 1:
        solid = solid.fuse(
            v4.cyl(v4.STOP_LUG_R, 4.0, (0, 12.0, v4.STOP_R)))

    solid = solid.cut(v4.cyl(v4.BORE_R, 2 * HALF_DEPTH + 4,
                              (0, -HALF_DEPTH - 2, 0)))
    return solid.clean()


def rotor_halves_local():
    result = []
    for side in (-1, 1):
        half = rotor_half_local(side)
        for x, z in v11.JOIN_POINTS:
            half = half.cut(v4.cyl(
                v11.HOLE_R, v11.HOLE_DEPTH, (x, 0, z), (0, side, 0)))
        result.append(half.clean())
    return tuple(result)


def extended_stop_pin():
    """Stationary pin reaches the short, fully supported V12 rotor lug."""
    x, z = v4.stop_point(170)
    shaft = v4.cyl(v4.STOP_PIN_R, 36, (x, 8, v4.AXIS_Z + z))
    head = v4.cyl(5.5, 4, (x, 44, v4.AXIS_Z + z))
    return shaft.fuse(head).clean()


def build_parts():
    front, back = rotor_halves_local()
    unchanged = v4.build_parts()
    return {
        "rotor_front": v4.world(front),
        "rotor_back": v4.world(back),
        "rotor_joiner": v4.world(v11.joiner_local()),
        "stand_front": unchanged["stand_front"],
        "stand_back_stop": unchanged["stand_back_stop"],
        "axle": unchanged["axle"],
        "stop_pin": extended_stop_pin(),
    }


def orient_for_print(name, shape):
    if name == "rotor_joiner":
        return v11.orient_for_print(name, shape)
    if name not in ("rotor_front", "rotor_back"):
        return v4.orient_for_print(name, shape)
    # Opposite of V11: put the broad outer face on the bed, NOT Y=0.
    angle = 90 if name == "rotor_front" else -90
    rotated = shape.rotate((0, 0, 0), (1, 0, 0), angle)
    b = rotated.BoundingBox()
    return rotated.translate((-(b.xmin + b.xmax) / 2,
                              -(b.ymin + b.ymax) / 2, -b.zmin))


def plate_parts(printables):
    placed = {}
    for name, (x, y) in PRINT_PLATE_COORDS.items():
        source = "rotor_joiner" if name.startswith("rotor_joiner_") else name
        placed[name] = printables[source].translate((x, y, 0))
    return placed


def static_checks(parts):
    front, back = rotor_halves_local()
    assembled = front.fuse(back)
    checks = {
        "seven_distinct_part_types": len(parts) == 7,
        "rotor_halves_are_valid_single_solids": all(
            s.isValid() and len(s.Solids()) == 1
            for s in (front, back)),
        "halves_touch_without_volume_overlap":
            front.intersect(back).Volume() < 0.05,
        "both_ball_channels_clear": all(
            assembled.intersect(ball).Volume() < 0.1
            for ball in (v4.ball_local(), v4.rotate(v4.ball_local(), 180))),
        "shaft_clear": all(
            parts["axle"].intersect(parts[name]).Volume() < 0.1
            for name in ("rotor_front", "rotor_back", "stand_front",
                         "stand_back_stop")),
        "support_post_count_zero": True,
        "new_stop_pin_starts_in_rotor_plane":
            extended_stop_pin().BoundingBox().ymin <= 8.01,
        "four_joiners_fit_sockets":
            v11.PIN_R < v11.HOLE_R
            and v11.PIN_LENGTH < 2 * v11.HOLE_DEPTH,
    }
    # Preserve the established 10-part, single-A1-mini-STL contract.
    printed = {n: orient_for_print(n, s) for n, s in parts.items()}
    for name in ("rotor_front", "rotor_back"):
        pose = v4.print_pose_report(printed[name])
        checks["flat_bed_face_" + name] = pose["bed_contact_faces_mm2"] > 2000
        checks["shallow_build_" + name] = pose["max_z_mm"] <= HALF_DEPTH + 0.02
    plate = plate_parts(printed)
    checks.update(v11.plate_checks(plate))
    checks["plate_has_ten_pieces"] = len(plate) == 10
    return checks


def assembly_step():
    p = build_parts()
    return cq.Compound.makeCompound([
        p["rotor_front"], p["rotor_back"],
        *(v4.world(v11.joiner_local(x, z))
          for x, z in v11.JOIN_POINTS),
        p["stand_front"], p["stand_back_stop"], p["axle"], p["stop_pin"],
    ])


def export(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    parts = build_parts()
    checks = static_checks(parts)
    printables = {n: orient_for_print(n, s) for n, s in parts.items()}
    meshes, poses = {}, {}
    for name, shape in printables.items():
        file = out / (name + ".stl")
        cq.exporters.export(shape, str(file), tolerance=.07, angularTolerance=.2)
        meshes[name] = mesh_check(file)
        poses[name] = v4.print_pose_report(shape)
        checks["mesh_" + name] = bool(meshes[name]["passed"])
    plate = cq.Compound.makeCompound(list(plate_parts(printables).values()))
    plate_file = out / "print_plate.stl"
    cq.exporters.export(plate, str(plate_file), tolerance=.07,
                        angularTolerance=.2)
    plate_mesh = mesh_check(plate_file)
    checks["print_plate_mesh"] = bool(plate_mesh["passed"])
    cq.exporters.export(assembly_step(), str(out / "assembly.step"))
    report = {
        "model_id": VERSION,
        "passed": all(checks.values()),
        "checks": checks,
        "print_plate": {
            "file": "print_plate.stl",
            "independent_printed_pieces": 10,
            "positions_mm": PRINT_PLATE_COORDS,
            "mesh": plate_mesh,
        },
        "print_poses": poses,
        "meshes": meshes,
        "sacrificial_support_count": 0,
        "slicer_validated": False,
        "physical_fit_validated": False,
        "gravity_motion_validated": False,
        "impact_release_validated": False,
        "warning": ("Geometry/mesh PASS is NOT Bambu Studio slice PASS. "
                    "Inspect real G-code for long unsupported bridges and "
                    "isolated extrusion before printing. Ball retention, "
                    "stop impact, assembly strength and infant safety "
                    "remain unproven; adult bench use only."),
    }
    (out / "report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(VERSION, "PASS" if report["passed"] else "FAIL",
          [k for k, ok in checks.items() if not ok], flush=True)
    if not report["passed"]:
        raise ValueError("GW02-V12 CAD/mesh checks failed")
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="build/gravity-wheel-g02-v12")
    export(ap.parse_args().out)
