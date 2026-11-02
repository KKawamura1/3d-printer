"""Issue #39 pilot: strict declarative *replay* of proven, revision-pinned CAD.

No geometry is silently reimplemented. Each supported recipe delegates to the
exact legacy exporter, retaining its engravings, roof, fit profile and checks.
Adding a new shape/knob requires an explicit engine change and CAD tests.
"""
import argparse
import hashlib
import json
from pathlib import Path

# Locked reference geometries. These are NOT a generic route compositor yet.
# A mismatched setting must fail, never quietly generate a different shape.
SUPPORTED = {
    "straight_tunnel": {
        "id": "T01", "version": "V4",
        "geometry": {"kind": "straight_tunnel", "size": [2, 2, 2], "height_change": 0},
        "enclosure": {"kind": "tunnel", "windows": []},
        "connection": {"profile": "E31-05"},
        "legacy": {"module": "parts.tunnel.design_e31", "part_id": "T01-V4"},
    },
    "windowed_downhill_tunnel": {
        "id": "D01", "version": "V2",
        "geometry": {"kind": "windowed_downhill_tunnel", "size": [4, 2, 3], "height_change": -1},
        "enclosure": {"kind": "tunnel", "windows": [
            {"side": "south", "x_mm": x, "width_mm": 8.0} for x in (-16.0, 0.0, 16.0)
        ]},
        "connection": {"profile": "E31-05"},
        "legacy": {"module": "parts.downhill_tunnel.design", "part_id": "D01-V2"},
    },
}


def validate_spec(spec):
    """Enforce the full supported geometry contract: no ignored or unsafe knobs."""
    if not isinstance(spec, dict):
        raise ValueError("Course recipe must be a JSON object")
    if not isinstance(spec.get("geometry"), dict):
        raise ValueError("Course recipe requires geometry object")
    kind = spec["geometry"].get("kind")
    expected = SUPPORTED.get(kind)
    if expected is None:
        raise ValueError(f"Unsupported course kind: {kind!r}")
    if set(spec) != set(expected):
        raise ValueError(f"{kind}: required keys are {sorted(expected)}")
    for key, value in expected.items():
        if spec[key] != value:
            raise ValueError(
                f"{kind}: {key} differs from the validated {expected['legacy']['part_id']} "
                "reference. New dimensions/options require an explicit engine adapter "
                "and corresponding CAD regression tests."
            )
    return expected


def load_spec(path):
    path = Path(path)
    spec = json.loads(path.read_text(encoding="utf-8"))
    validate_spec(spec)
    return spec


def export_config(config, out):
    """Export the original BRep/STL via a pinned, tested source adapter."""
    config = Path(config)
    spec = load_spec(config)
    out = Path(out)
    kind = spec["geometry"]["kind"]
    # Both dependencies are statically discoverable by cad_versions imports_for.
    if kind == "straight_tunnel":
        from parts.tunnel import design_e31 as source
    elif kind == "windowed_downhill_tunnel":
        from parts.downhill_tunnel import design as source
    else:
        raise ValueError(f"Unsupported course kind: {kind!r}")
    if source.PART_ID != spec["legacy"]["part_id"]:
        raise ValueError("Legacy source revision changed; replay is not safe")
    report = source.export(out)
    if report.get("passed") is not True:
        raise ValueError("Reference exporter did not pass its CAD checks")
    stl = out / "brick.stl"
    if not stl.is_file() or not (out / "report.json").is_file():
        raise ValueError("Reference exporter produced incomplete artifacts")
    # A *separate* manifest does not modify a legacy STL/report's provenance.
    manifest = {
        "schema_version": 1,
        "mode": "legacy_geometry_replay",
        "geometry_verified": True,
        "physical_fit_validated": False,
        "physical_rolling_validated": False,
        "slicing_validated": False,
        "id": spec["id"], "version": spec["version"], "kind": kind,
        "source_module": spec["legacy"]["module"],
        "source_part_id": source.PART_ID,
        "recipe_sha256": hashlib.sha256(config.read_bytes()).hexdigest(),
        "stl_sha256": hashlib.sha256(stl.read_bytes()).hexdigest(),
        "limitations": [
            "Only exact reference recipes supported; no arbitrary geometry composition.",
            "Legacy source exporter is reused, not independently reproduced.",
            "CAD validation does not prove printing, natural rolling or child safety.",
        ],
    }
    (out / "course-manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    manifest = export_config(args.config, args.out)
    print("COURSE REPLAY PASS", manifest["kind"], manifest["stl_sha256"], flush=True)


if __name__ == "__main__":
    main()
