"""Two A1 mini print campaigns: seven remaining PR56 models and six window pilots.

Usage:
  python scripts/course_followup_print.py --set missing
  python scripts/course_followup_print.py --set windows
  python scripts/course_followup_print.py --set all

The original physically tested meshes remain immutable. 3mm border, 4mm
minimum separation; only 0/90-degree bed rotations, never resizing.
"""
import argparse
import hashlib
import json
from pathlib import Path
import random
import shutil
import struct
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brickcad.course_contract import PRODUCTION_CONTRACT
from brickcad.course_windows import VERSIONS, build_window_variant
from experiments.course_validation_plate.assemble import (
    BED_MM, GAP_MM, MARGIN_MM, Rect, pack_order, fits, transform,
    load_mesh, layout_svg,
)
from scripts.course_catalog import load_registry, select, build, stl_info

# PR70's actual printing was 13/13 (issue #42), distinct from the 4 successful
# original PR55 specimens. Seven of twenty *PR56* meshes remain unprinted.
PRINTED_PR56 = frozenset({
    "SD03-V11", "SD01-V4", "SD02-V4", "D02-V4", "C02-V8",
    "S03-V10", "E01L-V1", "SC02L-V6", "D01-V3", "R01-V1",
    "C01-V6", "T01-V6", "S02-V16",
})
EXPECTED_MISSING = frozenset({
    "GC01-V5", "SC02-V12", "SC03-V5", "SC05-V1",
    "E01-V3", "SD04-V10", "S01-V8",
})


def missing_ids(registry=None):
    data = registry or load_registry()
    ids = {m["id"] for m in data["models"]}
    if len(ids) != 20 or not PRINTED_PR56 <= ids:
        raise ValueError("Canonical PR56 catalogue no longer matches physical evidence")
    remaining = ids - PRINTED_PR56
    if remaining != EXPECTED_MISSING:
        raise ValueError("Remaining physical validation list changed; review Issue #42")
    return sorted(remaining)


def choose_plate(rectangles, attempts=120):
    if not rectangles:
        raise ValueError("No candidates")
    best, key = [], (-1, 0.)
    for i in range(attempts):
        ordered = list(rectangles)
        if i % 5 == 0:
            ordered.sort(key=lambda r: -(r.w * r.h))
        elif i % 5 == 1:
            ordered.sort(key=lambda r: -max(r.w, r.h))
        elif i % 5 == 2:
            ordered.sort(key=lambda r: r.w * r.h)
        else:
            random.Random(37000 + i).shuffle(ordered)
        trial = pack_order(ordered, orientation_bias=bool(i % 2))
        score = (len(trial), sum(p.w * p.h for p in trial))
        if score > key:
            best, key = trial, score
    if not best:
        raise ValueError("One or more objects exceed the printable A1 mini bed")
    for i, item in enumerate(best):
        if not fits(item, best[:i] + best[i + 1:]):
            raise ValueError("Invalid, overlapping or out-of-bed packing")
    return best


def split_plates(rectangles):
    all_ids = {r.id for r in rectangles}
    if len(all_ids) != len(rectangles):
        raise ValueError("Model names must be unique")
    outstanding, result = list(rectangles), []
    while outstanding:
        placed = choose_plate(outstanding)
        result.append(placed)
        selected = {p.id for p in placed}
        outstanding = [r for r in outstanding if r.id not in selected]
    if {p.id for plate in result for p in plate} != all_ids:
        raise ValueError("Some requested parts were never assigned to a plate")
    return result


def prepare_sources(selection, base):
    base = Path(base)
    if selection == "missing":
        models = select(load_registry(), ",".join(missing_ids()))
        result = build(models, base / "catalogue")
        if result["generated_meshes"] != len(EXPECTED_MISSING):
            raise ValueError("Not all seven historical omissions were generated")
        model_meta = {m["id"]: m for m in result["models"]}
        paths = {
            ident: base / "catalogue" / entry["stl"]
            for ident, entry in model_meta.items()
        }
        for ident, entry in model_meta.items():
            evidence = entry["contract_evidence"]
            if (entry["production_contract"] != PRODUCTION_CONTRACT
                or evidence["model_id"] != ident
                or evidence["fit_calls"] < 1
                or evidence["e31_receiver_calls"] < 1
                or evidence["final_marking_labels"] != [ident]
                or not entry["geometry_verified"]):
                raise ValueError("Source CAD was not audited: " + ident)
    elif selection == "windows":
        paths, model_meta = {}, {}
        for source_id, new_id in VERSIONS.items():
            out = base / "window-models" / new_id
            entry = build_window_variant(source_id, out)
            model_meta[new_id] = entry
            paths[new_id] = out / "brick.stl"
            if (entry["contract_evidence"]["model_id"] != new_id
                or entry["contract_evidence"]["e31_receiver_calls"] < 1
                or entry["contract_evidence"]["final_marking_labels"] != [new_id]
                or not entry["report"]["passed"]):
                raise ValueError("Windowed mesh failed E31/final marking audit")
    else:
        raise ValueError("Choose missing or windows")
    for ident, path in paths.items():
        if not path.is_file():
            raise FileNotFoundError(str(path))
        if not stl_info(path)["triangles"]:
            raise ValueError("Mesh contains zero triangles: " + ident)
    return paths, model_meta


