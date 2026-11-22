"""SC02 pilot: compare clearance and larger windows without changing older IDs.

Stacked on PR #75: use its verified window geometry as the baseline.
CAD success is NOT physical rolling or durability validation.
"""
from dataclasses import dataclass, replace
from pathlib import Path
import argparse
import hashlib
import json

import cadquery as cq

from brickcad.course_artifacts import export_geometry, normalize_binary_stl
from brickcad.course_architectural_windows import (
    _verify_visibility, _window_geometry, model, plan, window_centres,
)
from brickcad.course_contract import PRODUCTION_CONTRACT, audited_production_course
from brickcad.course_r48_sloped_tunnel import (
    _clearance_factor, build_course, _passage_wire,
)
from brickcad.course_windows import mark_variant
from brickcad.verify import exact_bounds, mesh_check


SOURCE_ID = "SC02-V12"
# Extra *radius* in the internal passage: diameter allowance = twice this.
# The existing circular connection mouths and shared E31 fit do not change.
@dataclass(frozen=True)
class Trial:
    part_id: str
    radial_extra_mm: float
    expanded_windows: bool


TRIALS = (
    Trial("SC02-V18", .2, False),  # +0.4 mm internal passage diameter
    Trial("SC02-V19", .4, False),  # +0.8 mm internal passage diameter
    Trial("SC02-V20", .0, True),  # window-only: 5 larger outer windows
    Trial("SC02-V21", .4, True),  # combined candidate, NOT separately proven
)
LARGE_WINDOW_WIDTH_MM = 10.
LARGE_WINDOW_COUNT = 5
PLATE_CENTRES_MM = ((-34.,-34.), (34.,-34.), (-34.,34.), (34.,34.))


def centres_for(face, expanded):
    if not expanded:
        return tuple(window_centres(face))
    if face.kind != "convex":
        raise ValueError("This pilot is SC02 outer-convex only")
    return tuple(face.length*(i+1)/(LARGE_WINDOW_COUNT+1)
                 for i in range(LARGE_WINDOW_COUNT))


def check_plan():
    assert [t.part_id for t in TRIALS] == ["SC02-V18","SC02-V19","SC02-V20","SC02-V21"]
    assert len(set(t.part_id for t in TRIALS)) == len(TRIALS)
    for t in TRIALS:
        assert t.radial_extra_mm in (0.,.2,.4)
    # A positive allowance must vanish at both standard connection mouths.
    assert _clearance_factor(0.) == 0. and _clearance_factor(1.) == 0.
    assert _clearance_factor(.5) == 1. and _clearance_factor(.2) == 1.
    assert _clearance_factor(.05) == 0.
    # Verify actual section wires at the unchanged mouths, not just factors.
    p=model(SOURCE_ID)["source"]["recipe"]
    for at in (0.,1.):
        old=_passage_wire(at,p)
        for extra in (.2,.4):
            widened=_passage_wire(at,p,extra)
            if not old.isSame(widened):
                raise ValueError("Connection mouth was modified")


