"""Proven one-night 9-part plate for PR56's seven missing CAD models.

This is a shape-aware 2-D nesting WITNESS, not bounding-box packing. The XY
positions were selected from the actual binary STL projected silhouettes,
including 0/90/180/270-degree rotation. The script regenerates each CAD model,
reapplies the witness, and independently checks the physical output triangles
against A1 mini bed bounds and conservative 4 mm spacing. If regenerated CAD
changes enough to violate the witness, abort instead of publishing a stale STL.

All three open PR56 meshes remain unchanged; all four formerly unprinted
closed courses use separately versioned two-sided tall pointed windows. One single-sided
SD04 is retained as a physical comparison. No new window has a print approval.
"""
import hashlib
import json
import shutil
from pathlib import Path
import struct
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brickcad.course_windows import build_window_variant
from brickcad.course_visibility_windows import VISIBLE_DUAL_IDS, build_visible_window_variant
from experiments.course_validation_plate.assemble import DTYPE, load_mesh
from scripts.course_followup_print import EXPECTED_MISSING
from scripts.course_catalog import load_registry, select, build

BED_MM = 180.0
PIXELS_PER_MM = 2.0
BED_PIXELS = int(BED_MM * PIXELS_PER_MM)
MARGIN_MM = 3.0
MIN_RASTER_DISTANCE_MM = 4.49  # 0.5-mm raster overestimates actual clearance.
# Positions are upper-left corners (row, column), measured in 0.5-mm cells
# of a projected STL mask padded by five cells. "rot" is quarters *counter-
# clockwise* in the array; equivalently a clockwise rotation in Cartesian XY.
# Verified with the 2026-11-04 CAD/STL generation artifacts for PR73.
OVERNIGHT_LAYOUT = (
    (0,   1, "SD04-V15", 1),     # two-sided steep-sharp-left pilot
    (0,  74, "E01-V7",   1),     # two-sided large horizontal R48 tunnel
    (138, 0, "SD04-V16", 2),    # 1-window control, compare to SD04-V12
    (138,141, "S01-V11",  1),    # two-sided 2x2 vertical-shaft tunnel
    (0, 212, "SC03-V5",  1),    # unchanged open course
    (215, 0, "SC02-V16", 3),    # two-sided sloped R48 tunnel
    (130,215, "GC01-V5", 0),    # unchanged open course
    (207,113, "SC05-V1", 1),    # unchanged open course
    (267,217, "SD03-V15", 2),   # two-sided steep-sharp-right pilot
)
WINDOWED_ON_PLATE = {
    "SD04-V15": "SD04-V10",
    "E01-V7": "E01-V3",
    "SD04-V16": "SD04-V10",  # pointed 3-window one-sided control
    "S01-V11": "S01-V8",
    "SC02-V16": "SC02-V12",
    "SD03-V15": "SD03-V11",
}
DUAL_ON_PLATE = set(WINDOWED_ON_PLATE) & set(VISIBLE_DUAL_IDS.values())
OPEN_UNPRINTED = EXPECTED_MISSING - set(VISIBLE_DUAL_IDS)


def transform_for_plate(mesh, row, col, quarter_turns):
    """Rotate only around build-plate Z; never scale or flip the mesh."""
    transformed = mesh.copy()
    vertices, normals = transformed["vertices"], transformed["normal"]
    lo = vertices.min(axis=(0, 1))
    hi = vertices.max(axis=(0, 1))
    # The witness was generated from projected masks with 5px positive-end
    # canvas padding and 5px on EACH side before contour inflation.
    px_w = int(np.ceil((hi[0] - lo[0]) * PIXELS_PER_MM)) + 15
    px_h = int(np.ceil((hi[1] - lo[1]) * PIXELS_PER_MM)) + 15
    x = (vertices[..., 0].copy() - lo[0]) * PIXELS_PER_MM + 5
    y = (vertices[..., 1].copy() - lo[1]) * PIXELS_PER_MM + 5
    if quarter_turns == 0:
        new_x, new_y = x, y
    elif quarter_turns == 1:
        new_x, new_y = y, px_w - 1 - x
    elif quarter_turns == 2:
        new_x, new_y = px_w - 1 - x, px_h - 1 - y
    elif quarter_turns == 3:
        new_x, new_y = px_h - 1 - y, x
    else:
        raise ValueError("Only integer 90-degree plate rotations are allowed")
    vertices[..., 0] = (new_x + col) / PIXELS_PER_MM
    vertices[..., 1] = (new_y + row) / PIXELS_PER_MM
    vertices[..., 2] -= lo[2]
    original_nx, original_ny = normals[:, 0].copy(), normals[:, 1].copy()
    if quarter_turns == 1:
        normals[:, 0], normals[:, 1] = original_ny, -original_nx
    elif quarter_turns == 2:
        normals[:, 0], normals[:, 1] = -original_nx, -original_ny
    elif quarter_turns == 3:
        normals[:, 0], normals[:, 1] = -original_ny, original_nx
    return transformed


