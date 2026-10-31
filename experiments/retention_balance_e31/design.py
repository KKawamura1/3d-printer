"""E31-V1: balance printed-to-printed handling and genuine DUPLO retention.

Nine adult-only coupons in one A1 mini plate. E30-07 mating geometry is
preserved in two controls; candidate changes are receiver-only.
CAD/slicing cannot validate clutch force or child safety.
"""
from dataclasses import asdict, replace
from pathlib import Path
import hashlib
import json

import cadquery as cq

from brickcad.marking import engrave
from brickcad.model import build as build_brick
from brickcad.verify import exact_bounds
from experiments.full_height_fit.design import export_stl
from experiments.dual_fit_e29.design import (
    VERSION as E29_VERSION,
    BEAD_MINOR_RADIUS, BEAD_Z, SLOT_WIDTH, SLOT_END_RADIUS,
    parameters as e29_parameters, add_rounded_bead, add_receiver_slots,
)
from experiments.unified_fit_e30.design import VERSION as E30_VERSION

VERSION = "E31-V1"
PROFILE = "duplo-e27-play-v1"
SOURCE_VERSIONS = {"E29": "E29-V3", "E30": "E30-V1"}
# 9 x 2x2 coupons, 45mm centres, no printable bed or support geometry.
SPECIMENS = (
    dict(id="E31-01", kind="reference_A", xy=[45, 45]),
    dict(id="E31-02", kind="reference_B", xy=[90, 45]),
    dict(id="E31-03", kind="bead_014", xy=[135, 45]),
    dict(id="E31-04", kind="bead_018", xy=[45, 90]),
    dict(id="E31-05", kind="bead_020", xy=[90, 90]),
    dict(id="E31-06", kind="tube_1324", xy=[135, 90]),
    dict(id="E31-07", kind="tube_1328", xy=[45, 135]),
    dict(id="E31-08", kind="short_slots", xy=[90, 135]),
    dict(id="E31-09", kind="upper_contact", xy=[135, 135]),
)
BEAD_RADII = {"bead_014": .14, "bead_018": .18, "bead_020": .20}
TUBE_RADII = {"tube_1324": 6.62, "tube_1328": 6.64}
SHORT_SLOT_END_Z = 3.60  # E29 default: 4.40; root rounded R0.65
UPPER_BEAD_Z = 3.55
UPPER_BEAD_MINOR_R = .18
UPPER_BEAD_RADIAL_INSET = .05  # upper band OD = 13.46 at baseline


def plan():
    return [dict(s) for s in SPECIMENS]


def parameters(record):
    if (E29_VERSION, E30_VERSION) != (
            SOURCE_VERSIONS["E29"], SOURCE_VERSIONS["E30"]):
        raise ValueError("Upstream experiment changed; release a new E31 version")
    p = e29_parameters({"kind": "slotted_bead"})
    kind = record["kind"]
    if kind in TUBE_RADII:
        p = replace(p, tube_radius=TUBE_RADII[kind])
    elif kind not in (
            "reference_A", "reference_B", "bead_014", "bead_018",
            "bead_020", "short_slots", "upper_contact"):
        raise ValueError("Unknown E31 condition " + kind)
    return p


def add_custom_bead(shape, p, minor_radius, z=BEAD_Z, radial_inset=0.):
    # A smooth, integral toroidal bead. Not an isolated snap hook.
    ring = cq.Solid.makeTorus(
        p.tube_radius - radial_inset, minor_radius,
        cq.Vector(0, 0, z), cq.Vector(0, 0, 1))
    return shape.fuse(ring).clean()


def add_short_slots(shape):
    """Same 4 E29 rounded slot profiles, but shorter by 0.80 mm."""
    for angle in (0, 90, 180, 270):
        channel = (cq.Workplane("XY")
                   .box(4., SLOT_WIDTH, SHORT_SLOT_END_Z + .1,
                        centered=(True, True, False))
                   .translate((6., 0., -.1)).val())
        rounded_end = cq.Solid.makeCylinder(
            SLOT_END_RADIUS, 4., cq.Vector(4., 0., SHORT_SLOT_END_Z),
            cq.Vector(1, 0, 0))
        mouth = (cq.Workplane("YZ")
                 .polyline(((-.75, -.1), (.75, -.1),
                            (.55, .80), (-.55, .80)))
                 .close().extrude(4.).translate((4., 0., 0)).val())
        tool = channel.fuse(rounded_end).fuse(mouth)
        shape = shape.cut(tool.rotate((0, 0, 0), (0, 0, 1), angle))
    return shape.clean()


