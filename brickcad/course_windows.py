"""Experimental side peek windows for large PR56 tunnel geometries.

These are NEW versioned candidates: never overwrite the 20 physically assessed
production-catalogue meshes. Remove material only from a side wall, below the
roof and above the ball-course floor. The original 4-axis catalogue builds the
unmarked, E31-05-fitted BRep; window cutting is the sole geometry variation.
"""
from pathlib import Path
import hashlib
import json

import cadquery as cq

from brickcad.course_artifacts import export_geometry
from brickcad.course_contract import (
    PRODUCTION_CONTRACT, audited_production_course,
    engrave_course, engrave_course_west,
)
from brickcad.verify import exact_bounds
from scripts.course_catalog import load_registry

# Full ID bump prevents accidentally giving an untested windowed mesh the ID
# (and physical approval) of an older successful geometry.
VERSIONS = {
    "E01-V3": "E01-V4",
    "E01L-V1": "E01L-V2",
    "SC02-V12": "SC02-V13",
    "SC02L-V6": "SC02L-V7",
    "SD03-V11": "SD03-V12",
    "SD04-V10": "SD04-V11",
}

# Empirical pilot positions, in mm. Check both the open window and the roof/
# guard after printing. 4x4 curves put the opening on the exterior south/north
# wall near the inlet, while 2x4 sharp downhills use a short straight section.
# Center z is well above the rolling floor and below the continuous roof.
CUTS = {
    "E01-V3": ( -16., -19., 25.0, 30.),
    "E01L-V1": (-16.,  19., 25.0, 30.),
    "SC02-V12":(-16., -19., 40.0, 30.),
    "SC02L-V6":(-16.,  19., 40.0, 30.),
    "SD03-V11":(-16., -11., 40.0, 18.),
    "SD04-V10":(-16.,  11., 40.0, 18.),
}
WINDOW_LENGTH = 10.0
WINDOW_HEIGHT = 9.0


def window_cutter(source_id):
    x, y, z, depth = CUTS[source_id]
    # Aperture pierces ONE external wall and ends in the existing channel.
    # It does not extend across the whole part or touch roof/studs/receiver.
    return (cq.Workplane("XY")
            .box(WINDOW_LENGTH, depth, WINDOW_HEIGHT)
            .val().translate((x, y, z)))


def source_model(source_id):
    models = {m["id"]: m for m in load_registry()["models"]}
    if source_id not in VERSIONS or source_id not in models:
        raise ValueError("Not an approved large tunnel source: " + str(source_id))
    model = models[source_id]
    if model["course"]["enclosure"] != "tunnel":
        raise ValueError("Peek windows require a roofed tunnel")
    return model


def original_unmarked(model):
    source_id = model["id"]
    recipe = model["source"]["recipe"]
    if source_id.startswith(("E01-", "E01L-")):
        from brickcad.course_r48_tunnel import build_course
        return build_course(source_id, recipe, marked=False)
    if source_id.startswith(("SC02-", "SC02L-")):
        from brickcad.course_r48_sloped_tunnel import build_course
        return build_course(source_id, recipe, marked=False)
    if source_id.startswith(("SD03-", "SD04-")):
        from brickcad.course_loft_family import build_course
        return build_course(recipe, label=None)
    raise ValueError("Source is not a 2x4+ existing covered tunnel")


def mark_variant(shape, model, new_id, fit):
    recipe = model["source"]["recipe"]
    source_id = model["id"]
    if source_id.startswith(("E01-", "E01L-")):
        x = 0 if recipe["direction"] == "right" else -17
        return engrave_course(shape, new_id, x=x, y=-fit.depth / 2, z=12)
    if source_id.startswith(("SC02-", "SC02L-")):
        return engrave_course_west(
            shape, new_id, x=-fit.width / 2,
            y=-16 if recipe["direction"] == "right" else 16, z=12)
    return engrave_course(
        shape, new_id, x=recipe["label_x_mm"],
        y=-fit.depth / 2, z=recipe["label_z_mm"])


def build_window_variant(source_id, out):
    """Return a verified source manifest entry and its generated STL path."""
    model = source_model(source_id)
    new_id = VERSIONS[source_id]
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    with audited_production_course(new_id) as audit:
        original, fit = original_unmarked(model)
        cutter = window_cutter(source_id)
        shape = original.cut(cutter).clean()
        removed = original.Volume() - shape.Volume()
        if not (30. < removed < 4000.):
            raise ValueError(f"{new_id} side window did not intersect just the wall: {removed:.3f}")
        if not shape.isValid() or len(shape.Solids()) != 1:
            raise ValueError(f"{new_id} has broken the tunnel into disconnected pieces")
        shape = mark_variant(shape, model, new_id, fit)
    bounds = exact_bounds(shape)
    target = (fit.width, fit.depth, fit.height + fit.stud_height)
    if any(abs(float(got) - float(want)) > .11 for got, want in zip(bounds, target)):
        raise ValueError(f"{new_id} changed external brick dimensions: {bounds} vs {target}")
    # The centerline's round inlet/outlet, E31 underside and any original
    # support are unchanged outside the tightly bounded wall aperture.
    stl, mesh = export_geometry(
        shape, out, tolerance=.02 if source_id.startswith("SC02") else .01,
        angular_tolerance=.15 if source_id.startswith("SC02") else .1)
    checks = {
        "valid_single_solid": shape.isValid() and len(shape.Solids()) == 1,
        "side_aperture_removed_material": 30. < removed < 4000.,
        "original_bounding_box": all(
            abs(float(got) - float(want)) <= .11 for got, want in zip(bounds, target)),
        "mesh": mesh["passed"],
        "mesh_volume": (abs(mesh["signed_volume_mm3"] - shape.Volume()) /
                        shape.Volume() < .001),
    }
    report = {
        "part_id": new_id,
        "source_model_id": source_id,
        "passed": all(checks.values()),
        "checks": checks,
        "mesh": mesh,
        "geometry": {"bounds_mm": bounds, "volume_mm3": shape.Volume(),
                     "window_volume_removed_mm3": removed,
                     "window_width_mm": WINDOW_LENGTH,
                     "window_height_mm": WINDOW_HEIGHT},
        "production_contract": PRODUCTION_CONTRACT,
        "contract_evidence": audit.manifest(),
        "physical_fit_validated": False,
        "physical_rolling_validated": False,
        "slicing_validated": False,
    }
    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    if not report["passed"]:
        raise ValueError("Windowed CAD failed: " + repr(checks))
    return {
        "id": new_id, "source_model_id": source_id,
        "issue37_no": model["issue37_no"],
        "course": {**model["course"], "windows": 1},
        "size_studs": [4, 4] if source_id.startswith(("E01", "SC02")) else [4, 2],
        "stl": str(stl),
        "stl_sha256": hashlib.sha256(stl.read_bytes()).hexdigest(),
        "source_reference": model["source"]["reference"],
        "source_recipe": model["source"]["recipe"],
        "production_contract": PRODUCTION_CONTRACT,
        "contract_evidence": audit.manifest(),
        "report": report,
        "physical_fit_validated": False,
        "physical_rolling_validated": False,
        "slicing_validated": False,
    }
