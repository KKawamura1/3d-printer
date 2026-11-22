"""Opt-in larger/more windows on other existing PR75 roofed DUPLO rails.

This is a comparison experiment only. We reuse the *unchanged* PR56
source BReps and PR75 facade/visibility logic, never change the ball passage,
connection mouths, receiver/studs or an earlier printable revision.

SC02-right is deliberately excluded: PR #85 already compares its 5-window
variant against internal channel-clearance changes.
"""
import argparse
from dataclasses import replace
import json
from pathlib import Path

from brickcad.course_architectural_windows import (
    MIN_POST, _verify_visibility, _window_geometry,
    model, plan, source_unmarked, window_centres,
)
from brickcad.course_marking_v2 import (
    MarkSite, SIZE_MM, DEPTH_MM, POLICY_ID, engrave_large,
)
from brickcad.course_artifacts import export_geometry
from brickcad.course_contract import PRODUCTION_CONTRACT, audited_production_course
from brickcad.verify import exact_bounds


# Every new mesh gets its own version; never rewrite PR75's eleven versions.
TRIALS = {
    "E01-V3": "E01-V10",
    "E01L-V1": "E01L-V8",
    "SC02L-V6": "SC02L-V13",
    "SD03-V11": "SD03-V18",
    "SD04-V10": "SD04-V23",
    "T01-V6": "T01-V9",
}
# These compact walls are only ~32mm long. Four slightly narrower windows
# allow >=2.5mm solid pillars; simply adding a fourth 5.5mm hole would not.
COMPACT_WINDOW_WIDTH = 4.5
FLAT_EDGE_POST = 3.0
# A long 82mm outside sharp curve gets 5x8mm, and an R48 curve
# gets 5x10mm. These are experimental, not physically proven.
SHARP_OUTER_WIDTH = 8.0
R48_OUTER_WIDTH = 10.0
EXPANDED_CONVEX_COUNT = 5
EXPANDED_FLAT_COUNT = 4


def evenly_spaced_flat(length, width=COMPACT_WINDOW_WIDTH):
    """Four windows, with >=3mm edge posts and >=2.5mm between windows."""
    gap = (length - 2 * FLAT_EDGE_POST - EXPANDED_FLAT_COUNT * width) / 3
    if gap < MIN_POST:
        raise ValueError(f"Four windows leave only {gap:.2f}mm between pillars")
    return tuple(
        FLAT_EDGE_POST + width / 2 + i * (width + gap)
        for i in range(EXPANDED_FLAT_COUNT)
    )


def expanded_facade(source_id, facade):
    """Return (face, stations) without mutating original PR75 facade policy."""
    if facade.kind == "convex":
        width = (R48_OUTER_WIDTH if source_id.startswith("SC02")
                 else SHARP_OUTER_WIDTH)
        updated = replace(facade, width=width)
        centres = tuple(updated.length * (i + 1) / (EXPANDED_CONVEX_COUNT + 1)
                        for i in range(EXPANDED_CONVEX_COUNT))
    elif facade.kind == "flat" and (
        source_id.startswith(("E01", "T01"))
    ):
        updated = replace(facade, width=COMPACT_WINDOW_WIDTH)
        centres = evenly_spaced_flat(updated.length)
    else:
        # Preserve the 3-window opposite flat wall on SD03/SD04.
        updated, centres = facade, tuple(window_centres(facade))
    return updated, centres


def minimum_solid_post(face, centres):
    """Measure edge/post spans along the facade (not a substitute for BRep checks)."""
    if not centres:
        raise ValueError("A facade must keep at least one viewing window")
    spans = [centres[0] - face.width / 2]
    spans += [b - a - face.width for a, b in zip(centres, centres[1:])]
    spans.append(face.length - centres[-1] - face.width / 2)
    if min(spans) < MIN_POST - 1e-6:
        raise ValueError(f"{face.name}: too little solid wall {spans}")
    return min(spans)


