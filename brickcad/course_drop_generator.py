"""Issue #39: one CAD recipe generator for both roofed steep-drop exits.

S01-V8 (west to east) and S02-V15 (west to south) provide the engineering
reference. Existing parts and their version IDs are never overwritten.
This creates independent prototype IDs X01/X02 for parity and print tests.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path


def validate_spec(spec):
    if not isinstance(spec, dict) or set(spec) != {
            "id", "version", "geometry", "enclosure", "connection"}:
        raise ValueError("Required id, version, geometry, enclosure and connection")
    if not isinstance(spec["id"], str) or not re.fullmatch(r"X[0-9]{2}", spec["id"]):
        raise ValueError("Prototypes must use Xnn IDs, not overwrite historical S01/S02")
    if not isinstance(spec["version"], str) or not re.fullmatch(r"V[1-9][0-9]*", spec["version"]):
        raise ValueError("Invalid prototype revision")
    g = spec["geometry"]
    if not isinstance(g, dict) or set(g) != {
            "kind", "size", "height_change", "entry", "exit", "ramp_grade"}:
        raise ValueError("Invalid steep-drop geometry keys")
    if (g["kind"] != "roofed_steep_drop"
            or g["size"] != [2, 2, 3] or g["height_change"] != -1
            or g["entry"] != "west" or g["exit"] not in ("east", "south")
            or type(g["ramp_grade"]) not in (float, int)
            or abs(g["ramp_grade"] - .25) > 1e-8):
        raise ValueError("Only roofed 2x2x3 west-entry 0.25-grade east/south drop is established")
    if spec["enclosure"] != {"kind": "tunnel", "windows": []}:
        raise ValueError("No openings/windows allowed on the roofed drop chamber")
    if spec["connection"] != {"profile": "E31-05"}:
        raise ValueError("The steep-drop prototype requires E31-05 receiver")
    return spec


def load_spec(path):
    return validate_spec(json.loads(Path(path).read_text(encoding="utf-8")))


def export_config(config, out):
    from brickcad.course_steep_drop import export_course
    config = Path(config)
    spec = load_spec(config)
    out = Path(out)
    report = export_course(spec, out)
    if report.get("passed") is not True:
        raise ValueError("Steep drop failed CAD checks")
    stl = out / "brick.stl"
    manifest = {
        "schema_version": 2,
        "mode": "configured_cad_geometry",
        "id": spec["id"], "version": spec["version"],
        "geometry_reference": ("PR #38 S01-V8" if spec["geometry"]["exit"] == "east"
                               else "PR #41 S02-V15"),
        "geometry_verified": True, "physical_fit_validated": False,
        "physical_rolling_validated": False, "slicing_validated": False,
        "recipe_sha256": hashlib.sha256(config.read_bytes()).hexdigest(),
        "stl_sha256": hashlib.sha256(stl.read_bytes()).hexdigest(),
        "limitations": [
            "Independent CAD reconstruction; not a bitwise reproduction of historical PRs.",
            "A fall and inclined outlet may still lose momentum during real printing.",
            "No slicer or physical child-safety validation.",
        ],
    }
    (out / "course-manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = export_config(args.config, args.out)
    print("STEPPED-DROP COURSE PASS", result["id"], result["version"], flush=True)


if __name__ == "__main__":
    main()