def create_print_plates(selection, paths, metadata, output):
    output = Path(output)
    dims, meshes = [], {}
    for ident, file in paths.items():
        mesh = load_mesh(file)
        verts = mesh["vertices"].reshape(-1, 3)
        lengths = np.ptp(verts, axis=0)
        dims.append(Rect(ident, float(lengths[0]), float(lengths[1])))
        meshes[ident] = mesh
    batches = split_plates(dims)
    expected = set(paths)
    assembled = []
    for number, placements in enumerate(batches, 1):
        plate_dir = output / ("plate" + str(number))
        local = plate_dir / "individual"
        local.mkdir(parents=True, exist_ok=True)
        parts, items = [], []
        for p in placements:
            changed, lo, hi = transform(meshes[p.id], p)
            parts.append(changed)
            shutil.copyfile(paths[p.id], local / (p.id + ".stl"))
            items.append({
                "id": p.id,
                "source_model_id": metadata[p.id].get("source_model_id", p.id),
                "issue37_no": metadata[p.id]["issue37_no"],
                "rotation_deg": p.rotation_deg,
                "bounds_min_mm": lo,
                "bounds_max_mm": hi,
                "source_stl_sha256": stl_info(paths[p.id])["sha256"],
                "physical_fit_validated": False,
                "physical_rolling_validated": False,
                "slicing_validated": False,
            })
        merged = np.concatenate(parts)
        plate_path = plate_dir / ("a1mini-" + selection + "-plate" + str(number) + ".stl")
        with plate_path.open("wb") as dst:
            dst.write(("Issue37 " + selection + " " + str(number)).encode().ljust(80, b"\0"))
            dst.write(struct.pack("<I", len(merged)))
            dst.write(merged.tobytes())
        if len(load_mesh(plate_path)) != len(merged):
            raise ValueError("Combined plate STL does not round-trip")
        (plate_dir / "layout.svg").write_text(layout_svg(placements))
        plate_record = {
            "plate": number,
            "selection": selection,
            "bed_mm": BED_MM,
            "margin_mm": MARGIN_MM,
            "minimum_gap_mm": GAP_MM,
            "mesh": plate_path.name,
            "mesh_sha256": hashlib.sha256(plate_path.read_bytes()).hexdigest(),
            "count": len(items),
            "items": items,
            "slicing_validated": False,
            "physical_fit_validated": False,
            "physical_rolling_validated": False,
        }
        (plate_dir / "manifest.json").write_text(
            json.dumps(plate_record, ensure_ascii=False, indent=2) + "\n")
        assembled.append(plate_record)
    if {item["id"] for plate in assembled for item in plate["items"]} != expected:
        raise ValueError("Not all mesh files were included in a print plate")
    summary = {
        "selection": selection,
        "model_count": len(paths),
        "plate_count": len(assembled),
        "plates": [{"plate": p["plate"], "items": [m["id"] for m in p["items"]]}
                   for p in assembled],
        "source_data": {
            ident: {"source_model_id": metadata[ident].get("source_model_id", ident),
                    "course": metadata[ident]["course"],
                    "source_reference": metadata[ident].get("source_reference",
                        metadata[ident].get("source", {}).get("reference")),
                    "contract_evidence": metadata[ident]["contract_evidence"]}
            for ident in paths
        },
        "physical_fit_validated": False,
        "physical_rolling_validated": False,
        "slicing_validated": False,
    }
    (output / "manifest.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print("Prepared", len(paths), selection, "items in", len(assembled), "plate(s)", flush=True)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--set", choices=("missing", "windows", "all"), default="missing")
    parser.add_argument("--build", type=Path, default=ROOT / "build/course-followup")
    parser.add_argument("--print", dest="print_dir", type=Path, default=ROOT / "build/course-followup-plates")
    args = parser.parse_args()
    for selection in (("missing", "windows") if args.set == "all" else (args.set,)):
        paths, meta = prepare_sources(selection, args.build / selection)
        create_print_plates(selection, paths, meta, args.print_dir / selection)


if __name__ == "__main__":
    main()
