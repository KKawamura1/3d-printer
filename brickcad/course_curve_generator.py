"""One strict config entrypoint for the proven R16 west->south sharp curve family.

Y01 open and Y02 tunnel use the same centreline/cutter; a roof and local
turn-apex relief are enclosure options. No assumption about a successful
physical print is encoded as validation.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path


def validate_spec(spec):
    if not isinstance(spec, dict) or set(spec) != {
            "id", "version", "geometry", "enclosure", "connection"}:
        raise ValueError("Sharp-curve spec needs id, version, geometry, enclosure, connection")
    if not isinstance(spec["id"], str) or not re.fullmatch(r"Y[0-9]{2}", spec["id"]):
        raise ValueError("Curve prototypes must use Ynn IDs (never C01/C02)")
    if not isinstance(spec["version"], str) or not re.fullmatch(r"V[1-9][0-9]*", spec["version"]):
        raise ValueError("Invalid prototype revision")
    enclosure = spec["enclosure"]
    if not isinstance(enclosure, dict) or set(enclosure) != {"kind", "windows"}:
        raise ValueError("Enclosure must contain kind and windows")
    kind = enclosure["kind"]
    if kind not in ("open", "tunnel") or enclosure["windows"] != []:
        raise ValueError("R16 family supports only open / roofed tunnel, without windows")
    geometry = spec["geometry"]
    expected = {"kind": "sharp_curve_R16", "entry": "west", "exit": "south",
                "height_change": 0, "radius_mm": 16,
                "size": [2, 2, 1] if kind == "open" else [2, 2, 2]}
    if geometry != expected:
        raise ValueError("R16 geometry must match the PR #36 west/south prototype")
    if spec["connection"] != {"profile": "E31-05", "studs": (
            "none" if kind == "open" else "roof_four")}:
        raise ValueError("Studs and E31-05 must match the chosen enclosure")
    return spec


def load_spec(path):
    return validate_spec(json.loads(Path(path).read_text(encoding="utf-8")))


def export_config(config, out):
    from brickcad.course_sharp_curve import export_course
    config = Path(config)
    spec = load_spec(config)
    out = Path(out)
    report = export_course(spec, out)
    if report.get("passed") is not True:
        raise RuntimeError("Sharp curve failed CAD validations")
    manifest = {
        "schema_version": 2, "mode": "configured_cad_geometry",
        "id": spec["id"], "version": spec["version"],
        "geometry_reference": ("PR #36 C01-V5" if spec["enclosure"]["kind"] == "open"
                               else "PR #36 C02-V5 (C02-V2 restored guide)"),
        "pinned_reference_commit": "fc70fdd3bf34a6b675595d54c721cec4544e1e76",
        "recipe_sha256": hashlib.sha256(config.read_bytes()).hexdigest(),
        "stl_sha256": hashlib.sha256((out/"brick.stl").read_bytes()).hexdigest(),
        "geometry_verified": True,
        "physical_fit_validated": False,
        "physical_rolling_validated": False,
        "slicing_validated": False,
        "limitations": [
            "Stage 1 of PR #55 is assumed successful for prioritization, not observed.",
            "C02-V5 internal burrs and natural exit speed remain subject to user print feedback.",
            "Only an R16 west->south route is supported; alternative handedness is not implemented.",
        ],
    }
    (out/"course-manifest.json").write_text(
        json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    args = parser.parse_args()
    manifest = export_config(args.config,args.out)
    print("CONFIGURABLE SHARP CURVE PASS",manifest["id"],manifest["version"],flush=True)


if __name__ == "__main__":
    main()
