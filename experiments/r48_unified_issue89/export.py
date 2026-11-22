"""Issue #89: export/check the two newly generated (not cropped) R48 siblings.

Only these two specimens are generated. No heavy 20-part production rebuild.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import cadquery as cq

from brickcad.course_artifacts import export_geometry
from brickcad.course_r48_unified import (
    R48PairConfig, build_r48, centreline, floor_z, grade, port_contract,
)
from brickcad.standards import BALL_TRACK, DUPLO
from brickcad.verify import exact_bounds

PAIRS = (
    R48PairConfig("X89-E01-U1", 0.),
    R48PairConfig("X89-SC02-U1", DUPLO.height),
)
SPHERE_STATIONS = 21
CLEARANCE_LIFT_MM = .55  # HIGH LIFT ONLY: do not use as rolling/print-safety proof

def actual_port_rim_probe(shape, drop_mm):
    """Inspect the actual BRep at both mouths, not only port_config metadata.

    For 24 polar directions, points 0.15mm *inside* the 25.74mm
    circular rim must be in the open passage, and points 0.15mm outside
    must be solid. Sample 0.02mm inward from the real ±31.9mm end
    planes to avoid ambiguous exact-face topology. This is a geometric
    discriminator, not proof of OEM mating or a complete section scan.
    """
    radius = BALL_TRACK.radius
    for port in ("west", "north"):
        floor = BALL_TRACK.floor + (drop_mm if port == "west" else 0.)
        for degrees in range(0, 360, 15):
            theta = math.radians(degrees)
            for shift, should_be_solid in ((-.15, False), (.15, True)):
                distance = radius + shift
                side = distance * math.cos(theta)
                z = floor + radius + distance * math.sin(theta)
                p = (cq.Vector(-31.88, -16. + side, z)
                     if port == "west" else
                     cq.Vector(16. + side, 31.88, z))
                if shape.isInside(p, .001) != should_be_solid:
                    return False
    return True




def ball_clearance_samples(shape, drop_mm):
    """Rigid sphere vs entire finished solid, including windows and supports.

    A sphere on a slope sits above the geometric floor by r*sqrt(1+grade^2).
    At both ports elevation is unchanged. This is a finite CAD collision
    test, NOT a dynamic rolling or surface-roughness simulation.
    This +0.55mm height test is deliberately NOT the strict contact test;
    see ball_size_audit.py for diameter margin and near-contact collisions.
    """
    radius = BALL_TRACK.ball_diameter / 2
    samples = []
    for i in range(SPHERE_STATIONS):
        t = .03 + .94 * i / (SPHERE_STATIONS - 1)
        centre = centreline(t, drop_mm).add(
            cq.Vector(0, 0, radius * math.sqrt(1 + grade(t, drop_mm)**2)
                      + CLEARANCE_LIFT_MM)
        )
        sphere = cq.Solid.makeSphere(radius, centre, angleDegrees1=-90)
        samples.append(max(0., shape.intersect(sphere).Volume()))
    return samples


def export_pair(out):
    out = Path(out)
    reports = []
    for cfg in PAIRS:
        folder = out / cfg.model_id
        folder.mkdir(parents=True, exist_ok=True)
        shape, detail = build_r48(cfg)
        stl, mesh = export_geometry(
            shape, folder, tolerance=.02, angular_tolerance=.15)
        samples = ball_clearance_samples(shape, cfg.drop_mm)
        bounds = exact_bounds(shape)
        checks = {
            "brep_single_solid": shape.isValid() and len(shape.Solids()) == 1,
            "stl_watertight": bool(mesh["passed"]),
            "stl_brep_volume": abs(mesh["signed_volume_mm3"] - shape.Volume())
                               / shape.Volume() < .001,
            "duplo_xy_envelope": bounds[0] <= 63.9 and bounds[1] <= 63.9,
            "standard_stud_height": abs(bounds[2] - (
                cfg.roof_z + DUPLO.stud_height)) < .01,
            "no_clipped_studs": len(detail["top_studs"]) == 7,
            "no_clipped_e31_tubes": len(detail["complete_e31_tubes"]) == 3,
            "all_five_windows_open": len(detail["window_cut_volumes_mm3"]) == 5
                                     and min(detail["window_cut_volumes_mm3"]) > 50,
            "lifted_sphere_clearance_only": max(samples) < .01,
            "actual_brep_port_rim": actual_port_rim_probe(shape, cfg.drop_mm),
            "unchanged_port_diameter": (
                detail["port_contract"]["opening_diameter_mm"]
                == BALL_TRACK.opening
            ),
            "unchanged_port_radius": (
                detail["port_contract"]["west"][2] == BALL_TRACK.radius and
                detail["port_contract"]["north"][2] == BALL_TRACK.radius
            ),
            "matching_port_floor": (
                abs(detail["port_contract"]["west"][0][2]
                    - (BALL_TRACK.floor + cfg.drop_mm)) < 1e-9 and
                abs(detail["port_contract"]["north"][0][2]
                    - BALL_TRACK.floor) < 1e-9
            ),
        }
        report = {
            "id": cfg.model_id,
            "source_family": "issue89_unified_r48",
            "status": "CAD_PROTOTYPE_NOT_PRINT_CERTIFIED",
            "geometry": {"bounds_mm": bounds, "volume_mm3": shape.Volume()},
            "detail": detail,
            "ball_clearance_mm3": samples,
            "ball_clearance_max_mm3": max(samples),
            "diagnostic_ball_lift_mm": CLEARANCE_LIFT_MM,
            "near_contact_ball_audit_required": True,
            "checks": checks,
            "passed": all(checks.values()),
            "stl_sha256": hashlib.sha256(stl.read_bytes()).hexdigest(),
            "visual_reviewed": False,
            "bambu_studio_sliced": False,
            "physical_mating_checked": False,
            "natural_rolling_checked": False,
            "printed_child_safety_checked": False,
        }
        (folder / "report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        reports.append(report)
        if not report["passed"]:
            raise AssertionError(
                f"{cfg.model_id} checks failed: {checks}; collisions={samples}")
    # Both siblings must use exactly the same support layout, but a single
    # DUPLO-height change in the west port Z and in total roof elevation.
    one, two = reports
    assert one["detail"]["top_studs"] == two["detail"]["top_studs"]
    assert (one["detail"]["complete_e31_tubes"] ==
            two["detail"]["complete_e31_tubes"])
    assert abs(
        two["detail"]["port_contract"]["west"][0][2] -
        one["detail"]["port_contract"]["west"][0][2] -
        DUPLO.height
    ) < 1e-9
    (out / "pair-report.json").write_text(
        json.dumps({"issue": 89, "passed": True, "models": [
            {"id": r["id"], "volume_mm3": r["geometry"]["volume_mm3"],
             "ball_intersection_max_mm3": r["ball_clearance_max_mm3"]}
            for r in reports]}, ensure_ascii=False, indent=2) + "\n")
    return reports


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path,
                        default=Path("build/issue89-shared-r48"))
    args = parser.parse_args()
    for report in export_pair(args.out):
        print(report["id"], report["geometry"], report["checks"])
