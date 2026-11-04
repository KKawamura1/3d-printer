"""Issue #37 CAD catalogue: dispatch 23 categories to 20 proven CAD sources."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
# Direct script execution adds scripts/, not repository root, to sys.path.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from brickcad.course_contract import (
    validate_course_axes, kernel_for, PRODUCTION_CONTRACT, audited_production_course,
)
REGISTRY = ROOT / "experiments/course_catalog/registry.json"
CATEGORIES = list(range(1, 22)) + [24, 25]


def validate_geometry_recipe(kernel, course, recipe):
    """The geometry recipe can refine a course but cannot change its four axes."""
    slope, curve, enclosure = course["slope"], course["curve"], course["enclosure"]
    if not isinstance(recipe, dict):
        raise ValueError("Missing geometry recipe")
    if kernel == "straight_rail":
        if recipe != {"channel": "standard", "length_mm": 63.8}:
            raise ValueError("Straight open rail must use the standard channel, not a fit profile")
    elif kernel == "straight_tunnel":
        if recipe != {"roof": "transition", "transition_mm": 4, "ceiling_mm": 34.8}:
            raise ValueError("Unsupported straight tunnel roof")
    elif kernel == "downhill_windowed":
        if recipe != {"windows": [-16, 0, 16], "window_width_mm": 8,
                      "drop_mm": 19.2}:
            raise ValueError("Unsupported windowed downhill")
    elif kernel in ("horizontal_r48_tunnel", "sloped_r48_tunnel"):
        expected = ({"direction", "radius_mm", "ceiling_mm", "lip_mm", "transition_mm"}
                    if kernel == "horizontal_r48_tunnel" else
                    {"direction", "drop_mm", "roof_top_mm", "lip_mm", "transition_mm"})
        if set(recipe) != expected or recipe.get("direction") != curve.split("_")[-1]:
            raise ValueError("R48 recipe does not match course direction")
        if kernel == "horizontal_r48_tunnel":
            if any(recipe[k] != v for k, v in {
                "radius_mm": 48, "ceiling_mm": 34.8, "lip_mm": 1,
                "transition_mm": 4}.items()):
                raise ValueError("Unsupported horizontal R48 geometry")
        elif any(recipe[k] != v for k, v in {
                "drop_mm": 19.2, "roof_top_mm": 57.6, "lip_mm": 1,
                "transition_mm": 4}.items()):
            raise ValueError("Unsupported sloped R48 geometry")
    elif kernel == "sharp_r16":
        if recipe != {"enclosure": enclosure}:
            raise ValueError("R16 enclosure mismatch")
    elif kernel == "drop":
        if set(recipe) != {"exit", "mirror"} or (
            recipe["exit"] != ("east" if curve == "straight" else "south")
            or recipe["mirror"] is not (curve == "sharp_left")
        ):
            raise ValueError("Steep-drop course recipe has wrong direction")
    elif kernel == "loft":
        if set(recipe) not in (
            {"route", "drop_mm", "tunnel", "mirror", "mark_face", "label_z_mm"},
            {"route", "drop_mm", "tunnel", "mirror", "mark_face", "label_z_mm", "label_x_mm"},
        ):
            raise ValueError("Malformed loft recipe")
        path = "straight" if curve == "straight" else curve.split("_")[0]
        mir = ((curve == "gentle_right" and slope == "gentle")
               or curve == "sharp_left")
        if (recipe["route"] != path
            or recipe["drop_mm"] != (0 if slope == "horizontal" else 19.2)
            or type(recipe["tunnel"]) is not bool
            or recipe["tunnel"] != (enclosure == "tunnel")
            or type(recipe["mirror"]) is not bool
            or recipe["mirror"] != mir
            or recipe["mark_face"] != ("west" if path == "gentle" else "south")
            or not isinstance(recipe["label_z_mm"], (int, float))
            or not 0 < recipe["label_z_mm"] <= 15):
            raise ValueError("Loft recipe conflicts with canonical axes")
    else:
        raise ValueError("Unknown geometric kernel")


def load_registry(path=REGISTRY):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    items = data.get("models")
    if data.get("schema") != 1 or data.get("issue37_categories") != CATEGORIES:
        raise ValueError("Incorrect Issue #37 catalogue schema")
    if not isinstance(items, list) or len(items) != 20:
        raise ValueError("Expected 20 unique CAD sources")
    ids, categories = set(), []
    for m in items:
        ident, numbers, source = m["id"], m["issue37_no"], m["source"]
        if ident in ids or not re.fullmatch(r"[A-Z0-9-]+", ident):
            raise ValueError("Duplicate or invalid model ID")
        ids.add(ident)
        if (not isinstance(numbers, list) or not numbers
            or any(type(n) is not int or n not in CATEGORIES for n in numbers)):
            raise ValueError("Invalid Issue #37 classification")
        categories += numbers
        if m["reversible_unverified"] is not (len(numbers) == 2):
            raise ValueError("Reversible CAD must be explicitly unverified")
        kernel = validate_course_axes(m["course"], numbers)
        if source.get("kind") != "configured" or "family" in source or "fit_profile" in source:
            raise ValueError("Production may only use axes-configured CAD, not a legacy family")
        validate_geometry_recipe(kernel, m["course"], source.get("recipe"))
        reference = source.get("reference", {})
        if (type(reference.get("pr")) is not int or
            not re.fullmatch(r"[0-9a-f]{40}", reference.get("sha", ""))):
            raise ValueError("Geometry parity must pin original CAD provenance")
        if ident == "R01-V1":
            if (numbers != [1] or reference.get("pr") != 67
                or reference.get("cad_version") != "R01-V1"
                or reference.get("target") != "parts/straight_rail_e31"):
                raise ValueError("Straight open course must use R01-V1 E31 original")
    if sorted(categories) != CATEGORIES or sum(len(m["issue37_no"]) == 2 for m in items) != 3:
        raise ValueError("Catalogue does not cover exactly 23 categories")
    if "R01-V1" not in ids or "RAIL-LEGACY" in ids:
        raise ValueError("Production catalogue must contain the current straight rail")
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


def stl_info(path):
    raw = path.read_bytes()
    if len(raw) < 134 or (len(raw) - 84) % 50:
        raise ValueError("Invalid binary STL: " + str(path))
    triangles = struct.unpack_from("<I", raw, 80)[0]
    if triangles < 1 or len(raw) != 84 + triangles * 50:
        raise ValueError("Invalid STL triangle count: " + str(path))
    return {"bytes": len(raw), "triangles": triangles,
            "sha256": hashlib.sha256(raw).hexdigest()}


def export_one(model, output, *, audit):
    """Accept only validated CAD outputs from the current production contract."""
    ident = model["id"]
    folder = ROOT / "build/course-catalog-configured" / ident
    stl, report = folder / "brick.stl", folder / "report.json"
    if not stl.is_file() or not report.is_file():
        raise FileNotFoundError("CAD output missing: " + str(folder))
    result = json.loads(report.read_text())
    if (result.get("part_id") != ident or result.get("passed") is not True
        or result.get("mesh", {}).get("passed") is not True):
        raise ValueError("CAD checks failed or wrong version: " + ident)
    meta = stl_info(stl)
    dst = output / "models" / ident
    dst.mkdir(parents=True, exist_ok=True)
    shutil.copy2(stl, dst / "brick.stl")
    shutil.copy2(report, dst / "report.json")
    provenance = folder / "course-manifest.json"
    if provenance.is_file():
        shutil.copy2(provenance, dst / "course-manifest.json")
    evidence = audit.manifest()
    return {**model, "stl": "models/" + ident + "/brick.stl",
            "contract_evidence": evidence,
            "stl_info": meta, "geometry_verified": True,
            "production_contract": PRODUCTION_CONTRACT,
            "legacy_unverified_e31": False,
            "physical_fit_validated": False, "physical_rolling_validated": False,
            "slicing_validated": False}


def build_one(model, destination):
    """Dispatch only geometric algorithms, never fit/marking variants."""
    ident, recipe = model["id"], model["source"]["recipe"]
    kernel = kernel_for(model["course"])
    if kernel == "straight_rail":
        from brickcad.course_straight_rail import export_course
        export_course(ident, recipe, destination)
    elif kernel == "loft":
        from brickcad.course_loft_family import export_course
        export_course(ident, recipe, destination)
    elif kernel == "horizontal_r48_tunnel":
        from brickcad.course_r48_tunnel import export_course
        export_course(ident, recipe, destination)
    elif kernel == "sloped_r48_tunnel":
        from brickcad.course_r48_sloped_tunnel import export_course
        export_course(ident, recipe, destination)
    elif kernel == "straight_tunnel":
        from brickcad.course_straight_tunnel import export_course
        export_course(ident, recipe, destination)
    elif kernel == "downhill_windowed":
        from brickcad.course_prod_downhill import export_course
        name, version = ident.split("-")
        windows = [{"side": "south", "x_mm": x, "width_mm": recipe["window_width_mm"]}
                   for x in recipe["windows"]]
        export_course({"id": name, "version": version,
                       "enclosure": {"kind": "tunnel", "windows": windows}}, destination)
    else:
        from brickcad.course_configured_special import export_course
        export_course(ident, kernel, recipe, destination)


def build(models, output, strict_head=False):
    """All selected parts are constructed locally from shared production code.

    --strict-head is retained for CLI compatibility; historical references are
    used only by the independent BRep parity CI, never during production builds.
    """
    output.mkdir(parents=True, exist_ok=True)
    results = []
    for model in models:
        destination = ROOT / "build/course-catalog-configured" / model["id"]
        with audited_production_course(model["id"]) as audit:
            build_one(model, destination)
        results.append(export_one(model, output, audit=audit))
    categories = sorted(n for model in results for n in model["issue37_no"])
    manifest = {
        "generated_meshes": len(results), "covered_categories": categories,
        "complete_23_categories": categories == CATEGORIES,
        "production_contract": PRODUCTION_CONTRACT,
        "reverse_direction_unverified": [m["id"] for m in results
                                         if m["reversible_unverified"]],
        "legacy_unverified_e31": [],
        "models": results, "slicing_validated": False,
        "physical_fit_validated": False,
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
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
