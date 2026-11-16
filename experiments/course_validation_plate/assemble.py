"""Pack PR56 independent CAD meshes into one A1 mini verification plate.

The only source of geometry is scripts/course_catalog.py; no original PR builds,
historical STLs, or mesh scaling. Search over 0/90-degree orientations and
translate chosen meshes for printing. Physical validation remains separate.
"""
import argparse
from dataclasses import dataclass
import hashlib
from html import escape
import json
from pathlib import Path
import random
import shutil
import struct
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brickcad.course_contract import PRODUCTION_CONTRACT
from scripts.course_catalog import load_registry, stl_info

BED_MM = 180.0
MARGIN_MM = 3.0
GAP_MM = 4.0
# The four PR55 stage-1 models were physically accepted; repeat only S02 as a
# same-ID reference specimen for the PR56-versus-PR55 manufacturing comparison.
PR55_STAGE1 = frozenset({"E01-V3", "SD04-V10", "S02-V16", "S01-V8"})
CONTROL_ID = "S02-V16"
# Independent, risk-oriented tie-breaker. Specimen count is optimized first.
RISK_ORDER = (
    "SC02L-V6", "SC02-V12", "SD03-V11", "E01L-V1",
    "C02-V8", "SC05-V1", "S03-V10", "SC03-V5",
    "R01-V1", "T01-V6", "D02-V4", "D01-V3",
    "SD02-V4", "SD01-V4", "GC01-V5", "C01-V6",
)
PRIORITY = {ident: len(RISK_ORDER) - i for i, ident in enumerate(RISK_ORDER)}
DTYPE = np.dtype([
    ("normal", "<f4", (3,)),
    ("vertices", "<f4", (3, 3)),
    ("attr", "<u2"),
])


@dataclass(frozen=True)
class Rect:
    id: str
    w: float
    h: float
    priority: int = 0


@dataclass(frozen=True)
class Placement:
    id: str
    x: float
    y: float
    w: float
    h: float
    rotation_deg: int


def targets(registry):
    ids = {m["id"] for m in registry["models"]}
    if len(ids) != 20 or not PR55_STAGE1.issubset(ids) or not set(PRIORITY).issubset(ids):
        raise ValueError("PR56 catalogue and the PR55 control plan disagree")
    selected = [m["id"] for m in registry["models"]
                if m["id"] not in PR55_STAGE1 or m["id"] == CONTROL_ID]
    if len(selected) != 17 or set(selected) != set(PRIORITY) | {CONTROL_ID}:
        raise ValueError("Expected 16 untested catalogue IDs plus the one PR55 control")
    return selected


def load_mesh(path):
    raw = Path(path).read_bytes()
    if len(raw) < 134 or (len(raw) - 84) % DTYPE.itemsize:
        raise ValueError(f"Invalid binary STL: {path}")
    count = struct.unpack_from("<I", raw, 80)[0]
    if count < 1 or len(raw) != 84 + count * DTYPE.itemsize:
        raise ValueError(f"Invalid triangle count in {path}")
    mesh = np.frombuffer(raw, dtype=DTYPE, offset=84).copy()
    if not np.isfinite(mesh["vertices"]).all() or not np.isfinite(mesh["normal"]).all():
        raise ValueError(f"Nonfinite mesh: {path}")
    return mesh


def fits(proposed, placed):
    if (proposed.x < MARGIN_MM - 1e-4 or proposed.y < MARGIN_MM - 1e-4
            or proposed.x + proposed.w > BED_MM - MARGIN_MM + 1e-4
            or proposed.y + proposed.h > BED_MM - MARGIN_MM + 1e-4):
        return False
    for other in placed:
        separated = (
            proposed.x + proposed.w + GAP_MM <= other.x + 1e-4
            or other.x + other.w + GAP_MM <= proposed.x + 1e-4
            or proposed.y + proposed.h + GAP_MM <= other.y + 1e-4
            or other.y + other.h + GAP_MM <= proposed.y + 1e-4
        )
        if not separated:
            return False
    return True


def pack_order(order, *, orientation_bias):
    placed = []
    for rect in order:
        # Lower-left candidate coordinates aligned to a placed rectangle edge
        # (and their cross product) cover common rectangular shelf layouts.
        xs = sorted({MARGIN_MM} | {p.x + p.w + GAP_MM for p in placed})
        ys = sorted({MARGIN_MM} | {p.y + p.h + GAP_MM for p in placed})
        rotations = ((0, rect.w, rect.h), (90, rect.h, rect.w))
        if orientation_bias:
            rotations = tuple(reversed(rotations))
        available = [
            Placement(rect.id, x, y, w, h, angle)
            for x in xs for y in ys for angle, w, h in rotations
            if fits(Placement(rect.id, x, y, w, h, angle), placed)
        ]
        if available:
            # Prefer bottom-left; orientation bias explores alternate shelves.
            placed.append(min(available, key=lambda p: (p.y, p.x, p.rotation_deg)))
    return placed


