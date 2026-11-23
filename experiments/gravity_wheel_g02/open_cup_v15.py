"""GW02-V15: correct inverted stop lug, plus detachable DUPLO track mouths.

Adult bench prototype. The existing V14 front rotor / stands / axle / four
joiners are reused. Reuse both printed V14 rotor halves. Attach the separate stop boss with adhesive.
Two new entry/exit guides mate an ordinary 2x2 DUPLO tower and provide
BALL_TRACK-width channels facing the upper-right and lower-left cups.

Do not mistake slicer or BRep checks for a dynamic 180-degree transfer test.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import cadquery as cq

from brickcad.standards import BALL_TRACK, DUPLO
from brickcad.verify import mesh_check
from experiments.gravity_wheel_g02 import open_cup_v4 as v4
from experiments.gravity_wheel_g02 import open_cup_v11 as v11
from experiments.gravity_wheel_g02 import open_cup_v12 as v12
from experiments.gravity_wheel_g02 import open_cup_v14 as v14

VERSION = "GW02-V15"
# Rear (+Y) rotor outer panel ends at Y=16.0mm.
# Original V12..V14 tab began at Y=12 and poked 1.65mm INTO the ball region.
REAR_PANEL_INNER_Y = v4.CUP_IN_R
REAR_PANEL_OUTER_Y = v4.CUP_OUT_R
LUG_START_Y = 15.0  # 1 mm mechanically rooted INSIDE the 2.35-mm wall
LUG_END_Y = 20.8    # 4.8 mm protrudes OUTSIDE
PIN_START_Y = 17.8  # Always OUTSIDE the cup's outer panel (Y<=16)
PIN_END_Y = 44.0
STOP_ANGLE = 170
BALL_R = v4.BALL_R
PAD_PITCH = DUPLO.height

# A short unsupported hand-off gap is deliberate: fixed track lips should
# not enter the moving cup's swept envelope. No claim of automatic transfer.
ENTRY_PAD_CENTER_X = 80.0
EXIT_PAD_CENTER_X = -64.0
ENTRY_WORLD_PAD_Z = 4 * PAD_PITCH  # 4 full DUPLO block heights, 76.8mm
EXIT_WORLD_PAD_Z = 0.0
ENTRY_INNER_X = 67.0
ENTRY_OUTER_X = 96.0
EXIT_OUTER_X = -80.0
EXIT_INNER_X = -47.0
ENTRY_FLOOR = BALL_TRACK.floor
EXIT_OUTER_FLOOR = BALL_TRACK.floor
EXIT_INNER_FLOOR = 15.0  # ball centre at z~27.1mm
GUIDE_SLAB_THICKNESS = 2.2
GUIDE_WALL_THICKNESS = (BALL_TRACK.width - BALL_TRACK.opening) / 2
GUIDE_WALL_HEIGHT = BALL_TRACK.height - BALL_TRACK.floor


def external_stop_boss_local():
    """Separate test striker, glued to the OUTSIDE of the V14 rear panel.

    Foot Y=16..17.5 sits against its face; stud Y=17.5..21.8.
    This bond is NOT suitable for high-impact or children's use.
    """
    foot = v4.box(9.0, 1.5, 9.0, 0, 16.75, v4.STOP_R)
    stud = v4.cyl(v4.STOP_LUG_R, 4.3, (0, 17.5, v4.STOP_R))
    shape = foot.fuse(stud).clean()
    if not shape.isValid() or len(shape.Solids()) != 1:
        raise ValueError("Stop boss disconnected")
    return shape

def external_stop_pin():
    """Shorter pin reaches new outside-only striker without touching cup wall."""
    x, z = v4.stop_point(STOP_ANGLE)
    shaft = v4.cyl(v4.STOP_PIN_R, PIN_END_Y - PIN_START_Y,
                   (x, PIN_START_Y, v4.AXIS_Z + z))
    head = v4.cyl(5.5, 4, (x, PIN_END_Y, v4.AXIS_Z + z))
    return shaft.fuse(head).clean()


def sloped_slab(x0, z0, x1, z1, width, thickness):
    """X-direction continuous floor, top Z varies linearly x0->x1."""
    outline = [(x0, z0 - thickness), (x1, z1 - thickness),
               (x1, z1), (x0, z0)]
    return (cq.Workplane("XZ").polyline(outline).close()
            .extrude(width / 2, both=True).val())


def guide_head(kind):
    """Standalone printed guide. Receiver underside is shared E31-05 2x2.

    Geometry is local to the underside of its own DUPLO pad, Z=0. Placement
    in the GW02 assembly uses 4 blocks under the entry pad, none under exit.
    Standard track sidewalls, Y=+-15.825, opening=25.74.
    """
    if kind not in ("entry", "exit"):
        raise ValueError(kind)
    if kind == "entry":
        x0, x1 = ENTRY_INNER_X, ENTRY_OUTER_X
        z0, z1 = ENTRY_FLOOR, ENTRY_FLOOR
        cx = ENTRY_PAD_CENTER_X
    else:
        x0, x1 = EXIT_OUTER_X, EXIT_INNER_X
        z0, z1 = EXIT_OUTER_FLOOR, EXIT_INNER_FLOOR
        cx = EXIT_PAD_CENTER_X

    base = v4.duplo_pad(cx, 0)
    floor = sloped_slab(x0, z0, x1, z1, BALL_TRACK.width,
                        GUIDE_SLAB_THICKNESS)
    sidewalls = []
    for side in (-1, 1):
        y = side * (BALL_TRACK.width - GUIDE_WALL_THICKNESS) / 2
        wall = sloped_slab(x0, z0 + GUIDE_WALL_HEIGHT,
                           x1, z1 + GUIDE_WALL_HEIGHT,
                           GUIDE_WALL_THICKNESS, GUIDE_WALL_HEIGHT)
        sidewalls.append(wall.translate((0, y, 0)))

    shape = base.fuse(floor).fuse(*sidewalls)
    if kind == "exit":
        # The exit rises from 6.35 to 15mm. A NON-REMOVABLE web beneath the
        # chute grows upwards from the receiver top; this is not tree support.
        z_at_x48 = z0 + (z1-z0) * (32.0 / (x1-x0))
        rib = (cq.Workplane("XZ")
               .polyline([(-70.0, 6.0), (-48.1, 6.0),
                          (-48.1, z_at_x48 - GUIDE_SLAB_THICKNESS + .3),
                          (-70.0, z0 + (z1-z0)*10.0/(x1-x0) - GUIDE_SLAB_THICKNESS + .3)])
               .close().extrude(3.0, both=True).val())
        shape = shape.fuse(rib)
    shape = shape.clean()
    if not shape.isValid() or len(shape.Solids()) != 1:
        raise ValueError(f"{kind} guide is disconnected / invalid")
    return shape


def entry_mouth_world():
    dx = math.cos(math.radians(-v4.CUP_TILT))
    dz = -math.sin(math.radians(-v4.CUP_TILT))
    return (v4.POCKET_X + v4.CUP_LENGTH / 2 * dx,
            v4.AXIS_Z + v4.POCKET_Z + v4.CUP_LENGTH / 2 * dz)


def exit_mouth_world(angle=STOP_ANGLE):
    mx, mz = entry_mouth_world()
    x0, z0 = mx, mz - v4.AXIS_Z
    a = math.radians(angle)
    return (x0 * math.cos(a) + z0 * math.sin(a),
            v4.AXIS_Z - x0 * math.sin(a) + z0 * math.cos(a))


def build_parts():
    parts = v14.build_parts()
    parts["stop_boss"] = v4.world(external_stop_boss_local())
    parts["stop_pin"] = external_stop_pin()
    parts["entry_guide"] = guide_head("entry").translate(
        (0, 0, ENTRY_WORLD_PAD_Z))
    parts["exit_guide"] = guide_head("exit").translate(
        (0, 0, EXIT_WORLD_PAD_Z))
    return parts


def static_checks(parts):
    base = {k: v for k, v in parts.items()
            if k not in ("entry_guide", "exit_guide", "stop_boss")}
    checks = dict(v12.static_checks(base))
    before = v14.build_parts()
    for name in before:
        if name == "stop_pin":
            continue
        checks["v14_printed_part_unchanged_" + name] = (
            before[name].cut(parts[name]).Volume() < .01
            and parts[name].cut(before[name]).Volume() < .01)
    pin = parts["stop_pin"]
    boss_local = external_stop_boss_local()
    rear = v14.rotor_halves_local()[1]
    checks["boss_outside_not_inside"] = (
        boss_local.BoundingBox().ymin >= REAR_PANEL_OUTER_Y-.01
        and boss_local.BoundingBox().ymax >= 21.79
        and PIN_START_Y > REAR_PANEL_OUTER_Y+1.0)
    checks["pin_never_hits_original_cup"] = all(
        v4.world(v4.rotate(rear, a)).intersect(pin).Volume() < .02
        for a in range(0, 171, 5))
    checks["stop_pin_clear_of_stands"] = all(
        parts[k].intersect(pin).Volume() < .02
        for k in ("stand_front", "stand_back_stop"))
    checks["boss_clear_before_165"] = all(
        v4.world(v4.rotate(boss_local, a)).intersect(pin).Volume() < .02
        for a in range(0, 166, 5))
    checks["boss_contacts_at_172"] = (
        v4.world(v4.rotate(boss_local, 172)).intersect(pin).Volume() > .2)
    checks["boss_does_not_overlap_rear_half"] = (
        v4.world(boss_local).intersect(parts["rotor_back"]).Volume() < .02)
    checks["guides_valid_solids"] = all(
        parts[k].isValid() and len(parts[k].Solids()) == 1
        for k in ("entry_guide", "exit_guide"))
    checks["shared_ball_track_width"] = (
        abs(BALL_TRACK.width - 31.65) < 1e-6
        and abs(BALL_TRACK.opening - 25.74) < 1e-6)
    checks["entry_outer_port_floor"] = (
        abs(ENTRY_WORLD_PAD_Z + ENTRY_FLOOR -
            4 * DUPLO.height - BALL_TRACK.floor) < 1e-6)
    checks["exit_outer_port_floor"] = (
        EXIT_WORLD_PAD_Z + EXIT_OUTER_FLOOR == BALL_TRACK.floor)
    checks["guides_clear_of_stands"] = all(
        parts[guide].intersect(parts[stand]).Volume() < .1
        for guide in ("entry_guide", "exit_guide")
        for stand in ("stand_front", "stand_back_stop"))
    rotor = v14.rotor_halves_local()[0].fuse(rear)
    for guide in ("entry_guide", "exit_guide"):
        checks["guide_swept_clearance_" + guide] = all(
            v4.world(v4.rotate(rotor, a)).intersect(parts[guide]).Volume() < .1
            for a in range(0, 171, 10))
    return checks

def printing_pose(name, part):
    if name == "stop_boss":
        rotated = part.rotate((0, 0, 0), (1, 0, 0), 90)
        b = rotated.BoundingBox()
        return rotated.translate((-(b.xmin+b.xmax)/2,
                                  -(b.ymin+b.ymax)/2, -b.zmin))
    if name in ("entry_guide", "exit_guide"):
        pad_z = ENTRY_WORLD_PAD_Z if name == "entry_guide" else 0.
        s = part.translate((0, 0, -pad_z))
        b = s.BoundingBox()
        return s.translate((-(b.xmin+b.xmax)/2, 0, -b.zmin))
    return v12.orient_for_print(name, part)


def export(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    parts = build_parts()
    checks = static_checks(parts)
    mesh_reports = {}
    printables = {k: printing_pose(k, v) for k, v in parts.items()}
    for name, shape in printables.items():
        path = out / f"{name}.stl"
        cq.exporters.export(shape, str(path), tolerance=.07,
                            angularTolerance=.2)
        mesh_reports[name] = mesh_check(path)
        checks[f"mesh_{name}"] = bool(mesh_reports[name]["passed"])

    # The already-printed 8 V14 pieces require no reprint; handout this
    # four-item V15 patch plate, preserving one STL for the A1 mini.
    replacement = {
        "stop_boss": printables["stop_boss"].translate((-37, 62, 0)),
        "stop_pin": printables["stop_pin"].translate((-60, 62, 0)),
        "entry_guide": printables["entry_guide"].translate((-35, -35, 0)),
        "exit_guide": printables["exit_guide"].translate((35, -35, 0)),
    }
    checks.update({"replacement_" + k: ok
                   for k, ok in v11.plate_checks(replacement).items()})
    path = out / "replacement_plate.stl"
    cq.exporters.export(cq.Compound.makeCompound(list(replacement.values())),
                        str(path), tolerance=.07, angularTolerance=.2)
    mesh_reports["replacement_plate"] = mesh_check(path)
    checks["replacement_plate_mesh"] = mesh_reports["replacement_plate"]["passed"]

    guides = (printables["entry_guide"].translate((-34, 0, 0)),
              printables["exit_guide"].translate((34, 0, 0)))
    path = out / "guide_plate.stl"
    cq.exporters.export(cq.Compound.makeCompound(guides),
                        str(path), tolerance=.07, angularTolerance=.2)
    mesh_reports["guide_plate"] = mesh_check(path)
    checks["guide_plate_mesh"] = mesh_reports["guide_plate"]["passed"]

    cq.exporters.export(cq.Compound.makeCompound(list(parts.values())),
                        str(out / "assembly.step"))
    report = {
        "model_id": VERSION,
        "passed": all(checks.values()),
        "checks": checks,
        "meshes": mesh_reports,
        "replacement_printables": list(replacement),
        "entry_mouth_world": entry_mouth_world(),
        "exit_mouth_world": exit_mouth_world(),
        "adapter_mouth_x_mm": [ENTRY_INNER_X, EXIT_INNER_X],
        "entry_pad_level_mm": ENTRY_WORLD_PAD_Z,
        "exit_pad_level_mm": EXIT_WORLD_PAD_Z,
        "compatibility": (
            "Keep all V14 parts except the old long stop pin; "
            "install an adhesive stop boss on the rear outer face, a short pin and 2 guides."),
        "gravity_motion_validated": False,
        "impact_release_validated": False,
        "real_rail_join_tested": False,
        "slicer_validated": False,
        "warning": (
            "No physical drop-to-wheel/stop-to-rail tests. Inspect both "
            "new guides and replacement parts in A1 mini slicer. "
            "Adapter gaps are intentional to clear swept path. "
            "Do not hand small parts to children."),
    }
    (out / "report.json").write_text(json.dumps(
        report, indent=2, ensure_ascii=False) + "\n")
    print("V15", "PASS" if report["passed"] else "FAIL",
          [k for k, v in checks.items() if not v], flush=True)
    if not report["passed"]:
        raise ValueError("GW02-V15 validation failed")
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="build/gw02-v15")
    export(p.parse_args().out)