def layout(source_id):
    if source_id not in TRIALS:
        raise ValueError(f"Unsupported source: {source_id}")
    faces = []
    for face in plan(model(source_id)):
        updated, centres = expanded_facade(source_id, face)
        min_post = minimum_solid_post(updated, centres)
        faces.append((updated, centres, min_post))
    baseline = sum(len(window_centres(face)) for face in plan(model(source_id)))
    expanded = sum(len(centres) for _, centres, _ in faces)
    if expanded <= baseline:
        raise ValueError(f"No increase in actual window count: {source_id}")
    return faces, baseline, expanded


def large_mark_site(source_id, source, fit):
    """Keep the entire label on an actual planar exterior face.

    The low Z band sits below the pentagonal viewports; the west face is
    retained for the R48 sloped curve. Actual 3D coverage and collision are
    additionally checked during engraving (not assumed from these numbers).
    """
    if source_id.startswith("E01"):
        # Preserve the old printed-side orientation for right/left variants.
        x = 0. if source["source"]["recipe"]["direction"] == "right" else -17.
        return MarkSite("south", x, -fit.depth / 2, 10.)
    if source_id.startswith("SC02"):
        return MarkSite("west", -fit.width / 2, 16., 12.)
    if source_id.startswith(("SD03", "SD04")):
        return MarkSite("south", -16., -fit.depth / 2, 10.5)
    if source_id == "T01-V6":
        return MarkSite("south", 0., -fit.depth / 2, 10.5)
    raise ValueError("No checked exterior marking site for " + source_id)


def marking_sites(source_id, source, fit):
    """Try verified alternative vertical bands when the primary face breaks.

    The short sharp-turn faces have complicated sloped floors and may not
    support five-millimetre text at every Z. Try nearby Z values while
    always requiring the same BRep window clearance, exterior coverage,
    and valid single-solid result. No candidate bypasses those checks.
    """
    first = large_mark_site(source_id, source, fit)
    if source_id.startswith(("SD03", "SD04")):
        return (first,) + tuple(
            MarkSite(first.face, first.x_mm, first.y_mm, z)
            for z in (11., 11.5, 12., 12.5, 9.7)
        )
    return (first,)


