"""GW02-V13: four gently rounded openings in the two DUPLO stand roofs.

Issue #99: V12 rotor slices acceptably, but each stand has an ~23 mm
continuous unsupported bridge at print Z~=5 mm. V13 retains its shared
E31-05 receiver geometry below Z=4.74 and leaves the 12 x 10 mm pillar
unmodified. Only the stand's roof is pierced by four curved openings.

The opening's inside boundary is a 7.35 mm tube keep-out (E31 tube
outside radius 6.60 mm); its inner XY pillar rectangle is also excluded.
All changes are subtractions. The ten-piece V12 assembly and rotor are
preserved. CAD success is NOT a slicer or mechanical strength guarantee.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cadquery as cq

from brickcad.verify import mesh_check
from experiments.gravity_wheel_g02 import open_cup_v4 as v4
from experiments.gravity_wheel_g02 import open_cup_v11 as v11
from experiments.gravity_wheel_g02 import open_cup_v12 as v12

VERSION = "GW02-V13"
ROOF_CUT_Z_MIN = 4.74
ROOF_CUT_Z_MAX = 6.52
WINDOW_INNER_XY = 2.5
WINDOW_OUTER_XY = 13.0
WINDOW_CORNER_R = 0.6
TUBE_KEEP_OUT_R = 7.35
# Preserve the 12x10 pillar and add >0.3 mm of per-side clearance.
PILLAR_KEEP_HALF_X = 6.4
PILLAR_KEEP_HALF_Y = 5.4


def roof_window_cutters(stand_y: float):
    """Four openings, bounded away from the receiver tube, rim and pillar.

    Stand foot is centred on (0, stand_y). Existing cavity/tube is untouched
    below Z=4.74; keep-out solids are local to this stand, not the global XY.
    """
    height = ROOF_CUT_Z_MAX - ROOF_CUT_Z_MIN
    z = (ROOF_CUT_Z_MIN + ROOF_CUT_Z_MAX) / 2
    exclusion = v4.cyl(
        TUBE_KEEP_OUT_R, height + 2,
        (0, stand_y, ROOF_CUT_Z_MIN - 1), (0, 0, 1))
    pillar_keep = v4.box(
        2 * PILLAR_KEEP_HALF_X, 2 * PILLAR_KEEP_HALF_Y,
        height + 2, 0, stand_y, z)
    span = WINDOW_OUTER_XY - WINDOW_INNER_XY
    cutters = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx = sx * (WINDOW_INNER_XY + WINDOW_OUTER_XY) / 2
            cy = stand_y + sy * (WINDOW_INNER_XY + WINDOW_OUTER_XY) / 2
            rectangular = (
                cq.Workplane("XY")
                .box(span, span, height)
                .edges("|Z").fillet(WINDOW_CORNER_R)
                .val().translate((cx, cy, z))
            )
            annular_corner = rectangular.cut(exclusion).cut(pillar_keep).clean()
            if annular_corner.Volume() <= 0:
                raise ValueError(f"Empty window at quadrant {sx}, {sy}")
            cutters.append(annular_corner)
    return cq.Compound.makeCompound(cutters)


def open_stand_roof(shape, stand_y: float):
    """Keep V12/V4's mounting structure except the four roof windows."""
    result = shape.cut(roof_window_cutters(stand_y)).clean()
    if not result.isValid() or len(result.Solids()) != 1:
        raise ValueError("Stand roof opening damaged its connected solid")
    return result


def build_parts():
    parts = v12.build_parts()
    for side, name in ((-1, "stand_front"), (1, "stand_back_stop")):
        parts[name] = open_stand_roof(parts[name], side * v4.STAND_Y)
    return parts


