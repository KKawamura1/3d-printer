from brickcad.course_contract import course_fit
from brickcad.course_contract import add_course_receiver_features as add_e31_05_receiver_features
from brickcad.course_contract import engrave_course as engrave
"""PR #36 R16 curve reconstructed from shared route and roofed shell primitives.

C01-V6 and C02-V8 remain on an unmerged branch. This independent adapter
retains their exact quarter-torus, mirror direction and optional spherical
roof relief; parity against the pinned PR commit is tested independently.
"""
from dataclasses import asdict, dataclass, replace
from pathlib import Path
import hashlib
import json
import math
import struct
import cadquery as cq

from brickcad.connections import make_studs
from brickcad.model import receiver
from brickcad.ports import Port
from brickcad.standards import BALL_TRACK, DUPLO, ROUNDED_EDGES
from brickcad.verify import exact_bounds, intersection, mesh_check, VOLUME_TOL
from parts.tunnel.e31_fit import (SLOT_END_Z, SLOT_END_RADIUS)



@dataclass(frozen=True)
class SharpPath:
    turn_radius: float = DUPLO.pitch
    floor: float = BALL_TRACK.floor
    section_radius: float = BALL_TRACK.radius
    ball_diameter: float = BALL_TRACK.ball_diameter
    receiver_depth: float = 4.75
    numerical_lift: float = 0.05


ROOF_DOME_RADIUS = 10.5
ROOF_DOME_CENTER_Z = 24.5


def ports(path=SharpPath()):
    return (
        Port("west",(-16.,0.,path.floor),(-1.,0.,0.),path.section_radius),
        Port("south",(0.,-16.,path.floor),(0.,-1.,0.),path.section_radius),
    )


def ball_position(degrees,path=SharpPath(),diameter=None):
    a=math.radians(degrees)
    dia=path.ball_diameter if diameter is None else diameter
    return cq.Vector(-16+path.turn_radius*math.cos(a),
                     -16+path.turn_radius*math.sin(a),
                     path.floor+dia/2+path.numerical_lift)


def ball_intersections(shape,path=SharpPath(),*,diameter=None,samples=19):
    d=path.ball_diameter if diameter is None else diameter
    if samples<2 or d<=0:
        raise ValueError("Invalid sphere path sampling")
    return [intersection(shape,cq.Solid.makeSphere(
        d/2,ball_position(90*i/(samples-1),path,d),angleDegrees1=-90))
            for i in range(samples)]


def _torus_cut(path):
    # Preserve the exact C01/C02 R16 quarter-circle cutter:
    # tangent cylinders produced non-manifold STL seams.
    torus=(cq.Workplane("XZ")
           .moveTo(path.turn_radius,path.floor+path.section_radius)
           .circle(path.section_radius)
           .revolve(90,(0,0),(0,1)).val()
           .rotate((0,0,0),(0,0,1),-90)
           .translate((-16,16,0)))
    return torus


def _mark_north(shape, label, width, kind):
    """Use standard upright 3mm text on the finished north wall."""
    z = 11.5 if kind == "open" else 18.0
    turned = shape.rotate((0, 0, 0), (0, 0, 1), 180)
    marked = engrave(turned, label, x=0., y=-width/2, z=z)
    return marked.rotate((0, 0, 0), (0, 0, 1), -180)

