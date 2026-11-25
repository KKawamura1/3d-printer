"""GW02-V4: open two-cup 180-degree gravity wheel with adjustable impact stop.

A 24.26 mm ball enters from the upper right, then leaves toward the lower
left when the wheel hits a removable stop pin at ~160/170/180 degrees.
No fixed shroud. A radially inward-canted pocket and a shallow escape lip
retain the ball while the wheel turns; impact release remains unproven.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import cadquery as cq

from experiments.gravity_wheel_g02.design import duplo_pad, box, cyl, vec

VERSION = "GW02-V4"
BALL_D = 24.26
BALL_R = BALL_D / 2
AXIS_Z = 66.0
POCKET_X, POCKET_Z = 10.0, 35.0
CUP_TILT = -20.0
CUP_LENGTH = 42.0
CUP_OUT_R, CUP_IN_R = 16.0, 13.65
SLOT_WIDTH = 22.0
SLOT_LENGTH = 39.0
LIP_INNER_Z = 10.2
LIP_AXIAL_X = 19.65
LIP_LENGTH = 2.7
RELEASE_LIFT_MM = 2.5
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


def _cup_transform(shape):
    """Move a cup-local (+X = exit, +Z = outside radius) shape to the wheel."""
    return rotate(shape, -CUP_TILT).translate((POCKET_X, 0, POCKET_Z))


def cup_bore_local():
    return _cup_transform(cyl(
        CUP_IN_R, CUP_LENGTH - 2, (-CUP_LENGTH / 2 + 3, 0, 0), (1, 0, 0)))


def cup_shell_local():
    """Side rails plus outer wall, with an inward inspection/release relief."""
    outer = cyl(CUP_OUT_R, CUP_LENGTH,
                (-CUP_LENGTH / 2, 0, 0), (1, 0, 0))
    bore = cyl(CUP_IN_R, CUP_LENGTH - 2,
               (-CUP_LENGTH / 2 + 3, 0, 0), (1, 0, 0))
    # 22 mm is smaller than the 24.26 mm ball, including at the mouth.
    # Extend to the free end so a ball can lift 2.5 mm over the exit lip.
    relief = box(SLOT_LENGTH, SLOT_WIDTH, 22, 4.5, 0, -16)
    return _cup_transform(outer.cut(bore).cut(relief)).clean()


def cup_lip_local():
    """Short radial-outside step: blocks a level ball, not a lifted ball."""
    outer = cyl(CUP_OUT_R, CUP_LENGTH,
                (-CUP_LENGTH / 2, 0, 0), (1, 0, 0))
    lip_height = CUP_OUT_R - LIP_INNER_Z
    lip = box(LIP_LENGTH, SLOT_WIDTH, lip_height,
              LIP_AXIAL_X, 0, (CUP_OUT_R + LIP_INNER_Z) / 2)
    return _cup_transform(lip.intersect(outer)).clean()


def cup_local():
    return cup_shell_local().fuse(cup_lip_local()).clean()


def ball_at(axial_mm=0.0, inward_mm=0.0):
    """Sphere at a location relative to the center of the upper cup."""
    return _cup_transform(cq.Solid.makeSphere(
        BALL_R, vec(axial_mm, 0, -inward_mm), angleDegrees1=-90))


def centrifugal_outlet_projection_mm():
    """Negative means centrifugal acceleration pushes INTO the closed cup."""
    a = math.radians(CUP_TILT)
    return POCKET_X * math.cos(a) + POCKET_Z * math.sin(a)


def tangential_exit_alignment():
    """Cosine of the angle between exit axis and the rotating cup velocity."""
    a = math.radians(CUP_TILT)
    return (POCKET_Z * math.cos(a) - POCKET_X * math.sin(a)) / (
        math.hypot(POCKET_X, POCKET_Z))


def rotor_local():
    first = cup_shell_local()
    base = first.fuse(rotate(first, 180))
    spoke = (cq.Workplane("XZ")
             .polyline([(-5, -5), (5, -5),
                        (POCKET_X + 7, POCKET_Z),
                        (POCKET_X - 7, POCKET_Z)])
             .close().extrude(8, both=True).val())
    hub = cyl(ROTOR_HUB_R, 42, (0, -21, 0))
    side_rib = (cq.Workplane("XZ")
                .polyline([(-4, -2), (4, -2), (15, 35), (4, 35)])
                .close().extrude(7).val().translate((0, 18, 0)))
    rotor = (base.fuse(spoke).fuse(rotate(spoke, 180))
             .fuse(side_rib).fuse(rotate(side_rib, 180)).fuse(hub))
    # Clear any spokes/ribs that enter the ball running space.
    bore = cup_bore_local()
    rotor = rotor.cut(bore).cut(rotate(bore, 180))
    # Add the two retention lips AFTER the clearance cuts.
    lip = cup_lip_local()
    rotor = rotor.fuse(lip).fuse(rotate(lip, 180))
    # V2's web protruded into the elevated exit path; spokes already
    # connect the cup walls and hub, so no separate web is needed.
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
        "window_smaller_than_ball": SLOT_WIDTH < BALL_D - 2,
        "no_fixed_cover": "shroud" not in parts,
        "ball_center_clear": rotor.intersect(ball_local()).Volume() < 0.1,
        "outlet_points_radially_inward": centrifugal_outlet_projection_mm() < -2.0,
        "exit_aligned_with_impact_velocity": tangential_exit_alignment() > 0.99,
        "resting_ball_blocked_by_lip": cup_local().intersect(ball_at(18)).Volume() > 10,
        "lifted_ball_clears_lip": cup_local().intersect(ball_at(18, RELEASE_LIFT_MM)).Volume() < 0.1,
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
    cup = cup_local()
    # A geometric *possible* release corridor; not a proof that impact
    # supplies sufficient kinetic energy to follow this path.
    checks["exit_corridor_clear"] = all(
        cup.intersect(ball_at(x, min(RELEASE_LIFT_MM, max(0.0, x - 1) * RELEASE_LIFT_MM / 8))).Volume() < 0.1
        for x in (0, 8, 12, 16, 20, 26))
    for selected in STOP_ANGLES:
        pin = stopper(selected)
        checks[f"pin_clears_before_{selected}"] = (
            world(rotate(rotor, selected - 15)).intersect(pin).Volume() < 0.1)
        checks[f"pin_contacts_after_{selected}"] = (
            world(rotate(rotor, selected + 3)).intersect(pin).Volume() > 0.5)
        checks[f"pin_clears_stand_{selected}"] = (
            parts["stand_back_stop"].intersect(pin).Volume() < 0.1)
    return checks


# World-space BRep is used ONLY for assembly/clearance checks. Raw assembly
# positions must not leak into printable STL exports: the rotor, axle, and
# pin otherwise float far above the printer plate.
PRINT_X_ROTATION_DEG = {
    "rotor": 90,            # lie wheel on the broad Y- hub face
    "stand_front": 0,       # DUPLO receiver rim on the plate
    "stand_back_stop": 0,   # DUPLO receiver rim on the plate
    "axle": 90,             # headed end is the base
    "stop_pin": -90,        # wide pin head is the base
}


def orient_for_print(name, assembly_shape):
    """Apply print orientation, center the footprint, and touch z=0.

    This function must NOT change the world-space shape used for STEP or
    assembly collision tests. It changes pose, not functional dimensions.
    """
    if name not in PRINT_X_ROTATION_DEG:
        raise ValueError(f"Unknown printable part: {name}")
    shape = assembly_shape.rotate((0, 0, 0), (1, 0, 0),
                                  PRINT_X_ROTATION_DEG[name])
    bounds = shape.BoundingBox()
    return shape.translate((
        -(bounds.xmin + bounds.xmax) / 2,
        -(bounds.ymin + bounds.ymax) / 2,
        -bounds.zmin,
    ))


def print_pose_report(shape):
    """Actual print-oriented CAD envelope for buildability sanity checks."""
    b = shape.BoundingBox()
    return {
        "min_z_mm": b.zmin,
        "max_z_mm": b.zmax,
        "x_span_mm": b.xlen,
        "y_span_mm": b.ylen,
        "bed_contact_faces_mm2": sum(
            face.Area() for face in shape.Faces()
            if abs(face.BoundingBox().zmin) < 0.02
            and abs(face.BoundingBox().zmax) < 0.02
        ),
    }


def export(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    parts = build_parts()  # keep true assembly coordinates for STEP
    checks = static_checks(parts)
    from brickcad.verify import mesh_check
    meshes = {}
    print_poses = {}
    print_parts = {name: orient_for_print(name, shape)
                   for name, shape in parts.items()}
    for name, shape in print_parts.items():
        path = out / f"{name}.stl"
        pose = print_pose_report(shape)
        print_poses[name] = pose
        checks[f"print_on_bed_{name}"] = abs(pose["min_z_mm"]) < 0.01
        checks[f"print_contact_{name}"] = pose["bed_contact_faces_mm2"] > 1.0
        checks[f"print_bed_fits_{name}"] = (
            pose["x_span_mm"] <= 180.0
            and pose["y_span_mm"] <= 180.0)
        cq.exporters.export(shape, str(path), tolerance=.07, angularTolerance=.2)
        meshes[name] = mesh_check(path)
        checks[f"mesh_{name}"] = bool(meshes[name]["passed"])
        checks[f"mesh_on_bed_{name}"] = abs(meshes[name]["bounds_mm"][0][2]) < 0.08
    cq.exporters.export(
        cq.Compound.makeCompound(list(parts.values())),
        str(out / "assembly.step"))
    report = {
        "model_id": VERSION,
        "passed": all(checks.values()),
        "checks": checks,
        "mesh": {"passed": all(x["passed"] for x in meshes.values())},
        "meshes": meshes,
        "print_poses": print_poses,
        "stl_orientation": "print-oriented Z=0; assembly.step remains world coordinates",
        "stop_angles_deg": STOP_ANGLES,
        "ball_diameter_mm": BALL_D,
        "axis_height_mm": AXIS_Z,
        "ball_center_vertical_drop_mm": 2 * POCKET_Z,
        "outlet_radial_projection_mm": centrifugal_outlet_projection_mm(),
        "exit_tangent_alignment": tangential_exit_alignment(),
        "retaining_lip_rise_mm": CUP_IN_R - LIP_INNER_Z,
        "nominal_release_lift_mm": RELEASE_LIFT_MM,
        "impact_release_validated": False,
        "physical_fit_validated": False,
        "gravity_motion_validated": False,
        "inlet_outlet_guides_included": False,
        "self_reset_included": False,
        "warning": "Adult bench prototype. A static exit corridor does not establish dynamic release. No physical impact, pin retention, "
                   "slicing, support needs, or automatic motion validated.",
    }
    (out / "report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(VERSION, "PASS" if report["passed"] else "FAIL",
          [k for k, ok in checks.items() if not ok], flush=True)
    if not report["passed"]:
        raise ValueError("GW02-V4 failed static or mesh checks")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="build/gravity-wheel-g02-v4")
    export(parser.parse_args().out)
