"""E29-V3: dual-fit DUPLO concepts; adult-only experimental coupons.

Only rounded/recessed contact features. Physical fit, fatigue and child safety
are NOT validated by CAD, mesh or automated tests.
"""
from dataclasses import asdict, replace
from pathlib import Path
import hashlib
import json

import cadquery as cq

from brickcad.marking import engrave
from brickcad.model import brick_from_fit, build as build_brick
from brickcad.verify import exact_bounds
from experiments.full_height_fit.design import export_stl

VERSION = "E29-V3"
PROFILE = "duplo-e27-play-v1"
# Each coupon is 31.8 mm square. 2 rows x 3 columns, 45 mm spacing.
SPECIMENS = (
    dict(id="E29-01", kind="baseline", xy=(45, 68)),
    dict(id="E29-02", kind="groove", xy=(90, 68)),
    dict(id="E29-03", kind="slotted", xy=(135, 68)),
    dict(id="E29-04", kind="slotted_bead", xy=(45, 112)),
    dict(id="E29-05", kind="hybrid", xy=(90, 112)),
)
GROOVE_PROFILE = (
    (4.70, 1.05), (4.51, 1.55), (4.51, 2.70),
    (4.70, 3.20), (5.00, 3.20), (5.00, 1.05),
)
SLOT_WIDTH = 1.10
SLOT_END_RADIUS = .65
SLOT_END_Z = 4.40
BEAD_MINOR_RADIUS = .16
BEAD_Z = 2.25


def plan():
    return [dict(s) for s in SPECIMENS]


def parameters(record):
    p = brick_from_fit(PROFILE, nx=2, ny=2)
    if record["kind"] == "slotted":
        p = replace(p, tube_radius=6.65)
    elif record["kind"] in ("slotted_bead", "hybrid"):
        p = replace(p, tube_radius=6.60)
    elif record["kind"] not in ("baseline", "groove"):
        raise ValueError("Unknown E29 variant")
    assert p.cavity_xy == (25.4, 25.4)
    assert p.stud_radius == 4.7 and p.stud_inner_radius == 3.2
    assert p.tube_inner_radius == 4.7
    return p


def add_waist(shape, p):
    """Shallow recessed stud waist with sloping ramps, no protruding hooks.

    Wall thickness at waist is 4.51 - 3.20 = 1.31 mm.
    """
    cutter = (cq.Workplane("XZ").polyline(GROOVE_PROFILE).close()
              .revolve(360, (0, 0), (0, 1)).val())
    for x, y in p.studs():
        shape = shape.cut(cutter.translate((x, y, p.height)))
    return shape.clean()


def add_rounded_bead(shape, p):
    """Integral toroidal ridge, later interrupted by four receiver slots."""
    bead = cq.Solid.makeTorus(
        p.tube_radius, BEAD_MINOR_RADIUS,
        cq.Vector(0, 0, BEAD_Z), cq.Vector(0, 0, 1))
    return shape.fuse(bead).clean()


def add_receiver_slots(shape):
    """Four broad tube quadrants, NOT thin detachable snap fingers.

    Rounded slot ends reduce root stress. Slot entrance is open beneath the
    brick; accessible slot edges still require physical burr inspection.
    """
    for angle in (0, 90, 180, 270):
        channel = (cq.Workplane("XY")
                   .box(4., SLOT_WIDTH, SLOT_END_Z + .1,
                        centered=(True, True, False))
                   .translate((6., 0., -.1)).val())
        rounded_end = cq.Solid.makeCylinder(
            SLOT_END_RADIUS, 4., cq.Vector(4., 0., SLOT_END_Z),
            cq.Vector(1, 0, 0))
        # Widen the exposed mouth slightly, making insertion less snag-prone.
        mouth = (cq.Workplane("YZ")
                 .polyline(((-.75, -.1), (.75, -.1),
                            (.55, .80), (-.55, .80)))
                 .close().extrude(4.).translate((4., 0., 0)).val())
        tool = channel.fuse(rounded_end).fuse(mouth)
        tool = tool.rotate((0, 0, 0), (0, 0, 1), angle)
        shape = shape.cut(tool)
    return shape.clean()


def coupon(record):
    kind = record["kind"]
    p = parameters(record)
    # Existing safe-touch nominal finish: body R0.8, stud lip R0.5,
    # receiver entry 0.3 mm chamfer. NOT a physical safety certification.
    shape = build_brick(p, corner_radius=.8, stud_lip_radius=.5, entry=.3)
    if kind in ("slotted_bead", "hybrid"):
        shape = add_rounded_bead(shape, p)
    if kind in ("slotted", "slotted_bead", "hybrid"):
        shape = add_receiver_slots(shape)
    if kind in ("groove", "hybrid"):
        shape = add_waist(shape, p)
    shape = engrave(shape, record["id"], x=0, y=-p.depth / 2,
                    z=11.5, size=3., depth=.4)
    if not shape.isValid() or len(shape.Solids()) != 1:
        raise ValueError(f"Invalid or disconnected {record['id']}")
    if any(abs(a-b) > 1e-4 for a, b in
           zip(exact_bounds(shape), (31.8, 31.8, 23.7))):
        raise ValueError(f"Bad dimensions: {record['id']}")
    return p, shape


def generate(out=Path("build/dual-fit-e29")):
    out = Path(out)
    if out.exists() and any(out.iterdir()):
        raise ValueError("Use an empty E29 output directory")
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
        if (not restored.isValid() or len(restored.Solids()) != 1 or
                abs(restored.Volume() - shape.Volume()) / shape.Volume() > 1e-6):
            raise ValueError(f"STEP roundtrip failed: {record['id']}")
        report = dict(
            passed=mesh["mesh"]["passed"], id=record["id"],
            kind=record["kind"], version=VERSION,
            baseline_profile=PROFILE, parameters=asdict(p),
            volume_mm3=shape.Volume(), bounds_mm=exact_bounds(shape),
            mesh=mesh["mesh"], source_sha256=source_sha,
            physical_fit_validated=False, slicing_validated=False,
            child_safe_validated=False,
            limitations=[
                "Not a toy; adult-only until print, burr, crack and repeated fit tests pass.",
                "PLA snap fatigue and actual clutch force are not simulated.",
                "The bead is a smooth internal ridge, not an exposed hook.",
            ])
        (folder / "report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        x, y = record["xy"]
        placed.append(shape.translate((x-90, y-90, 0)))
    plate = cq.Compound.makeCompound(placed)
    if not plate.isValid() or len(plate.Solids()) != len(records):
        raise ValueError("Plate is not five disconnected valid solids")
    for i, a in enumerate(placed):
        for b in placed[i+1:]:
            if a.intersect(b).Volume() > 1e-7:
                raise ValueError("Coupons overlap")
    bounds = exact_bounds(plate)
    if any(abs(a-b) > 1e-4 for a, b in
           zip(bounds, (121.8, 75.8, 23.7))):
        raise ValueError(f"Plate bounds: {bounds}")
    mesh = export_stl(plate, out / "E29-plate.stl")
    report = dict(passed=mesh["mesh"]["passed"], version=VERSION,
                  source_issue=26, baseline_profile=PROFILE,
                  specimens=records, bounds_mm=bounds,
                  printer="Bambu Lab A1 mini", layer_height_mm=.2,
                  physical_fit_validated=False,
                  slicing_validated=False, child_safe_validated=False,
                  plate_solids=5, mesh=mesh["mesh"])
    (out / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print("E29 EXPORTED", bounds, flush=True)
    return records


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("build/dual-fit-e29"))
    generate(parser.parse_args().out)
