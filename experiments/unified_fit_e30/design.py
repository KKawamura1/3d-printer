"""E30-V1: one-print E28+E29 hybrid fitting experiment for DUPLO.

Consolidates nine 2x2 specimens so both directions of printed/printed mating
can be tested within one A1 mini print. Experimental adult-only coupons.
"""
from dataclasses import asdict
from pathlib import Path
import hashlib
import json

import cadquery as cq

from brickcad.marking import engrave
from brickcad.model import build as build_brick
from brickcad.verify import exact_bounds
from experiments.full_height_fit.design import export_stl
from experiments.receiver_contact_e28.design import (
    VERSION as E28_VERSION, parameters as e28_parameters,
)
from experiments.dual_fit_e29.design import (
    VERSION as E29_VERSION, parameters as e29_parameters,
    add_waist, add_rounded_bead, add_receiver_slots,
)

VERSION = "E30-V1"
PROFILE = "duplo-e27-play-v1"
SOURCE_VERSIONS = {"E28": "E28-V1", "E29": "E29-V3"}
# A1 mini 180 x 180 bed. Distinct 31.8 mm bodies, 45 mm center spacing.
# Deliberately interleave baseline and hybrid positions for comparison.
SPECIMENS = (
    dict(id="E30-01", source="E28-01/E29-01", kind="baseline_A", xy=[45, 45]),
    dict(id="E30-02", source="E28-02/E29-01", kind="baseline_B", xy=[90, 45]),
    dict(id="E30-03", source="E28-03", kind="wall_relief", xy=[135, 45]),
    dict(id="E30-04", source="E28-04", kind="tube_relief", xy=[45, 90]),
    dict(id="E30-05", source="E29-02", kind="groove", xy=[90, 90]),
    dict(id="E30-06", source="E29-03", kind="slotted", xy=[135, 90]),
    dict(id="E30-07", source="E29-04", kind="slotted_bead", xy=[45, 135]),
    dict(id="E30-08", source="E29-05", kind="hybrid_A", xy=[90, 135]),
    dict(id="E30-09", source="E29-05", kind="hybrid_B", xy=[135, 135]),
)


def plan():
    return [dict(row) for row in SPECIMENS]


def parameters(record):
    if (E28_VERSION, E29_VERSION) != (
            SOURCE_VERSIONS["E28"], SOURCE_VERSIONS["E29"]):
        raise ValueError("Source experiment versions changed; release a new E30 version")
    kind = record["kind"]
    if kind in ("baseline_A", "baseline_B"):
        p = e28_parameters(dict(condition=kind, cavity_xy_mm=[25.4, 25.4],
                                tube_od_mm=13.5))
        assert p == e29_parameters(dict(kind="baseline"))
    elif kind == "wall_relief":
        p = e28_parameters(dict(condition=kind, cavity_xy_mm=[25.6, 25.6],
                                tube_od_mm=13.5))
    elif kind == "tube_relief":
        p = e28_parameters(dict(condition=kind, cavity_xy_mm=[25.4, 25.4],
                                tube_od_mm=13.3))
    elif kind in ("groove", "slotted", "slotted_bead"):
        p = e29_parameters(dict(kind=kind))
    elif kind in ("hybrid_A", "hybrid_B"):
        p = e29_parameters(dict(kind="hybrid"))
    else:
        raise ValueError("Unknown E30 condition: " + kind)
    return p


