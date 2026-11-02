"""Configured roofed steep-drop assembly sharing east/south outlet geometry.

Reference principles: PR #38 S01-V5 / PR #41 S02-V8. These sources are on
unmerged branches, so this adapter contains the independently implemented
common primitives; exact cross-branch BRep equality is NOT claimed.
"""
from dataclasses import asdict, dataclass, replace
import hashlib
import json
import math
import struct
from pathlib import Path

import cadquery as cq

from brickcad.connections import make_studs
from brickcad.marking import engrave
from brickcad.model import brick_from_fit, receiver
from brickcad.ports import Port
from brickcad.standards import BALL_TRACK, DUPLO, ROUNDED_EDGES
from brickcad.verify import VOLUME_TOL, exact_bounds, intersection, mesh_check
from parts.tunnel.e31_fit import add_e31_05_receiver_features


@dataclass(frozen=True)
class DropGeometry:
    low_floor: float = BALL_TRACK.floor
    drop: float = DUPLO.height
    radius: float = BALL_TRACK.radius
    shaft_radius: float = 13.15
    receiver_depth: float = 4.75
    roof_thickness: float = 1.8
    taper_start_offset: float = 5.0
    ramp_grade: float = .65
    ramp_start: float = -15.0
    ramp_end: float = 13.0

    @property
    def low_center(self):
        return self.low_floor + self.radius

    @property
    def high_center(self):
        return self.low_center + self.drop


def position(exit_direction, longitudinal, z):
    return cq.Vector(longitudinal, 0, z) if exit_direction == "east" else (
        cq.Vector(0, -longitudinal, z))


def exit_parameters(direction):
    if direction not in ("east", "south"):
        raise ValueError("Unimplemented drop exit direction")
    return -2.0 if direction == "east" else 0.0


def ball_centres(direction, d=DropGeometry()):
    shaft_u = exit_parameters(direction)
    lift = (BALL_TRACK.ball_diameter/2 * (math.sqrt(1+d.ramp_grade**2)-1))
    landing_z = d.low_center + d.ramp_grade*(d.ramp_end-shaft_u) + lift
    return (
        cq.Vector(-16,0,d.high_center),
        position(direction,shaft_u,d.high_center),
        position(direction,shaft_u,landing_z),
        position(direction,d.ramp_end,d.low_center+lift),
        position(direction,16,d.low_center),
    )


def ports(direction, d=DropGeometry()):
    low = (16,0,d.low_floor) if direction == "east" else (0,-16,d.low_floor)
    outward = (1,0,0) if direction == "east" else (0,-1,0)
    return (
        Port("high_west",(-16,0,d.low_floor+d.drop),(-1,0,0),d.radius),
        Port("low_"+direction,low,outward,d.radius),
    )


def _north_engrave(shape, label, width):
    plane = cq.Plane(origin=(0.,width/2-.4,18.),
                     xDir=(-1,0,0),normal=(0,1,0))
    cutter = cq.Workplane(plane).text(
        label,2.7,.45,font="DejaVu Sans",kind="bold",combine=False).val()
    result = shape.cut(cutter).clean()
    if not result.isValid() or len(result.Solids()) != 1:
        raise ValueError("Engraving broke steep-turn solid")
    if shape.Volume()-result.Volume() < .2:
        raise ValueError("Steep-turn revision has no visible engraving")
    return result


