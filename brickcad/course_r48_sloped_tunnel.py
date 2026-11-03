"""Shared sloped R48 tunnel kernel with clipped supports and shaped roof.

This reconstructs the native SC02/SC02L geometry from common primitives
rather than importing parts.sloped_curve.design or any old exporter.
"""
from dataclasses import replace
from pathlib import Path
import hashlib
import json
import math
import struct
import cadquery as cq

from brickcad.standards import BALL_TRACK,DUPLO
from brickcad.model import brick_from_fit
from brickcad.connections import make_receiver,make_studs
from brickcad.marking import engrave_west
from brickcad.verify import mesh_check,exact_bounds
from parts.tunnel.e31_fit import add_e31_05_receiver_features

RADIUS=48.
DROP=19.2
FULL_TUBES=((-16.,-16.),(0.,0.),(16.,16.))
CLIPPED_TUBES=((0.,-16.),(-16.,0.),(16.,0.),(0.,16.))
TOP_Z=57.6
STUD_OVERLAP=.15
CAVITY_DEPTH=BALL_TRACK.floor-DUPLO.roof
WIDTH=BALL_TRACK.width
HEIGHT=BALL_TRACK.height
FLOOR=BALL_TRACK.floor
OPENING=BALL_TRACK.opening
CHANNEL_RADIUS=BALL_TRACK.radius


def spec(recipe):
    if (not isinstance(recipe,dict) or set(recipe)!={"direction","drop_mm",
          "roof_top_mm","lip_mm","transition_mm"}
          or recipe["direction"] not in ("right","left")
          or recipe["drop_mm"]!=19.2 or recipe["roof_top_mm"]!=57.6
          or recipe["lip_mm"]!=1 or recipe["transition_mm"]!=4):
        raise ValueError("Unsupported R48 sloped tunnel geometry")
    return recipe


def height(t):
    return DROP*(1-3*t*t+2*t*t*t)


def _position(w,t):
    return (w.rotate((0,0,0),(0,0,1),-90+90*t).translate((-32,32,0)))


def section(t):
    floor=FLOOR+height(t)
    top=HEIGHT+height(t)
    half=WIDTH/2
    w=(cq.Workplane("XZ").moveTo(RADIUS-half,FLOOR-.1)
       .lineTo(RADIUS+half,FLOOR-.1)
       .lineTo(RADIUS+half,top)
       .lineTo(RADIUS+OPENING/2,top)
       .threePointArc((RADIUS,floor),(RADIUS-OPENING/2,top))
       .lineTo(RADIUS-half,top).close().val())
    corners=[v for v in w.Vertices() if v.Center().z>top-.01]
    w=w.fillet2D(.5,corners)
    return _position(w,t)


def curved_footprint():
    return (cq.Workplane("XZ").moveTo(RADIUS-WIDTH/2,0)
            .lineTo(63.9,0).lineTo(63.9,60)
            .lineTo(RADIUS-WIDTH/2,60).close()
            .revolve(90,(0,0),(0,1)).val()
            .rotate((0,0,0),(0,0,1),-90).translate((-32,32,0)))


def cut_receiver_edges(shape):
    edges=[]
    for e in shape.Edges():
        box=e.BoundingBox()
        c=e.Center()
        radius=math.hypot(c.x+32,c.y-32)
        if (e.geomType()=="LINE" and box.zlen>4.4 and
                box.zmax<CAVITY_DEPTH+1e-5
                and box.xlen<1e-5 and box.ylen<1e-5
                and min(abs(radius-(RADIUS-WIDTH/2)),abs(radius-63.9))<1e-4):
            edges.append(e)
    return edges


