"""Package validated PR20 STL outputs for GitHub Actions artifacts.

The CAD models are generated in separate bounded stages; this script only
verifies their reports and STL binary framing before copying for download.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct


SOURCE_STLS = {
    "S01-V2.stl": ("sloped_curve", "sloped_curve/brick.stl"),
    "S02-V2.stl": ("S02-V2", "S02-V2/brick.stl"),
    "E01-V2.stl": ("elbow", "elbow/brick.stl"),
    "T01-V2.stl": ("tunnel", "tunnel/brick.stl"),
    "T02-V1.stl": ("T02-V1", "T02-V1/brick.stl"),
    "T03-V1.stl": ("T03-V1", "T03-V1/brick.stl"),
    "T04-V1.stl": ("T04-V1", "T04-V1/brick.stl"),
}
EXPECTED_SPECIMENS = [
    "S01-V2", "S02-V2", "E01-V2-A", "E01-V2-B",
    "T01-V2", "T02-V1", "T03-V1", "T04-V1",
]


def load_passed_report(path):
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("passed") is not True or report.get("mesh", {}).get("passed") is not True:
        raise ValueError(f"Unvalidated CAD export: {path}")
    return report


def verify_binary_stl(path):
    length = path.stat().st_size
    if length < 134 or (length - 84) % 50 != 0:
        raise ValueError(f"Not a binary STL: {path} ({length} bytes)")
    with path.open("rb") as infile:
        infile.seek(80)
        facets = struct.unpack("<I", infile.read(4))[0]
    if facets <= 0 or 84 + facets * 50 != length:
        raise ValueError(f"STL facet count inconsistent: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as infile:
        for chunk in iter(lambda: infile.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"bytes": length, "triangles": facets, "sha256": digest.hexdigest()}


def package(parts_root, comparison_root, output):
    # Fail without modifying the release folder if any source or report is invalid.
    sources = {}
    for name, (folder, relpath) in SOURCE_STLS.items():
        root = comparison_root if folder in {"S02-V2", "T02-V1", "T03-V1", "T04-V1"} else parts_root
        part_folder = root / folder
        load_passed_report(part_folder / "report.json")
        path = root / relpath
        sources[name] = (path, verify_binary_stl(path))
    batch_root = parts_root / "batch"
    batch = load_passed_report(batch_root / "report.json")
    labels = [item["id"] for item in batch["specimens"]]
    if labels != EXPECTED_SPECIMENS:
        raise ValueError(f"Unexpected model IDs or count: {labels}")
    sources["play-set-8.stl"] = (batch_root / "play-set-8.stl", verify_binary_stl(batch_root / "play-set-8.stl"))
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"Release folder must be empty: {output}")
    output.mkdir(parents=True, exist_ok=True)
    for name, (src, _meta) in sources.items():
        shutil.copyfile(src, output / name)
    manifest = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": os.getenv("GITHUB_SHA"),
        "git_ref": os.getenv("GITHUB_REF"),
        "specimens": labels,
        "physical_fit_validated": False,
        "slicing_validated": False,
        "files": {name: meta for name, (_path, meta) in sources.items()},
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (output / "SHA256SUMS.txt").write_text(
        "".join(f"{meta['sha256']}  {name}\n" for name, (_path, meta) in sources.items()), encoding="utf-8"
    )
    summary = os.getenv("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as report:
            report.write("## Printable STL artifact\n\n")
            report.write(f"Source commit: {os.getenv('GITHUB_SHA', 'unknown')}  \n")
            report.write("Download print-ready-play-set-8 from this run's Artifacts section.\n\n")
            report.write("Contains the 8-piece plate, 7 unique individual STLs, a JSON manifest and SHA256 sums.\n")
            report.write("Physical fit and slicing are **not** verified.\n")
    for name, (_path, meta) in sources.items():
        print(f"ARTIFACT {name}: {meta['bytes']} bytes; {meta['triangles']} triangles; sha256={meta['sha256']}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parts-root", type=Path, default=Path("build/print-source"))
    parser.add_argument("--comparison-root", type=Path, default=Path("build/pr20-comparison"))
    parser.add_argument("--out", type=Path, default=Path("build/print-ready"))
    args = parser.parse_args()
    package(args.parts_root, args.comparison_root, args.out)


if __name__ == "__main__":
    main()