def build_course(spec, *, reference_label=None, mark=True):
    path=SharpPath()
    if abs(path.turn_radius-16)>1e-6 or path.section_radius>=14.4:
        raise ValueError("Unsupported R16 cut radius/wall")
    if path.floor-path.receiver_depth<1.6-1e-6:
        raise ValueError("Receiver leaves less than 1.6 mm floor")
    kind=spec["enclosure"]["kind"]
    height_units=1 if kind=="open" else 2
    p=course_fit(nx=2,ny=2,height_units=height_units)
    outer=(cq.Workplane("XY")
           .box(p.width,p.depth,p.height,centered=(True,True,False))
           .edges("|Z").fillet(ROUNDED_EDGES.corner_radius)
           .edges(">Z").fillet(.5))
    body=receiver(p,outer,path.receiver_depth,0).val()
    body=add_e31_05_receiver_features(body,p.tubes(),p.tube_radius,
                                      receiver_depth=path.receiver_depth)
    # The receiver intersects the R16 cut first; leftover tube/support is
    # geometrically clipped, never replaced by detached uncut full supports.
    body=body.cut(_torus_cut(path)).clean().mirror("XZ")
    if kind=="tunnel":
        mid=-16+path.turn_radius/math.sqrt(2)
        dome=cq.Solid.makeSphere(
            ROOF_DOME_RADIUS,cq.Vector(mid,mid,ROOF_DOME_CENTER_Z),
            angleDegrees1=-90)
        body=body.cut(dome).clean()
        # C02 has a full, load-bearing square roof: four studs are supported.
        studs=make_studs(p.studs(),p.height,p.stud_radius,
                         p.stud_inner_radius,p.stud_height,
                         ROUNDED_EDGES.stud_lip_radius).val()
        body=body.fuse(studs).clean()
    # C01 open course: NO top studs, even on the remaining corner.
    if not body.isValid() or len(body.Solids())!=1:
        raise ValueError("Sharp curve must be one valid connected solid")
    if not mark:
        return body,p,path
    label=reference_label or (spec["id"]+"-"+spec["version"])
    return _mark_north(body,label,p.depth,kind),p,path


def checks(shape,p,path,kind):
    nominal=ball_intersections(shape,path,samples=19)
    oversize=ball_intersections(shape,path,diameter=28.,samples=5)
    bounds=exact_bounds(shape)
    height=19.2 if kind=="open" else 42.9
    mid=-16+path.turn_radius/math.sqrt(2)
    c={
        "single_valid_solid":shape.isValid() and len(shape.Solids())==1,
        "2x2_footprint_and_height":all(abs(a-b)<1e-5 for a,b in
                                        zip(bounds,(31.8,31.8,height))),
        "ball_path_clear":max(nominal)<VOLUME_TOL,
        "oversized_ball_blocked":max(oversize)>VOLUME_TOL,
        "receiver_bore_open":not shape.isInside(cq.Vector(0,0,1)),
        "receiver_wall":shape.isInside(cq.Vector(4,4,1)),
        "e31_short_slots_leave_roof": (
            abs(SLOT_END_Z - 3.50) < 1e-6 and
            path.receiver_depth - SLOT_END_Z - SLOT_END_RADIUS >= .60 - 1e-6),
        "remaining_curve_floor":shape.isInside(cq.Vector(mid,mid,path.floor-.15)),
        "west_to_south_ports":(
            ports(path)[0].floor_xyz_mm==(-16.,0.,path.floor)
            and ports(path)[1].floor_xyz_mm==(0.,-16.,path.floor)),
    }
    if kind=="open":
        c["all_top_studs_omitted"]=all(not shape.isInside(
            cq.Vector(x,y,p.height+1)) for x,y in p.studs())
    else:
        c.update({
            "four_roof_studs_supported":all(shape.isInside(
                cq.Vector(x,y,p.height-.1)) for x,y in p.studs()),
            "four_roof_studs_hollow":all(not shape.isInside(
                cq.Vector(x,y,p.height+2)) for x,y in p.studs()),
            "four_roof_studs_have_walls":all(shape.isInside(
                cq.Vector(x+4,y,p.height+2)) for x,y in p.studs()),
            "roof_above_relief":shape.isInside(cq.Vector(mid,mid,36.)),
            "relief_open_at_bend":not shape.isInside(cq.Vector(mid,mid,34.)),
            # These two pockets became empty in C02-V4 and trapped the ball:
            "inner_wall_north_retained":shape.isInside(cq.Vector(0,12.5,20)),
            "inner_wall_east_retained":shape.isInside(cq.Vector(12.5,0,20)),
            "visible_round_mouths":all(
                shape.isInside(cq.Vector(*xyz)) == solid
                for angle in range(0, 360, 30)
                for radius, solid in ((path.section_radius-.45,False),
                                      (path.section_radius+.45,True))
                for xyz in (
                    (-15.8,radius*math.cos(math.radians(angle)),
                     path.floor+path.section_radius+radius*math.sin(math.radians(angle))),
                    (radius*math.cos(math.radians(angle)),-15.8,
                     path.floor+path.section_radius+radius*math.sin(math.radians(angle)))
                )
            ),
            "minimum_roof":p.height-max(
                path.floor+2*path.section_radius,
                ROOF_DOME_CENTER_Z+ROOF_DOME_RADIUS)>=DUPLO.roof,
        })
    return c,nominal,oversize,bounds


