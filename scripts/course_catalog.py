"""Issue #37 CAD catalogue: dispatch 23 categories to 20 proven CAD sources."""
import argparse
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
# Direct script execution adds scripts/, not repository root, to sys.path.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
REGISTRY = ROOT / "experiments/course_catalog/registry.json"
CATEGORIES = list(range(1, 22)) + [24, 25]


def load_registry(path=REGISTRY):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    items = data.get("models")
    if data.get("schema") != 1 or data.get("issue37_categories") != CATEGORIES:
        raise ValueError("Incorrect Issue #37 catalogue schema")
    if not isinstance(items, list) or len(items) != 20:
        raise ValueError("Expected 20 unique CAD sources")
    ids, categories = set(), []
    for m in items:
        model_id, numbers, source = m["id"], m["issue37_no"], m["source"]
        if model_id in ids or not re.fullmatch(r"[A-Z0-9-]+", model_id):
            raise ValueError("Duplicate or invalid model ID")
        ids.add(model_id)
        if (not isinstance(numbers, list) or not numbers
                or any(type(n) is not int or n not in CATEGORIES for n in numbers)):
            raise ValueError("Invalid category number")
        categories += numbers
        if m["reversible_unverified"] is not (len(numbers) > 1):
            raise ValueError("Reversible CAD must be marked unverified")
        kind = source.get("kind")
        if kind not in ("local", "pr", "legacy", "configured"):
            raise ValueError("Missing CAD source kind")
        if kind == "configured":
            if source.get("family") not in ("loft","sharp_r16","drop","horizontal_r48_tunnel","sloped_r48_tunnel") or not isinstance(source.get("recipe"), dict):
                raise ValueError("Configured model needs a real geometry recipe")
            # Cheap catalogue checks run without CadQuery installed.
            recipe = source["recipe"]
            if source["family"] == "sloped_r48_tunnel":
                t=recipe
                if (set(t)!={"direction","drop_mm","roof_top_mm","lip_mm","transition_mm"} or
                        t["direction"] not in ("right","left") or
                        t["drop_mm"]!=19.2 or t["roof_top_mm"]!=57.6 or
                        t["lip_mm"]!=1 or t["transition_mm"]!=4):
                    raise ValueError("Unsupported sloped R48 tunnel recipe")
            if source["family"] == "horizontal_r48_tunnel":
                t=recipe
                if (set(t)!={"direction","radius_mm","ceiling_mm","lip_mm","transition_mm"} or
                        t["direction"] not in ("right","left") or t["radius_mm"]!=48 or
                        t["ceiling_mm"]!=34.8 or t["lip_mm"]!=1 or t["transition_mm"]!=4):
                    raise ValueError("Unsupported R48 roofed course recipe")
            if source["family"] == "sharp_r16":
                if recipe not in ({"enclosure":"open"},{"enclosure":"tunnel"}):
                    raise ValueError("Unsupported R16 recipe")
            if source["family"] == "drop":
                if (set(recipe)!={"exit","mirror"} or
                        recipe["exit"] not in ("east","south") or
                        type(recipe["mirror"]) is not bool or
                        (recipe["exit"]=="east" and recipe["mirror"])):
                    raise ValueError("Unsupported steep-drop recipe")
            required = {"route","drop_mm","tunnel","mirror","mark_face",
                        "label_z_mm"}
            if source["family"]=="loft" and (not required.issubset(recipe) or set(recipe) - (required | {"label_x_mm"})):
                raise ValueError("Malformed loft recipe")
            if (source["family"]=="loft" and (recipe["route"] not in ("straight","sharp","gentle")
                    or recipe["drop_mm"] not in (0,19.2)
                    or type(recipe["tunnel"]) is not bool
                    or type(recipe["mirror"]) is not bool
                    or recipe["mark_face"] not in ("south","west"))):
                raise ValueError("Unsupported loft recipe")
            ref = source.get("reference", {})
            if (type(ref.get("pr")) is not int or
                    not re.fullmatch(r"[0-9a-f]{40}", ref.get("sha", ""))):
                raise ValueError("Reference CAD provenance must be pinned")
        if kind == "pr":
            if (type(source.get("pr")) is not int or source["pr"] < 1
                    or not re.fullmatch(r"[0-9a-f]{40}", source.get("sha", ""))):
                raise ValueError("Source must pin PR number and full commit SHA")
        if kind not in ("legacy", "configured"):
            if (not re.fullmatch(r"(parts|experiments)/[a-z0-9_]+", source.get("target", ""))
                    or not re.fullmatch(r"[A-Z0-9-]+", source.get("cad_version", ""))):
                raise ValueError("Missing safe CAD target or version")
        if kind == "legacy" and (model_id != "RAIL-LEGACY" or source.get("module") != "parts.straight_rail.design"):
            raise ValueError("Only horizontal rail trial may use legacy exporter")
    if sorted(categories) != CATEGORIES or sum(len(m["issue37_no"]) == 2 for m in items) != 3:
        raise ValueError("Catalogue does not cover exactly 23 categories")
    return data