def coupon(record):
    p = parameters(record)
    kind = record["kind"]
    shape = build_brick(p, corner_radius=.8, stud_lip_radius=.5, entry=.3)

    if kind in BEAD_RADII:
        shape = add_custom_bead(shape, p, BEAD_RADII[kind])
    else:
        # Preserve the exact E30-07 bead for both controls and all other cases.
        shape = add_rounded_bead(shape, p)

    if kind == "upper_contact":
        # Distinct upper contact band; intentionally weaker than lower bead.
        # Inspect Bambu Studio toolpaths: this subtle radial feature may vanish.
        shape = add_custom_bead(
            shape, p, UPPER_BEAD_MINOR_R, z=UPPER_BEAD_Z,
            radial_inset=UPPER_BEAD_RADIAL_INSET)

    if kind == "short_slots":
        shape = add_short_slots(shape)
    else:
        shape = add_receiver_slots(shape)

    shape = engrave(shape, record["id"], x=0, y=-p.depth/2,
                    z=11.5, size=3., depth=.4)
    if not shape.isValid() or len(shape.Solids()) != 1:
        raise ValueError("Invalid/disconnected E31 coupon " + record["id"])
    if any(abs(x-y) > 1e-4 for x,y in
           zip(exact_bounds(shape), (31.8, 31.8, 23.7))):
        raise ValueError("Bad E31 coupon bounds " + record["id"])
    return p, shape


def generate(out=Path("build/e31-retention-balance")):
    out = Path(out)
    if out.exists() and any(out.iterdir()):
        raise ValueError("Use an empty E31 output directory")
    out.mkdir(parents=True, exist_ok=True)
    source_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    placed = []
    records = plan()
    for record in records:
        print("BUILD", record["id"], record["kind"], flush=True)
        p, shape = coupon(record)
        folder = out / record["id"]
        folder.mkdir()
        mesh = export_stl(shape, folder / "brick.stl")
        cq.exporters.export(shape, str(folder / "brick.step"))
        restored = cq.importers.importStep(str(folder / "brick.step")).val()
        step_ok = (restored.isValid() and len(restored.Solids()) == 1
                   and abs(restored.Volume() - shape.Volume()) /
                   shape.Volume() <= 1e-6)
        if not step_ok:
            raise ValueError("STEP roundtrip failed: " + record["id"])
        report = dict(
            passed=mesh["mesh"]["passed"] and step_ok,
            id=record["id"], kind=record["kind"], version=VERSION,
            source_versions=SOURCE_VERSIONS, profile=PROFILE,
            parameters=asdict(p), volume_mm3=shape.Volume(),
            bounds_mm=exact_bounds(shape), mesh=mesh["mesh"],
            source_sha256=source_sha, step_roundtrip_passed=step_ok,
            slicing_validated=False, physical_fit_validated=False,
            child_safe_validated=False,
            limitations=[
                "Adult-only experimental coupons; not child-safe validated.",
                "CAD cannot predict insertion, extraction, fatigue or shake retention.",
                "Inspect toolpaths at 0.20mm layers: changed beads may disappear.",
            ])
        (folder / "report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        x, y = record["xy"]
        placed.append(shape.translate((x-90, y-90, 0)))
    plate = cq.Compound.makeCompound(placed)
    if not plate.isValid() or len(plate.Solids()) != len(records):
        raise ValueError("E31 plate must contain nine distinct solids")
    for i,a in enumerate(placed):
        for b in placed[i+1:]:
            if a.intersect(b).Volume() > 1e-7:
                raise ValueError("Overlapping E31 parts")
    bounds = exact_bounds(plate)
    if any(abs(a-b) > 1e-4 for a,b in
           zip(bounds, (121.8, 121.8, 23.7))):
        raise ValueError("Unexpected E31 plate bounds " + str(bounds))
    mesh = export_stl(plate, out/"E31-plate.stl")
    report = dict(
        passed=mesh["mesh"]["passed"], version=VERSION,
        source_issue=26, source_experiment="E30-V1",
        source_versions=SOURCE_VERSIONS, source_sha256=source_sha,
        specimens=records, bounds_mm=bounds, plate_solids=9,
        bed_mm=[180,180], expected_layer_height_mm=.2,
        physical_fit_validated=False, slicing_validated=False,
        child_safe_validated=False, mesh=mesh["mesh"])
    (out/"report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2)+"\n")
    print("E31 EXPORTED", bounds, flush=True)
    return records


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path,
                        default=Path("build/e31-retention-balance"))
    generate(parser.parse_args().out)
