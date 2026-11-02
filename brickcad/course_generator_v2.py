"""Issue #39 phase 2: configurable straight downhill tunnel geometry.

Restricted to the proven D01-V2 route, roof and E31-05 fit family. Geometry
is assembled from the original CAD primitives, but window positions/count/
width and the engraved revision come from a checked recipe.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

from brickcad.course_downhill import build_course, export_course

_ID = re.compile(r"^D[0-9]{2}$")
_VERSION = re.compile(r"^V[1-9][0-9]*$")


def validate_spec(spec):
    if not isinstance(spec, dict) or set(spec) != {
            "id", "version", "geometry", "enclosure", "connection"}:
        raise ValueError("Expected id, version, geometry, enclosure and connection")
    if not isinstance(spec["id"], str) or not _ID.fullmatch(spec["id"]):
        raise ValueError("Course ID must be D followed by two digits")
    if not isinstance(spec["version"], str) or not _VERSION.fullmatch(spec["version"]):
        raise ValueError("Course version must be V followed by positive integer")
    if spec["geometry"] != {
            "kind": "straight_downhill_tunnel", "size": [4, 2, 3],
            "height_change": -1, "entry": "west", "exit": "east"}:
        raise ValueError("Only the D01-derived straight downhill/2x4x3/west-east route is supported")
    if spec["connection"] != {"profile": "E31-05"}:
        raise ValueError("Only E31-05 receiver has a corresponding CAD adapter")
    enclosure = spec["enclosure"]
    if not isinstance(enclosure, dict) or set(enclosure) != {"kind", "windows"}:
        raise ValueError("Enclosure must specify kind and windows")
    if enclosure["kind"] != "tunnel":
        raise ValueError("Open steep/downhill variants are not supported")
    windows = enclosure["windows"]
    if not isinstance(windows, list) or len(windows) > 3:
        raise ValueError("0 to 3 windows are supported")
    spans = []
    previous = None
    for w in windows:
        if not isinstance(w, dict) or set(w) != {"side", "x_mm", "width_mm"}:
            raise ValueError("Each window needs side, x_mm, width_mm")
        if w["side"] != "south":
            raise ValueError("Only south-side windows are implemented")
        x, width = w["x_mm"], w["width_mm"]
        if (type(x) not in (int, float) or type(width) not in (int, float)
                or not -20 <= x <= 20 or not 6 <= width <= 10):
            raise ValueError("Window centres must be within +/-20 mm, width 6..10 mm")
        left, right = x-width/2, x+width/2
        if left < -25 or right > 25:
            raise ValueError("Windows need at least 6.9 mm solid ends")
        if previous is not None and left-previous < 3:
            raise ValueError("Windows must be sorted with 3 mm or more solid separation")
        previous = right
        spans.append((left, right))
    return spec


def load_spec(path):
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_spec(config)


def export_config(config, out):
    config = Path(config)
    spec = load_spec(config)
    report = export_course(spec, Path(out))
    if report.get("passed") is not True:
        raise RuntimeError("Configured geometry failed CAD validation")
    mesh_path = Path(out) / "brick.stl"
    manifest = {
        "schema_version": 2,
        "mode": "configured_cad_geometry",
        "id": spec["id"], "version": spec["version"],
        "geometry_verified": True,
        "physical_fit_validated": False,
        "physical_rolling_validated": False,
        "slicing_validated": False,
        "geometry_reference": "D01-V2",
        "recipe_sha256": hashlib.sha256(config.read_bytes()).hexdigest(),
        "stl_sha256": hashlib.sha256(mesh_path.read_bytes()).hexdigest(),
        "limitations": [
            "D01-derived geometry only; no curves, acute drops, or north windows.",
            "33 finite ball samples are not a rolling simulation.",
            "E31-05 fit transfer requires physical validation for this revision.",
        ],
    }
    (Path(out) / "course-manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = export_config(args.config, args.out)
    print("CONFIGURABLE COURSE PASS", result["id"], result["version"], flush=True)


if __name__ == "__main__":
    main()