def _normalize_stl(stl):
    raw=stl.read_bytes()
    if len(raw)<84 or len(raw)!=84+50*struct.unpack_from("<I",raw,80)[0]:
        raise ValueError("Malformed binary STL")
    kept=[]
    for i in range(struct.unpack_from("<I",raw,80)[0]):
        tri=raw[84+50*i:134+50*i]
        v=struct.unpack("<12fH",tri)[3:12]
        if len({tuple(v[j:j+3]) for j in (0,3,6)})==3:
            kept.append(tri)
    if len(kept)<struct.unpack_from("<I",raw,80)[0]:
        stl.write_bytes(raw[:80]+struct.pack("<I",len(kept))+b"".join(kept))


def export_course(spec,out):
    out=Path(out)
    out.mkdir(parents=True,exist_ok=True)
    shape,p,path=build_course(spec)
    kind=spec["enclosure"]["kind"]
    valid,nominal,oversize,bounds=checks(shape,p,path,kind)
    stl=out/"brick.stl"
    cq.exporters.export(shape,str(stl),tolerance=.01,angularTolerance=.1)
    _normalize_stl(stl)
    cq.exporters.export(shape,str(out/"brick.step"))
    mesh=mesh_check(stl)
    valid["watertight_mesh"]=mesh["passed"]
    valid["mesh_volume"]=abs(
        mesh["signed_volume_mm3"]-shape.Volume())/shape.Volume()<.001
    report={
        "part_id":spec["id"]+"-"+spec["version"],"passed":all(valid.values()),
        "schema_version":2,"kind":"configured_R16_"+kind,
        "checks":valid,"geometry":{
            "bounds_mm":bounds,"volume_mm3":shape.Volume(),
            "fit_profile_id":p.fit_profile_id,
            "parameters":asdict(p),
        },
        "ports":[asdict(port) for port in ports(path)],
        "stud_count":0 if kind=="open" else 4,
        "fit_profile":"E31-05","fit_physical_validated":False,
        "ball_samples_mm3":nominal,
        "oversized_ball_samples_mm3":oversize,
        "mesh":mesh,"sha256_stl":hashlib.sha256(stl.read_bytes()).hexdigest(),
        "e31_05":{"receiver_depth_mm":path.receiver_depth,"slot_end_z_mm":SLOT_END_Z},
        "physical_rolling_validated":False,"slicing_validated":False,
        "pr55_stage1_print_assumed_success":False,
        "pr55_stage1_print_report_received":False,
        "limitations":[
            "Old PR55 prints do not validate this newly revised prototype.",
            "C02-V4 wide turning chamber and C02R-V1 head-on impact rejected.",
            "R16 C02-V8 internal burrs may require post-print inspection.",
            "Finite sphere samples and mesh cannot prove reliable natural rolling.",
        ],
    }
    (out/"report.json").write_text(json.dumps(
        report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if not report["passed"]:
        raise RuntimeError("Sharp curve CAD checks failed: "+
                           ",".join(k for k,v in valid.items() if not v))
    return report