def build_trial(trial, out):
    from brickcad.course_r48_sloped_tunnel import spec
    source=model(SOURCE_ID)
    recipe=spec(source["source"]["recipe"])
    folder=Path(out)/trial.part_id
    folder.mkdir(parents=True,exist_ok=True)
    with audited_production_course(trial.part_id) as audit:
        before,fit=build_course(
            SOURCE_ID,recipe,marked=False,radial_extra_mm=trial.radial_extra_mm)
        initial_bounds=exact_bounds(before)
        # Do not change the existing PR75 common window policy for other parts.
        # Extract its exact three-window SC02 plan, optionally make five wider holes.
        faces=plan(source)
        if len(faces)!=1 or faces[0].kind!="convex":
            raise ValueError("Unexpected SC02 facade layout")
        face=replace(faces[0],width=LARGE_WINDOW_WIDTH_MM) if trial.expanded_windows else faces[0]
        centres=centres_for(face,trial.expanded_windows)
        if len(centres)!=(LARGE_WINDOW_COUNT if trial.expanded_windows else 3):
            raise ValueError("Wrong number of windows")
        shape=before
        windows=[]
        for centre in centres:
            cutter,geo=_window_geometry(face,centre)
            updated=shape.cut(cutter).clean()
            if not updated.isValid() or len(updated.Solids())!=1:
                raise ValueError(f"{trial.part_id}: invalid window cut at {centre}")
            volume_removed=shape.Volume()-updated.Volume()
            if volume_removed<=8.:
                raise ValueError(f"{trial.part_id}: window removed too little solid")
            _verify_visibility(before,updated,geo,guard=True)
            windows.append({"station_mm":round(centre,4),
                            "width_mm":face.width,
                            "removed_mm3":round(volume_removed,3)})
            shape=updated
        shape=mark_variant(shape,source,trial.part_id,fit)
    contract=audit.manifest()
    if contract["final_marking_labels"]!=[trial.part_id]:
        raise ValueError("Part ID was not engraved exactly once")
    if not shape.isValid() or len(shape.Solids())!=1:
        raise ValueError("Final SC02 trial is not one solid")
    bounds=exact_bounds(shape)
    if any(abs(a-b)>.11 for a,b in zip(bounds,initial_bounds)):
        raise ValueError(f"Change modified original bounding box {bounds} {initial_bounds}")
    stl,mesh=export_geometry(shape,folder,tolerance=.02,angular_tolerance=.15)
    checks={
        "single_valid_solid":shape.isValid() and len(shape.Solids())==1,
        "original_dimensions":all(abs(a-b)<.11 for a,b in zip(bounds,initial_bounds)),
        "watertight_stl":mesh["passed"],
        "stl_volume":abs(mesh["signed_volume_mm3"]-shape.Volume())/shape.Volume()<.001,
        "windows_count":len(windows)==(LARGE_WINDOW_COUNT if trial.expanded_windows else 3),
        "standard_mouths":_clearance_factor(0.)==_clearance_factor(1.)==0.,
        "engraved_once":contract["final_marking_labels"]==[trial.part_id],
    }
    report={
        "part_id":trial.part_id,"source_model_id":SOURCE_ID,
        "passed":all(checks.values()),"checks":checks,
        "radial_extra_mm":trial.radial_extra_mm,
        "nominal_diameter_extra_mm":2*trial.radial_extra_mm,
        "clearance_ramp_t":[.05,.20,.80,.95],
        "window_count":len(windows),"windows":windows,
        "bounds_mm":bounds,
        "source_unchanged":True,"production_contract":PRODUCTION_CONTRACT,
        "contract_evidence":contract,
        "physical_rolling_validated":False,
        "slicer_validated":False,
        "durability_validated":False,
        "caveats":[
            "Radius is an experimental CAD passage enlargement, not a measured minimum gap.",
            "A watertight STL and sightlines cannot prove rolling, fit, or wall durability.",
            "Concave-side windows omitted from this first structurally conservative comparison.",
        ],
    }
    (folder/"report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
    if not report["passed"]:
        raise ValueError(f"Trial checks failed: {trial.part_id} {checks}")
    return shape,report,stl


def export(out):
    check_plan()
    out=Path(out)
    out.mkdir(parents=True,exist_ok=True)
    shapes=[]
    reports=[]
    for trial in TRIALS:
        shape,report,stl=build_trial(trial,out)
        shapes.append(shape)
        reports.append(report)
        print(trial.part_id,"PASS",report["checks"],flush=True)
    placed=[]
    for shape,(x,y) in zip(shapes,PLATE_CENTRES_MM):
        placed.append(shape.translate((x,y,0)))
    plate=cq.Compound.makeCompound(placed)
    plate_bounds=exact_bounds(plate)
    # A1 mini bed is 180x180, with 3mm margin in both directions.
    if max(plate_bounds[:2])>174. or min(plate_bounds[:2])<0.:
        raise ValueError("Unexpected plate bounds")
    if max(plate_bounds[0],plate_bounds[1])>174.:
        raise ValueError("A1 mini plate overflow")
    plate_stl=out/"sc02-compare-4.stl"
    cq.exporters.export(plate,str(plate_stl),tolerance=.02,angularTolerance=.15)
    normalize_binary_stl(plate_stl)
    plate_mesh=mesh_check(plate_stl)
    if not plate_mesh["passed"]:
        raise ValueError("Four-part comparison plate is not a closed mesh")
    result={
        "passed":True,"cases":reports,
        "plate_bounds_mm":plate_bounds,
        "plate_model_ids":[t.part_id for t in TRIALS],
        "plate_stl_sha256":hashlib.sha256(plate_stl.read_bytes()).hexdigest(),
        "note":"CAD-only approval. Slicer and physical fit/rolling remain untested.",
    }
    (out/"report.json").write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    return result


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",type=Path,default=Path("build/sc02-robustness"))
    args=parser.parse_args()
    export(args.out)