def pack(rectangles, *, attempts=320):
    if not any(r.id == CONTROL_ID for r in rectangles):
        raise ValueError("PR55 control specimen is mandatory")
    if len({r.id for r in rectangles}) != len(rectangles):
        raise ValueError("Duplicate model IDs")
    mandatory = next(r for r in rectangles if r.id == CONTROL_ID)
    remaining = [r for r in rectangles if r.id != CONTROL_ID]
    best, best_score = None, None
    for i in range(attempts):
        rng = random.Random(56000 + i)
        if i % 8 == 0:
            order = sorted(remaining, key=lambda r: r.w * r.h)
        elif i % 8 == 1:
            order = sorted(remaining, key=lambda r: -(r.w * r.h))
        elif i % 8 == 2:
            order = sorted(remaining, key=lambda r: -r.priority)
        elif i % 8 == 3:
            order = sorted(remaining, key=lambda r: max(r.w, r.h))
        else:
            order = remaining.copy()
            rng.shuffle(order)
        result = pack_order([mandatory] + order, orientation_bias=i % 2)
        if not result or result[0].id != CONTROL_ID:
            raise ValueError("Cannot place mandatory PR55 control on A1 mini")
        score = (
            len(result) - 1,  # untested first; mandatory control doesn't count
            sum(PRIORITY.get(p.id, 0) for p in result),
            -sum(p.w * p.h for p in result),
        )
        if best_score is None or score > best_score:
            best, best_score = result, score
    if not best:
        raise ValueError("Unable to pack any source meshes")
    for i, item in enumerate(best):
        if not fits(item, best[:i] + best[i + 1:]):
            raise ValueError("Final plate has overlapping or out-of-bed footprints")
    return best


def transform(mesh, placement):
    result = mesh.copy()
    vertices = result["vertices"]
    normals = result["normal"]
    if placement.rotation_deg == 90:
        ox = vertices[..., 0].copy()
        vertices[..., 0] = -vertices[..., 1]
        vertices[..., 1] = ox
        nx = normals[..., 0].copy()
        normals[..., 0] = -normals[..., 1]
        normals[..., 1] = nx
    elif placement.rotation_deg != 0:
        raise ValueError("No arbitrary-angle rotation permitted")
    lo = vertices.reshape(-1, 3).min(axis=0)
    vertices[..., 0] += placement.x - float(lo[0])
    vertices[..., 1] += placement.y - float(lo[1])
    vertices[..., 2] -= float(lo[2])
    actual_lo = vertices.reshape(-1, 3).min(axis=0)
    actual_hi = vertices.reshape(-1, 3).max(axis=0)
    if (abs(float(actual_hi[0] - actual_lo[0]) - placement.w) > 0.02
            or abs(float(actual_hi[1] - actual_lo[1]) - placement.h) > 0.02):
        raise ValueError("Incorrect transformed footprint")
    return result, actual_lo.astype(float).tolist(), actual_hi.astype(float).tolist()


def audit_source(manifest, chosen):
    if manifest.get("production_contract") != PRODUCTION_CONTRACT:
        raise ValueError("Wrong PR56 production contract")
    models = {x["id"]: x for x in manifest["models"]}
    if len(models) != len(manifest["models"]) or set(models) != set(chosen):
        raise ValueError("CAD source manifest must contain exactly the requested IDs")
    for ident, m in models.items():
        proof = m.get("contract_evidence", {})
        if (m.get("source", {}).get("kind") != "configured"
                or m.get("geometry_verified") is not True
                or m.get("legacy_unverified_e31") is not False
                or m.get("production_contract") != PRODUCTION_CONTRACT
                or proof.get("model_id") != ident
                or proof.get("production_contract") != PRODUCTION_CONTRACT
                or proof.get("fit_calls", 0) < 1
                or proof.get("e31_receiver_calls", 0) < 1
                or proof.get("final_marking_labels") != [ident]):
            raise ValueError(f"Missing common E31-05 + final-ID-engraving evidence: {ident}")
    return models