def build_course(spec):
    direction = spec["geometry"]["exit"]
    d = DropGeometry()
    shaft_u = exit_parameters(direction)
    if d.shaft_radius <= BALL_TRACK.ball_diameter/2 or d.shaft_radius >= 15.9-1.6:
        raise ValueError("Vertical shaft has insufficient ball clearance or wall")
    if d.low_floor-d.receiver_depth < 1.6:
        raise ValueError("Underside receiver must retain 1.6 mm floor")
    if not 0 < d.ramp_grade <= .7:
        raise ValueError("Unsafe ramp grade")
    if not d.ramp_start < shaft_u < d.ramp_end:
        raise ValueError("Shaft and ramp are out of order")
    if d.ramp_grade*(d.ramp_end-d.ramp_start) > d.drop-1.+1e-9:
        raise ValueError("Ramp blocks upper inlet floor")
    p = replace(brick_from_fit("duplo-e27-play-v1",nx=2,ny=2,height_units=3),
                tube_radius=6.60)
    cap_start = d.high_center+d.taper_start_offset
    cap_tip = p.height-d.roof_thickness
    if not d.high_center < cap_start < cap_tip:
        raise ValueError("Cone roof geometry is invalid")
    if cap_tip-(d.high_center+d.radius) < 1.5 or d.roof_thickness < 1.6:
        raise ValueError("Insufficient inner clearance or roof")

    outer = (cq.Workplane("XY")
             .box(p.width,p.depth,p.height,centered=(True,True,False))
             .edges("|Z").fillet(ROUNDED_EDGES.corner_radius)
             .edges(">Z").chamfer(.5))
    body = receiver(p,outer,d.receiver_depth,ROUNDED_EDGES.receiver_entry).val()
    shaft_pt = position(direction,shaft_u,d.low_floor)
    shaft = cq.Solid.makeCylinder(
        d.shaft_radius, cap_start-d.low_floor,shaft_pt,cq.Vector(0,0,1))
    cone = cq.Solid.makeCone(
        d.shaft_radius,0.,cap_tip-cap_start,
        position(direction,shaft_u,cap_start),cq.Vector(0,0,1))
    high = cq.Solid.makeCylinder(
        d.radius,18.,cq.Vector(-18.,0,d.high_center),cq.Vector(1,0,0))
    if direction == "east":
        low = cq.Solid.makeCylinder(
            d.radius,21.,position(direction,shaft_u,d.low_center),
            cq.Vector(1,0,0))
    else:
        low = cq.Solid.makeCylinder(
            d.radius,18.,cq.Vector(0,-18.,d.low_center),cq.Vector(0,1,0))
    path = ball_centres(direction,d)
    start,end = path[2],path[3]
    dv = end.sub(start)
    slope_cut = cq.Solid.makeCylinder(d.radius,dv.Length,start,dv.normalized())
    shape = (body.cut(shaft).cut(cone).cut(high)
             .cut(low).cut(slope_cut).clean())

    # Build same 1:1.54 ramp for both directions, then rotate toward south.
    ramp = (cq.Workplane("XZ")
            .polyline(((d.ramp_start,d.low_floor-.2),
                       (d.ramp_end,d.low_floor-.2),
                       (d.ramp_end,d.low_floor),
                       (d.ramp_start,d.low_floor+
                        d.ramp_grade*(d.ramp_end-d.ramp_start))))
            .close().extrude(14.,both=True).val())
    if direction == "south":
        ramp = ramp.rotate((0,0,0),(0,0,1),-90)
    shape = shape.fuse(ramp).clean()
    # Full 2x2 rectangular envelope (not a partial/curved perimeter).
    # Nonrectangular future adapters MUST clip studs and receiver to footprint.
    shape = add_e31_05_receiver_features(shape,p.tubes(),p.tube_radius)
    studs = make_studs(
        p.studs(),p.height,p.stud_radius-p.clearance,
        p.stud_inner_radius,p.stud_height,
        lip_radius=ROUNDED_EDGES.stud_lip_radius).val()
    shape = shape.fuse(studs).clean()
    if not shape.isValid() or len(shape.Solids()) != 1:
        raise ValueError("Steep-drop result must be one valid solid")

    label = spec["id"]+"-"+spec["version"]
    if direction == "east":
        shape = engrave(shape,label,x=0.,y=-p.depth/2,z=12.)
    else:
        shape = _north_engrave(shape,label,p.depth)
    return shape,p,d


def collision_checks(shape,direction,d):
    points = ball_centres(direction,d)
    r = BALL_TRACK.ball_diameter/2
    samples,sweeps = [],[]
    for start,end in zip(points,points[1:]):
        delta = end.sub(start)
        for i in range(13):
            c = start.add(delta.multiply(i/12))
            samples.append(intersection(shape,cq.Solid.makeSphere(
                r,c,angleDegrees1=-90)))
        sweeps.append(intersection(shape,cq.Solid.makeCylinder(
            r,delta.Length,start,delta.normalized())))
        sweeps.append(intersection(shape,cq.Solid.makeSphere(
            r,start,angleDegrees1=-90)))
    sweeps.append(intersection(shape,cq.Solid.makeSphere(
        r,points[-1],angleDegrees1=-90)))
    return samples,sweeps


