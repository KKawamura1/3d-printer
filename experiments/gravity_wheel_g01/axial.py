"""GW01-V2: axial-flow, tilted-axis two-pocket gravity wheel.

An adult-supervised mechanical prototype, NOT a validated toy.
Ball enters along +Y, rotates a pocket, then leaves along +Y via the stationary
outlet gate. Tilt keeps an axial downhill component while the wheel turns.
All lengths in millimetres. Build in the same environment as the repo's CAD.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import cadquery as cq

from brickcad.course_contract import (
    RECEIVER_DEPTH_MM, add_course_receiver_features, course_fit,
)
from brickcad.model import receiver

VERSION = "GW01-V2"
BALL_DIAMETER = 24.26
BALL_R = BALL_DIAMETER / 2
PITCH = 16.0
AXIS_Z = 53.5
AXIS_SLOPE = -0.12
AXIS_TILT_DEG = math.degrees(math.atan(AXIS_SLOPE))
POCKET_X = 34.0
POCKET_HALF_LENGTH = 38.0
CUP_INSIDE_R = 13.55
CUP_OUTSIDE_R = 16.25
GATE_Y = 42.0
GATE_THICKNESS = 3.0
GATE_RADIUS = 47.5
GATE_OPEN_R = 14.2
OUTLET_ANGLES = (50, 55, 60, 65, 70, 75, 80)
AXLE_R = 2.25
BORE_R = 2.80
STAND_X = 48.0
STAND_Y = 64.0


def cylinder(r, length, xyz, direction=(0, 1, 0)):
    return cq.Solid.makeCylinder(r, length, cq.Vector(*xyz), cq.Vector(*direction))


def box(x, y, z, cx=0, cy=0, cz=0):
    return cq.Workplane("XY").box(x, y, z).translate((cx, cy, cz)).val()


def pose(shape):
    """Local wheel coords to world coords; both bearings share a tilted axis."""
    return shape.translate((0, 0, AXIS_Z)).rotate(
        (0, 0, AXIS_Z), (1, 0, AXIS_Z), AXIS_TILT_DEG
    )


def cup():
    """Continuous open-ended U-section; neither end has a rotating gate."""
    length = 2 * POCKET_HALF_LENGTH
    outer = cylinder(CUP_OUTSIDE_R, length, (-POCKET_X, -POCKET_HALF_LENGTH, 0))
    inner = cylinder(
        CUP_INSIDE_R, length + 2, (-POCKET_X, -POCKET_HALF_LENGTH - 1, 0)
    )
    lower = box(120, length + 4, 110, 0, 0, -55 + 7.4)
    return outer.cut(inner).intersect(lower).clean()


def rotor_local():
    first = cup()
    second = first.rotate((0, 0, 0), (0, 1, 0), 180)
    # Bridge ends stay outside the 24.26mm ball's swept envelope.
    web = box(41, 2 * POCKET_HALF_LENGTH, 7.0)
    hub = cylinder(8.5, 2 * POCKET_HALF_LENGTH, (0, -POCKET_HALF_LENGTH, 0))
    shape = first.fuse(second).fuse(web).fuse(hub)
    return shape.cut(
        cylinder(BORE_R, 2 * POCKET_HALF_LENGTH + 2, (0, -POCKET_HALF_LENGTH - 1, 0))
    ).clean()


def pocket_center(theta_deg):
    """Nominal X,Z position of a ball in the inlet-side pocket."""
    t = math.radians(theta_deg)
    x, z = -POCKET_X, -0.8
    return (
        x * math.cos(t) - z * math.sin(t),
        x * math.sin(t) + z * math.cos(t),
    )


def gate_local(outlet: bool):
    """Fixed entrance hole / curved discharge slot, not rotating guards."""
    y = GATE_Y if outlet else -GATE_Y - GATE_THICKNESS
    plate = cylinder(GATE_RADIUS, GATE_THICKNESS, (0, y, 0))
    for angle in (OUTLET_ANGLES if outlet else (0,)):
        x, z = pocket_center(angle)
        plate = plate.cut(
            cylinder(GATE_OPEN_R, GATE_THICKNESS + 2, (x, y - 1, z))
        )
    return plate.cut(
        cylinder(BORE_R + 0.5, GATE_THICKNESS + 2, (0, y - 1, 0))
    ).clean()


def underside_base(x, y):
    """Same E31-05 shallow receiver used by the established course geometry."""
    p = course_fit(nx=2, ny=2, height_units=1, height=6.35)
    outer = (
        cq.Workplane("XY")
        .box(p.width, p.depth, p.height, centered=(True, True, False))
        .edges("|Z").fillet(0.8)
    )
    base = receiver(p, outer, RECEIVER_DEPTH_MM, 0.25).val()
    base = add_course_receiver_features(
        base, p.tubes(), p.tube_radius, receiver_depth=RECEIVER_DEPTH_MM
    )
    return base.translate((x, y, 0))


def frame(outlet: bool):
    """E31 base, post, bridge and perforated disc fused into a single frame."""
    side = +1 if outlet else -1
    y = side * STAND_Y
    z_axis = AXIS_Z + AXIS_SLOPE * y
    base = underside_base(STAND_X, y)
    stem = box(
        10, 12, z_axis + 6 - 6.35,
        STAND_X, y, (z_axis + 6 + 6.35) / 2,
    )
    bridge_y = side * 52.7
    bridge = box(
        13, 27, 12, STAND_X, bridge_y,
        AXIS_Z + AXIS_SLOPE * bridge_y,
    )
    return base.fuse(stem).fuse(bridge).fuse(pose(gate_local(outlet))).clean()


def axle():
    shaft = cylinder(AXLE_R, 148, (0, -74, 0))
    head = cylinder(5.2, 2.8, (0, -76.8, 0))
    return pose(shaft.fuse(head).clean())


def guide_local(outlet: bool):
    """Separate sloping axial approach/departure guides for fit experiments."""
    if outlet:
        x, z = pocket_center(64)
        z += 0.9  # keep lower exit channel above z=0
        mid_y, length = 57.0, 20.0
    else:
        x, z = pocket_center(0)
        mid_y, length = -65.0, 37.0
    floor = box(30.4, length, 2.8, x, mid_y, z - BALL_R - 1.5)
    fence_l = box(2.6, length, 11.0, x - 14.0, mid_y, z - BALL_R + 4)
    fence_r = box(2.6, length, 11.0, x + 14.0, mid_y, z - BALL_R + 4)
    return floor.fuse(fence_l).fuse(fence_r).clean()


def build_parts():
    return {
        "rotor": pose(rotor_local()),
        "frame_inlet": frame(False),
        "frame_outlet": frame(True),
        "axle": axle(),
        "guide_inlet": pose(guide_local(False)),
        "guide_outlet": pose(guide_local(True)),
    }


def validate(parts):
    checks = {
        "six_valid_solids": len(parts) == 6 and all(
            s.isValid() and len(s.Solids()) == 1 and s.Volume() > 0
            for s in parts.values()
        ),
        "axial_slope_downhill": AXIS_SLOPE < -0.08,
        "port_larger_than_ball": 2 * GATE_OPEN_R >= BALL_DIAMETER + 3,
        "inlet_to_outlet_sense": pocket_center(64)[1] < pocket_center(0)[1] - 20,
    }
    moving = rotor_local()
    gates = gate_local(False), gate_local(True)
    for angle in range(0, 91, 15):
        rotated = moving.rotate((0, 0, 0), (0, 1, 0), -angle)
        checks[f"gate_clear_{angle}deg"] = all(
            rotated.intersect(g).Volume() < 0.01 for g in gates
        )
    checks["rotor_clear_frames_idle"] = all(
        parts["rotor"].intersect(parts[n]).Volume() < 0.01
        for n in ("frame_inlet", "frame_outlet")
    )
    checks["axle_clear_rotor_and_frames"] = all(
        parts["axle"].intersect(parts[n]).Volume() < 0.01
        for n in ("rotor", "frame_inlet", "frame_outlet")
    )
    checks["guides_clear_frames_and_rotor"] = all(
        parts[g].intersect(parts[n]).Volume() < 0.01
        for g in ("guide_inlet", "guide_outlet")
        for n in ("rotor", "frame_inlet", "frame_outlet", "axle")
    )
    return checks


def export(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    parts = build_parts()
    checks = validate(parts)
    mesh_stats = {}
    for name, shape in parts.items():
        filename = out / (name + ".stl")
        cq.exporters.export(
            shape, str(filename), tolerance=0.06, angularTolerance=0.2
        )
        # Keep official export self-checking, as in GW01-V1.
        from brickcad.verify import mesh_check
        mesh_stats[name] = mesh_check(filename)
        checks[f"mesh_{name}"] = bool(mesh_stats[name]["passed"])
    cq.exporters.export(
        cq.Compound.makeCompound(list(parts.values())),
        str(out / "assembly.step"),
    )
    report = {
        "version": VERSION,
        "passed": all(checks.values()),
        "checks": checks,
        "ball_diameter_mm": BALL_DIAMETER,
        "axis_tilt_deg": AXIS_TILT_DEG,
        "axis_height_at_y0_mm": AXIS_Z,
        "gate_port_diameter_mm": 2 * GATE_OPEN_R,
        "stand_xy_mm": [[STAND_X, -STAND_Y], [STAND_X, STAND_Y]],
        "mesh": mesh_stats,
        "physical_fit_validated": False,
        "physical_rolling_validated": False,
        "cautions": [
            "Only static CAD checks. Motion, friction and ball release are NOT proven.",
            "Manual arming. Reliable self-reset not designed.",
            "Small-parts/axle retention safety incomplete.",
            "Existing-rail inlet/outlet transfer must be adjusted physically.",
        ],
    }
    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(VERSION, "PASS" if report["passed"] else "FAIL", checks, flush=True)
    if not report["passed"]:
        raise RuntimeError("GW01-V2 static geometry validation failed")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="build/gravity-wheel-g01-v2")
    export(parser.parse_args().out)
