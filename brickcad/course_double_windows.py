"""Independent **two-sided** peep-window prototypes for Issue37 closed courses.

Derived from the same unmarked, audited PR56 production BRep; no parameter
change to the E31-05 receivers, ball path, top studs or nominal dimensions.
Both side walls are opened above the rolling guard, but no roof/floor is
removed. Every version is distinct from the original and the single-window
pilot so physical tests can never be misattributed.
"""
from pathlib import Path
import hashlib
import json

import cadquery as cq

from brickcad.course_artifacts import export_geometry
from brickcad.course_contract import (
    PRODUCTION_CONTRACT, audited_production_course, engrave_course,
)
from brickcad.course_windows import (
    CUTS, VERSIONS, WINDOW_LENGTH, WINDOW_HEIGHT, original_unmarked,
    mark_variant, window_cutter,
)
from brickcad.verify import exact_bounds
from scripts.course_catalog import load_registry

# Seven 2-sided candidates. Four are still physically unprinted in PR56.
# Other three are comparison candidates to the already successful base parts.
DOUBLE_VERSIONS = {
    "E01-V3": "E01-V5",
    "E01L-V1": "E01L-V3",
    "SC02-V12": "SC02-V14",
    "SC02L-V6": "SC02L-V8",
    "SD03-V11": "SD03-V13",
    "SD04-V10": "SD04-V12",
    "S01-V8": "S01-V9",
}

# (x, y, z, x_extent, y_extent, z_extent) mm for the *opposite* wall.
# E01 inner wall is unusually thick (solid body to ±31.9), so it needs a
# long passage. SC02 curved footprint has a thin inside wall instead.
# Opposite y offsets mirror for left/right models; SD has two flat walls.
OTHER_CUTS = {
    "E01-V3": (-16., 17., 25., 10., 37., 9.),
    "E01L-V1":(-16.,-17., 25., 10., 37., 9.),
    "SC02-V12":(-16., 5., 40., 10., 18., 9.),
    "SC02L-V6":(-16.,-5., 40., 10., 18., 9.),
    "SD03-V11":(-16.,11., 40., 10., 18., 9.),
    "SD04-V10":(-16.,-11.,40., 10., 18., 9.),
    "S01-V8": (-2., 16., 40., 7., 14., 8.),
}
# S01 has a 2x2 vertical shaft: the ±Y walls are only ~2.75 mm thick.
FIRST_S01 = (-2., -16., 40., 7., 14., 8.)

# Probe points that must be solid before and open after cutting; each tuple
# is (outer wall point, opposite wall point) in the same horizontal Z slice.
# This checks two real, through-wall openings rather than superficial dents.
WALL_PROBES = {
    "E01-V3": ((-16.,-30.,25.), (-16.,20.,25.)),
    "E01L-V1":((-16., 30.,25.), (-16.,-20.,25.)),
    "SC02-V12":((-16.,-28.,40.), (-16.,2.,40.)),
    "SC02L-V6":((-16., 28.,40.), (-16.,-2.,40.)),
    "SD03-V11":((-16.,-14.5,40.), (-16.,14.5,40.)),
    "SD04-V10":((-16.,14.5,40.),(-16.,-14.5,40.)),
    "S01-V8":((-2.,-14.5,40.), (-2.,14.5,40.)),
}


def _pr56_model(source_id):
    models = {m["id"]: m for m in load_registry()["models"]}
    model = models.get(source_id)
    if (source_id not in DOUBLE_VERSIONS or model is None
            or model["course"]["enclosure"] != "tunnel"
            or model["course"]["windows"] != 0):
        raise ValueError("Not a verified two-sided source: " + str(source_id))
    return model


def _make_cutter(spec):
    x, y, z, w, d, h = spec
    return cq.Workplane("XY").box(w, d, h).val().translate((x, y, z))


def dual_cutters(source_id):
    _pr56_model(source_id)
    if source_id == "S01-V8":
        return (_make_cutter(FIRST_S01), _make_cutter(OTHER_CUTS[source_id]))
    return window_cutter(source_id), _make_cutter(OTHER_CUTS[source_id])


