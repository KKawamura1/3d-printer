"""A1 mini 1-plate print trial: only E01 and SC02, no diameter coupons.

R48 passage stopping and neighbour junctions are the actual experiment.
Preserve the two independently verified source meshes exactly, shifting them
only in XY. A multi-shell STL is intended for Bambu Studio on a single bed.
The CAD port diameter is fixed at 25.74mm; no variant mouths are generated.
"""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path

FILENAME = "PR91_R48_E01_SC02_2parts_A1mini.stl"
BED_SIZE_MM = 180.
PLACEMENTS = (("X89-E01-U1", -36., 0.),
              ("X89-SC02-U1", 36., 0.))


def placed_mesh(path, dx, dy):
    raw = Path(path).read_bytes()
    if len(raw) < 84:
        raise ValueError(f"Too short to be a binary STL: {path}")
    triangle_count = struct.unpack_from("<I", raw, 80)[0]
    if triangle_count < 1 or len(raw) != 84 + 50 * triangle_count:
        raise ValueError(f"Invalid STL facet count: {path}")
    data = bytearray(raw[84:])
    bounds = [[math.inf] * 3, [-math.inf] * 3]
    for idx in range(triangle_count):
        base = 50 * idx
        # STL triangle: normal(12 bytes), vertex0, vertex1, vertex2, attr(2).
        # Normals, triangle connectivity and all z values remain untouched.
        for vertex in (0, 1, 2):
            offset = base + 12 + 12 * vertex
            x, y, z = struct.unpack_from("<3f", data, offset)
            x += dx
            y += dy
            if not all(math.isfinite(v) for v in (x, y, z)):
                raise ValueError("Non-finite STL coordinate")
            struct.pack_into("<3f", data, offset, x, y, z)
            for axis, coord in enumerate((x, y, z)):
                bounds[0][axis] = min(bounds[0][axis], coord)
                bounds[1][axis] = max(bounds[1][axis], coord)
    return triangle_count, bytes(data), bounds, hashlib.sha256(raw).hexdigest()


def pack_plate(source_root, out_dir):
    source_root, out_dir = Path(source_root), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pieces, rows = [], []
    for model_id, dx, dy in PLACEMENTS:
        path = source_root / model_id / "brick.stl"
        n, facets, bounds, source_hash = placed_mesh(path, dx, dy)
        pieces.append((n, facets))
        rows.append({
            "part": model_id, "role": "R48 tunnel test specimen",
            "xy_translation_mm": [dx, dy],
            "source_stl_sha256": source_hash,
            "triangles": n, "bounds_mm": bounds
        })

    extrema = [[min(r["bounds_mm"][0][axis] for r in rows)
                 for axis in range(3)],
               [max(r["bounds_mm"][1][axis] for r in rows)
                 for axis in range(3)]]
    bed_half = BED_SIZE_MM / 2
    if any(extrema[0][i] < -bed_half or extrema[1][i] > bed_half
           for i in (0, 1)):
        raise ValueError(f"Outside 180x180 A1 mini bed: {extrema}")
    if extrema[0][2] < -.002 or extrema[1][2] > BED_SIZE_MM:
        raise ValueError(f"Outside printer Z range: {extrema}")
    first, second = rows
    if second["bounds_mm"][0][0] - first["bounds_mm"][1][0] < 5:
        raise ValueError("At least 5mm separation required between models")

    count = sum(n for n, _ in pieces)
    header = b"PR91 R48 E01 flat + SC02 slope, no gauges".ljust(80, b" ")
    out = out_dir / FILENAME
    out.write_bytes(header + struct.pack("<I", count) +
                    b"".join(facets for _, facets in pieces))
    if out.stat().st_size != 84 + 50 * count:
        raise ValueError("Broken combined STL")
    report = {
        "printer": "Bambu Lab A1 mini",
        "bed_mm": [180, 180],
        "stl": FILENAME,
        "parts": rows,
        "part_count": 2,
        "all_parts_preverified_by_export_step": True,
        "bounds_mm": extrema,
        "xy_size_mm": [extrema[1][axis] - extrema[0][axis]
                       for axis in (0, 1)],
        "mating_port_diameter_mm": 25.74,
        "internal_radial_relief_max_mm": 1.0,
        "outer_windows_per_tunnel": 5,
        "window_width_along_arc_mm": 12.0,
        "no_comparison_gauges": True,
        "print_slicer_and_physical_rolling_validated": False,
        "stl_sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
    }
    (out_dir / "print_plate_manifest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return out, report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path,
                        default=Path("build/issue89-shared-r48"))
    parser.add_argument("--out", type=Path,
                        default=Path("build/issue89-shared-r48/plate"))
    args = parser.parse_args()
    out, report = pack_plate(args.source_root, args.out)
    print(out, report["xy_size_mm"], report["part_count"],
          report["stl_sha256"])