def layout_svg(placements):
    scale = 3
    cells = []
    for p in placements:
        cells.append(
            f'<rect x="{p.x*scale:.2f}" y="{p.y*scale:.2f}" '
            f'width="{p.w*scale:.2f}" height="{p.h*scale:.2f}" '
            f'fill="#dbeafe" stroke="#1d4ed8" stroke-width="1.5"/>'
            f'<text x="{(p.x+p.w/2)*scale:.2f}" y="{(p.y+p.h/2)*scale:.2f}" '
            f'text-anchor="middle" dominant-baseline="middle" font-size="10">'
            f'{escape(p.id)}</text>'
        )
    size = int(BED_MM * scale)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" '
            f'height="{size}" viewBox="0 0 {size} {size}">'
            f'<rect width="{size}" height="{size}" fill="#fafafa" '
            f'stroke="#555" stroke-width="2"/>' + "".join(cells) + '</svg>\n')


def assemble(source_root, output, expected):
    source_root, output = Path(source_root), Path(output)
    manifest = json.loads((source_root / "manifest.json").read_text(encoding="utf-8"))
    models = audit_source(manifest, expected)
    specs, meshes = [], {}
    for ident in expected:
        model = models[ident]
        stl = source_root / model["stl"]
        info = stl_info(stl)
        if info != model["stl_info"]:
            raise ValueError(f"Source STL hash / triangle count mismatch: {ident}")
        report = json.loads((stl.parent / "report.json").read_text(encoding="utf-8"))
        if (report.get("part_id") != ident or report.get("passed") is not True
                or report.get("mesh", {}).get("passed") is not True):
            raise ValueError(f"CAD report not passed: {ident}")
        mesh = load_mesh(stl)
        verts = mesh["vertices"].reshape(-1, 3)
        span = np.ptp(verts, axis=0)
        specs.append(Rect(ident, float(span[0]), float(span[1]), PRIORITY.get(ident, 0)))
        meshes[ident] = (mesh, stl, info)
    placements = pack(specs)
    chosen_ids = {p.id for p in placements}
    output.mkdir(parents=True, exist_ok=True)
    (output / "individual").mkdir(exist_ok=True)
    moved = []
    detail = []
    for p in placements:
        mesh, source, meta = meshes[p.id]
        shifted, low, high = transform(mesh, p)
        moved.append(shifted)
        shutil.copyfile(source, output / "individual" / f"{p.id}.stl")
        detail.append({
            "id": p.id, "issue37_no": models[p.id]["issue37_no"],
            "course": models[p.id]["course"],
            "source_sha256": meta["sha256"],
            "reference": models[p.id]["source"]["reference"],
            "contract_evidence": models[p.id]["contract_evidence"],
            "rotation_deg": p.rotation_deg,
            "bounds_min_mm": low, "bounds_max_mm": high,
            "triangle_count": len(mesh),
            "physically_tested_pr56": False,
        })
    combined = np.concatenate(moved)
    name = f"pr56-validation-{len(placements)}parts.stl"
    destination = output / name
    with destination.open("wb") as handle:
        handle.write(b"PR56 independent-CAD A1-mini validation plate".ljust(80, b"\0"))
        handle.write(struct.pack("<I", len(combined)))
        handle.write(combined.tobytes())
    if len(load_mesh(destination)) != len(combined):
        raise ValueError("Assembled binary STL does not round-trip")
    shutil.copyfile(source_root / "manifest.json", output / "pr56-source-manifest.json")
    (output / "layout.svg").write_text(layout_svg(placements), encoding="utf-8")
    result = {
        "source": "PR56 configured course catalogue only",
        "production_contract": PRODUCTION_CONTRACT,
        "bed_mm": BED_MM, "margin_mm": MARGIN_MM, "minimum_gap_mm": GAP_MM,
        "source_model_count": len(expected),
        "printed_model_count": len(placements),
        "unverified_models_on_plate": len(placements) - 1,
        "reference_pr55_stage1_id": CONTROL_ID,
        "excluded_successful_pr55_stage1": sorted(PR55_STAGE1 - {CONTROL_ID}),
        "not_on_plate": sorted(set(expected) - chosen_ids),
        "covered_issue37_categories": sorted(no for d in detail for no in d["issue37_no"]),
        "mesh": name,
        "mesh_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "slicing_validated": False, "physical_fit_validated": False,
        "physical_rolling_validated": False,
        "optimality_proven": False, "packing_attempts": 320,
        "items": detail,
    }
    (output / "manifest.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Packed {len(placements)}/{len(expected)} sources; "
          f"{len(placements)-1} untested and one PR55 control; excluded "
          + ", ".join(result["not_on_plate"]), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("targets", "build"), default="build")
    parser.add_argument("--sources", type=Path, default=ROOT / "build/course-catalog")
    parser.add_argument("--out", type=Path, default=ROOT / "build/course-validation-plate")
    args = parser.parse_args()
    selected = targets(load_registry())
    if args.mode == "targets":
        print(",".join(selected))
    else:
        assemble(args.sources, args.out, selected)


if __name__ == "__main__":
    main()