def static_checks(parts):
    checks = dict(v12.static_checks(parts))
    originals = v12.build_parts()
    checks["v12_rotors_and_axle_unchanged"] = all(
        abs(parts[k].Volume() - originals[k].Volume()) < .01
        and parts[k].cut(originals[k]).Volume() < .01
        and originals[k].cut(parts[k]).Volume() < .01
        for k in ("rotor_front", "rotor_back", "rotor_joiner",
                  "axle", "stop_pin"))
    z_guard = v4.box(160, 200, 6.0, 0, 0, 1.70)  # Z = -1.3 .. 4.7
    upper_guard = v4.box(160, 200, 90.0, 0, 0, 51.52)  # Z >= 6.52
    for side, name in ((-1, "stand_front"), (1, "stand_back_stop")):
        original, modified = originals[name], parts[name]
        removed = original.cut(modified)
        checks[f"stand_single_valid_{side}"] = (
            modified.isValid() and len(modified.Solids()) == 1)
        checks[f"stand_roof_removed_{side}"] = (
            200 < removed.Volume() < 1500)
        checks[f"no_added_stand_geometry_{side}"] = (
            modified.cut(original).Volume() < .01)
        checks[f"receiver_shape_below_4p70_identical_{side}"] = (
            removed.intersect(z_guard).Volume() < .01)
        checks[f"upper_pillar_and_bearing_identical_{side}"] = (
            removed.intersect(upper_guard).Volume() < .01)
        tube_guard = v4.cyl(
            TUBE_KEEP_OUT_R - .05, 6.6, (0, side * v4.STAND_Y, -.1),
            (0, 0, 1))
        checks[f"shared_E31_tube_preserved_{side}"] = (
            removed.intersect(tube_guard).Volume() < .01)
        pillar_guard = v4.box(
            2 * PILLAR_KEEP_HALF_X, 2 * PILLAR_KEEP_HALF_Y, 6.6,
            0, side * v4.STAND_Y, 3.3)
        checks[f"pillar_root_preserved_{side}"] = (
            removed.intersect(pillar_guard).Volume() < .01)
    return checks


def assembly_step(parts):
    return cq.Compound.makeCompound([
        parts["rotor_front"], parts["rotor_back"],
        *(v4.world(v11.joiner_local(x, z))
          for x, z in v11.JOIN_POINTS),
        parts["stand_front"], parts["stand_back_stop"],
        parts["axle"], parts["stop_pin"],
    ])


def export(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    parts = build_parts()
    checks = static_checks(parts)
    printables = {name: v12.orient_for_print(name, shape)
                  for name, shape in parts.items()}
    meshes, poses = {}, {}
    for name, shape in printables.items():
        path = out / (name + ".stl")
        cq.exporters.export(shape, str(path), tolerance=.07, angularTolerance=.2)
        meshes[name] = mesh_check(path)
        poses[name] = v4.print_pose_report(shape)
        checks["mesh_" + name] = bool(meshes[name]["passed"])
        checks["mesh_on_bed_" + name] = abs(meshes[name]["bounds_mm"][0][2]) < .08
    plate = cq.Compound.makeCompound(
        list(v12.plate_parts(printables).values()))
    plate_path = out / "print_plate.stl"
    cq.exporters.export(plate, str(plate_path),
                        tolerance=.07, angularTolerance=.2)
    plate_mesh = mesh_check(plate_path)
    checks["print_plate_mesh"] = bool(plate_mesh["passed"])
    checks["print_plate_mesh_on_bed"] = (
        abs(plate_mesh["bounds_mm"][0][2]) < .08)
    cq.exporters.export(assembly_step(parts), str(out / "assembly.step"))
    report = {
        "model_id": VERSION,
        "passed": all(checks.values()),
        "checks": checks,
        "print_plate": {
            "file": "print_plate.stl",
            "independent_printed_pieces": 10,
            "positions_mm": v12.PRINT_PLATE_COORDS,
            "mesh": plate_mesh,
        },
        "print_poses": poses,
        "meshes": meshes,
        "change_from_v12": "Four curved roof windows in each of the two stands only",
        "window_geometry_mm": {
            "inner_xy": WINDOW_INNER_XY,
            "outer_xy": WINDOW_OUTER_XY,
            "tube_keepout_radius": TUBE_KEEP_OUT_R,
            "pillar_half_width_xy": [
                PILLAR_KEEP_HALF_X, PILLAR_KEEP_HALF_Y],
            "cut_z": [ROOF_CUT_Z_MIN, ROOF_CUT_Z_MAX],
            "corner_radius": WINDOW_CORNER_R,
        },
        "sacrificial_support_count": 0,
        "slicer_validated": False,
        "physical_fit_validated": False,
        "impact_release_validated": False,
        "gravity_motion_validated": False,
        "warning": (
            "CAD passing does not prove G-code bridge support. "
            "Compare stand Z=4.8-5.2 bridges using A1 mini PLA Basic "
            "0.20mm support OFF, and do not print until reviewed. "
            "Striker loads, stand strength, child safety unverified."
        ),
    }
    (out / "report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(VERSION, "PASS" if report["passed"] else "FAIL",
          [k for k, v in checks.items() if not v], flush=True)
    if not report["passed"]:
        raise ValueError("GW02-V13 CAD or mesh checks failed")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="build/gravity-wheel-g02-v13")
    export(parser.parse_args().out)
