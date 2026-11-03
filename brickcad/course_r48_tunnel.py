"""Independent, parameter-driven 4x4 E31 R48 horizontal roofed tunnel.

Uses R48 centreline + evolving circular/raised roof section. The old
parts.gentle_curve_tunnel.design and parts.elbow.design are NOT imported.
"""
from dataclasses import dataclass,replace,asdict
from pathlib import Path
import hashlib
import json
import math
import struct
import cadquery as cq

from brickcad.model import brick_from_fit,receiver
from brickcad.connections import make_studs
from brickcad.marking import engrave
from brickcad.standards import BALL_TRACK,ROUNDED_EDGES
from brickcad.verify import mesh_check,exact_bounds
from parts.tunnel.e31_fit import add_e31_05_receiver_features

TURN_CENTRE=(-32.,32.,0.)
N_STATIONS=72


@dataclass(frozen=True)
class RoofSettings:
    direction: str
    radius_mm: float
    ceiling_mm: float
    lip_mm: float
    transition_mm: float

    @classmethod
    def parse(cls,data):
        if not isinstance(data,dict) or set(data)!={"direction","radius_mm","ceiling_mm","lip_mm","transition_mm"}:
            raise ValueError("Roofed R48 recipe is incomplete")
        opts=cls(**data)
        if (opts.direction not in ("right","left") or
                opts.radius_mm!=48 or opts.ceiling_mm!=34.8 or
                opts.lip_mm!=1 or opts.transition_mm!=4):
            raise ValueError("Unverified R48 tunnel geometry parameters")
        return opts

    @property
    def floor(self):
        return BALL_TRACK.floor

    @property
    def channel_radius(self):
        return BALL_TRACK.radius

    @property
    def cavity_height(self):
        return 4.75

    @property
    def bridge_width(self):
        return 2*(self.floor+self.channel_radius+
                  math.sqrt(2)*self.channel_radius-self.ceiling_mm)


def blend(distance,p):
    u=min(1.,max(0.,(distance-p.lip_mm)/p.transition_mm))
    return u*u*(3-2*u)


def section(angle,progress,p):
    theta=math.radians(angle)
    normal=(-math.sin(theta),math.cos(theta),0)
    inward=(-math.cos(theta),-math.sin(theta),0)
    plane=cq.Plane(
        origin=(TURN_CENTRE[0]+p.radius_mm*math.cos(theta),
                TURN_CENTRE[1]+p.radius_mm*math.sin(theta),0),
        xDir=inward,normal=normal)
    radius=p.channel_radius
    cy=p.floor+radius
    a=radius/math.sqrt(2)
    b=p.bridge_width/2
    def mix(circle,raised):
        return circle*(1-progress)+raised*progress
    end=(mix(radius*math.cos(math.radians(75)),b),
         mix(cy+radius*math.sin(math.radians(75)),p.ceiling_mm))
    mid=(mix(radius/2,(a+b)/2),
         mix(cy+radius*math.sqrt(3)/2,(cy+a+p.ceiling_mm)/2))
    apex_z=mix(cy+radius,p.ceiling_mm)
    wire=(cq.Workplane(plane).moveTo(-a,cy+a)
          .threePointArc((0,p.floor),(a,cy+a)))
    if progress>=1-1e-12:
        return wire.lineTo(b,p.ceiling_mm).lineTo(-b,p.ceiling_mm).lineTo(-a,cy+a).close().val()
    return (wire.threePointArc(mid,end)
            .threePointArc((0,apex_z),(-end[0],end[1]))
            .threePointArc((-mid[0],mid[1]),(-a,cy+a)).close().val())


def channel(p):
    total=p.radius_mm*math.pi/2
    stations=[]
    for i in range(N_STATIONS+1):
        distance=total*i/N_STATIONS
        val=blend(min(distance,total-distance),p)
        stations.append(section(-90+90*i/N_STATIONS,val,p))
    return cq.Solid.makeLoft(stations,ruled=True)


