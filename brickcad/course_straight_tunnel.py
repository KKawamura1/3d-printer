"""Independent 2x2 E31 straight tunnel: circular mouths and raised roof."""
from dataclasses import dataclass,replace
from pathlib import Path
import hashlib
import json
import math
import cadquery as cq
from brickcad.course_artifacts import export_geometry
from brickcad.course_geometry import smoothstep_rise_expanded
from brickcad.model import brick_from_fit,receiver
from brickcad.connections import make_studs
from brickcad.marking import engrave
from brickcad.standards import BALL_TRACK,ROUNDED_EDGES
from brickcad.verify import exact_bounds
from parts.tunnel.e31_fit import add_e31_05_receiver_features


@dataclass(frozen=True)
class Tunnel:
    floor: float=BALL_TRACK.floor
    radius: float=BALL_TRACK.radius
    ceiling: float=34.8
    cavity_height: float=4.75
    entry: float=.3

    @property
    def bridge_width(self):
        return 2*(self.floor+self.radius+math.sqrt(2)*self.radius-self.ceiling)


def passage_wire(x,blend,t):
    cy=t.floor+t.radius
    a=t.radius/math.sqrt(2)
    b=t.bridge_width/2
    def mix(cx,cz,tx,tz):
        return (cx*(1-blend)+tx*blend,cz*(1-blend)+tz*blend)
    end=mix(t.radius*math.cos(math.radians(75)),
            cy+t.radius*math.sin(math.radians(75)),b,t.ceiling)
    mid=mix(t.radius*.5,cy+t.radius*math.sqrt(3)/2,
            (a+b)/2,(cy+a+t.ceiling)/2)
    apex=(0,(cy+t.radius)*(1-blend)+t.ceiling*blend)
    w=(cq.Workplane("YZ",origin=(x,0,0))
       .moveTo(-a,cy+a).threePointArc((0,t.floor),(a,cy+a)))
    if blend==1:
        w=w.lineTo(b,t.ceiling).lineTo(-b,t.ceiling).lineTo(-a,cy+a)
    else:
        w=(w.threePointArc(mid,end).threePointArc(apex,(-end[0],end[1]))
           .threePointArc((-mid[0],mid[1]),(-a,cy+a)))
    return w.close().val()


def build_course(model_id,recipe,*,marked=True):
    if recipe!={"roof":"transition","transition_mm":4,"ceiling_mm":34.8}:
        raise ValueError("Only validated T01 circular-to-teardrop roof supported")
    t=Tunnel()
    p=replace(brick_from_fit("duplo-e27-play-v1",nx=2,ny=2,height_units=2),
              tube_radius=6.60)
    body=(cq.Workplane("XY")
          .box(p.width,p.depth,p.height,centered=(True,True,False))
          .edges("|Z").fillet(ROUNDED_EDGES.corner_radius)
          .edges(">Z").fillet(ROUNDED_EDGES.corner_radius))
    shell=receiver(p,body,t.cavity_height,ROUNDED_EDGES.receiver_entry)
    cy=t.floor+t.radius
    a=t.radius/math.sqrt(2)
    bb=t.bridge_width/2
    # Construct the circular entry/exit loft with 1mm full-round lip and
    # eight smoothstep transition stations at each end.
    stations=[(-p.width/2-1,0),(-p.width/2+1,0)]
    for i in range(1,9):
        u=i/8
        stations.append((-p.width/2+1+4*u,smoothstep_rise_expanded(u)))
    stations += [(-x,b) for x,b in reversed(stations)]
    cut=cq.Solid.makeLoft([passage_wire(x,progress,t) for x,progress in stations],
                          ruled=True)
    shell=shell.cut(cut)
    mouths=[e for e in shell.val().Edges()
            if abs(abs(e.Center().x)-p.width/2)<1e-5
            and e.BoundingBox().zmin>t.floor-.01
            and e.BoundingBox().zmax<t.ceiling+.01
            and e.BoundingBox().ymin>-t.radius-.01
            and e.BoundingBox().ymax<t.radius+.01]
    if mouths:
        shell=shell.newObject(mouths).fillet(t.entry)
    studs=make_studs(p.studs(),p.height,p.stud_radius-p.clearance,
                     p.stud_inner_radius,p.stud_height,
                     lip_radius=ROUNDED_EDGES.stud_lip_radius)
    shape=shell.union(studs).val().clean()
    shape=add_e31_05_receiver_features(shape,p.tubes(),p.tube_radius,
                                       receiver_depth=t.cavity_height)
    if marked:
        shape=engrave(shape,model_id,x=0,y=-p.depth/2,z=10.)
    if not shape.isValid() or len(shape.Solids())!=1:
        raise ValueError("T01 configured geometry not a valid solid")
    return shape,p




def export_course(model_id,recipe,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    shape,p=build_course(model_id,recipe)
    stl,m=export_geometry(shape,out,tolerance=.01,angular_tolerance=.1)
    checks={"single_valid_solid":shape.isValid() and len(shape.Solids())==1,
            "watertight":m["passed"],
            "mesh_volume":abs(shape.Volume()-m["signed_volume_mm3"])/shape.Volume()<.001}
    report={"part_id":model_id,"passed":all(checks.values()),
            "checks":checks,"mesh":m,
            "geometry":{"bounds_mm":exact_bounds(shape),"volume_mm3":shape.Volume()},
            "source_engine":"brickcad.course_straight_tunnel",
            "physical_fit_validated":False,"physical_rolling_validated":False,
            "slicing_validated":False}
    (out/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    (out/"course-manifest.json").write_text(json.dumps({
        "schema_version":1,"mode":"independent_configured_geometry",
        "model_id":model_id,"source_engine":"brickcad.course_straight_tunnel",
        "recipe":recipe,"geometry_verified":report["passed"],
        "stl_sha256":hashlib.sha256(stl.read_bytes()).hexdigest(),
        "physical_fit_validated":False,"slicing_validated":False},
        ensure_ascii=False,indent=2)+"\n")
    if not report["passed"]:
        raise ValueError("T01 failed CAD checks "+str(checks))
    return report
