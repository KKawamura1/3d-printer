"""GW01-V1: manually armed, gravity-driven two-pocket DUPLO ball wheel.

Experimental mechanism, NOT a certified toy or proven gravity motion.
All dimensions in mm; X is rail direction, Y is wheel axle, Z is vertical.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math

import cadquery as cq

from brickcad.course_contract import course_fit, add_course_receiver_features
from brickcad.model import receiver
from brickcad.standards import BALL_TRACK
from brickcad.verify import mesh_check

MODEL_ID = "GW01-V1"
BALL_R = BALL_TRACK.ball_diameter / 2  # measured approximate ball: 24.26 mm
PITCH = 16.0
AXIS_Z = 6.35 + 2 * 19.2 + BALL_R + 1.3  # upper rail, 2 bricks higher
CUP_X = 35.0
CUP_INSIDE_R = 13.5
CUP_OUTSIDE_R = 16.5
CUP_LIP_Z = 8.0
CORE_HALF_WIDTH = 13.0
GUARD_INNER_Y = 13.0
GUARD_OUTER_Y = 15.4
FRAME_INNER_Y = 17.5
AXLE_R = 2.25
ROTOR_BORE_R = 2.75
FRAME_BORE_R = 2.52
PEG_R = 1.78
PEG_HOLE_R = 1.83
PEG_X = 12.0


def cylinder(radius, length, xyz, direction=(0, 1, 0)):
    return cq.Solid.makeCylinder(radius, length, cq.Vector(*xyz), cq.Vector(*direction))


def make_cup():
    """An upward-open U profile. Mirroring 180 degrees makes the opposite cup."""
    outer = cylinder(CUP_OUTSIDE_R, 2 * CORE_HALF_WIDTH,
                     (-CUP_X, -CORE_HALF_WIDTH, 0))
    inner = cylinder(CUP_INSIDE_R, 2 * CORE_HALF_WIDTH + 2,
                     (-CUP_X, -CORE_HALF_WIDTH - 1, 0))
    below_lip = (cq.Workplane("XY").box(140, 40, 100)
                 .translate((0, 0, CUP_LIP_Z - 50)).val())
    return outer.cut(inner).intersect(below_lip).clean()


def rotor():
    cup = make_cup()
    opposite = cup.rotate((0, 0, 0), (0, 1, 0), 180)
    # Symmetric structure is balanced when empty; only the incoming ball
    # creates torque. The spokes end *outside* the swept ball pocket.
    spoke = cq.Workplane("XY").box(44, 2 * CORE_HALF_WIDTH, 9).val()
    hub = cylinder(9.0, 2 * CORE_HALF_WIDTH, (0, -CORE_HALF_WIDTH, 0))
    shape = cup.fuse(opposite).fuse(spoke).fuse(hub).clean()
    shape = shape.cut(cylinder(ROTOR_BORE_R, 28, (0, -14, 0)))
    # Blind sockets for the two protective face guards, never open into bowls.
    for x in (-PEG_X, PEG_X):
        shape = shape.cut(cylinder(PEG_HOLE_R, 3.2, (x, 9.8, 0)))
        shape = shape.cut(cylinder(PEG_HOLE_R, 3.2, (x, -13.0, 0)))
    return shape.clean().translate((0, 0, AXIS_Z))


def guard(side):
    """Covers both axial cup exits. Windows are smaller than the 24.26 mm ball."""
    if side not in (-1, 1):
        raise ValueError("side must be -1 or +1")
    y0 = GUARD_INNER_Y if side == 1 else -GUARD_OUTER_Y
    thickness = GUARD_OUTER_Y - GUARD_INNER_Y
    pads = [cylinder(18, thickness, (x, y0, 0)) for x in (-CUP_X, CUP_X)]
    centre = cylinder(10, thickness, (0, y0, 0))
    bar = (cq.Workplane("XY").box(70, thickness, 8)
           .translate((0, y0 + thickness / 2, 0)).val())
    shape = pads[0].fuse(pads[1]).fuse(centre).fuse(bar).clean()
    for x in (-CUP_X, CUP_X):
        shape = shape.cut(cylinder(7.0, thickness + 2, (x, y0 - 1, 0)))
    shape = shape.cut(cylinder(ROTOR_BORE_R, thickness + 2,
                               (0, y0 - 1, 0)))
    # Blind dowels align guards; physical retention must be checked after print.
    peg_start = GUARD_INNER_Y - 3.0 if side == 1 else -GUARD_INNER_Y
    for x in (-PEG_X, PEG_X):
        shape = shape.fuse(cylinder(PEG_R, 3.0, (x, peg_start, 0)))
    return shape.clean().translate((0, 0, AXIS_Z))


def stand(side):
    """Each frame has a separate 2x2 E31-05 underside receiver (no top studs)."""
    if side not in (-1, 1):
        raise ValueError("side must be -1 or +1")
    from brickcad.course_contract import RECEIVER_DEPTH_MM
    p = course_fit(nx=2, ny=2, height_units=1, height=6.35)
    outer = (cq.Workplane("XY").box(p.width, p.depth, p.height,
                                    centered=(True, True, False))
             .edges("|Z").fillet(0.8))
    base = receiver(p, outer, RECEIVER_DEPTH_MM, 0.25).val()
    base = add_course_receiver_features(base, p.tubes(), p.tube_radius,
                                        receiver_depth=RECEIVER_DEPTH_MM)
    base = base.translate((0, side * 2 * PITCH, 0))
    # A profile on the inner edge of each base, clear of rotating face guards.
    outline = [(-18, 6.1), (18, 6.1), (14, 13), (8, 51),
               (8, AXIS_Z + 6), (-8, AXIS_Z + 6), (-8, 51), (-14, 13)]
    slab = cq.Workplane("XZ").polyline(outline).close().extrude(6).val()
    slab = slab.translate((0, 23.5 if side == 1 else -17.5, 0))
    shape = base.fuse(slab).clean()
    hole_start = FRAME_INNER_Y - 1 if side == 1 else -23.5 - 1
    shape = shape.cut(cylinder(FRAME_BORE_R, 8,
                               (0, hole_start, AXIS_Z)))
    return shape.clean()


def axle():
    """One-piece removable axle; adult inspection required to avoid end escape."""
    shaft = cylinder(AXLE_R, 52, (0, -26, AXIS_Z))
    head = cylinder(5.0, 2, (0, -28, AXIS_Z))
    return shaft.fuse(head).clean()


def build_parts():
    return {
        "rotor": rotor(),
        "guard_left": guard(-1),
        "guard_right": guard(1),
        "stand_left": stand(-1),
        "stand_right": stand(1),
        "axle": axle(),
    }


def idle_ball():
    """Ball at the left cup's nominal sitting position, no dynamic simulation."""
    return cq.Solid.makeSphere(BALL_R, cq.Vector(-CUP_X, 0, AXIS_Z - 1.3),
                               angleDegrees1=-90)