def raster_projection(mesh):
    import cv2  # Optional for the ordinary CAD version-selection CI; installed in the plate job.
    """Rasterize all triangles conservatively from above at 0.5mm resolution.

    No bounding-box approximation: concave curves keep their empty XY space.
    """
    xy = np.rint(mesh["vertices"][..., :2] * PIXELS_PER_MM).astype(np.int32)
    canvas = np.zeros((BED_PIXELS, BED_PIXELS), dtype=np.uint8)
    for start in range(0, len(xy), 10000):
        cv2.fillPoly(canvas, [triangle for triangle in xy[start:start+10000]], 1)
    return canvas


def write_binary_stl(mesh, path):
    with Path(path).open("wb") as fp:
        fp.write(b"Issue37 PR56 overnight 9-part plate".ljust(80, b"\0"))
        fp.write(struct.pack("<I", len(mesh)))
        fp.write(mesh.tobytes())


def build_overnight(output):
    import cv2  # Plate build dependency only; ordinary source tests do not require OpenCV.
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    local = output / "individual"
    local.mkdir(exist_ok=True)
    source_root = ROOT / "build/course-overnight-sources"
    open_models = select(load_registry(), ",".join(sorted(OPEN_UNPRINTED)))
    open_result = build(open_models, source_root / "unroofed")
    paths = {m["id"]: source_root / "unroofed" / m["stl"]
             for m in open_result["models"]}
    window_reports = {}
    for new_id, parent_id in WINDOWED_ON_PLATE.items():
        out = source_root / "windows" / new_id
        candidate = build_visible_window_variant(
            parent_id, out, sides=2 if new_id in DUAL_ON_PLATE else 1)
        if candidate["id"] != new_id or not candidate["report"]["passed"]:
            raise ValueError("Unexpected pointed-window variant output")
        window_reports[new_id] = candidate["report"]
        reports_dir = output / "window-reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(out / "report.json", reports_dir / (new_id + ".json"))
        print("TRACK-ALIGNED WINDOWS", new_id,
              [len(face) for face in
               candidate["report"]["geometry"]["windows"]], flush=True)
        paths[new_id] = out / "brick.stl"
    requested = [item[2] for item in OVERNIGHT_LAYOUT]
    if (len(requested) != len(set(requested)) or len(requested) != 9
            or set(requested) != OPEN_UNPRINTED | set(WINDOWED_ON_PLATE)
            or set(paths) != set(requested)
            or {v for k,v in WINDOWED_ON_PLATE.items() if k in DUAL_ON_PLATE}
               < (EXPECTED_MISSING - OPEN_UNPRINTED)):
        raise ValueError("Nine-mesh one-night plan no longer covers every unprinted tunnel")

    seen = []
    pieces = []
    manifest_items = []
    overall_min = float("inf")
    preview = np.full((BED_PIXELS, BED_PIXELS, 3), 246, dtype=np.uint8)
    colors = [(102, 170, 196), (144, 171, 115), (208, 153, 99),
              (187, 135, 164), (107, 178, 160), (165, 160, 214),
              (214, 174, 180), (164, 186, 113), (119, 161, 217)]
    for index, (row, col, ident, quarter_turns) in enumerate(OVERNIGHT_LAYOUT):
        src = paths[ident]
        if not src.is_file():
            raise FileNotFoundError(str(src))
        from_stl = load_mesh(src)
        transformed = transform_for_plate(from_stl, row, col, quarter_turns)
        positions = transformed["vertices"].reshape(-1, 3)
        if (positions[:, :2].min() < MARGIN_MM - 0.051 or
                positions[:, :2].max() > BED_MM - MARGIN_MM + 0.051 or
                positions[:, 2].min() < -0.051):
            raise ValueError(f"Bed margin violated for {ident}")
        if not np.isfinite(positions).all():
            raise ValueError(f"Non-finite mesh for {ident}")
        projected = raster_projection(transformed)
        if not projected.any():
            raise ValueError("Projected CAD is empty: " + ident)
        for other, preceding in seen:
            # The 0.5-mm raster is deliberately conservatively compared
            # against 4.49 mm: XY rounding can add <= 0.5mm error.
            dist = cv2.distanceTransform(
                (1 - preceding).astype(np.uint8), cv2.DIST_L2,
                cv2.DIST_MASK_PRECISE)
            gap = float(dist[projected != 0].min()) / PIXELS_PER_MM
            overall_min = min(overall_min, gap)
            if gap < MIN_RASTER_DISTANCE_MM:
                raise ValueError(
                    f"Insufficient 4 mm footprint clearance for {ident} / {other}: "
                    f"raster gap={gap:.2f} mm")
        seen.append((ident, projected))
        preview[projected != 0] = colors[index]
        write_binary_stl(transformed, local / f"{ident}.stl")
        pieces.append(transformed)
        manifest_items.append({
            "id": ident,
            "model_type": ("double_window" if ident in DUAL_ON_PLATE else
                           "single_window_comparison" if ident in WINDOWED_ON_PLATE else
                           "PR56_unprinted_open"),
            "visible_windows_per_face": (
                [len(x) for x in
                 window_reports[ident]["geometry"]["faces"]]
                if ident in window_reports else []),
            "source_sha256": hashlib.sha256(src.read_bytes()).hexdigest(),
            "rotation_quarters": quarter_turns,
            "placement_row_px": row,
            "placement_col_px": col,
            "bounds_min_mm": positions.min(axis=0).astype(float).tolist(),
            "bounds_max_mm": positions.max(axis=0).astype(float).tolist(),
            "physical_fit_validated": False,
            "physical_rolling_validated": False,
            "slicing_validated": False,
        })
    if not len(pieces) == 9:
        raise ValueError("Some physical test pieces are missing")
    assembled = np.concatenate(pieces)
    dest = output / "pr56-overnight-9parts.stl"
    write_binary_stl(assembled, dest)
    if len(load_mesh(dest)) != len(assembled):
        raise ValueError("Combined STL failed triangle-count roundtrip")
    picture = Image.fromarray(preview).resize((720, 720), resample=Image.Resampling.NEAREST)
    painter = ImageDraw.Draw(picture)
    for item in manifest_items:
        px, py = item["bounds_min_mm"][:2]
        painter.text((px * 4 + 2, py * 4 + 2), item["id"], fill=(15, 15, 15))
    picture.save(output / "layout.png")
    report = {
        "model_count": 9,
        "pr56_classifications_covered": 7,
        "unprinted_open_models": len(OPEN_UNPRINTED),
        "two_sided_window_models": len(DUAL_ON_PLATE),
        "single_sided_comparison_models": len(set(WINDOWED_ON_PLATE)-DUAL_ON_PLATE),
        "bed_mm": BED_MM,
        "edge_margin_mm": MARGIN_MM,
        "minimum_approximate_projected_gap_mm": overall_min,
        "acceptance_raster_gap_mm": MIN_RASTER_DISTANCE_MM,
        "combined_stl_sha256": hashlib.sha256(dest.read_bytes()).hexdigest(),
        "original_models_unchanged": True,
        "geometry_and_bed_validated": True,
        "physical_fit_validated": False,
        "physical_rolling_validated": False,
        "slicing_validated": False,
        "items": manifest_items,
    }
    (output / "manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print("A1 mini overnight plate: 9/9 sources, seven unprinted classifications "
          "including all four two-sided tunnels; "
          f"raster closest-gap {overall_min:.2f} mm", flush=True)
    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "build/course-overnight-plate")
    args = parser.parse_args()
    build_overnight(args.out)
