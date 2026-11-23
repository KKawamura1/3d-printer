"""PR91-approved R48 geometry, mirrored into two *new* left roofed courses.

The successful right-hand geometry remains untouched. PR91 already mirrors
the complete unmarked BRep; PR94's shared 5mm engraving helper finishes the
reflected west skirt so labels are upright and fully contained.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

from brickcad.course_artifacts import export_geometry
from brickcad.course_contract import RECEIVER_DEPTH_MM, course_fit
from brickcad.course_finish import engrave_trial_west_skirt
from brickcad.course_r48_unified import R48FamilyConfig, build_r48_family
from brickcad.standards import BALL_TRACK, DUPLO
from brickcad.verify import exact_bounds, mesh_check
from experiments.r48_unified_issue89.compare_relief_plate import (
    _horizontal_slice_area_mm2, _stud_insertion_clearance,
)
from experiments.r48_unified_issue89.export import actual_port_rim_probe
from experiments.r48_unified_issue89.plate_export import placed_mesh

# Same accepted PR91 R10 bore, 25.74mm ports, five 12mm rounded windows,
# SC02 print-tested receiver and full/clipped supports.
SPECIMENS = {
    "X89-E01L-R10": 0.,
    "X89-SC02L-R10": DUPLO.height,
}
LOCATIONS = {"X89-E01L-R10": (-36., 0.),
             "X89-SC02L-R10": (36., 0.)}
PLATE_NAME = "X89_R48_left_E01L_SC02L_2parts_A1mini.stl"
OUTER_BED_MM = 180.
RELIEF_MM = 1.0


def reflected_ports_ok(shape, drop_mm):
    """Audit *actual left* mouths by mapping them onto PR91's tested probe.

    Reflecting back does not redesign or re-mesh the passage; the identical
    96-point test probes physical west and SOUTH left ports.
    """
    return actual_port_rim_probe(shape.mirror("XZ"), drop_mm)


def build_specimen(root, model_id):
    if model_id not in SPECIMENS:
        raise ValueError(f"Unknown left R48 specimen: {model_id}")
    root = Path(root)
    drop_mm = SPECIMENS[model_id]
    cfg = R48FamilyConfig(model_id, drop_mm, "roofed",
                          direction="left", relief_mm=RELIEF_MM)
    # The core intentionally rejects left marked=True: the label was never
    # validated. Generate the exact PR91 reflected BRep before engraving.
    unmarked, detail = build_r48_family(cfg, marked=False)
    fit = course_fit(nx=4, ny=4, height_units=2 if drop_mm == 0 else 3)
    # The west skirt after Y-mirroring is Y=[0,31.9], not [-31.9,0].
    # Reuse PR94's complete-text/overflow BRep guard, do not mirror text.
    physical_label = model_id.removeprefix("X89-")
    shape = engrave_trial_west_skirt(
        unmarked, physical_label, x=-fit.width / 2,
        y=16., face_width_mm=31.9)
    output = root / model_id
    stl, mesh = export_geometry(shape, output, tolerance=.02,
                                angular_tolerance=.15)
    bounds = exact_bounds(shape)
    # PR91's underside audit expects the right-handed support coordinates.
    # Mirror a COPY for its insertion/clearance audit, not for export.
    reflected_back = shape.mirror("XZ")
    support_z01 = _horizontal_slice_area_mm2(shape, .10)
    support_z465 = _horizontal_slice_area_mm2(
        shape, RECEIVER_DEPTH_MM - .10)
    checks = {
        "valid_single_solid": shape.isValid() and len(shape.Solids()) == 1,
        "stl_watertight": bool(mesh["passed"]),
        "stl_volume_matches_brep":
            abs(mesh["signed_volume_mm3"] - shape.Volume())
            / shape.Volume() < .001,
        "bed_xy_envelope":
            bounds[0] <= fit.width + .01 and bounds[1] <= fit.depth + .01,
        "expected_stud_height":
            abs(bounds[2] - (cfg.roof_z + DUPLO.stud_height)) < .01,
        "five_pr91_big_windows":
            len(detail["window_cut_volumes_mm3"]) == 5
            and min(detail["window_cut_volumes_mm3"]) > 50,
        "proven_sc02_printable_receiver":
            detail["underbody_source"] ==
            "course_r48_sloped_tunnel.open_curve",
        "three_complete_four_partial_tubes":
            len(detail["complete_e31_tubes"]) == 3
            and detail["partial_e31_tubes"] == 4,
        "seven_complete_studs": len(detail["top_studs"]) == 7,
        "unchanged_25_74mm_port":
            detail["port_contract"]["opening_diameter_mm"] ==
            BALL_TRACK.opening,
        "physical_left_port_rims": reflected_ports_ok(shape, drop_mm),
        "left_stud_insertion_nonclutch_clearance":
            _stud_insertion_clearance(reflected_back),
        "pr91_bed_support_z0p1": support_z01 > 600.,
        "pr91_receiver_support_z4p65": support_z465 > 650.,
        "r10_relief": detail["interior_radial_relief_mm"] == RELIEF_MM,
        "left_direction": detail["direction"] == "left",
    }
    if not all(checks.values()):
        raise ValueError(f"{model_id}: {checks}")
    report = {
        "id": model_id,
        "physical_label": physical_label,
        "model_family": "PR91 R48 common geometry, mirrored after completion",
        "source": "brickcad.course_r48_unified.build_r48_family",
        "direction": "left",
        "drop_mm": drop_mm,
        "relief_mm": RELIEF_MM,
        "mouth_diameter_mm": BALL_TRACK.opening,
        "windows_count": 5,
        "windows_width_mm": 12.,
        "bounds_mm": bounds,
        "support_area_z0p10_mm2": round(support_z01, 2),
        "support_area_z4p65_mm2": round(support_z465, 2),
        "stl_sha256": hashlib.sha256(stl.read_bytes()).hexdigest(),
        "stl_triangles": mesh.get("triangles"),
        "mesh": mesh,
        "checks": checks,
        "slicer_checked": False,
        "physical_rolling_checked": False,
        "long_term_stopping_frequency_checked": False,
    }
    (output / "trial-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    print(f"{model_id}: valid left course, five windows, STL checked", flush=True)
    return report


def assemble_plate(root):
    """Verify individual files and only XY-translate their binary STL facets."""
    root = Path(root)
    rows, binary_parts = [], []
    for model_id, drop_mm in SPECIMENS.items():
        report = json.loads((root / model_id / "trial-report.json").read_text())
        stl = root / model_id / "brick.stl"
        dx, dy = LOCATIONS[model_id]
        n, facets, bounds, sha = placed_mesh(stl, dx, dy)
        if (report["id"] != model_id
                or report["drop_mm"] != drop_mm
                or report["stl_sha256"] != sha
                or not all(report["checks"].values())):
            raise ValueError(f"{model_id}: report or STL mismatch")
        rows.append({"id": model_id, "offset_xy_mm": [dx, dy],
                     "stl_sha256": sha, "bounds": bounds})
        binary_parts.append((n, facets))
    for row in rows:
        low, high = row["bounds"]
        if (low[2] < -.002 or high[2] > OUTER_BED_MM
                or any(low[i] < -OUTER_BED_MM/2 + 3.
                       or high[i] > OUTER_BED_MM/2 - 3.
                       for i in (0, 1))):
            raise ValueError(f"Out of A1 mini envelope: {row}")
    a, b = rows[0]["bounds"], rows[1]["bounds"]
    if b[0][0] - a[1][0] < 5.:
        raise ValueError("Less than 5mm space between the two STLs")
    nfaces = sum(n for n, _ in binary_parts)
    header = b"PR91 common R48 left E01L SC02L 5-window specimens".ljust(80, b" ")
    plate = root / PLATE_NAME
    plate.write_bytes(
        header + struct.pack("<I", nfaces)
        + b"".join(tris for _, tris in binary_parts))
    if plate.stat().st_size != 84 + 50 * nfaces:
        raise ValueError("Invalid assembled binary STL length")
    combined_mesh = mesh_check(plate)
    if not combined_mesh["passed"]:
        raise ValueError(f"Combined plate mesh rejected: {combined_mesh}")
    manifest = {
        "plate_name": PLATE_NAME,
        "printer": "Bambu Lab A1 mini",
        "one_plate": True,
        "parts": rows,
        "source_geometry": "PR91 merged common R48 R10",
        "engraving": "PR94 west skirt 5mm label helper, reflected side",
        "mouth_diameter_mm": BALL_TRACK.opening,
        "slicer_checked": False,
        "physical_rolling_checked": False,
        "combined_mesh": combined_mesh,
        "plate_sha256": hashlib.sha256(plate.read_bytes()).hexdigest(),
    }
    (root / "plate-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    print(f"Plate: {plate}, 2 left courses, hashes verified", flush=True)
    return plate, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("build/r48-left"))
    parser.add_argument("--specimen", choices=list(SPECIMENS))
    parser.add_argument("--assemble-only", action="store_true")
    args = parser.parse_args()
    if args.assemble_only:
        assemble_plate(args.out)
    elif args.specimen:
        build_specimen(args.out, args.specimen)
    else:
        for model_id in SPECIMENS:
            build_specimen(args.out, model_id)
        assemble_plate(args.out)


if __name__ == "__main__":
    main()