def open_curve():
    p=replace(brick_from_fit("duplo-e27-play-v1",nx=4,ny=4,
              height=HEIGHT+DROP),tube_radius=6.60)
    base=cq.Workplane("XY").box(p.width,p.depth,FLOOR,centered=(True,True,False))
    base=base.edges("|Z").fillet(.8).edges(">Z").fillet(.5)
    base=make_receiver(base,FULL_TUBES,p.cavity_xy,CAVITY_DEPTH,
                       p.tube_radius,p.tube_inner_radius,0)
    swept=cq.Solid.makeLoft([section(i/24) for i in range(25)],ruled=False)
    footprint=cq.Workplane("XY").box(
        p.width,p.depth,60,centered=(True,True,False)).val()
    shape=base.union(swept.intersect(footprint)).val().intersect(curved_footprint()).clean()
    corners=cut_receiver_edges(shape)
    if len(corners)!=4:
        raise ValueError("Expected four curved receiver wall ends")
    shape=shape.fillet(.5,corners).clean()
    bottom=[e for e in shape.Edges() if
            abs(e.BoundingBox().zmin)<1e-5 and
            abs(e.BoundingBox().zmax)<1e-5]
    shape=shape.fillet(.5,bottom).clean()
    # The original tunnel assembly generated the open foundation with a
    # temporary ID before enclosing it; the cover subsequently fills this.
    shape=engrave_west(shape,"SC02-V12",x=-p.width/2,y=-16,z=12)
    return shape,p


def _zshift(t):
    return height(min(1.,max(0.,t)))


def _blend(t,p):
    distance=min(t,1-t)*RADIUS*math.pi/2
    u=max(0.,min(1.,(distance-p["lip_mm"])/p["transition_mm"]))
    return min(.995,u*u*(3-2*u))


def _outer_wire(t):
    base=FLOOR-.75
    wire=cq.Workplane("XZ").polyline([
        (RADIUS-WIDTH/2,base),(RADIUS+WIDTH/2,base),
        (RADIUS+WIDTH/2,TOP_Z),(RADIUS-WIDTH/2,TOP_Z)
    ]).close().val()
    return _position(wire,t)


def _passage_wire(t,p):
    floor=FLOOR+_zshift(t)
    radius=CHANNEL_RADIUS
    cy=floor+radius
    a=radius/math.sqrt(2)
    roof=floor+30.30
    b=cy+math.sqrt(2)*radius-roof
    progress=_blend(t,p)
    def mix(circle,pointed):
        return circle*(1-progress)+pointed*progress
    end=(mix(radius*math.cos(math.radians(75)),b),
         mix(cy+radius*math.sin(math.radians(75)),roof))
    mid=(mix(.5*radius,(a+b)/2),
         mix(cy+radius*math.sqrt(3)/2,(cy+a+roof)/2))
    apex=(0,mix(cy+radius,roof))
    wire=(cq.Workplane("XZ").moveTo(RADIUS-a,cy+a)
          .threePointArc((RADIUS,floor),(RADIUS+a,cy+a))
          .threePointArc((RADIUS+mid[0],mid[1]),(RADIUS+end[0],end[1]))
          .threePointArc((RADIUS+apex[0],apex[1]),(RADIUS-end[0],end[1]))
          .threePointArc((RADIUS-mid[0],mid[1]),(RADIUS-a,cy+a))
          .close().val())
    return _position(wire,t)


def stations():
    dt=1./(RADIUS*math.pi/2)
    items=[-.02,0.,dt,2*dt,3*dt,4*dt,5*dt]
    items += [i/32 for i in range(1,32)]
    items += [1-5*dt,1-4*dt,1-3*dt,1-2*dt,1-dt,1.,1.02]
    return sorted(set(round(x,7) for x in items))


def make_cover(p):
    ts=stations()
    outer=cq.Solid.makeLoft([_outer_wire(t) for t in ts],ruled=True)
    passage=cq.Solid.makeLoft([_passage_wire(t,p) for t in ts],ruled=True)
    clip=cq.Workplane("XY").box(63.8,63.8,90,centered=(True,True,False)).val()
    return outer.intersect(clip).intersect(curved_footprint()).clean(),passage


def clipped_receivers(shape,p):
    clip=curved_footprint()
    for x,y in CLIPPED_TUBES:
        ring=(cq.Workplane("XY",origin=(x,y,0))
              .circle(p.tube_radius).circle(p.tube_inner_radius)
              .extrude(CAVITY_DEPTH+.25).val())
        partial=ring.intersect(clip)
        if not partial.Solids() or partial.Volume()<20:
            raise ValueError("Unsupported clipped receiver sliver")
        shape=shape.fuse(partial).clean()
    return shape


