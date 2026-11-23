"""GW02-V14: make three V13 auto-support contact sites self-supporting.

Targets observed in the user's support-ON Bambu Studio G-code:
- rotor end lips near printed Z=4.4..5.0 (four contact clusters);
- DUPLO stand receiver centre at Z=4.2..5.0;
- stop-stand fan overhang at Z=14.8..15.8.

The rotor lips get permanent outer-side-plate connections, not disposable
scaffolds. The tube ceiling becomes a steep conical pocket above the shared
E31-05 insertion zone (unchanged below Z=4.70). Two stand gussets are supported
by the existing roof cross and rise to the lower rim of the stop fan.

IMPORTANT: No claim that Bambu Studio will generate *zero* auto supports
until a fresh support-ON G-code has been sliced and checked.
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
from experiments.gravity_wheel_g02 import open_cup_v13 as v13

VERSION = "GW02-V14"
CONE_START_Z = 4.74
CONE_BOTTOM_RADIUS = 4.68
CONE_TOP_RADIUS = 0.15
CONE_HEIGHT = 8.0  # dr/dz ~= 0.566; >60 degrees above the bed.
LIP_WEB_INNER_Y = 10.8
LIP_WEB_OUTER_Y = 16.0
LIP_WEB_AXIAL_LENGTH = v4.LIP_LENGTH  # Retention lip length unchanged.
STAND_GUSSET_Z0 = 6.35
STAND_GUSSET_Z1 = 19.0
STAND_GUSSET_HALF_X_START = 15.0
STAND_GUSSET_HALF_X_END = 19.0
GUSSET_Y0 = 0.5
GUSSET_Y1 = 2.3


def lip_plate_web_local(side: int):
    """Close the lip-to-bed-facing-panel gap OUTSIDE the ball running space.

    V12's cylindrical V4 lip tapers away from the rectangular outer panel:
    at |Y|~11 it starts at print Z~5 mm and is held only by an end bridge.
    This little vertical-ended rib reaches the exterior panel at |Y|=16,
    adding a permanent supported connection instead of a removable post.
    """
    if side not in (-1, 1):
        raise ValueError("side must be -1 or +1")
    width = LIP_WEB_OUTER_Y - LIP_WEB_INNER_Y
    return v12._cup_frame(v4.box(
        LIP_WEB_AXIAL_LENGTH,
        width,
        v4.CUP_OUT_R - v4.LIP_INNER_Z,
        v4.LIP_AXIAL_X,
        side * (LIP_WEB_OUTER_Y + LIP_WEB_INNER_Y) / 2,
        (v4.CUP_OUT_R + v4.LIP_INNER_Z) / 2))


def rotor_halves_local():
    halves = v12.rotor_halves_local()
    result = []
    for side, original in zip((-1, 1), halves):
        web = lip_plate_web_local(side)
        updated = original.fuse(web).fuse(v4.rotate(web, 180)).clean()
        if not updated.isValid() or len(updated.Solids()) != 1:
            raise ValueError(f"V14 rotor {side} is not a connected solid")
        result.append(updated)
    return tuple(result)


def cone_roof_clearance(stand_y):
    """Extend central tube void up into the pillar with a >60deg cone.

    The common receiver below Z=4.70 is untouched. At 4.74mm, the open
    central cavity radius ~4.68mm matches the inner bore. Each new layer
    reduces the radius by ~0.113mm so it never suddenly closes a 9.4mm roof.
    """
    return cq.Solid.makeCone(
        CONE_BOTTOM_RADIUS,
        CONE_TOP_RADIUS,
        CONE_HEIGHT,
        v4.vec(0, stand_y, CONE_START_Z),
        v4.vec(0, 0, 1))


def bracket_gussets(stand_y):
    """Permanent webs whose bases lie on the existing centre-cross roof.

    The fan at world Z=~15..19 spans x=+-20, beyond the 12mm wide pillar.
    These two thin Z-up webs start inside the 31.8mm foot outline and
    extend to the fan; nothing needs to be snapped or cut off after print.
    """
    pieces = []
    for sign in (-1, 1):
        x0 = sign * STAND_GUSSET_HALF_X_START
        x1 = sign * STAND_GUSSET_HALF_X_END
        inner = sign * 5.5
        z0, z1 = STAND_GUSSET_Z0, STAND_GUSSET_Z1
        profile = (cq.Workplane("XZ")
                   .polyline([(inner, z0), (x0, z0),
                              (x1, z1), (inner, z1)])
                   .close().extrude(GUSSET_Y1 - GUSSET_Y0)
                   .val())
        # XZ positive extrusion runs along -Y; translate to [Y0,Y1].
        profile = profile.translate((0, stand_y + GUSSET_Y1, 0))
        pieces.append(profile)
    return pieces


def build_parts():
    parts = v13.build_parts()
    front, back = rotor_halves_local()
    parts["rotor_front"] = v4.world(front)
    parts["rotor_back"] = v4.world(back)
    for side, name in ((-1, "stand_front"), (1, "stand_back_stop")):
        y = side * v4.STAND_Y
        new = parts[name].cut(cone_roof_clearance(y))
        if side == 1:
            for gusset in bracket_gussets(y):
                new = new.fuse(gusset)
        new = new.clean()
        if not new.isValid() or len(new.Solids()) != 1:
            raise ValueError(f"V14 {name} invalid or disconnected")
        parts[name] = new
    return parts


def static_checks(parts):
    checks = dict(v12.static_checks(parts))
    prior = v13.build_parts()
    pre_halves = v12.rotor_halves_local()
    now_halves = rotor_halves_local()
    original_rotor = pre_halves[0].fuse(pre_halves[1])
    rotor = now_halves[0].fuse(now_halves[1])
    checks["both_rotor_halves_valid"] = all(
        p.isValid() and len(p.Solids()) == 1 for p in now_halves)
    checks["rotors_only_gain_permanent_lip_webs"] = all(
        old.cut(new).Volume() < .05 and 10 < new.Volume()-old.Volume() < 500
        for old, new in zip(pre_halves, now_halves))
    checks["ball_clearance_centres_unaffected"] = all(
        rotor.intersect(v4.rotate(v4.ball_local(), angle)).Volume() < .1
        for angle in (0, 180))
    # Retention and impact release still require physical testing; at minimum
    # avoid changing the original corridor's interference by more than 0.1mm3.
    for x in (0, 8, 12, 16, 20, 26):
        lift = min(v4.RELEASE_LIFT_MM,
                   max(0, x - 1) * v4.RELEASE_LIFT_MM / 8)
        ball = v4.ball_at(x, lift)
        checks[f"lifted_ball_corridor_{x}"] = (
            rotor.intersect(ball).Volume()
            <= original_rotor.intersect(ball).Volume() + .1)
    bottom_guard = v4.box(100, 200, 6.0, 0, 0, 1.7)
    for side, name in ((-1, "stand_front"), (1, "stand_back_stop")):
        old, new = prior[name], parts[name]
        checks[f"receiver_foot_lower_geometry_preserved_{side}"] = (
            old.intersect(bottom_guard).cut(new).Volume() < .01
            and new.intersect(bottom_guard).cut(old).Volume() < .01)
        checks[f"central_pocket_removed_material_{side}"] = (
            old.cut(new).Volume() > 80.0)
        checks[f"stand_single_solid_{side}"] = (
            new.isValid() and len(new.Solids()) == 1)
        # The bearing and stop-hole region, above all newly added features,
        # should be unchanged.
        upper = v4.box(100, 200, 85, 0, 0, 61.5)  # Z >= 19.0
        checks[f"bearing_and_stop_holes_unchanged_{side}"] = (
            old.intersect(upper).cut(new).Volume() < .01
            and new.intersect(upper).cut(old).Volume() < .01)
    checks["stopping_stand_has_permanent_gussets"] = (
        parts["stand_back_stop"].cut(prior["stand_back_stop"]).Volume() > 100)
    checks["front_stand_no_added_material"] = (
        parts["stand_front"].cut(prior["stand_front"]).Volume() < .01)
    checks["axle_stop_and_joiners_identical"] = all(
        parts[k].cut(prior[k]).Volume() < .01
        and prior[k].cut(parts[k]).Volume() < .01
        for k in ("axle", "stop_pin", "rotor_joiner"))
    return checks


def export(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    parts = build_parts()
    checks = static_checks(parts)
    printable = {name: v12.orient_for_print(name, s)
                 for name, s in parts.items()}
    meshes = {}
    poses = {}
    for name, solid in printable.items():
        file = out / f"{name}.stl"
        cq.exporters.export(solid, str(file), tolerance=.07,
                            angularTolerance=.2)
        mesh = mesh_check(file)
        meshes[name] = mesh
        poses[name] = v4.print_pose_report(solid)
        checks[f"mesh_{name}"] = bool(mesh["passed"])
    placed = v12.plate_parts(printable)
    checks.update(v11.plate_checks(placed))
    checks["ten_separate_printables"] = len(placed) == 10
    plate_file = out / "print_plate.stl"
    cq.exporters.export(cq.Compound.makeCompound(list(placed.values())),
                        str(plate_file), tolerance=.07, angularTolerance=.2)
    plate_mesh = mesh_check(plate_file)
    checks["print_plate_mesh"] = bool(plate_mesh["passed"])
    cq.exporters.export(v13.assembly_step(parts), str(out / "assembly.step"))
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
        "meshes": meshes,
        "print_poses": poses,
        "sacrificial_support_count": 0,
        "slicer_support_count_verified": False,
        "slicer_validated": False,
        "physical_fit_validated": False,
        "impact_release_validated": False,
        "gravity_motion_validated": False,
        "changes_from_v13": [
            "Four rotor lip-to-exterior-panel permanent vertical webs",
            "Self-supporting cone above both stand tube bores (Z4.74..12.74)",
            "Two permanent fan gussets on rear stand",
        ],
        "warning": ("Check support-ON and support-OFF Bambu Studio G-code. "
                    "This geometry is a candidate for LESS auto support, "
                    "not a proof of zero support. Ball motion and clamp "
                    "strength remain untested."),
    }
    (out / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(VERSION, "PASS" if report["passed"] else "FAIL",
          [k for k, ok in checks.items() if not ok], flush=True)
    if not report["passed"]:
        raise ValueError("V14 CAD checks failed")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="build/gw02-v14")
    export(parser.parse_args().out)
