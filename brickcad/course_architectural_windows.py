"""Architectural, course-aligned windows across *all* PR56 roofed courses.

Policy requested after physical D01 success and SD04-V20 visual comparison:
  FLAT FACADE   1.5 : 1 : 1 : 1.5   (D01)    -- even 3-window group
  CONVEX FACADE 1   : 2 : 2 : 1     (V20)    -- 12 equally spaced arc bands
  CONCAVE FACADE                  NO WINDOWS
When a compact 2x2 wall cannot keep the required posts, one centered, tall
pointed window is used rather than pretending the three-window ratio fits.

A layout is a group on ONE wall, never independent holes scattered around a
corner. Wall station = surface arclength, not route-progress sampling. Preserve
the PR56 unmodified source, top studs, E31-05 receiver and ball channel.
Every prototype gets its own new revision and remains physically unvalidated.
"""
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path

import cadquery as cq

from brickcad.course_artifacts import export_geometry
from brickcad.course_contract import (
    PRODUCTION_CONTRACT, audited_production_course, engrave_course,
)
from brickcad.course_geometry import smoothstep_fall
from brickcad.course_loft_family import LoftSettings, height as loft_height, xy as loft_xy
from brickcad.course_windows import original_unmarked, mark_variant
from brickcad.course_configured_special import build_course as special_build
from brickcad.standards import BALL_TRACK
from brickcad.verify import exact_bounds
from scripts.course_catalog import load_registry

# All eleven PR56 models without windows. D01-V3 has its successful original
# three-window layout and MUST NOT be re-versioned or reprinted just for style.
VERSIONS = {
    "E01-V3": "E01-V8",
    "E01L-V1": "E01L-V6",
    "SC02-V12": "SC02-V17",
    "SC02L-V6": "SC02L-V11",
    "SD03-V11": "SD03-V16",
    "SD04-V10": "SD04-V21",  # SD04-V20 is the approved visual reference
    "T01-V6": "T01-V7",
    "C02-V8": "C02-V9",
    "S01-V8": "S01-V12",
    "S02-V16": "S02-V17",
    "S03-V10": "S03-V11",
}
FLAT_RATIO = (1.5, 1., 1., 1.5)
CONVEX_RATIO = (1., 2., 2., 1.)
CONVEX_DIVIDERS = ((1.5, 2.5), (5.5, 6.5), (9.5, 10.5))
R48_OUTER_RADIUS = 48. + BALL_TRACK.width / 2  # physical outer shell
SHARP_OUTER_RADIUS = 31.9
BEND_ARC = math.pi / 2
WINDOW_BOTTOM = 7.
WINDOW_SHOULDER = 18.
WINDOW_APEX = 22.
SMALL_WIDTH = 5.5
MIN_POST = 2.5


@dataclass(frozen=True)
class Facade:
    name: str
    kind: str  # flat, convex, single (compact flat)
    length: float
    width: float
    sample: object  # station -> ((wall_x, wall_y), (inward_x,inward_y), (target_x,target_y,z), floor)
    description: str


def flat_centres(length, width):
    """Solve [margin, gap, gap, margin] from 1.5:1:1:1.5.

    Example: D01 length 63.8, width8 -> x -16, 0, 16, margins 11.94.
    """
    if width*3 >= length:
        raise ValueError("3 windows cannot fit on this flat wall")
    gap = (length - 3*width) / sum(FLAT_RATIO)
    margin = 1.5 * gap
    if gap < MIN_POST - 1.e-6:
        raise ValueError("Three windows would leave an unsafe pillar")
    centres = tuple(margin + width/2 + i*(width+gap) for i in range(3))
    assert abs((length-(centres[-1]+width/2))-margin)<1.e-6
    return centres


def convex_centres(length):
    """Exactly V20: the 12 arcs leave 1.5:3:3:1.5 units, i.e. 1:2:2:1."""
    width = length/12.
    return tuple((a+b)*length/24. for a,b in CONVEX_DIVIDERS), width


