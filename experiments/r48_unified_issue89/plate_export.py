"""One-plate A1 mini STL: PR91 flat + sloped R48 and 4 upright mouth gauges.

Regenerate from the exact same two verified STEP-derived STL files, without
altering their mesh geometry. Mouth gauges have an upright 24.50, 25.00, 25.74
or 26.50 mm through hole and are NOT compatible DUPLO connection adapters.
Run after experiments.r48_unified_issue89.export.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import tempfile

import cadquery as cq

BED_MM = 180.
PORT_GAUGES_MM = (24.5, 25.0, 25.74, 26.5)
PARTS = (("X89-E01-U1", -37., -35.),
         ("X89-SC02-U1", 37., -35.))
GAUGE_X = (-51., -17., 17., 51.)
FILENAME = "PR91_R48_E01_SC02_plus_4_mouth_gauges_A1mini.stl"


def make_port_gauge(diameter):
    body = cq.Workplane("XY").box(10., 36., 37.5,
             centered=(True, True, False)).val()
    foot = (cq.Workplane("XY").box(22., 38., 2.,
            centered=(True, True, False)).translate((-4, 0, 0)).val())
    body = body.fuse(foot).clean()
    hole = (cq.Workplane("YZ", origin=(-6., 0, 0))
            .center(0, 6.35 + diameter / 2)
            .circle(diameter / 2).extrude(12.).val())
    body = body.cut(hole).clean()
    text = (cq.Workplane("XY", origin=(0, 0, 1.90))
            .text(f"{diameter:.2f}", 4.2, .70,
                  font="DejaVu Sans", kind="bold", combine=True).val()
            .rotate((0, 0, 0), (0, 0, 1), 90).translate((-10., 0, 0)))
    body = body.fuse(text).clean()
    if not body.isValid() or len(body.Solids()) != 1:
        raise ValueError(f"Gauge {diameter} is not a valid single CAD solid")
    return body


def shifted_stl(path, dx, dy):
    raw = Path(path).read_bytes()
    if len(raw) < 84:
        raise ValueError(f"Bad STL header: {path}")
    count = struct.unpack_from("<I", raw, 80)[0]
    if not count or len(raw) != 84 + 50 * count:
        raise ValueError(f"Bad STL facet count: {path}")
    facets = []
    bounds = [[math.inf] * 3, [-math.inf] * 3]
    for i in range(count):
        a = list(struct.unpack_from("<12fH", raw, 84 + 50 * i))
        for j in (3, 6, 9):
            for k, shift in enumerate((dx, dy, 0.)):
                a[j+k] += shift
                if not math.isfinite(a[j+k]):
                    raise ValueError("Non-finite facet")
                bounds[0][k] = min(bounds[0][k], a[j+k])
                bounds[1][k] = max(bounds[1][k], a[j+k])
        facets.append(struct.pack("<12fH", *a))
    return count, b"".join(facets), bounds


def xy_gap(a, b):
    def gap(u0, u1, v0, v1):
        return max(0., u0-v1, v0-u1)
    return math.hypot(
        gap(a[0][0], a[1][0], b[0][0], b[1][0]),
        gap(a[0][1], a[1][1], b[0][1], b[1][1]),
    )


def pack_plate(source_root, out_dir):
    source_root, out_dir = Path(source_root), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pieces, rows = [], []
    for model, x, y in PARTS:
        stl = source_root / model / "brick.stl"
        n, faces, bounds = shifted_stl(stl, x, y)
        pieces.append((n, faces))
        rows.append({"part": model, "type": "R48 tunnel",
                     "bounds_mm": bounds, "triangles": n,
                     "source_sha256": hashlib.sha256(stl.read_bytes()).hexdigest()})
    with tempfile.TemporaryDirectory(prefix="pr91-plate-") as tmp:
        for diameter, x in zip(PORT_GAUGES_MM, GAUGE_X):
            gauge = make_port_gauge(diameter)
            fn = Path(tmp) / f"gauge-{diameter:.2f}.stl"
            cq.exporters.export(gauge, str(fn), tolerance=.02,
                                angularTolerance=.12)
            n, faces, bounds = shifted_stl(fn, x, 39.)
            pieces.append((n, faces))
            rows.append({"part": f"GAUGE-{diameter:.2f}",
                         "type": "Upright aperture coupon; not DUPLO adapter",
                         "hole_diameter_mm": diameter,
                         "bounds_mm": bounds, "triangles": n})
    extrema = [[min(r["bounds_mm"][0][i] for r in rows) for i in range(3)],
               [max(r["bounds_mm"][1][i] for r in rows) for i in range(3)]]
    if not (-90 < extrema[0][0] and extrema[1][0] < 90 and
            -90 < extrema[0][1] and extrema[1][1] < 90 and
            abs(extrema[0][2]) < .002 and extrema[1][2] < BED_MM):
        raise ValueError(f"Part outside A1 mini build volume: {extrema}")
    for i, a in enumerate(rows):
        for b in rows[i + 1:]:
            if xy_gap(a["bounds_mm"], b["bounds_mm"]) < 4:
                raise ValueError(f"Colliding/too-near pieces: {a['part']}, {b['part']}")
    total = sum(n for n, _ in pieces)
    stl = out_dir / FILENAME
    header = b"PR91 two R48 tunnels + four upright port gauges".ljust(80, b" ")
    stl.write_bytes(header + struct.pack("<I", total) +
                    b"".join(faces for _, faces in pieces))
    assert stl.stat().st_size == 84 + 50 * total
    report = {
        "printer": "Bambu Lab A1 mini", "bed_mm": [180, 180],
        "bounds_mm": extrema,
        "xy_size_mm": [extrema[1][i] - extrema[0][i] for i in (0, 1)],
        "stl": FILENAME, "parts": rows, "separate_shell_count": len(rows),
        "total_triangles": total,
        "mating_port_opening_diameter_mm": 25.74,
        "internal_radial_relief_max_mm": 1.0,
        "internal_lower_semicircle_equivalent_diameter_mm": 27.74,
        "passage_roof_is_not_circular": True,
        "outer_windows_per_tunnel": 5,
        "nominal_window_width_along_arc_mm": 12.,
        "window_corner_radius_mm": .8,
        "gauge_only_not_real_port_variants": True,
        "physical_print_rolling_and_slicing_verified": False,
        "source_pr": "https://github.com/KKawamura1/3d-printer/pull/91",
        "stl_sha256": hashlib.sha256(stl.read_bytes()).hexdigest()
    }
    (out_dir / "print_plate_manifest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    return stl, report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path,
                        default=Path("build/issue89-shared-r48"))
    parser.add_argument("--out", type=Path,
                        default=Path("build/issue89-shared-r48/plate"))
    args = parser.parse_args()
    output, info = pack_plate(args.source_root, args.out)
    print(output, info["xy_size_mm"], info["separate_shell_count"],
          info["stl_sha256"])
