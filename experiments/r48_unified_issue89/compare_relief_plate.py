"""PR91 full R48 course A/B test: same 25.74mm mouths, different bore relief.

Generate 2x E01 + 2x SC02 *complete rails*, not detached diameter
gauges. 0.4mm and 1.0mm are the maximum *radial* relief within the
passage; the entrance/exit remain 25.74mm in every part. Place all four
on one A1 mini 180x180 bed without changing mesh geometry.

Run: python -m experiments.r48_unified_issue89.compare_relief_plate \
        --out build/issue89-r48-relief-comparison
"""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path

from brickcad.course_artifacts import export_geometry
from brickcad.course_r48_unified import R48PairConfig, build_r48
from brickcad.standards import BALL_TRACK, DUPLO
from brickcad.verify import exact_bounds
from experiments.r48_unified_issue89.export import actual_port_rim_probe
from experiments.r48_unified_issue89.plate_export import placed_mesh

FILE_NAME = "PR91_R48_E01_SC02_R04_R10_4parts_A1mini.stl"
# Row: E01 (flat) / SC02 (one DUPLO downhill). Column: R04 / R10.
# Each model envelope 63.8mm; model centres 72mm apart.
SPECIMENS = (
    ("X89-E01-R04", 0., .4, -36., -36.),
    ("X89-E01-R10", 0., 1.0, 36., -36.),
    ("X89-SC02-R04", DUPLO.height, .4, -36., 36.),
    ("X89-SC02-R10", DUPLO.height, 1.0, 36., 36.),
)
BED = 180.0


def assemble_four(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    records = []
    binary_parts = []
    for model_id, drop_mm, relief_mm, x, y in SPECIMENS:
        cfg = R48PairConfig(model_id, drop_mm, relief_mm=relief_mm)
        shape, details = build_r48(cfg, marked=True)
        path = out / model_id
        stl, mesh = export_geometry(shape, path, tolerance=.02,
                                    angular_tolerance=.15)
        bounds = exact_bounds(shape)
        checks = {
            "valid_single_solid": shape.isValid() and
                                  len(shape.Solids()) == 1,
            "water_tight_stl": bool(mesh["passed"]),
            "stl_volume_matches_brep": abs(
                mesh["signed_volume_mm3"] - shape.Volume()
            ) / shape.Volume() < .001,
            "duplo_envelope": bounds[0] <= 63.9 and bounds[1] <= 63.9,
            "stud_height": abs(
                bounds[2] - (cfg.roof_z + DUPLO.stud_height)) < .01,
            "complete_studs": len(details["top_studs"]) == 7,
            "complete_receiver_tubes":
                len(details["complete_e31_tubes"]) == 3,
            "five_windows": len(details["window_cut_volumes_mm3"]) == 5
                            and min(details["window_cut_volumes_mm3"]) > 50,
            "mouth_contract":
                details["port_contract"]["opening_diameter_mm"]
                == BALL_TRACK.opening,
            "mouth_actual_brep":
                actual_port_rim_probe(shape, cfg.drop_mm),
            "requested_relief":
                details["interior_radial_relief_mm"] == relief_mm,
        }
        if not all(checks.values()):
            raise ValueError(f"{model_id}: {checks}")
        count, facet_bytes, shifted_bounds, src_hash = placed_mesh(stl, x, y)
        records.append({
            "id": model_id,
            "track": "E01" if drop_mm == 0 else "SC02",
            "drop_mm": drop_mm,
            "interior_radial_relief_mm": relief_mm,
            "mouth_diameter_mm": BALL_TRACK.opening,
            "internal_bottom_arc_equivalent_max_diameter_mm":
                round(BALL_TRACK.opening + 2 * relief_mm * .995, 3),
            "not_a_constant_diameter_circular_tube": True,
            "windows": 5,
            "engraved_label": model_id,
            "mesh_triangles": count,
            "mesh_sha256": src_hash,
            "volume_mm3": shape.Volume(),
            "world_translation_xy_mm": [x, y],
            "world_bounds_mm": shifted_bounds,
            "checks": checks,
            "actual_rolling_tested": False,
            "slice_tested": False,
        })
        binary_parts.append((count, facet_bytes))
        (path / "trial-report.json").write_text(
            json.dumps(records[-1], indent=2, ensure_ascii=False) + "\n"
        )
        print(f"{model_id}: diameter +{relief_mm:.2f}mm radial, "
              f"all CAD/port/mesh checks passed", flush=True)

    bounds = [
        [min(row["world_bounds_mm"][0][i] for row in records)
         for i in range(3)],
        [max(row["world_bounds_mm"][1][i] for row in records)
         for i in range(3)]
    ]
    if not all(-BED/2 < bounds[0][i] and bounds[1][i] < BED/2
               for i in (0, 1)):
        raise ValueError(f"Out of A1 mini bed: {bounds}")
    if bounds[0][2] < -.002 or bounds[1][2] > BED:
        raise ValueError(f"Out of printer Z: {bounds}")
    for i, row in enumerate(records):
        for other in records[i+1:]:
            a, b = row["world_bounds_mm"], other["world_bounds_mm"]
            gap_x = max(0., a[0][0] - b[1][0], b[0][0] - a[1][0])
            gap_y = max(0., a[0][1] - b[1][1], b[0][1] - a[1][1])
            if math.hypot(gap_x, gap_y) < 5:
                raise ValueError(f"Model separation <5mm: {row['id']}, "
                                 f"{other['id']}")

    nfaces = sum(n for n, _ in binary_parts)
    plate_stl = out / FILE_NAME
    header = b"PR91 E01-SC02 0.4 vs 1.0 internal radial relief".ljust(80, b" ")
    plate_stl.write_bytes(
        header + struct.pack("<I", nfaces) +
        b"".join(facets for _, facets in binary_parts))
    if plate_stl.stat().st_size != 84 + nfaces * 50:
        raise ValueError("Incomplete combined STL output")
    report = {
        "experiment": "E01/SC02 0.4mm vs 1.0mm interior radial relief",
        "one_plate_stl": FILE_NAME,
        "printer": "Bambu Lab A1 mini",
        "bed_mm": [180, 180],
        "part_count": 4,
        "bounds_mm": bounds,
        "xy_dimensions_mm": [bounds[1][i] - bounds[0][i]
                             for i in (0, 1)],
        "parts": records,
        "fixed_mouth_diameter_mm": BALL_TRACK.opening,
        "only_controlled_variable": "interior radial relief mm (0.4/1.0)",
        "physical_rolling_verified": False,
        "printer_slicing_verified": False,
        "stl_sha256": hashlib.sha256(plate_stl.read_bytes()).hexdigest()
    }
    (out / "comparison-report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(f"4-part plate: {report['xy_dimensions_mm']}mm, "
          f"{plate_stl.stat().st_size} bytes", flush=True)
    return plate_stl, report


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path,
                   default=Path("build/issue89-r48-relief-comparison"))
    args = p.parse_args()
    assemble_four(args.out)