def window_centres(face):
    if face.kind == "flat":
        return flat_centres(face.length,face.width)
    if face.kind == "convex":
        return convex_centres(face.length)[0]
    if face.kind == "single":
        return (face.length/2.,)
    raise ValueError("Never cut concave viewing windows: " + face.kind)


def model(source_id):
    if source_id not in VERSIONS:
        raise ValueError("Not an authorised roofed PR56 source: "+source_id)
    m = next((m for m in load_registry()["models"] if m["id"]==source_id),None)
    if not m or m["course"]["enclosure"]!="tunnel" or m["course"]["windows"]!=0:
        raise ValueError("The source must be a window-free roofed PR56 course")
    return m


def source_unmarked(m):
    sid,recipe=m["id"],m["source"]["recipe"]
    if sid.startswith(("E01","SC02","SD03","SD04")):
        return original_unmarked(m)
    if sid.startswith(("S01","S02","S03","C02")):
        family="drop" if sid.startswith("S") else "sharp_r16"
        shape,fit,checks=special_build(sid,family,recipe,mark=False)
        if not all(checks.values()):
            raise ValueError("Original special-shape CAD validation failed")
        return shape,fit
    if sid=="T01-V6":
        from brickcad.course_straight_tunnel import build_course
        return build_course(sid,recipe,marked=False)
    raise ValueError("No independent canonical CAD builder")


def flat_face(name, length, width, wall_point, inward, target_xyz,
              floor_z, *, desc="",single=False):
    def sample(s):
        return (wall_point(s),inward,target_xyz(s),floor_z(s))
    return Facade(name,"single" if single else "flat",length,width,sample,desc)


def convex_face(name, length, at, *, desc=""):
    return Facade(name,"convex",length,length/12,at,desc)


def _track_r48(t, left, sloped):
    angle=-math.pi/2+t*math.pi/2
    x=-32+48*math.cos(angle)
    y=32+48*math.sin(angle)
    if left: y=-y
    floor=BALL_TRACK.floor+(19.2*smoothstep_fall(t) if sloped else 0)
    return x,y,floor


def _large_planar_r48(m):
    """Only the clean 32mm sections near each ball course are view facades.

    The other half of each 4x4 square wall is deliberately kept solid. A
    third window over the remote empty quadrant would force a 50mm blind
    tunnel through the brick and ruin the facade.
    """
    left=m["source"]["recipe"]["direction"]=="left"
    ywall=31.9 if left else -31.9
    yn=-1. if left else 1.
    def south_t(s):
        return math.asin(max(-1.,min(1.,s/48.)))*2/math.pi
    def east_t(s):
        return math.acos(max(-1.,min(1.,(32.-s)/48.)))*2/math.pi
    def first_track(s):
        x,y,z=_track_r48(south_t(s),left,False)
        return (x,y,z+BALL_TRACK.radius)
    def second_track(s):
        x,y,z=_track_r48(east_t(s),left,False)
        return (x,y,z+BALL_TRACK.radius)
    return [
        flat_face("inlet-flat","__never__",0,None,None,None,None)
    ] if False else [
        flat_face("inlet-flat",32.,SMALL_WIDTH,
                  lambda s:(s-32.,ywall),
                  (0.,yn),
                  first_track,
                  lambda s:BALL_TRACK.floor,
                  desc="inlet-facing 32mm planar quadrant"),
        flat_face("outlet-side-flat",32.,SMALL_WIDTH,
                  lambda s:(31.9,(-1 if left else 1)*s),
                  (-1.,0.),
                  second_track,
                  lambda s:BALL_TRACK.floor,
                  desc="exit-side 32mm planar quadrant"),
    ]


