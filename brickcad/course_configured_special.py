"""Generate R16 and steep-drop models with independent PR56 CAD primitives."""
from pathlib import Path
import hashlib
import json
import cadquery as cq
from brickcad.course_artifacts import export_geometry

from brickcad.course_contract import engrave_course as engrave
from brickcad.verify import exact_bounds
from brickcad.course_prod_sharp_curve import build_course as build_sharp, checks as sharp_checks
from brickcad.course_prod_steep_drop import build_course as build_drop, geometry_checks as drop_checks


def build_course(model_id, family, recipe, *, mark=True):
    name,version = model_id.split("-")
    if family == "sharp_r16":
        kind=recipe["enclosure"]
        if kind not in ("open","tunnel"):
            raise ValueError("Unverified R16 enclosure")
        spec={"id":name,"version":version,"enclosure":{"kind":kind,"windows":[]}}
        shape,p,path=build_sharp(spec,reference_label=model_id,mark=mark)
        validations,_,_,_=sharp_checks(shape,p,path,kind)
    elif family == "drop":
        direction=recipe["exit"]
        mirror=recipe["mirror"]
        if direction not in ("east","south") or (direction=="east" and mirror):
            raise ValueError("Unverified shaft configuration")
        spec={"id":name,"version":version,"geometry":{"exit":direction}}
        bare,p,d=build_drop(spec,mark=False)
        validations,_,_,_=drop_checks(bare,p,d,direction)
        shape=bare.mirror("XZ") if mirror else bare
        if mark:
            if mirror:
                shape=engrave(shape,model_id,x=0.,y=-p.depth/2,z=18.)
            else:
                shape,_,_=build_drop(spec,mark=True)
    else:
        raise ValueError("Unsupported configured family")
    if not shape.isValid() or len(shape.Solids()) != 1:
        raise ValueError("Configured model must be one connected solid")
    return shape,p,validations




def export_course(model_id,family,recipe,out):
    out=Path(out)
    out.mkdir(parents=True,exist_ok=True)
    shape,p,validations=build_course(model_id,family,recipe)
    stl,mesh=export_geometry(shape,out,tolerance=.01,angular_tolerance=.1)
    checks={**validations,
            "valid_single_solid":shape.isValid() and len(shape.Solids())==1,
            "watertight_mesh":mesh["passed"]}
    report={"part_id":model_id,"passed":all(checks.values()),
            "checks":checks,"mesh":mesh,
            "geometry":{"bounds_mm":exact_bounds(shape),"volume_mm3":shape.Volume()},
            "source_engine":"brickcad.course_configured_special",
            "physical_fit_validated":False,"physical_rolling_validated":False,
            "slicing_validated":False}
    (out/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    (out/"course-manifest.json").write_text(json.dumps({
        "schema_version":1,"mode":"independent_configured_geometry",
        "model_id":model_id,"source_engine":"brickcad.course_configured_special",
        "family":family,"recipe":recipe,"geometry_verified":report["passed"],
        "stl_sha256":hashlib.sha256(stl.read_bytes()).hexdigest(),
        "physical_fit_validated":False,"slicing_validated":False},
        ensure_ascii=False,indent=2)+"\n")
    if not report["passed"]:
        raise ValueError(f"{model_id} geometry validation failed: "+str(checks))
    return report
