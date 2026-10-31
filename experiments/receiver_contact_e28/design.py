"""E28: diagnose independent receiver wall and tube contact without finer layers."""
from dataclasses import asdict, replace
from pathlib import Path
import hashlib
import json

import cadquery as cq

from brickcad.marking import engrave
from brickcad.model import brick_from_fit, build as build_brick
from brickcad.provenance import design_manifest
from brickcad.standards import ROUNDED_EDGES
from brickcad.verify import exact_bounds
from experiments.full_height_fit.design import export_stl

VERSION = "E28-V1"
BASE_PROFILE = "duplo-e27-play-v1"
# Positions for the 180 x 180 mm A1 mini plate; no rotation.
SPECIMENS = (
    dict(id="E28-01", condition="baseline_A", bed_center_xy_mm=[69, 69],
         cavity_xy_mm=[25.40, 25.40], tube_od_mm=13.50),
    dict(id="E28-02", condition="baseline_B", bed_center_xy_mm=[111, 69],
         cavity_xy_mm=[25.40, 25.40], tube_od_mm=13.50),
    dict(id="E28-03", condition="wall_relief", bed_center_xy_mm=[69, 111],
         cavity_xy_mm=[25.60, 25.60], tube_od_mm=13.50),
    dict(id="E28-04", condition="tube_relief", bed_center_xy_mm=[111, 111],
         cavity_xy_mm=[25.40, 25.40], tube_od_mm=13.30),
)


def plan():
    return [dict(r) for r in SPECIMENS]


def parameters(record):
    p = brick_from_fit(BASE_PROFILE, nx=2, ny=2)
    if record["condition"] == "wall_relief":
        # Inset 3.30 -> 3.20 widens opening by 0.20 mm TOTAL.
        p = replace(p, receiver_inset_xy=(3.20, 3.20))
    elif record["condition"] == "tube_relief":
        p = replace(p, tube_radius=6.65)
    elif record["condition"] not in ("baseline_A", "baseline_B"):
        raise ValueError("Unknown E28 condition")
    assert all(abs(a-b) < 1e-8 for a,b in zip(p.cavity_xy,record["cavity_xy_mm"]))
    assert abs(2*p.tube_radius-record["tube_od_mm"]) < 1e-8
    assert (p.stud_radius,p.stud_inner_radius,p.tube_inner_radius)==(4.7,3.2,4.7)
    return p


def coupon(record):
    p = parameters(record)
    raw = build_brick(p, corner_radius=.8, stud_lip_radius=.5, entry=.3)
    # Label is recessed into -Y outside wall, above the 4.5 mm contact band.
    shape = engrave(raw, record["id"], x=0, y=-p.depth/2, z=11.5,
                    size=3.0, depth=.4)
    assert shape.isValid() and len(shape.Solids())==1
    assert all(abs(a-b)<1e-6 for a,b in zip(exact_bounds(shape),(31.8,31.8,23.7)))
    return p,shape


def generate(out=Path("build/receiver-contact-e28")):
    out=Path(out)
    if out.exists() and any(out.iterdir()):
        raise ValueError("Use an empty E28 output directory")
    out.mkdir(parents=True, exist_ok=True)
    source_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    placed=[]
    records=plan()
    for record in records:
        print("BUILD",record["id"],record["condition"],flush=True)
        p,shape=coupon(record)
        folder=out/record["id"]
        folder.mkdir()
        exported=export_stl(shape,folder/"brick.stl")
        cq.exporters.export(shape,str(folder/"brick.step"))
        restored=cq.importers.importStep(str(folder/"brick.step")).val()
        step_ok=(restored.isValid() and len(restored.Solids())==1
                 and abs(restored.Volume()-shape.Volume())<1e-4)
        if not step_ok:
            raise ValueError("STEP roundtrip failed for "+record["id"])
        report=dict(
            passed=exported["mesh"]["passed"] and step_ok,
            id=record["id"],condition=record["condition"],version=VERSION,
            specimen=record,mesh=exported["mesh"],
            collapsed_triangles_removed=exported["collapsed_triangles_removed"],
            step_roundtrip_passed=step_ok,
            design=design_manifest(p,finish=ROUNDED_EDGES),
            geometry=dict(parameters=asdict(p),bounds_mm=exact_bounds(shape),
                          volume_mm3=shape.Volume()),
            source_sha256=source_sha,physical_fit_validated=False,
            slicing_validated=False,
            limitations=[
                "CAD clearance does not predict clutch force or actual contact location.",
                "Same stud CAD does not guarantee identical printed toolpaths.",
                "Diagnostic trial only; not an adopted fit profile."])
        (folder/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
        x,y=record["bed_center_xy_mm"]
        placed.append(shape.translate((x-90,y-90,0)))
    plate=cq.Compound.makeCompound(placed)
    if not plate.isValid() or len(plate.Solids())!=4:
        raise ValueError("Plate must have four independent valid solids")
    for i,a in enumerate(placed):
        for b in placed[i+1:]:
            if a.intersect(b).Volume()>1e-7:
                raise ValueError("Plate coupons overlap")
    bounds=exact_bounds(plate)
    if any(abs(a-b)>1e-5 for a,b in zip(bounds,(73.8,73.8,23.7))):
        raise ValueError(f"Unexpected plate bounds: {bounds}")
    exported=export_stl(plate,out/"E28-plate.stl")
    report=dict(passed=exported["mesh"]["passed"],version=VERSION,
        mesh=exported["mesh"],specimens=records,bounds_mm=bounds,
        source_sha256=source_sha,expected_printer="Bambu Lab A1 mini",
        bed_size_mm=[180,180],physical_fit_validated=False,
        slicing_validated=False,plate_contains_four_disconnected_solids=True,
        limitations=["Slicer, printed dimensions and fit still unverified."])
    (out/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print("E28 CAD EXPORTED",bounds,flush=True)
    return records


if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,default=Path("build/receiver-contact-e28"))
    generate(parser.parse_args().out)
