"""Issue #89 diameter-margin audit on actual generated R48 STEP solids.

This audit deliberately does not borrow the former +0.55mm *vertical lift*
that masked sloped-floor and roof collisions. The contact-reference lift is
only 0.03mm, used to avoid false positive OCC volume at exact tangency.
It diagnoses rigid centreline spheres, not rolling dynamics or OEM tolerance.
"""
import argparse
import json
import math
from pathlib import Path

import cadquery as cq

from brickcad.course_r48_unified import centreline, grade
from brickcad.standards import BALL_TRACK, DUPLO

DIAMETERS_MM = (24.26, 24.5, 25., 25.2, 25.5, 26., 28.)
STATIONS = (0., .03, .1, .25, .5, .65, .75, .85, .9, .97, 1.)
CONTACT_LIFT_MM = .03
INTERSECTION_TOL_MM3 = .01
MODELS = (("X89-E01-U1", 0.), ("X89-SC02-U1", DUPLO.height))


def sample_sphere(shape, *, drop_mm, ball_diameter, station,
                  contact_lift=CONTACT_LIFT_MM):
    """BRep intersection volume at the nominal ball centreline, in mm³.

    Includes the grade adjustment to the ball-centre height. An intersection
    can be with the floor, sidewall or roof; inspect intersection bounds
    separately before deciding whether raising the centre would fix it.
    """
    if ball_diameter <= 0 or not (0 <= station <= 1):
        raise ValueError("Invalid ball diameter/station")
    radius = ball_diameter / 2
    centre = centreline(station, drop_mm).add(cq.Vector(
        0, 0,
        radius * math.sqrt(1 + grade(station, drop_mm) ** 2)
        + contact_lift
    ))
    ball = cq.Solid.makeSphere(radius, centre, angleDegrees1=-90)
    return max(0., shape.intersect(ball).Volume())


def audit_model(shape, *, model_id, drop_mm):
    diameters = []
    for diameter in DIAMETERS_MM:
        volumes = [
            sample_sphere(shape, drop_mm=drop_mm,
                          ball_diameter=diameter, station=t)
            for t in STATIONS
        ]
        hit = [(t, round(v, 4)) for t, v in zip(STATIONS, volumes)
               if v >= INTERSECTION_TOL_MM3]
        diameters.append({
            "diameter_mm": diameter,
            "port_theoretical_possible": diameter < BALL_TRACK.opening,
            "max_intersection_mm3": round(max(volumes), 4),
            "colliding_positions": [{"t": t, "volume_mm3": v} for t, v in hit],
            "sampled_centreline_clearance": not bool(hit),
        })
    return {"model_id": model_id, "drop_mm": drop_mm,
            "diameter_results": diameters}


def audit_from_steps(step_root, out):
    reports = []
    for model_id, drop_mm in MODELS:
        step = Path(step_root) / model_id / "brick.step"
        if not step.exists():
            raise FileNotFoundError(
                f"Generate PR91 two-model STEP files first: {step}"
            )
        shape = cq.importers.importStep(str(step)).val()
        if not shape.isValid() or len(shape.Solids()) != 1:
            raise ValueError(f"Invalid input BRep: {step}")
        reports.append(audit_model(
            shape, model_id=model_id, drop_mm=drop_mm
        ))
    standard = next(
        r for r in reports if r["model_id"] == "X89-SC02-U1"
    )
    standard_ball = next(
        x for x in standard["diameter_results"]
        if x["diameter_mm"] == BALL_TRACK.ball_diameter
    )
    result = {
        "issue": 89,
        "source": "PR #91 generated STEP BRep (both flat/sloped)",
        "static_test_only": True,
        "contact_lift_mm": CONTACT_LIFT_MM,
        "previous_test_lift_mm": .55,
        "intersection_tolerance_mm3": INTERSECTION_TOL_MM3,
        "nominal_ball_diameter_mm": BALL_TRACK.ball_diameter,
        "nominal_port_opening_mm": BALL_TRACK.opening,
        "upper_ball_diameter_physical_limit_mm": BALL_TRACK.opening,
        "stations": STATIONS,
        "models": reports,
        "strict_nominal_slope_clearance_passed":
            standard_ball["sampled_centreline_clearance"],
        "print_ready": False,
        "limitations": [
            "Sampled centreline locations only, not a continuous swept volume",
            "No varying XY ball-centre offsets or lateral wobble",
            "The ball is raised just 0.03mm to avoid exact-tangent boolean noise",
            "No measured manufactured mouth variation, material friction or kinetic simulation",
            "CAD intersection small positive values can be touch/contact defects, not proof of ball stopping",
        ],
    }
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({
        "print_ready": result["print_ready"],
        "strict_nominal_slope_clearance_passed":
            result["strict_nominal_slope_clearance_passed"],
        "diameters": {
            row["model_id"]: [
                (item["diameter_mm"], item["max_intersection_mm3"])
                for item in row["diameter_results"]
            ] for row in reports
        }
    }, ensure_ascii=False, indent=2))
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--step-root", type=Path,
                   default=Path("build/issue89-shared-r48"))
    p.add_argument("--out", type=Path,
                   default=Path("build/issue89-shared-r48/oversize-audit.json"))
    a = p.parse_args()
    audit_from_steps(a.step_root, a.out)