def _unmarked(source_id, model):
    if source_id == "S01-V8":
        # Shared steep-drop kernel, preserving the PR56 four-axis routing and
        # its ball/receiver prechecks. Never call the old PR38 design.py.
        from brickcad.course_configured_special import build_course
        shape, fit, checks = build_course(
            source_id, "drop", model["source"]["recipe"], mark=False)
        if not all(checks.values()):
            raise ValueError("Steep-drop canonical BRep failed geometry checks")
        return shape, fit
    return original_unmarked(model)


def build_dual_window_variant(source_id, out):
    model = _pr56_model(source_id)
    new_id = DOUBLE_VERSIONS[source_id]
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    cut1, cut2 = dual_cutters(source_id)
    with audited_production_course(new_id) as audit:
        original, fit = _unmarked(source_id, model)
        original_bounds = exact_bounds(original)
        # Fail if either side's hole is blocked, blind or misplaced.
        for point in WALL_PROBES[source_id]:
            if not original.isInside(cq.Vector(*point)):
                raise ValueError(f"{new_id} wall probe starts outside original body: {point}")
        shape = original
        removed_sides = []
        for cutter in (cut1, cut2):
            old_volume = shape.Volume()
            shape = shape.cut(cutter).clean()
            delta = old_volume - shape.Volume()
            removed_sides.append(delta)
            if delta <= 15 or not shape.isValid() or len(shape.Solids()) != 1:
                raise ValueError(
                    f"{new_id} double-sided cut fails validity or volume: "
                    f"removed={delta:.2f}")
        for point in WALL_PROBES[source_id]:
            if shape.isInside(cq.Vector(*point)):
                raise ValueError(f"{new_id} has a blind/incomplete window: {point}")
        # Every cutter's Z bounds leave at least the roof, a low guard wall
        # and the underside receiver; enforce this invariant in CAD.
        for cutter in (cut1, cut2):
            bb = cutter.BoundingBox()
            if bb.zmin < 19.0 or bb.zmax > 48.0:
                raise ValueError("A window reaches the floor or roof zone")
        if source_id == "S01-V8":
            shape = engrave_course(
                shape, new_id, x=0., y=-fit.depth/2, z=12.)
        else:
            shape = mark_variant(shape, model, new_id, fit)
    bounds = exact_bounds(shape)
    if any(abs(a-b) > .11 for a,b in zip(bounds, original_bounds)):
        raise ValueError(f"{new_id} changed the original outside dimensions")
    stl, mesh = export_geometry(
        shape, out,
        tolerance=.02 if source_id.startswith("SC02") else .01,
        angular_tolerance=.15 if source_id.startswith("SC02") else .1)
    checks = {
        "valid_single_solid": shape.isValid() and len(shape.Solids()) == 1,
        "both_real_through_wall_windows": all(x > 15 for x in removed_sides),
        "original_external_bounds": all(
            abs(a-b) <= .11 for a,b in zip(bounds, original_bounds)),
        "mesh_watertight": mesh["passed"],
        "mesh_volume_matches_brep": (
            abs(mesh["signed_volume_mm3"] - shape.Volume()) /
            shape.Volume() < .001),
    }
    report = {
        "part_id": new_id,
        "source_model_id": source_id,
        "passed": all(checks.values()),
        "checks": checks,
        "mesh": mesh,
        "geometry": {
            "bounds_mm": bounds,
            "volume_mm3": shape.Volume(),
            "window_count": 2,
            "removed_per_side_mm3": removed_sides,
        },
        "production_contract": PRODUCTION_CONTRACT,
        "contract_evidence": audit.manifest(),
        "physical_fit_validated": False,
        "physical_rolling_validated": False,
        "slicing_validated": False,
    }
    (out / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    if not report["passed"]:
        raise ValueError(f"{new_id} CAD/STL validation failed: {checks}")
    return {
        "id": new_id,
        "source_model_id": source_id,
        "issue37_no": model["issue37_no"],
        "course": {**model["course"], "windows": 2},
        "size_studs": [2, 2] if source_id == "S01-V8" else (
            [4, 4] if source_id.startswith(("E01", "SC02")) else [4, 2]),
        "stl": str(stl),
        "stl_sha256": hashlib.sha256(stl.read_bytes()).hexdigest(),
        "source_reference": model["source"]["reference"],
        "production_contract": PRODUCTION_CONTRACT,
        "contract_evidence": audit.manifest(),
        "report": report,
        "physical_fit_validated": False,
        "physical_rolling_validated": False,
        "slicing_validated": False,
    }