def select(registry, expression):
    if expression == "all":
        return registry["models"]
    terms = [s.strip() for s in expression.split(",") if s.strip()]
    if not terms:
        raise ValueError("No selection")
    ids = {m["id"] for m in registry["models"]}
    selected = set()
    for term in terms:
        if term in ids:
            selected.add(term)
        elif term.isdecimal() and int(term) in CATEGORIES:
            selected.update(m["id"] for m in registry["models"]
                            if int(term) in m["issue37_no"])
        else:
            raise ValueError("Unknown catalogue model or category: " + term)
    return [m for m in registry["models"] if m["id"] in selected]


def run(*argv, cwd=ROOT, capture=False):
    return subprocess.run(argv, cwd=cwd, text=True, check=True, capture_output=capture)


def stl_info(path):
    raw = path.read_bytes()
    if len(raw) < 134 or (len(raw) - 84) % 50:
        raise ValueError("Invalid binary STL: " + str(path))
    triangles = struct.unpack_from("<I", raw, 80)[0]
    if triangles < 1 or len(raw) != 84 + triangles * 50:
        raise ValueError("Invalid STL triangle count: " + str(path))
    return {"bytes": len(raw), "triangles": triangles,
            "sha256": hashlib.sha256(raw).hexdigest()}


def export_one(model, source_root, output):
    src = model["source"]
    if src["kind"] == "configured":
        folder = source_root / "build/course-catalog-configured" / model["id"]
    elif src["kind"] == "legacy":
        folder = source_root / "build/course-catalog-legacy"
    else:
        folder = source_root / "build/cad-delivery" / src["target"] / src["cad_version"]
    stl, report = folder / "brick.stl", folder / "report.json"
    if not stl.is_file() or not report.is_file():
        raise FileNotFoundError("CAD output missing: " + str(folder))
    result = json.loads(report.read_text())
    if result.get("passed") is not True or result.get("mesh", {}).get("passed") is not True:
        raise ValueError("Unverified CAD output: " + model["id"])
    if src["kind"] == "pr" and result.get("part_id") not in (None, model["id"]):
        raise ValueError("Unexpected CAD report ID: " + model["id"])
    meta = stl_info(stl)
    dst = output / "models" / model["id"]
    dst.mkdir(parents=True, exist_ok=True)
    shutil.copy2(stl, dst / "brick.stl")
    shutil.copy2(report, dst / "report.json")
    provenance = folder / "course-manifest.json"
    if provenance.is_file():
        shutil.copy2(provenance, dst / "course-manifest.json")
    return {**model, "stl": "models/" + model["id"] + "/brick.stl",
            "stl_info": meta, "geometry_verified": True,
            "legacy_unverified_e31": src["kind"] == "legacy",
            "physical_fit_validated": False, "physical_rolling_validated": False,
            "slicing_validated": False}