def build_trial(source_id, root):
    new_id = TRIALS[source_id]
    folder = Path(root) / new_id
    folder.mkdir(parents=True, exist_ok=True)
    faces, previous_count, expected_count = layout(source_id)
    source = model(source_id)

    with audited_production_course(new_id) as audit:
        original, fit = source_unmarked(source)
        original_bounds = exact_bounds(original)
        shape = original
        evidence = []
        for face, centres, min_post in faces:
            apertures = []
            for centre in centres:
                cutter, geometry = _window_geometry(face, centre)
                next_shape = shape.cut(cutter).clean()
                removed = shape.Volume() - next_shape.Volume()
                if not next_shape.isValid() or len(next_shape.Solids()) != 1:
                    raise ValueError(f"{new_id}/{face.name}: non-solid cut at {centre}")
                if removed <= 8.:
                    raise ValueError(f"{new_id}/{face.name}: ineffective window at {centre}")
                wall_samples = _verify_visibility(original, next_shape, geometry,
                                                  guard=True)
                apertures.append({
                    "station_mm": round(centre, 4),
                    "width_mm": face.width,
                    "removed_material_mm3": round(removed, 3),
                    "precut_wall_samples": wall_samples,
                    "postcut_blocked_samples": 0,
                })
                shape = next_shape
            evidence.append({
                "facade": face.name,
                "kind": face.kind,
                "length_mm": face.length,
                "minimum_nominal_post_mm": round(min_post, 3),
                "concave_wall_cut": False,
                "windows": apertures,
            })
        # New opt-in shared 5mm label. It must not consume any viewing hole;
        # a BRep material-coverage test also guards against clipped letters.
        failures = []
        for site in marking_sites(source_id, source, fit):
            try:
                marked, marking = engrave_large(
                    shape, original, new_id, site, audit=audit)
            except ValueError as exc:
                failures.append(str(exc))
                print("REJECT MARK SITE", new_id, str(exc), flush=True)
                continue
            shape = marked
            break
        else:
            raise ValueError(
                f"{new_id}: all exterior engraving sites rejected: {failures}")
        marking["attempts"] = len(failures) + 1

    contract = audit.manifest()
    if contract.get("final_marking_labels") != [new_id]:
        raise ValueError(f"{new_id}: unique revision engraving missing")
    bounds = exact_bounds(shape)
    if not shape.isValid() or len(shape.Solids()) != 1:
        raise ValueError(f"{new_id}: final BRep is not one connected solid")
    if any(abs(a - b) > .11 for a, b in zip(bounds, original_bounds)):
        raise ValueError(f"{new_id}: outside dimensions changed unexpectedly")

    stl, mesh = export_geometry(
        shape, folder,
        tolerance=.02 if source_id.startswith("SC02") else .01,
        angular_tolerance=.15 if source_id.startswith("SC02") else .1)
    count = sum(len(f["windows"]) for f in evidence)
    checks = {
        "more_windows_than_pr75": count > previous_count,
        "expected_window_count": count == expected_count,
        "minimum_station_post_mm": all(
            f["minimum_nominal_post_mm"] >= MIN_POST for f in evidence),
        "no_concave_windows": all(not f["concave_wall_cut"] for f in evidence),
        "all_windows_see_ball": all(w["precut_wall_samples"] > 0
                                    for f in evidence for w in f["windows"]),
        "one_valid_solid": shape.isValid() and len(shape.Solids()) == 1,
        "source_external_dimensions": all(
            abs(a - b) <= .11 for a, b in zip(bounds, original_bounds)),
        "engraved_once": contract.get("final_marking_labels") == [new_id],
        "large_marking_policy": (
            marking["policy"] == POLICY_ID
            and marking["size_mm"] == SIZE_MM
            and marking["depth_mm"] == DEPTH_MM
            and marking["window_mark_overlap_mm3"] <= 0.01
            and marking["actual_material_coverage"] >= 0.70
            and marking["removed_outside_text_mm3"] <= 0.08
            and marking["added_outside_original_mm3"] <= 0.08),
        "watertight_stl": mesh["passed"],
        "mesh_volume_matches_cad": (
            abs(mesh["signed_volume_mm3"] - shape.Volume())
            / shape.Volume() < .001),
    }
    report = {
        "part_id": new_id,
        "source_model_id": source_id,
        "passed": all(checks.values()),
        "checks": checks,
        "geometry": {
            "bounds_mm": bounds,
            "volume_mm3": shape.Volume(),
            "previous_pr75_window_count": previous_count,
            "total_windows": count,
            "facades": evidence,
        },
        "production_contract": PRODUCTION_CONTRACT,
        "marking_policy": marking,
        "contract_evidence": {
            **contract, "additional_marking_policy": POLICY_ID,
        },
        "mesh": mesh,
        "physical_fit_validated": False,
        "physical_rolling_validated": False,
        "slicing_validated": False,
        "durability_validated": False,
    }
    (folder / "report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    if not report["passed"]:
        raise ValueError(f"{new_id}: failed CAD checks: {checks}")
    print(f"{new_id}: {previous_count} -> {count} windows CAD PASS", flush=True)
    return report


def export(root, source_ids):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    reports = [build_trial(source_id, root) for source_id in source_ids]
    summary = {
        "passed": all(r["passed"] for r in reports),
        "cases": reports,
        "source_count": len(reports),
        "note": "CAD-only; no slicer, fatigue or physical rolling result",
    }
    (root / "report.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=sorted(TRIALS),
                        help="Build only one source (recommended for iteration)")
    parser.add_argument("--out", type=Path, default=Path("build/course-expanded-windows"))
    args = parser.parse_args()
    export(args.out, [args.model] if args.model else sorted(TRIALS))
