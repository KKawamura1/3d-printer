"""Independently reconstruct the pre-E31 horizontal straight rail.

Historical geometry only: this is NOT an E31 or current engraving candidate.
No calls to parts.straight_rail.design or other historical exporters.
"""
from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import math
import struct
import cadquery as cq

from brickcad.model import brick_from_fit,receiver
from brickcad.standards import BALL_TRACK
from brickcad.verify import mesh_check,exact_bounds


@dataclass(frozen=True)
class Rail:
    length: float=63.8
    width: float=BALL_TRACK.width
    height: float=BALL_TRACK.height
    opening: float=BALL_TRACK.opening
    floor: float=BALL_TRACK.floor
    outer_radius: float=.8
    lip_radius: float=.5
    end_chamfer: float=.15
    entry: float=.3
    roof: float=1.6

    @property
    def radius(self):
        depth=self.height-self.floor
        return ((self.opening/2)**2+depth*depth)/(2*depth)


def build_course(recipe):
    if recipe!={"width_mm":31.65,"length_mm":63.8,
               "fit_profile":"duplo-straight-rail-trial-v1"}:
        raise ValueError("Only historical straight rail geometry is supported")
    r=Rail()
    p=brick_from_fit("duplo-straight-rail-trial-v1",nx=4,ny=2,
                     body_offset_xy=(0.,r.width-31.8),height=r.height)
    outer=cq.Workplane("XY").box(r.length,r.width,r.height,
                                 centered=(True,True,False))
    outer=outer.edges("|Z").fillet(r.outer_radius).edges(">Z").fillet(r.outer_radius)
    result=receiver(p,outer,r.floor-r.roof,r.entry,(r.length,r.width))
    groove=cq.Solid.makeCylinder(r.radius,r.length+2,
                 cq.Vector(-r.length/2-1,0,r.floor+r.radius),cq.Vector(1,0,0))
    result=result.cut(groove)
    lips=[e for e in result.val().Edges()
          if e.geomType()=="LINE" and
          e.Length()>r.length-2*r.outer_radius-1 and
          abs(abs(e.Center().y)-r.opening/2)<.01]
    if len(lips)!=2:
        raise ValueError("Expected two long channel lips")
    result=result.newObject(lips).fillet(r.lip_radius)
    for x,ra,rb in [(-r.length/2,r.radius+r.end_chamfer,r.radius),
                    (r.length/2-r.end_chamfer,r.radius,r.radius+r.end_chamfer)]:
        lead=cq.Solid.makeCone(ra,rb,r.end_chamfer,
                               cq.Vector(x,0,r.floor+r.radius),cq.Vector(1,0,0))
        result=result.cut(lead)
    shape=result.val().clean()
    if not shape.isValid() or len(shape.Solids())!=1:
        raise ValueError("Invalid reconstructed legacy rail")
    return shape,p


def _strip(stl):
    raw=stl.read_bytes()
    n=struct.unpack_from("<I",raw,80)[0]
    if n<1 or len(raw)!=84+50*n:
        raise ValueError("Malformed STL")
    keep=[]
    for i in range(n):
        tri=raw[84+50*i:134+50*i]
        points=struct.unpack("<12fH",tri)[3:12]
        if len({tuple(points[j:j+3]) for j in (0,3,6)})==3:
            keep.append(tri)
    if len(keep)!=n:
        stl.write_bytes(raw[:80]+struct.pack("<I",len(keep))+b"".join(keep))


def export_course(model_id,recipe,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    shape,p=build_course(recipe)
    stl=out/"brick.stl"
    cq.exporters.export(shape,str(stl),tolerance=.01,angularTolerance=.1)
    _strip(stl)
    cq.exporters.export(shape,str(out/"brick.step"))
    m=mesh_check(stl)
    checks={"valid_single_solid":shape.isValid() and len(shape.Solids())==1,
            "watertight":m["passed"],
            "mesh_volume":abs(m["signed_volume_mm3"]-shape.Volume())/
                          shape.Volume()<.001}
    report={"part_id":model_id,"passed":all(checks.values()),"checks":checks,
            "mesh":m,"geometry":{"bounds_mm":exact_bounds(shape),
                                 "volume_mm3":shape.Volume()},
            "source_engine":"brickcad.course_legacy_rail",
            "legacy_unverified_e31":True,"standard_marking_validated":False,
            "physical_fit_validated":False,"physical_rolling_validated":False,
            "slicing_validated":False}
    (out/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    (out/"course-manifest.json").write_text(json.dumps({
        "schema_version":1,"mode":"independent_legacy_geometry",
        "model_id":model_id,"source_engine":"brickcad.course_legacy_rail",
        "legacy_unverified_e31":True,"standard_marking_validated":False,
        "geometry_verified":report["passed"],
        "stl_sha256":hashlib.sha256(stl.read_bytes()).hexdigest(),
        "physical_fit_validated":False,"slicing_validated":False},
        ensure_ascii=False,indent=2)+"\n")
    if not report["passed"]:
        raise ValueError("Legacy rail CAD verification failed")
    return report