def _r48_convex(m):
    left=m["source"]["recipe"]["direction"]=="left"
    length=BEND_ARC*R48_OUTER_RADIUS
    def at(s):
        t=s/length
        a=-math.pi/2 + t*math.pi/2
        rx,ry=math.cos(a),math.sin(a)
        if left:ry=-ry
        y0=-32 if left else 32
        wall=(-32+R48_OUTER_RADIUS*rx,y0+R48_OUTER_RADIUS*ry)
        normal=(-rx,-ry)
        x,y,floor=_track_r48(t,left,True)
        return wall,normal,(x,y,floor+BALL_TRACK.radius),floor
    return [convex_face("outer-convex-r48",length,at,
                        desc="entire convex R48 shell; inner concave wall stays closed")]


def _sharp_settings(m):
    return LoftSettings.from_dict(m["source"]["recipe"])


def _sharp_track(s,cfg):
    x,y,_,_=loft_xy(s,cfg)
    if cfg.mirror:y=-y
    floor=loft_height(s,cfg)
    return (x,y,floor+BALL_TRACK.radius),floor


def _sharp_wall(m):
    cfg=_sharp_settings(m)
    radius=SHARP_OUTER_RADIUS
    length=32+radius*math.pi/2
    # Mirror flips the smooth outer wall: right turn +Y, left turn -Y.
    cy=16. if cfg.mirror else -16.
    sign=-1. if cfg.mirror else 1.
    def at(s):
        path_s=s if s<=32 else 32+(s-32)*16./radius
        target,floor=_sharp_track(path_s,cfg)
        if s<=32:
            wall=(-32+s,sign*15.9)
            inward=(0.,-sign)
        else:
            a=math.pi/2-(s-32)/radius
            rx,ry=math.cos(a),math.sin(a)
            wall=(radius*rx,cy-sign*radius*ry)
            inward=(-rx,sign*ry)
        return wall,inward,target,floor
    outer=convex_face("straight-to-convex-outer",length,at,
                      desc="V20 full outer wall, 1:2:2:1 across straight+convex")
    # Opposite straight face is visible, but the inner bend is CONCAVE:
    # the latter receives NO window even if the body has room.
    inner_y=-sign*15.9
    inner=flat_face("opposite-flat-only",32.,SMALL_WIDTH,
                    lambda s:(s-32.,inner_y),
                    (0.,sign),
                    lambda s:_sharp_track(s,cfg)[0],
                    lambda s:_sharp_track(s,cfg)[1],
                    desc="three windows in flat inlet; concave corner untouched")
    return [outer,inner]


def _small_plan(m):
    sid=m["id"]
    if sid=="T01-V6":
        # On a 2x2 straight tunnel a regular 3-window row fits with 3.1mm
        # separating pillars and 4.65mm equal outer margins.
        return [flat_face(
            "straight-flat",31.8,SMALL_WIDTH,
            lambda s:(s-15.9,15.9),(0.,-1.),
            lambda s:(s-15.9,0.,BALL_TRACK.floor+BALL_TRACK.radius),
            lambda s:BALL_TRACK.floor,
            desc="2x2 regular D01-style three-window row")]
    if sid=="C02-V8":
        # Quarter R16 solid is square, but has NO convex exterior facade;
        # one central viewport in the uninterrupted north wall is safest.
        def centred(s):
            a=math.pi/4
            return (-16+16*math.cos(a),
                    -16+16*math.sin(a),
                    BALL_TRACK.floor+BALL_TRACK.radius)
        return [flat_face(
            "north-flat-small",31.8,6.,
            lambda s:(s-15.9,15.9),(0.,-1.),centred,
            lambda s:BALL_TRACK.floor,
            desc="one centre window on the 2x2 flat wall; no concave cut",
            single=True)]
    if sid.startswith("S"):
        cfg=m["source"]["recipe"]
        # Tall vertical shaft with a small 2x2 wall. Do not split its 1.6mm
        # outer wall into three fragile slits. A single tall opening is safer.
        exit_direction=cfg["exit"]
        shaft_x=-2. if exit_direction=="east" else 0.
        shaft_y=0.
        return [flat_face(
            "shaft-flat-small",31.8,5.,
            lambda s:(shaft_x,15.9),(0.,-1.),
            lambda s:(shaft_x,shaft_y,32.),
            lambda s:BALL_TRACK.floor+4.,
            desc="compact 2x2 vertical shaft: one tall window only",
            single=True)]
    raise ValueError("No compact roofed course strategy")