def build(models, output, strict_head=False):
    buckets = defaultdict(list)
    for m in models:
        source = m["source"]
        buckets[(source["kind"], source.get("sha", "self"))].append(m)
    output.mkdir(parents=True, exist_ok=True)
    results = []
    for (kind, sha), chosen in buckets.items():
        source_root, temp, worktree = ROOT, None, None
        if kind == "pr":
            if strict_head:
                for model in chosen:
                    src = model["source"]
                    current = run("gh", "api",
                                  "repos/" + os.environ["GITHUB_REPOSITORY"] +
                                  "/pulls/" + str(src["pr"]), "--jq", ".head.sha",
                                  capture=True).stdout.strip()
                    if current != src["sha"]:
                        raise ValueError("PR #" + str(src["pr"]) +
                                         " advanced; repin and revalidate " + model["id"])
            temp = Path(tempfile.mkdtemp(prefix="issue37-cad-"))
            worktree = temp / "source"
            run("git", "fetch", "origin", sha)
            run("git", "worktree", "add", "--detach", str(worktree), sha)
            source_root = worktree
        try:
            if kind == "configured":
                for model in chosen:
                    source = model["source"]
                    dest = ROOT / "build/course-catalog-configured" / model["id"]
                    if source["family"] == "loft":
                        from brickcad.course_loft_family import export_course
                        export_course(model["id"],source["recipe"],dest)
                    elif source["family"] == "horizontal_r48_tunnel":
                        from brickcad.course_r48_tunnel import export_course
                        export_course(model["id"],source["recipe"],dest)
                    elif source["family"] == "sloped_r48_tunnel":
                        from brickcad.course_r48_sloped_tunnel import export_course
                        export_course(model["id"],source["recipe"],dest)
                    else:
                        from brickcad.course_configured_special import export_course
                        export_course(model["id"],source["family"],source["recipe"],dest)
            elif kind == "legacy":
                run(sys.executable, "-m", "parts.straight_rail.design",
                    "--kind", "rail", "--out",
                    str(ROOT / "build/course-catalog-legacy"))
            else:
                targets = sorted({m["source"]["target"] for m in chosen})
                for model in chosen:
                    src = model["source"]
                    config = source_root / src["target"] / "cad-build.json"
                    if not config.is_file():
                        raise FileNotFoundError("Missing source CAD config: " + str(config))
                    revision = json.loads(config.read_text())["version"]
                    if revision != src["cad_version"]:
                        raise ValueError("Source version changed: " + model["id"])
                run(sys.executable, "scripts/cad_versions.py", "--mode", "build",
                    "--targets", ",".join(targets), cwd=source_root)
            results.extend(export_one(m, source_root, output) for m in chosen)
        finally:
            if worktree is not None and worktree.exists():
                run("git", "worktree", "remove", "--force", str(worktree))
            if temp is not None:
                shutil.rmtree(temp, ignore_errors=True)
    categories = sorted(n for m in results for n in m["issue37_no"])
    manifest = {"generated_meshes": len(results), "covered_categories": categories,
                "complete_23_categories": categories == CATEGORIES,
                "reverse_direction_unverified": [m["id"] for m in results
                                                  if m["reversible_unverified"]],
                "legacy_unverified_e31": [m["id"] for m in results
                                          if m["legacy_unverified_e31"]],
                "models": results, "slicing_validated": False,
                "physical_fit_validated": False}
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("ISSUE37 GENERATED:", len(results), "meshes covering",
          len(categories), "categories", flush=True)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("validate", "plan", "build"), default="plan")
    parser.add_argument("--targets", default="all")
    parser.add_argument("--strict-head", action="store_true")
    parser.add_argument("--out", type=Path, default=ROOT / "build/course-catalog")
    opts = parser.parse_args()
    registry = load_registry()
    chosen = select(registry, opts.targets)
    if opts.mode == "validate":
        print("COURSE CATALOG VALID: 23 categories / 20 meshes")
    elif opts.mode == "plan":
        for m in chosen:
            print(m["id"], m["issue37_no"], m["source"])
    else:
        build(chosen, opts.out, opts.strict_head)


if __name__ == "__main__":
    main()