def geometry_checks(shape,p,d,direction):
    samples,sweeps=collision_checks(shape,direction,d)
    bounds=exact_bounds(shape)
    shaft_u=exit_parameters(direction)
    shaft_pt=position(direction,shaft_u,p.height-.1)
    checks={
        "valid_connected_brep":shape.isValid() and len(shape.Solids())==1,
        "bounds_2x2x3":all(abs(a-b)<.01 for a,b in
                          zip(bounds,(31.8,31.8,p.height+p.stud_height))),
        "ball_samples_clear":max(samples)<VOLUME_TOL,
        "ball_capsule_segments_clear":max(sweeps)<VOLUME_TOL,
        "tapered_roof_closed":shape.isInside(shaft_pt),
        "receiver_bore_open":not shape.isInside(cq.Vector(0,0,1)),
        "receiver_wall":shape.isInside(cq.Vector(3.89,3.89,1)),
        "lower_floor_present":shape.isInside(cq.Vector(0,0,6.2)),
        "four_stud_walls":all(shape.isInside(cq.Vector(x+3.9,y,p.height+1))
                               for x,y in p.studs()),
        "ramp_floor_below_inlet":d.drop-d.ramp_grade*
                              (d.ramp_end-d.ramp_start) >= 1-1e-8,
        "ramp_outlet_clear":not shape.isInside(
            position(direction,d.ramp_end,d.low_floor+.2)),
        "one_course_between_ports":abs(
            ports(direction,d)[0].floor_xyz_mm[2]-
            ports(direction,d)[1].floor_xyz_mm[2]-DUPLO.height)<1e-6,
    }
    if direction == "south":
        checks["lower_west_closed"]=shape.isInside(
            cq.Vector(-15.7,0,d.low_center))
    return checks,samples,sweeps,bounds


def _strip_collapsed_facets(stl):
    raw=stl.read_bytes()
    if len(raw)<84 or len(raw)!=84+struct.unpack_from("<I",raw,80)[0]*50:
        raise ValueError("Invalid binary STL")
    retained=[]
    for i in range(struct.unpack_from("<I",raw,80)[0]):
        tri=raw[84+50*i:134+50*i]
        v=struct.unpack("<12fH",tri)[3:12]
        if len({tuple(v[j:j+3]) for j in (0,3,6)})==3:
            retained.append(tri)
    stl.write_bytes(raw[:80]+struct.pack("<I",len(retained))+b"".join(retained))


def export_course(spec,out):
    out=Path(out)
    out.mkdir(parents=True,exist_ok=True)
    shape,p,d=build_course(spec)
    direction=spec["geometry"]["exit"]
    checks,samples,sweeps,bounds=geometry_checks(shape,p,d,direction)
    stl=out/"brick.stl"
    cq.exporters.export(shape,str(stl),tolerance=.03,angularTolerance=.2)
    _strip_collapsed_facets(stl)
    cq.exporters.export(shape,str(out/"brick.step"))
    mesh=mesh_check(stl)
    checks["mesh_watertight"]=mesh["passed"]
    report={
        "part_id":spec["id"]+"-"+spec["version"],
        "passed":all(checks.values()),"checks":checks,
        "bounds_mm":bounds,"parameters":asdict(d),
        "ports":[asdict(port) for port in ports(direction,d)],
        "exit_direction":direction,
        "ramp_angle_deg":math.degrees(math.atan(d.ramp_grade)),
        "landing_to_exit_ramp_drop_mm":
            d.ramp_grade*(d.ramp_end-exit_parameters(direction)),
        "centreline_points_mm":[v.toTuple() for v in ball_centres(direction,d)],
        "ball_samples_mm3":samples,"ball_sweep_mm3":sweeps,
        "e31_05":{"tube_od_mm":13.2,"split_slots":4,
                  "physical_fit_validated":False},
        "mesh":mesh,"sha256_stl":hashlib.sha256(stl.read_bytes()).hexdigest(),
        "physical_fit_validated":False,"physical_rolling_validated":False,
        "slicing_validated":False,
        "limitations":[
            "Geometric sphere/capsule path is not proof of natural ball rolling.",
            "Roof overhang and E31-05 fit still need real slicing/printing.",
            "Reference PRs #38/#41 are on independent unmerged branches."
        ],
    }
    (out/"report.json").write_text(
        json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    if not report["passed"]:
        raise RuntimeError("Steep-drop CAD verification failed: "+
                           ", ".join(k for k,v in checks.items() if not v))
    return report