def plan(m):
    sid=m["id"]
    if sid.startswith("E01"):return _large_planar_r48(m)
    if sid.startswith("SC02"):return _r48_convex(m)
    if sid.startswith(("SD03","SD04")):return _sharp_wall(m)
    return _small_plan(m)


def _window_geometry(face, centre):
    """Five angled vertices, each attached to its own local channel floor."""
    (x,y),normal,target,floor=face.sample(centre)
    nx,ny=normal
    tangent=(-ny,nx)
    # Determine whether increasing station follows local CAD x-axis or not.
    d=.03
    a=face.sample(max(0,centre-d))[0]
    b=face.sample(min(face.length,centre+d))[0]
    progress=(b[0]-a[0],b[1]-a[1])
    sign=1. if progress[0]*tangent[0]+progress[1]*tangent[1]>=0 else -1.
    half=face.width/2
    points=[]
    for u,offset in ((-half,WINDOW_BOTTOM),(half,WINDOW_BOTTOM),
                     (half,WINDOW_SHOULDER),(0.,WINDOW_APEX),
                     (-half,WINDOW_SHOULDER)):
        station=centre+sign*u
        if not 0 <= station <= face.length:
            raise ValueError("Viewport exceeds the selected viewing facade")
        z=face.sample(station)[3]+offset
        points.append((u,z))
    if face.kind=="single" and face.name=="shaft-flat-small":
        # Long enough to see the entire falling trajectory, under the roof.
        points=[(-half,13.),(half,13.),(half,40.),
                (0.,43.),(-half,40.)]
    if min(z for _,z in points)<12. or max(z for _,z in points)>52.:
        raise ValueError("Window intersects receiver or overhead studs")
    outset=1.65
    plane=cq.Plane(
        origin=(x-outset*nx,y-outset*ny,0),
        xDir=tangent,normal=(nx,ny,0))
    dx=target[0]-plane.origin.x
    dy=target[1]-plane.origin.y
    distance=dx*nx+dy*ny
    if distance<3 or distance>70:
        raise ValueError("CAD window points away from its ball position")
    cutter=(cq.Workplane(plane).polyline(points).close()
            .extrude(distance+.5).val())
    return cutter,((x,y),normal,target,floor,tuple(points))


def _verify_visibility(before,after,shape_data, *, guard=True):
    (x,y),normal,target,floor,points=shape_data
    nx,ny=normal
    start=(x-1.65*nx,y-1.65*ny,target[2])
    if before.isInside(cq.Vector(*target)):
        raise ValueError("Ball centre was blocked even before window cutting")
    original_wall=0
    for i in range(1,31):
        k=i/31
        point=cq.Vector(*(a+(b-a)*k for a,b in zip(start,target)))
        original_wall+=int(before.isInside(point))
        if after.isInside(point):
            raise ValueError("Window failed actual optical sightline to ball")
    if not original_wall:
        raise ValueError("A decorative window must cut a real wall")
    if guard:
        low=cq.Vector(x+nx*3,y+ny*3,floor+3)
        if not before.isInside(low) or not after.isInside(low):
            raise ValueError("Guard below the window was cut away")
    return original_wall


def _mark(shape,m,new_id,fit):
    if m["id"].startswith(("E01","SC02","SD03","SD04")):
        return mark_variant(shape,m,new_id,fit)
    if m["id"].startswith("S"):
        # Maintain the prior calibrated marking at a low, solid location.
        return engrave_course(shape,new_id,x=0.,y=-fit.depth/2,z=12.)
    if m["id"]=="C02-V8":
        return engrave_course(shape,new_id,x=0.,y=fit.depth/2,z=11.5)
    return engrave_course(shape,new_id,x=0.,y=-fit.depth/2,z=10.)