def roof_studs(shape,p):
    studs=make_studs(p.studs(),TOP_Z-STUD_OVERLAP,
                     p.stud_radius-p.clearance,p.stud_inner_radius,
                     p.stud_height+STUD_OVERLAP,lip_radius=.5).val()
    clipped=studs.intersect(curved_footprint().translate((0,0,p.stud_height+1.)))
    if not clipped.Solids():
        raise ValueError("No clipped studs remain")
    return shape.fuse(clipped).clean()


def build_course(model_id,recipe,*,marked=True):
    pset=spec(recipe)
    base,p=open_curve()
    cover,passage=make_cover(pset)
    shape=base.fuse(cover).cut(passage).clean()
    shape=clipped_receivers(shape,p)
    shape=add_e31_05_receiver_features(shape,FULL_TUBES,p.tube_radius,
                                        receiver_depth=CAVITY_DEPTH)
    shape=roof_studs(shape,p)
    if pset["direction"]=="left":
        shape=shape.mirror("XZ")
    if marked:
        shape=engrave_west(shape,model_id,x=-p.width/2,
              y=-16 if pset["direction"]=="right" else 16,z=12,size=3,depth=.4)
    if not shape.isValid() or len(shape.Solids())!=1:
        raise ValueError("Configured sloped R48 tunnel must be one solid")
    return shape,p


def _strip(stl):
    raw=stl.read_bytes()
    n=struct.unpack_from("<I",raw,80)[0]
    if n<1 or len(raw)!=84+50*n:
        raise ValueError("Malformed binary STL")
    kept=[]
    for i in range(n):
        facet=raw[84+50*i:134+50*i]
        vs=struct.unpack("<12fH",facet)[3:12]
        if len({tuple(vs[j:j+3]) for j in (0,3,6)})==3:
            kept.append(facet)
    if len(kept)!=n:
        stl.write_bytes(raw[:80]+struct.pack("<I",len(kept))+b"".join(kept))


def export_course(model_id,recipe,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    shape,p=build_course(model_id,recipe)
    stl=out/"brick.stl"
    # Intermediate tessellation passes both manifold and volume checks: .01/.10
    # was nonmanifold and PR40's .03/.20 exceeded the mesh-volume tolerance.
    # This changes only STL sampling, never the independently tested BRep.
    cq.exporters.export(shape,str(stl),tolerance=.02,angularTolerance=.15)
    _strip(stl)
    cq.exporters.export(shape,str(out/"brick.step"))
    m=mesh_check(stl)
    checks={"valid_solid":shape.isValid() and len(shape.Solids())==1,
            "watertight_mesh":m["passed"],
            "mesh_volume":abs(m["signed_volume_mm3"]-shape.Volume())/
                          shape.Volume()<.001}
    report={"part_id":model_id,"passed":all(checks.values()),"checks":checks,
            "mesh":m,"geometry":{"bounds_mm":exact_bounds(shape),
                                 "volume_mm3":shape.Volume()},
            "source_engine":"brickcad.course_r48_sloped_tunnel",
            "physical_fit_validated":False,"physical_rolling_validated":False,
            "slicing_validated":False}
    (out/"report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
    (out/"course-manifest.json").write_text(json.dumps({
        "schema_version":1,"mode":"independent_configured_geometry",
        "model_id":model_id,"recipe":recipe,
        "source_engine":"brickcad.course_r48_sloped_tunnel",
        "geometry_verified":report["passed"],
        "stl_sha256":hashlib.sha256(stl.read_bytes()).hexdigest(),
        "physical_fit_validated":False,"slicing_validated":False},
        ensure_ascii=False,indent=2)+"\n")
    if not report["passed"]:
        raise ValueError("Sloped R48 tunnel CAD check failed: "+str(checks)+" mesh="+str(m)+" brep_volume_mm3="+str(shape.Volume())+" relative_mesh_volume_delta="+str(abs(m["signed_volume_mm3"]-shape.Volume())/shape.Volume()))
    return report