def build_unmarked(p):
    fit=replace(brick_from_fit("duplo-e27-play-v1",nx=4,ny=4,height_units=2),
                tube_radius=6.60)
    body=(cq.Workplane("XY")
          .box(fit.width,fit.depth,fit.height,centered=(True,True,False))
          .edges("|Z").fillet(ROUNDED_EDGES.corner_radius)
          .edges(">Z").fillet(ROUNDED_EDGES.corner_radius))
    shell=receiver(fit,body,p.cavity_height,ROUNDED_EDGES.receiver_entry)
    shell=shell.cut(channel(p))
    studs=make_studs(fit.studs(),fit.height,fit.stud_radius-fit.clearance,
                     fit.stud_inner_radius,fit.stud_height,
                     ROUNDED_EDGES.stud_lip_radius)
    result=shell.union(studs).val().clean()
    result=add_e31_05_receiver_features(
        result,fit.tubes(),fit.tube_radius,receiver_depth=p.cavity_height)
    if not result.isValid() or len(result.Solids())!=1:
        raise ValueError("R48 roofed geometry must be one solid")
    return result,fit


def build_course(model_id,recipe,*,marked=True):
    p=RoofSettings.parse(recipe)
    shape,fit=build_unmarked(p)
    if p.direction=="left":
        shape=shape.mirror("XZ")
    if marked:
        x=0 if p.direction=="right" else -17
        shape=engrave(shape,model_id,x=x,y=-fit.depth/2,z=12)
    return shape,fit


def _strip(stl):
    raw=stl.read_bytes()
    n=struct.unpack_from("<I",raw,80)[0]
    if n<1 or len(raw)!=84+50*n:
        raise ValueError("Invalid STL")
    kept=[]
    for i in range(n):
        facet=raw[84+50*i:134+50*i]
        vertices=struct.unpack("<12fH",facet)[3:12]
        if len({tuple(vertices[j:j+3]) for j in (0,3,6)})==3:
            kept.append(facet)
    if len(kept)!=n:
        stl.write_bytes(raw[:80]+struct.pack("<I",len(kept))+b"".join(kept))


def export_course(model_id,recipe,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    shape,fit=build_course(model_id,recipe)
    if not shape.isValid() or len(shape.Solids())!=1:
        raise ValueError("Invalid configured E31 R48 BRep")
    stl=out/"brick.stl"
    cq.exporters.export(shape,str(stl),tolerance=.01,angularTolerance=.1)
    _strip(stl)
    cq.exporters.export(shape,str(out/"brick.step"))
    m=mesh_check(stl)
    checks={"valid_single_solid":shape.isValid() and len(shape.Solids())==1,
            "watertight":m["passed"],
            "mesh_volume":abs(m["signed_volume_mm3"]-shape.Volume())/shape.Volume()<.001}
    report={"part_id":model_id,"passed":all(checks.values()),"checks":checks,
            "mesh":m,"geometry":{"bounds_mm":exact_bounds(shape),
                                 "volume_mm3":shape.Volume()},
            "source_engine":"brickcad.course_r48_tunnel",
            "physical_fit_validated":False,"physical_rolling_validated":False,
            "slicing_validated":False}
    (out/"report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
    (out/"course-manifest.json").write_text(json.dumps({
        "schema_version":1,"model_id":model_id,"source_engine":"brickcad.course_r48_tunnel",
        "mode":"independent_configured_geometry","recipe":recipe,
        "stl_sha256":hashlib.sha256(stl.read_bytes()).hexdigest(),
        "geometry_verified":report["passed"],"slicing_validated":False,
        "physical_fit_validated":False},indent=2,ensure_ascii=False)+"\n")
    if not report["passed"]:
        raise ValueError("E31 R48 tunnel CAD validation failed: "+str(checks))
    return report
