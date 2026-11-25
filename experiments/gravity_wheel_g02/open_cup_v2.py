"""GW02-V2: open two-cup 180-degree gravity wheel with adjustable impact stop.

A 24.26 mm ball enters from the upper right, then leaves toward the lower
left when the wheel hits a removable stop pin at ~160/170/180 degrees.
No fixed shroud. Static engineering trial only; actual motion untested.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import cadquery as cq

from experiments.gravity_wheel_g02.design import duplo_pad, box, cyl, vec

VERSION = "GW02-V2"
BALL_D = 24.26
BALL_R = BALL_D / 2
AXIS_Z = 66.0
POCKET_X, POCKET_Z = 10.0, 35.0
CUP_TILT = 10.0
CUP_LENGTH = 42.0
CUP_OUT_R, CUP_IN_R = 16.0, 13.65
SLOT_WIDTH = 17.0
SLOT_LENGTH = 29.0
ROTOR_HUB_R = 8.5
BORE_R, AXLE_R = 2.85, 2.45
STAND_Y = 32.0
STOP_R = 42.0
STOP_LUG_R = 3.0
STOP_PIN_R, STOP_HOLE_R = 2.2, 2.65
STOP_ANGLES = (160, 170, 180)
CONTACT_LEAD_DEG = math.degrees(
    2 * math.asin((STOP_LUG_R + STOP_PIN_R) / (2 * STOP_R))
)


def rotate(shape, angle):
    return shape.rotate((0, 0, 0), (0, 1, 0), angle)


def world(shape):
    return shape.translate((0, 0, AXIS_Z))


def cup_local():
    """Slotted cylindrical basket, solid outer wall and bottomed inner end."""
    dx = math.cos(math.radians(CUP_TILT))
    dz = math.sin(math.radians(CUP_TILT))
    start = (POCKET_X - CUP_LENGTH / 2 * dx, 0,
             POCKET_Z - CUP_LENGTH / 2 * dz)
    outer = cyl(CUP_OUT_R, CUP_LENGTH, start, (dx, 0, dz))
    bore_start = (start[0] + 3 * dx, 0, start[2] + 3 * dz)
    inner = cyl(CUP_IN_R, CUP_LENGTH - 2, bore_start, (dx, 0, dz))
    window = box(SLOT_LENGTH, SLOT_WIDTH, 12, 0, 0, -17)
    window = rotate(window, -CUP_TILT).translate((POCKET_X, 0, POCKET_Z))
    return outer.cut(inner).cut(window).clean()


def rotor_local():
    first = cup_local()
    base = first.fuse(rotate(first, 180))
    spoke = (cq.Workplane("XZ")
             .polyline([(-5, -5), (5, -5),
                        (POCKET_X + 7, POCKET_Z),
                        (POCKET_X - 7, POCKET_Z)])
             .close().extrude(8, both=True).val())
    hub = cyl(ROTOR_HUB_R, 42, (0, -21, 0))
    # Side struts touch the Y+14 mm cup wall, not the open inward radial slot.
    side_rib = (cq.Workplane("XZ")
                .polyline([(-4, -2), (4, -2), (15, 35), (4, 35)])
                .close().extrude(7).val().translate((0, 18, 0)))
    rotor = (base.fuse(spoke).fuse(rotate(spoke, 180))
             .fuse(side_rib).fuse(rotate(side_rib, 180)).fuse(hub))
    dx, dz = math.cos(math.radians(CUP_TILT)), math.sin(math.radians(CUP_TILT))
    start = (POCKET_X - CUP_LENGTH / 2 * dx + 3 * dx, 0,
             POCKET_Z - CUP_LENGTH / 2 * dz + 3 * dz)
    bore = cyl(CUP_IN_R, CUP_LENGTH - 2, start, (dx, 0, dz))
    rotor = rotor.cut(bore).cut(rotate(bore, 180))
    # Below the ball running volume, bridge both cups to the axle hub.
    web = box(13, 9, 21, 9, 0, 11)
    rotor = rotor.fuse(web).fuse(rotate(web, 180))
    # Only one striker, on the rear Y+ side. The opposite cup does not catch.
    rotor = rotor.fuse(cyl(STOP_LUG_R, 15, (0, 12, STOP_R)))
    return rotor.cut(cyl(BORE_R, 44, (0, -22, 0))).clean()


def stop_point(target_angle):
    # Offset the pin center ahead of nominal first contact.
    a = math.radians(target_angle + CONTACT_LEAD_DEG)
    return STOP_R * math.sin(a), STOP_R * math.cos(a)


def bracket_local():
    outer = [(51 * math.sin(math.radians(a)),
              51 * math.cos(math.radians(a)))
             for a in range(147, 206, 3)]
    inner = [(32 * math.sin(math.radians(a)),
              32 * math.cos(math.radians(a)))
             for a in range(205, 146, -3)]
    fan = (cq.Workplane("XZ").polyline(outer + inner)
           .close().extrude(7).val().translate((0, 37, 0)))
    for target in STOP_ANGLES:
        x, z = stop_point(target)
        fan = fan.cut(cyl(STOP_HOLE_R, 9, (x, 29, z)))
    return fan.clean()


def stand(side):
    y = side * STAND_Y
    foot = duplo_pad(0, y)
    stem = box(12, 10, AXIS_Z - 6.35, 0, y, (AXIS_Z + 6.35) / 2)
    bearing = cyl(8, 9, (0, y - 4.5, AXIS_Z))
    solid = foot.fuse(stem).fuse(bearing)
    if side > 0:
        solid = solid.fuse(world(bracket_local()))
        # 170/180 holes cross the upright: drill the final joined solid.
        for target in STOP_ANGLES:
            x, z = stop_point(target)
            solid = solid.cut(cyl(STOP_HOLE_R, 30, (x, 16, AXIS_Z + z)))
    return solid.cut(cyl(BORE_R, 12, (0, y - 6, AXIS_Z))).clean()


def axle():
    return (cyl(AXLE_R, 75, (0, -37.5, AXIS_Z))
            .fuse(cyl(5.5, 3, (0, -40.5, AXIS_Z))).clean())


def stopper(target_angle=170):
    """One removable pin, to insert in any of the three rear bracket holes."""
    if target_angle not in STOP_ANGLES:
        raise ValueError(f"Stop angle must be one of {STOP_ANGLES}")
    x, z = stop_point(target_angle)
    shaft = cyl(STOP_PIN_R, 27, (x, 17, AXIS_Z + z))
    head = cyl(5.5, 4, (x, 44, AXIS_Z + z))
    return shaft.fuse(head).clean()


def build_parts():
    return {
        "rotor": world(rotor_local()),
        "stand_front": stand(-1),
        "stand_back_stop": stand(1),
        "axle": axle(),
        "stop_pin": stopper(170),
    }


def ball_local():
    return cq.Solid.makeSphere(
        BALL_R, vec(POCKET_X, 0, POCKET_Z), angleDegrees1=-90)


def static_checks(parts):
    rotor = rotor_local()
    checks = {
        "five_valid_single_solids": len(parts) == 5 and all(
            s.isValid() and len(s.Solids()) == 1 and s.Volume() > 0
            for s in parts.values()),
        "ball_fits_cup": 2 * CUP_IN_R > BALL_D + 2.5,
        "window_smaller_than_ball": SLOT_WIDTH < BALL_D - 5,
        "no_fixed_cover": "shroud" not in parts,
        "ball_center_clear": rotor.intersect(ball_local()).Volume() < 0.1,
        "shaft_clears_rotor_and_bearings": all(
            parts["axle"].intersect(parts[k]).Volume() < 0.1
            for k in ("rotor", "stand_front", "stand_back_stop")),
        "rotor_clears_both_stands_0_to_180": all(
            world(rotate(rotor, a)).intersect(parts[k]).Volume() < 0.1
            for a in range(0, 181, 15)
            for k in ("stand_front", "stand_back_stop")),
        "stop_holes_separate": all(
            math.dist(stop_point(a), stop_point(b)) > 2 * STOP_HOLE_R + 1
            for a, b in zip(STOP_ANGLES, STOP_ANGLES[1:])),
        "ball_drop_70_mm": 2 * POCKET_Z == 70,
    }
    for selected in STOP_ANGLES:
        pin = stopper(selected)
        checks[f"pin_clears_before_{selected}"] = (
            world(rotate(rotor, selected - 15)).intersect(pin).Volume() < 0.1)
        checks[f"pin_contacts_after_{selected}"] = (
            world(rotate(rotor, selected + 3)).intersect(pin).Volume() > 0.5)
        checks[f"pin_clears_stand_{selected}"] = (
            parts["stand_back_stop"].intersect(pin).Volume() < 0.1)
    return checks


def export(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    parts = build_parts()
    checks = static_checks(parts)
    from brickcad.verify import mesh_check
    meshes = {}
    for name, shape in parts.items():
        path = out / f"{name}.stl"
        cq.exporters.export(shape, str(path), tolerance=.07, angularTolerance=.2)
        meshes[name] = mesh_check(path)
        checks[f"mesh_{name}"] = bool(meshes[name]["passed"])
    cq.exporters.export(
        cq.Compound.makeCompound(list(parts.values())),
        str(out / "assembly.step"))
    report = {
        "model_id": VERSION,
        "passed": all(checks.values()),
        "checks": checks,
        "mesh": {"passed": all(x["passed"] for x in meshes.values())},
        "meshes": meshes,
        "stop_angles_deg": STOP_ANGLES,
        "ball_diameter_mm": BALL_D,
        "axis_height_mm": AXIS_Z,
        "ball_center_vertical_drop_mm": 2 * POCKET_Z,
        "physical_fit_validated": False,
        "gravity_motion_validated": False,
        "inlet_outlet_guides_included": False,
        "self_reset_included": False,
        "warning": "Adult bench prototype. No physical impact, pin retention, "
                   "slicing, or automatic motion validated.",
    }
    (out / "report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(VERSION, "PASS" if report["passed"] else "FAIL",
          [k for k, ok in checks.items() if not ok], flush=True)
    if not report["passed"]:
        raise ValueError("GW02-V2 failed static or mesh checks")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="build/gravity-wheel-g02-v2")
    export(parser.parse_args().out)
