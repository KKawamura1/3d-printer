"""Export verified individual and A1 mini plate STLs for the 4×2 trial."""
import argparse
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import struct

import cadquery as cq

from brickcad.course_artifacts import export_geometry
from brickcad.course_contract import RECEIVER_DEPTH_MM
from brickcad.standards import BALL_TRACK
from brickcad.verify import exact_bounds, mesh_check
from experiments.compact_curve.design import (
    SPECIMENS, build_base, mark_body, orient_body,
)
from experiments.r48_unified_issue89.plate_export import placed_mesh

PLATE = "X4A_4x2_downhill_sharp_curves_4parts_A1mini.stl"
VOLUME_TOLERANCE = .001  # mm³ for BRep differences


def volume_difference(before, after):
    return [before.cut(after).Volume(), after.cut(before).Volume()]


def actual_mouths_match(shape, specimen):
    """Check the actual recessed face, on both sides of its nominal rim."""
    radius = BALL_TRACK.radius
    sign = 1 if specimen.left else -1
    for is_entry in (True, False):
        floor = BALL_TRACK.floor + (specimen.drop_mm if is_entry else 0.)
        angles = range(0, 360, 15) if specimen.tunnel else range(195, 360, 15)
        for degrees in angles:
            angle = math.radians(degrees)
            for offset in (-.15, .15):
                side = (radius + offset) * math.cos(angle)
                z = floor + radius + (radius + offset) * math.sin(angle)
                point = (cq.Vector(-31.88, side, z) if is_entry else
                         cq.Vector(16 + side, sign * 15.88, z))
                if shape.isInside(point, .001) != (offset > 0):
                    return False
    return True


def write_json(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def export_specimen(root, specimen, unmarked, fit, windows, render_viewer):
    body = mark_body(orient_body(unmarked, specimen), specimen, fit)
    output = root / specimen.id
    stl, mesh = export_geometry(body, output, tolerance=.01, angular_tolerance=.1)
    bounds = exact_bounds(body)
    expected_height = fit.height + (fit.stud_height if specimen.tunnel else 0)
    checks = {
        "one_valid_solid": body.isValid() and len(body.Solids()) == 1,
        "expected_footprint_and_height": all(
            abs(a - b) < .01 for a, b in zip(bounds, (fit.width, fit.depth, expected_height))
        ),
        "actual_mouths_match_25_74_mm": actual_mouths_match(body, specimen),
        "mesh_volume_matches_brep": abs(mesh["signed_volume_mm3"] - body.Volume())
        < body.Volume() * .001,
        "watertight_mesh": mesh["passed"],
        "openings": len(windows) == (3 if specimen.tunnel else 0),
    }
    if not all(checks.values()):
        raise ValueError(f"{specimen.id}: {checks}")
    report = {
        "passed": True,
        "id": specimen.id,
        "drop_mm": specimen.drop_mm,
        "tunnel": specimen.tunnel,
        "direction": "left" if specimen.left else "right",
        "mouth_diameter_mm": BALL_TRACK.opening,
        "geometry": {
            "bounds_mm": bounds,
            "volume_mm3": body.Volume(),
            "parameters": asdict(fit),
        },
        "window_removal_mm3": windows,
        "stl_sha256": hashlib.sha256(stl.read_bytes()).hexdigest(),
        "mesh": mesh,
        "checks": checks,
        "slicing_validated": False,
        "physical_fit_validated": False,
        "physical_rolling_validated": False,
    }
    if render_viewer:
        from brickcad.render import viewer
        from brickcad.verify import fit_report

        report["fit"] = fit_report(fit, body)
        viewer(body, fit, report, output)
    write_json(output / "report.json", report)
    print(specimen.id, bounds, "checked", flush=True)
    return report


def export_plate(out):
    facets = []
    triangles = 0
    rows = []
    for index, specimen in enumerate(SPECIMENS):
        y = 24. - 48. * (index // 2)
        x = 36. if specimen.left else -36.
        stl = out / specimen.id / "brick.stl"
        count, data, bounds, digest = placed_mesh(stl, x, y)
        triangles += count
        facets.append(data)
        rows.append(dict(id=specimen.id, position_mm=[x, y],
                         bounds_mm=bounds, individual_sha256=digest))
    for index, row in enumerate(rows):
        low_a, high_a = row["bounds_mm"]
        if low_a[2] < -.002 or high_a[2] > 180 or any(
            low_a[i] < -90 or high_a[i] > 90 for i in (0, 1)
        ):
            raise ValueError(f"{row['id']} outside A1 mini build volume")
        for other in rows[:index]:
            low_b, high_b = other["bounds_mm"]
            if not any(max(low_a[i] - high_b[i], low_b[i] - high_a[i]) >= 5
                       for i in (0, 1)):
                raise ValueError(f"{row['id']} and {other['id']} are too close")
    plate = out / PLATE
    plate.write_bytes(b"X4A 4x2 downhill curve trial".ljust(80, b" ") +
                      struct.pack("<I", triangles) + b"".join(facets))
    mesh = mesh_check(plate)
    if not mesh["passed"]:
        raise ValueError(f"Combined A1 mini STL failed mesh validation: {mesh}")
    return {"name": PLATE, "models": rows, "mesh": mesh,
            "stl_sha256": hashlib.sha256(plate.read_bytes()).hexdigest()}


def export_trial(out, *, render_viewer=False):
    # Exclude the external engraving and compare the BRep over the receiver's
    # full depth. A clipped/closed tube or extra underside bridge changes it.
    receiver_slab = cq.Workplane("XY").box(
        70, 40, RECEIVER_DEPTH_MM, centered=(True, True, False)
    ).val()
    reference_receiver = None
    report = {"passed": True, "models": [], "checks": {},
              "receiver_differences_mm3": {}}
    for right, left in zip(SPECIMENS[::2], SPECIMENS[1::2]):
        bare, prepared, fit, windows = build_base(right.settings)
        receiver = bare.intersect(receiver_slab)
        if reference_receiver is None:
            reference_receiver = receiver
        difference = volume_difference(reference_receiver, receiver)
        if max(difference) > VOLUME_TOLERANCE:
            raise ValueError(f"{right.id}: underside changed between variants: {difference}")
        report["receiver_differences_mm3"][right.id] = difference
        for specimen in (right, left):
            report["models"].append(export_specimen(
                out, specimen, prepared, fit, windows, render_viewer
            ))
    report["checks"]["common_receiver_before_engraving"] = True
    report["plate"] = export_plate(out)
    report["mesh"] = report["plate"]["mesh"]
    write_json(out / "report.json", report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--viewer", action="store_true")
    args = parser.parse_args()
    export_trial(args.out, render_viewer=args.viewer)
