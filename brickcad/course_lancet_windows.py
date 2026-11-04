"""D01-V3-style *vertical pentagon* window arrays on PR56 tunnel BReps.

Every printed candidate has a NEW ID, so none of the former single-rectangle
experimental artifacts are overwritten. Retains E31-05 fit, ball passage, roof,
and 3 mm final-ID engraving. The five-point aperture (bottom, 2 shoulders,
1 peaked top) follows the proven D01-V3 window vocabulary.

Prefer three narrow windows on EACH visible wall; fallback to two or one if a
source wall is too short, curved away, or fails BRep safety checks. This is a
real series of separately cut slits, not one stretched rectangular hole.
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
    original_unmarked, mark_variant,
)
from brickcad.course_configured_special import build_course as build_special
from brickcad.course_double_windows import DOUBLE_VERSIONS, WALL_PROBES
from brickcad.verify import exact_bounds
from scripts.course_catalog import load_registry

# Supersede (do not silently overwrite) the old rectangle-windowed pilots.
LANCET_DUAL_IDS = {
    "E01-V3": "E01-V6", "E01L-V1": "E01L-V4",
    "SC02-V12": "SC02-V15", "SC02L-V6": "SC02L-V9",
    "SD03-V11": "SD03-V14", "SD04-V10": "SD04-V14",
    "S01-V8": "S01-V10",
}
LANCET_SINGLE_IDS = {"SD04-V10": "SD04-V13"}

# Surface A/B specifies whether the slits are on a south/north Y wall or on
# E01's short exit east X wall. Last two values are probe/target and depth.
# The coordinates originate from the previously successful 2-sided BRep
# prototype and are sampled independently for each candidate opening.
SURFACES = {
    "E01-V3": (("y-", -30., -35., 31.), ("x+", 29., 35., 16.)),
    "E01L-V1":(("y+",  30.,  35., 31.), ("x+", 29., 35., 16.)),
    "SC02-V12":(("y-", -28., -34., 30.), ("y+", 2., 15., 19.)),
    "SC02L-V6":(("y+", 28., 34., 30.), ("y-", -2., -15., 19.)),
    "SD03-V11":(("y-", -14.5, -20., 18.), ("y+", 14.5, 20., 18.)),
    "SD04-V10":(("y+", 14.5, 20., 18.), ("y-", -14.5, -20., 18.)),
    "S01-V8":(("y-", -14.5, -19., 14.), ("y+", 14.5, 19., 14.)),
}
# (z bottom, z shoulders, z top): tall, upper pointed window, like D01.
# roof is at 38.4 / 57.6 mm respectively, not the 62.1 stud top.
LEVELS = {
    "E01": (19.0, 29.5, 33.0),
    "SC02": (33.0, 45.0, 48.5),
    "SD": (32.0, 45.0, 48.5),
    "S01": (32.0, 44.0, 47.0),
}
# Try a row of three, then a symmetric row of two, then one in the middle.
# Separation for the full row is at least 2 mm (6 mm width, 8 mm pitch).
LONGITUDES = {
    "E01": (-24., -16., -8.),
    "SC02": (-24., -16., -8.),
    "SD": (-24., -16., -8.),
    "S01": (-2.,),
}
WIDTH = 6.0
WIDTH_SMALL = 5.0


def _family(source_id):
    if source_id.startswith("E01"): return "E01"
    if source_id.startswith("SC02"): return "SC02"
    if source_id.startswith("SD03") or source_id.startswith("SD04"): return "SD"
    if source_id.startswith("S01"): return "S01"
    raise ValueError("Unsupported window series")


def _model(source_id):
    models = {m["id"]: m for m in load_registry()["models"]}
    if (source_id not in LANCET_DUAL_IDS or source_id not in models
            or models[source_id]["course"]["enclosure"] != "tunnel"):
        raise ValueError("Unknown PR56 window candidate: " + source_id)
    return models[source_id]


def _source_unmarked(source_id, model):
    if source_id == "S01-V8":
        shape, fit, checks = build_special(
            source_id, "drop", model["source"]["recipe"], mark=False)
        if not all(checks.values()):
            raise ValueError("Canonical S01 steep-drop geometry failed")
        return shape, fit
    return original_unmarked(model)


def _pentagon(side, longitudinal, start, depth, family):
    """Five-vertex pointed opening extruded through only one side wall.

    y faces: use the XZ plane (horizontal X axis).
    x exit face: use the YZ plane (horizontal Y axis).
    """
    small = family == "S01"
    width = WIDTH_SMALL if small else WIDTH
    z0, z1, z2 = LEVELS[family]
    half = width / 2.
    points = [
        (longitudinal - half, z0),
        (longitudinal + half, z0),
        (longitudinal + half, z1),
        (longitudinal, z2),
        (longitudinal - half, z1),
    ]
    if side == "y-":
        # XZ workplane extrudes towards +Y when negative distance.
        return (cq.Workplane("XZ", origin=(0,start,0))
                .polyline(points).close().extrude(-depth).val())
    if side == "y+":
        return (cq.Workplane("XZ", origin=(0,start,0))
                .polyline(points).close().extrude(depth).val())
    if side == "x+":
        return (cq.Workplane("YZ", origin=(start,0,0))
                .polyline(points).close().extrude(-depth).val())
    raise ValueError("Unrecognized side")


def _probe(side, coordinate, longitudinal, z):
    return cq.Vector(coordinate, longitudinal, z) if side == "x+" else (
        cq.Vector(longitudinal, coordinate, z))


def _choices(family, prefer):
    bases = LONGITUDES[family]
    if len(bases) == 1:
        return ((bases[0],),)
    mid = bases[1]
    return (bases, (bases[0], bases[-1]), (mid,))


def _make_face(shape, original, source_id, surf, family, *, prefer=3):
    side, probe_coord, origin, depth = surf
    bottom, shoulder, peak = LEVELS[family]
    for seq in _choices(family, prefer):
        if len(seq) > prefer:
            continue
        candidate = shape
        amounts = []
        valid = True
        probes = []
        for x in seq:
            probe = _probe(side, probe_coord, x, (bottom + shoulder) / 2.)
            if not original.isInside(probe):
                valid = False
                break
            cutter = _pentagon(side, x, origin, depth, family)
            removed_before = candidate.Volume()
            candidate = candidate.cut(cutter).clean()
            delta = removed_before - candidate.Volume()
            if (delta < 6.0 or not candidate.isValid()
                    or len(candidate.Solids()) != 1 or candidate.isInside(probe)):
                valid = False
                break
            # A five-sided slit must not touch the near-bottom receiver,
            # top studs or continuous roof.
            bb = cutter.BoundingBox()
            if bb.zmin < 18.5 or bb.zmax > 49.0:
                valid = False
                break
            amounts.append(round(delta, 2))
            probes.append(tuple(probe.toTuple()))
        if valid:
            return candidate, {
                "face": side, "count": len(seq), "centres_mm": list(seq),
                "width_mm": WIDTH_SMALL if family == "S01" else WIDTH,
                "z_bottom_mm": bottom, "z_shoulder_mm": shoulder,
                "z_peak_mm": peak, "removed_mm3": amounts,
                "open_probes_mm": probes,
            }
    raise ValueError(
        f"No valid D01-style pointed slit on {source_id} surface {side}")


def build_lancet_variant(source_id, output, *, sides=2):
    """Produce a CAD verified two-face or one-face series, with fallback 3→2→1."""
    if sides not in (1,2):
        raise ValueError("Only one or two viewing faces")
    model = _model(source_id)
    part_id = (LANCET_DUAL_IDS if sides == 2 else LANCET_SINGLE_IDS)[source_id]
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    with audited_production_course(part_id) as audit:
        original, fit = _source_unmarked(source_id, model)
        shape = original
        initial_bounds = exact_bounds(original)
        family = _family(source_id)
        face_records = []
        for face in SURFACES[source_id][:sides]:
            shape, face_record = _make_face(
                shape, original, source_id, face, family,
                prefer=1 if source_id == "S01-V8" else 3)
            face_records.append(face_record)
        if source_id == "S01-V8":
            shape = engrave_course(
                shape, part_id, x=0., y=-fit.depth / 2, z=12.)
        else:
            shape = mark_variant(shape, model, part_id, fit)
    bounds = exact_bounds(shape)
    if (not shape.isValid() or len(shape.Solids()) != 1
            or any(abs(a-b) > .11 for a,b in zip(bounds,initial_bounds))):
        raise ValueError(f"{part_id}: bounds / connected BRep mismatch")
    stl,mesh = export_geometry(
        shape,out,tolerance=.02 if family=="SC02" else .01,
        angular_tolerance=.15 if family=="SC02" else .1)
    checks = {
        "valid_connected": shape.isValid() and len(shape.Solids())==1,
        "outer_dimensions_unchanged": all(
            abs(a-b) <= .11 for a,b in zip(bounds,initial_bounds)),
        "face_count": len(face_records) == sides,
        "all_faces_have_real_openings": all(x["count"]>=1 for x in face_records),
        "water_tight": mesh["passed"],
        "volume_correspondence": abs(
            mesh["signed_volume_mm3"]-shape.Volume())/shape.Volume() < .001,
    }
    report = {
        "part_id":part_id,"source_model_id":source_id,
        "passed":all(checks.values()),"checks":checks,"mesh":mesh,
        "geometry":{"bounds_mm":bounds,"volume_mm3":shape.Volume(),
            "faces":face_records,
            "total_window_count":sum(x["count"] for x in face_records),
            "window_style":"D01-V3 pointed tall pentagonal aperture"},
        "production_contract":PRODUCTION_CONTRACT,
        "contract_evidence":audit.manifest(),
        "physical_fit_validated":False,
        "physical_rolling_validated":False,
        "slicing_validated":False,
    }
    (out/"report.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    if not report["passed"]:
        raise ValueError(f"Invalid {part_id} mesh: {checks}")
    return {
        "id":part_id,"source_model_id":source_id,
        "issue37_no":model["issue37_no"],
        "course":{**model["course"],"windows":sides},
        "stl":str(stl),"stl_sha256":hashlib.sha256(stl.read_bytes()).hexdigest(),
        "source_reference":model["source"]["reference"],
        "production_contract":PRODUCTION_CONTRACT,
        "contract_evidence":audit.manifest(),
        "report":report,
        "physical_fit_validated":False,"physical_rolling_validated":False,
        "slicing_validated":False,
    }