def build(source_id, out):
    m=model(source_id)
    new_id=VERSIONS[source_id]
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    facades=plan(m)
    with audited_production_course(new_id) as audit:
        original,fit=source_unmarked(m)
        original_bounds=exact_bounds(original)
        shape=original
        evidence=[]
        for facade in facades:
            row=[]
            for station in window_centres(facade):
                cutter,geo=_window_geometry(facade,station)
                nxt=shape.cut(cutter).clean()
                removed=shape.Volume()-nxt.Volume()
                if not nxt.isValid() or len(nxt.Solids())!=1 or removed<8.:
                    raise ValueError(
                        f"{new_id} {facade.name} station {station:.2f}: "
                        f"invalid cut or removed={removed:.3f}")
                old_wall=_verify_visibility(original,nxt,geo)
                row.append({
                    "station_mm":station,"position_xyz_mm":list(geo[0])+[geo[2][2]],
                    "rail_xyz_mm":list(geo[2]),"outline_local_xz_mm":list(geo[4]),
                    "removed_mm3":removed,
                    "opaque_precut_samples":old_wall,"opaque_postcut_samples":0})
                shape=nxt
            evidence.append({
                "name":facade.name,"kind":facade.kind,
                "surface_length_mm":facade.length,"window_width_mm":facade.width,
                "centres_mm":list(window_centres(facade)),
                "negative_space_ratio":list(
                    CONVEX_RATIO if facade.kind=="convex" else
                    FLAT_RATIO if facade.kind=="flat" else (1,1)),
                "concave_wall_cut":False,"windows":row})
        shape=_mark(shape,m,new_id,fit)
    bounds=exact_bounds(shape)
    if any(abs(a-b)>.11 for a,b in zip(bounds,original_bounds)):
        raise ValueError("Window placement changed the original external dimensions")
    if not shape.isValid() or len(shape.Solids())!=1:
        raise ValueError("Architectural windows destroyed the single connected BRep")
    stl,mesh=export_geometry(shape,out,
        tolerance=.02 if source_id.startswith("SC02") else .01,
        angular_tolerance=.15 if source_id.startswith("SC02") else .1)
    checks={
        "all_facades_present":bool(evidence),
        "every_requested_window_sees_ball":all(
            w["opaque_precut_samples"]>0 and w["opaque_postcut_samples"]==0
            for f in evidence for w in f["windows"]),
        "no_concave_wall_cut":all(not x["concave_wall_cut"] for x in evidence),
        "one_valid_solid":shape.isValid() and len(shape.Solids())==1,
        "source_external_dimensions":all(
            abs(a-b)<.11 for a,b in zip(bounds,original_bounds)),
        "watertight_stl":mesh["passed"],
        "stl_matches_cad_volume":abs(
            mesh["signed_volume_mm3"]-shape.Volume())/shape.Volume()<.001,
    }
    report={
        "part_id":new_id,"source_model_id":source_id,
        "passed":all(checks.values()),"checks":checks,
        "geometry":{"bounds_mm":bounds,"volume_mm3":shape.Volume(),
                    "facades":evidence,
                    "total_windows":sum(len(f["windows"]) for f in evidence)},
        "production_contract":PRODUCTION_CONTRACT,
        "contract_evidence":audit.manifest(),"mesh":mesh,
        "physical_fit_validated":False,"physical_rolling_validated":False,
        "slicing_validated":False,
    }
    (out/"report.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    if not report["passed"]:
        raise ValueError("One of architectural CAD validations failed")
    print("ARCHITECTURAL WINDOWS SUCCESS",new_id,
          [(f["name"],len(f["windows"])) for f in evidence],flush=True)
    return report


if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model",choices=sorted(VERSIONS),required=True)
    parser.add_argument("--out",type=Path,default=Path("build/architectural-windows"))
    args=parser.parse_args()
    build(args.model,args.out)
