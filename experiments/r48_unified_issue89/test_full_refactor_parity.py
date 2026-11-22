"""Exact PR91 R48 complete-solid BRep parity against the pre-refactor head.

The baseline is pinned to PR91 commit 3bbe661, BEFORE the shared
receiver/stud and paired outer/passage sweep refactor. Both programs build
the same *unmarked* complete part, including all five windows and E31 tubes.
Comparing only the lower foundation would miss new roof or window regressions.

Run one model per CI job:
  python -m experiments.r48_unified_issue89.test_full_refactor_parity \
    --model-id X89-E01-R04 --out build/r48-brep-parity

Reference code is imported only in an isolated old git worktree/subprocess.
It must never be used by the production generator.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

import cadquery as cq

from brickcad.course_r48_unified import R48FamilyConfig, build_r48_family
from brickcad.standards import DUPLO

BASELINE_SHA = "3bbe661942e433e9480a5c311902203b669fbc39"
ROOT = Path(__file__).resolve().parents[2]
# Same test plate, same exact geometry and relief, before vs after refactor.
SPECIMENS = {
    "X89-E01-R04": (0., .4),
    "X89-E01-R10": (0., 1.),
    "X89-SC02-R04": (DUPLO.height, .4),
    "X89-SC02-R10": (DUPLO.height, 1.),
}
MAX_DELTA_MM3 = .001

# Executes in pinned old worktree, not in the new code's process or path.
REFERENCE_SCRIPT = """
import sys
from brickcad.course_r48_unified import R48PairConfig, build_r48
model_id, drop, relief, output = sys.argv[1:]
shape, details = build_r48(R48PairConfig(model_id, float(drop),
                                        relief_mm=float(relief)), marked=False)
assert shape.isValid() and len(shape.Solids()) == 1
shape.exportBrep(output)
"""


def check(model_id, out):
    if model_id not in SPECIMENS:
        raise ValueError("Unknown PR91 comparison specimen: " + model_id)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    drop, relief = SPECIMENS[model_id]
    with TemporaryDirectory(prefix="pr91-shape-parity-") as tmp:
        baseline_root = Path(tmp) / "baseline"
        old_file = Path(tmp) / "before.brep"
        added = False
        try:
            subprocess.run(
                ["git", "cat-file", "-e", BASELINE_SHA + "^{commit}"],
                check=True, cwd=ROOT, capture_output=True)
            subprocess.run(
                ["git", "worktree", "add", "--detach", "--quiet",
                 str(baseline_root), BASELINE_SHA],
                check=True, cwd=ROOT, capture_output=True)
            added = True
            env = os.environ.copy()
            env["PYTHONPATH"] = str(baseline_root)
            result = subprocess.run(
                [sys.executable, "-c", REFERENCE_SCRIPT,
                 model_id, str(drop), str(relief), str(old_file)],
                check=False, cwd=baseline_root, env=env,
                capture_output=True, text=True, timeout=1200)
            if result.returncode:
                raise RuntimeError(
                    "Baseline BRep generation failed: " +
                    result.stdout[-2000:] + result.stderr[-2000:])
            old = cq.Shape.importBrep(str(old_file))
        finally:
            if added:
                subprocess.run(
                    ["git", "worktree", "remove", "--force",
                     str(baseline_root)],
                    cwd=ROOT, check=False, capture_output=True)

    current, details = build_r48_family(
        R48FamilyConfig(model_id, drop, "roofed", relief_mm=relief),
        marked=False)
    if not old.isValid() or len(old.Solids()) != 1:
        raise AssertionError("Baseline is not one valid solid")
    if not current.isValid() or len(current.Solids()) != 1:
        raise AssertionError("Refactored shape is not one valid solid")

    difference = {
        "baseline_volume_mm3": old.Volume(),
        "refactored_volume_mm3": current.Volume(),
        "baseline_only_mm3": old.cut(current).Volume(),
        "refactored_only_mm3": current.cut(old).Volume(),
        "absolute_volume_delta_mm3": abs(old.Volume() - current.Volume()),
    }
    checks = {
        "baseline_is_single_valid_solid": old.isValid() and
            len(old.Solids()) == 1,
        "refactored_is_single_valid_solid": current.isValid() and
            len(current.Solids()) == 1,
        **{key + "_within_tolerance": value <= MAX_DELTA_MM3
           for key, value in difference.items()
           if key in ("baseline_only_mm3", "refactored_only_mm3",
                      "absolute_volume_delta_mm3")},
    }
    report = {
        "model_id": model_id,
        "baseline_sha": BASELINE_SHA,
        "target_commit": os.environ.get("GITHUB_SHA"),
        "marked": False,
        "drop_mm": drop,
        "relief_mm": relief,
        "includes": [
            "entire R48 rail", "curved underside", "all E31 receivers",
            "roof studs", "track passage", "windows",
        ],
        "difference": difference,
        "checks": checks,
        "passed": all(checks.values()),
        "no_physical_print_or_slicer_claim": True,
    }
    (out / (model_id + ".json")).write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(report, indent=2), flush=True)
    if not report["passed"]:
        raise AssertionError(f"{model_id}: full BRep parity failed")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-id", required=True,
                        choices=sorted(SPECIMENS))
    parser.add_argument("--out", type=Path,
                        default=Path("build/issue89-refactor-parity"))
    args = parser.parse_args()
    check(args.model_id, args.out)