def coupon(record):
    """Reuse E28/E29 geometry exactly, changing the exterior ID engraving only."""
    kind = record["kind"]
    p = parameters(record)
    shape = build_brick(p, corner_radius=.8, stud_lip_radius=.5, entry=.3)
    if kind in ("slotted_bead", "hybrid_A", "hybrid_B"):
        shape = add_rounded_bead(shape, p)
    if kind in ("slotted", "slotted_bead", "hybrid_A", "hybrid_B"):
        shape = add_receiver_slots(shape)
    if kind in ("groove", "hybrid_A", "hybrid_B"):
        shape = add_waist(shape, p)
    shape = engrave(shape, record["id"], x=0, y=-p.depth / 2,
                    z=11.5, size=3.0, depth=.4)
    if not shape.isValid() or len(shape.Solids()) != 1:
        raise ValueError("Invalid/disconnected coupon: " + record["id"])
    if any(abs(a-b) > 1e-4 for a, b in zip(
            exact_bounds(shape), (31.8, 31.8, 23.7))):
        raise ValueError("Invalid coupon bounds: " + record["id"])
    return p, shape


def generate(out=Path("build/unified-fit-e30")):
    out = Path(out)
    if out.exists() and any(out.iterdir()):
        raise ValueError("Use an empty E30 output directory")
    out.mkdir(parents=True, exist_ok=True)
    source_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    records = plan()
    placed = []
    for row in records:
        print("BUILD", row["id"], row["kind"], flush=True)
        p, shape = coupon(row)
        folder = out / row["id"]
        folder.mkdir()
        mesh = export_stl(shape, folder / "brick.stl")
        cq.exporters.export(shape, str(folder / "brick.step"))
        restored = cq.importers.importStep(str(folder / "brick.step")).val()
        step_ok = (restored.isValid() and len(restored.Solids()) == 1
                   and abs(restored.Volume()-shape.Volume()) /
                   shape.Volume() <= 1e-6)
        if not step_ok:
            raise ValueError("STEP roundtrip failed: " + row["id"])
        report = dict(
            passed=mesh["mesh"]["passed"] and step_ok,
            id=row["id"], kind=row["kind"], source=row["source"],
            version=VERSION, source_versions=SOURCE_VERSIONS,
            geometry=dict(parameters=asdict(p), volume_mm3=shape.Volume(),
                          bounds_mm=exact_bounds(shape)),
            step_roundtrip_passed=step_ok, mesh=mesh["mesh"],
            source_sha256=source_sha,
            slicing_validated=False, physical_fit_validated=False,
            child_safe_validated=False,
            limitations=[
                "No slicer/physical fit/child safety validation.",
                "Printed pairs must be physically tested; geometry alone does not predict force.",
                "Adult handling only until burr/fragment and fatigue inspections.",
            ])
        (folder/"report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        x, y = row["xy"]
        placed.append(shape.translate((x-90, y-90, 0)))
    plate = cq.Compound.makeCompound(placed)
    if not plate.isValid() or len(plate.Solids()) != len(records):
        raise ValueError("Plate must contain nine disconnected solids")
    for i, a in enumerate(placed):
        for b in placed[i+1:]:
            if a.intersect(b).Volume() > 1e-7:
                raise ValueError("Overlapping coupons")
    bounds = exact_bounds(plate)
    if any(abs(a-b) > 1e-4 for a,b in zip(bounds, (121.8,121.8,23.7))):
        raise ValueError(f"Unexpected plate bounds {bounds}")
    mesh = export_stl(plate, out/"E30-plate.stl")
    report = dict(
        passed=mesh["mesh"]["passed"], version=VERSION,
        source_versions=SOURCE_VERSIONS, source_issue=26,
        source_prs=[23,27], source_sha256=source_sha,
        specimens=records, bounds_mm=bounds, plate_solids=len(placed),
        bed_mm=[180,180], spacing_mm=45, printer="Bambu Lab A1 mini",
        expected_layer_height_mm=.2, mesh=mesh["mesh"],
        slicing_validated=False, physical_fit_validated=False,
        child_safe_validated=False,
        limitations=[
            "One print job: nine 2x2 coupons, with baseline and hybrid duplicated.",
            "Bambu Studio toolpaths and supports not yet inspected.",
            "Not a toy until adult safety/fatigue testing; no physical validation.",
        ])
    (out/"report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print("E30 EXPORTED", bounds, flush=True)
    return records


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("build/unified-fit-e30"))
    generate(parser.parse_args().out)