def validate(parts):
    checks = {
        "six_separate_valid_solids": len(parts) == 6 and all(
            s.isValid() and len(s.Solids()) == 1 and s.Volume() > 0
            for s in parts.values()),
        "ball_clears_idle_cup": parts["rotor"].intersect(idle_ball()).Volume() < 0.01,
        "ball_clears_side_guards": all(
            parts[n].intersect(idle_ball()).Volume() < 0.01
            for n in ("guard_left", "guard_right")),
        "axle_clearance": all(
            parts[n].intersect(parts["axle"]).Volume() < 0.01
            for n in ("rotor", "guard_left", "guard_right", "stand_left", "stand_right")),
    }
    rotor_assembly = cq.Compound.makeCompound(
        [parts[n] for n in ("rotor", "guard_left", "guard_right")])
    pivot = cq.Vector(0, 0, AXIS_Z)
    for angle in range(0, 91, 15):
        moving = rotor_assembly.rotate(pivot, cq.Vector(0, 1, AXIS_Z), -angle)
        checks[f"frame_clear_{angle}deg"] = all(
            moving.intersect(parts[n]).Volume() < .01
            for n in ("stand_left", "stand_right"))
    return checks


def export(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    parts = build_parts()
    checks = validate(parts)
    meshes = {}
    for name, shape in parts.items():
        target = out / (name + ".stl")
        cq.exporters.export(shape, str(target), tolerance=0.04,
                            angularTolerance=0.2)
        meshes[name] = mesh_check(target)
        checks[f"mesh_{name}"] = bool(meshes[name]["passed"])
    cq.exporters.export(cq.Compound.makeCompound(list(parts.values())),
                        str(out / "assembly.step"))
    report = {
        "model_id": MODEL_ID,
        "passed": all(checks.values()),
        "checks": checks,
        "mesh": {"passed": all(m["passed"] for m in meshes.values()),
                 "parts": meshes},
        "ball_diameter_mm": BALL_TRACK.ball_diameter,
        "upper_rail_floor_mm": 6.35 + 2 * 19.2,
        "lower_rail_floor_mm": 6.35,
        "axis_height_mm": AXIS_Z,
        "frame_mount_spacing_mm": 64.0,
        "stl_sha256": {n: hashlib.sha256((out / (n + ".stl")).read_bytes()).hexdigest()
                       for n in parts},
        "physical_fit_validated": False,
        "physical_rolling_validated": False,
        "slicer_support_free_validated": False,
        "limitations": [
            "Static BRep checks only; gravity torque, friction, and cup release angle are not simulated.",
            "Wheel requires manual positioning before each ball; no automatic re-arm.",
            "Dowel fit, wheel retention, underside connection, and 3D print orientation untested.",
            "Axle is removable; do not provide loose parts or 24.26 mm ball to young children.",
            "Two vertically separated rails and any catch chute must be arranged and tested physically."
        ]
    }
    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False,
                                                  indent=2) + "\n")
    print(MODEL_ID, "PASS" if report["passed"] else "FAIL", checks, flush=True)
    if not report["passed"]:
        raise RuntimeError("Gravity wheel geometry checks failed")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("build/gravity-wheel-g01"))
    export(parser.parse_args().out)
