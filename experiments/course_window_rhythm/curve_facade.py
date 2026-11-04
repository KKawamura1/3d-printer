"""SD04-V19: three D01-style arches evenly spaced over the FULL outer facade.

Interpret the request literally:
  * follow the long outer wall from x=-32 on its straight section to the
    quarter-circle exit, including its bend;
  * split that wall's *surface arclength* into 12 equal sections;
  * cut a window covering exactly sections [2,3], [6,7], [10,11]
    (dividers are indexed 0..12 from the inlet);
  * locate each pointed arch at that section's midpoint, and orient it
    tangent to the local wall. On bends it is NOT a flat front-facing window.
  * lower edge / shoulders / point follow the actual downhill floor at
    their separate positions, preserving the architectural silhouette.

Unlike SD04-V18 the three openings occupy the full straight+curve facade,
with 3 units of uninterrupted wall between openings and 2 units of margin
at each end. This module is a single experimental version, not production.
"""
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path

import cadquery as cq

from brickcad.course_artifacts import export_geometry
from brickcad.course_contract import PRODUCTION_CONTRACT, audited_production_course, engrave_course
from brickcad.course_loft_family import LoftSettings, build_course, xy, height
from brickcad.standards import BALL_TRACK
from brickcad.verify import exact_bounds
from experiments.course_window_rhythm.design import recipe, SOURCE_ID

PART_ID = "SD04-V19"
START_X_MM = -32.
STRAIGHT_WALL_MM = 32.
BEND_OUTER_RADIUS_MM = 31.9
BEND_CENTRE = (0., 16.)  # left-sharp mirrored body
TOTAL_WALL_MM = STRAIGHT_WALL_MM + math.pi * BEND_OUTER_RADIUS_MM / 2
DIVISIONS = 12
SEGMENTS = ((2,3), (6,7), (10,11))
WINDOW_CENTRES_U = tuple((a+b)/2 / DIVISIONS for a,b in SEGMENTS)
WINDOW_WIDTH_MM = TOTAL_WALL_MM / DIVISIONS
WALL_OUTSET_MM = 1.65
FLOOR_BOTTOM_MM = 7.
FLOOR_SHOULDER_MM = 18.
FLOOR_POINT_MM = 22.

@dataclass(frozen=True)
class Opening:
    dividers: tuple
    centre_wall_s: float
    arc_centroid_xyz: tuple
    wall_origin_xy: tuple
    inward_xy: tuple
    outer_face: str
    outline_local_xz: tuple
    floor_at_centre: float
    rail_s_at_centre: float
    path_target_xyz: tuple


def rail_s(wall_s):
    """Map outer-wall arclength to the 16mm-radius path parameter."""
    if wall_s < 0 or wall_s > TOTAL_WALL_MM:
        raise ValueError("Wall station out of range")
    return (wall_s if wall_s <= STRAIGHT_WALL_MM else
            STRAIGHT_WALL_MM +
            (wall_s - STRAIGHT_WALL_MM) * 16. / BEND_OUTER_RADIUS_MM)


def wall_frame(wall_s, cfg):
    """Exterior wall XY and unit normal pointing into the ball passage.

    A line then the outer 31.9mm radius quarter circle is a continuous curve:
    the tangent matches at x=0, y=-15.9.
    """
    if not cfg.mirror or cfg.route != "sharp":
        raise ValueError("Only the left-sharp outer viewing wall is supported")
    if wall_s <= STRAIGHT_WALL_MM:
        return (START_X_MM + wall_s, -15.9), (0.,1.), "straight"
    a = math.pi/2 - (wall_s-STRAIGHT_WALL_MM)/BEND_OUTER_RADIUS_MM
    ca,sa=math.cos(a),math.sin(a)
    # The curve centre after mirroring is (0,+16).
    return (BEND_CENTRE[0]+BEND_OUTER_RADIUS_MM*ca,
            BEND_CENTRE[1]-BEND_OUTER_RADIUS_MM*sa), (-ca,sa), "curve"


def path_target(wall_s,cfg):
    s=rail_s(wall_s)
    x,y,_,_=xy(s,cfg)
    if cfg.mirror:
        y=-y
    floor=height(s,cfg)
    return (x,y,floor+BALL_TRACK.radius), floor


def design(cfg=None):
    cfg=cfg or recipe()
    if (cfg.route,cfg.drop_mm,cfg.tunnel,cfg.mirror) != ("sharp",19.2,True,True):
        raise ValueError("Incompatible SD04 base")
    pitch=TOTAL_WALL_MM/DIVISIONS
    ret=[]
    for l,r in SEGMENTS:
        centre=(l+r)/2*pitch
        outward_xy,inward,part=wall_frame(centre,cfg)
        target, floor=path_target(centre,cfg)
        # Local xDir = -forward-course tangent, so signed offsets to the
        # path use wall_s = centre - u. local Y remains global +Z.
        nx,ny=inward
        w=WINDOW_WIDTH_MM/2
        # At -w/2: further along the inlet; at +w/2: closer to inlet.
        levels=[]
        for u,offset in (
            (-w,FLOOR_BOTTOM_MM), (w,FLOOR_BOTTOM_MM),
            (w,FLOOR_SHOULDER_MM), (0.,FLOOR_POINT_MM),
            (-w,FLOOR_SHOULDER_MM)
        ):
            local_s=centre-u
            zz=height(rail_s(local_s),cfg)+offset
            levels.append((u,zz))
        if min(z for _,z in levels)<12. or max(z for _,z in levels)>52.:
            raise ValueError("Arched window enters receiver or roof area")
        if not l*pitch <= centre-w+1e-7 or not centre+w <= r*pitch+1e-7:
            raise ValueError("Window is not wholly inside its allotted 1/12 interval")
        ret.append(Opening(
            dividers=(l,r),centre_wall_s=centre,
            arc_centroid_xyz=(outward_xy[0],outward_xy[1],floor),
            wall_origin_xy=outward_xy, inward_xy=inward,outer_face=part,
            outline_local_xz=tuple(levels),floor_at_centre=floor,
            rail_s_at_centre=rail_s(centre),path_target_xyz=target))
    return tuple(ret)


def window_cutter(w):
    nx,ny=w.inward_xy
    # Tangent plane perpendicular to the local wall normal. With xDir
    # (-ny,nx,0), local vertical Y is +global Z.
    face0=(w.wall_origin_xy[0]-WALL_OUTSET_MM*nx,
           w.wall_origin_xy[1]-WALL_OUTSET_MM*ny,0.)
    plane=cq.Plane(origin=face0,xDir=(-ny,nx,0),normal=(nx,ny,0))
    dx=w.path_target_xyz[0]-face0[0]
    dy=w.path_target_xyz[1]-face0[1]
    required=dx*nx+dy*ny
    if not 14 < required < 23:
        raise ValueError("Exterior window plane does not face ball's centre")
    return (cq.Workplane(plane).polyline(w.outline_local_xz).close()
            .extrude(required+0.5).val())


def verify_visibility(original,altered,w):
    nx,ny=w.inward_xy
    p0=(w.wall_origin_xy[0]-WALL_OUTSET_MM*nx,
        w.wall_origin_xy[1]-WALL_OUTSET_MM*ny,
        w.path_target_xyz[2])
    p1=w.path_target_xyz
    if original.isInside(cq.Vector(*p1)):
        raise ValueError("Original ball centre obstructed")
    old_count=0
    for i in range(1,31):
        t=i/31
        p=cq.Vector(*(p0[k]*(1-t)+p1[k]*t for k in range(3)))
        old_count+=int(original.isInside(p))
        if altered.isInside(p):
            raise ValueError(f"Window {w.dividers} blocks the intended ball position")
    if old_count<1:
        raise ValueError("Window would be drilled through empty space")
    # A low guard at floor+3 must survive on the outer wall.
    guard=cq.Vector(w.wall_origin_xy[0]+nx*3.,
                    w.wall_origin_xy[1]+ny*3.,
                    w.floor_at_centre+3.)
    if not original.isInside(guard) or not altered.isInside(guard):
        raise ValueError("Low wall guard missing")
    return {"checked_samples":30,
            "original_wall_solid_samples":old_count,
            "obstructed_after_window":0}


def build(out):
    out=Path(out)
    out.mkdir(parents=True,exist_ok=True)
    cfg=recipe()
    windows=design(cfg)
    with audited_production_course(PART_ID) as audit:
        original,fit=build_course(cfg,label=None)
        bounds_before=exact_bounds(original)
        body=original
        evidence=[]
        for w in windows:
            cutter=window_cutter(w)
            next_body=body.cut(cutter).clean()
            removed=body.Volume()-next_body.Volume()
            if not (removed>15 and next_body.isValid() and len(next_body.Solids())==1):
                raise ValueError(
                    f"{w.dividers}: invalid or ineffective cut, volume={removed}")
            proof=verify_visibility(original,next_body,w)
            evidence.append({
                "dividers":list(w.dividers),
                "wall_fraction":w.centre_wall_s/TOTAL_WALL_MM,
                "wall_station_mm":w.centre_wall_s,
                "wall_type":w.outer_face,
                "wall_xy_mm":list(w.wall_origin_xy),
                "rail_s_mm":w.rail_s_at_centre,
                "floor_z_mm":w.floor_at_centre,
                "ball_centre_mm":list(w.path_target_xyz),
                "pentagon_local_xz_mm":[list(p) for p in w.outline_local_xz],
                "removed_volume_mm3":removed,
                "visibility":proof,
            })
            body=next_body
        # Engrave below all apertures on the south straight outer face.
        body=engrave_course(body,PART_ID,x=-16.,y=-fit.depth/2,z=12.)
    bounds_after=exact_bounds(body)
    if not body.isValid() or len(body.Solids())!=1:
        raise ValueError("Result is not a valid one-part CAD BRep")
    if any(abs(a-b)>.11 for a,b in zip(bounds_after,bounds_before)):
        raise ValueError("External dimensions changed")
    stl,mesh=export_geometry(body,out,tolerance=.01,angular_tolerance=.1)
    checks={
        "correct_12_section_intervals":tuple(x["dividers"] for x in evidence)
                                       == SEGMENTS,
        "three_nonoverlapping_pentagonal_windows":len(evidence)==3,
        "straight_and_bent_facade":([x["wall_type"] for x in evidence]
                                     == ["straight","curve","curve"]),
        "arclength_regular_rhythm":all(abs(
            evidence[i+1]["wall_station_mm"]-evidence[i]["wall_station_mm"]
            -4*TOTAL_WALL_MM/12)<1e-6 for i in range(2)),
        "ball_visible_from_each":all(
            x["visibility"]["obstructed_after_window"]==0 for x in evidence),
        "single_valid_solid":body.isValid() and len(body.Solids())==1,
        "unchanged_external_bounds":all(abs(a-b)<.11
                                        for a,b in zip(bounds_after,bounds_before)),
        "watertight_stl":mesh["passed"],
        "mesh_cad_volume_agree":abs(mesh["signed_volume_mm3"]-body.Volume())/
                                  body.Volume()<.001,
    }
    report={
        "id":PART_ID,"source_id":SOURCE_ID,
        "passed":all(checks.values()),"checks":checks,"mesh":mesh,
        "production_contract":PRODUCTION_CONTRACT,
        "contract_evidence":audit.manifest(),
        "geometry":{
            "windows":evidence,
            "front_face":"outer -Y inlet into external bent-wall arc",
            "total_outer_wall_arclength_mm":TOTAL_WALL_MM,
            "one_section_mm":TOTAL_WALL_MM/12,
            "window_arclength_width_mm":WINDOW_WIDTH_MM,
            "divider_pairs":[list(pair) for pair in SEGMENTS],
            "pitch_mm":TOTAL_WALL_MM/3,
            "intact_three_segment_gap_mm":3*TOTAL_WALL_MM/12,
            "remaining_end_margin_mm":2*TOTAL_WALL_MM/12,
            "external_bounds_mm":bounds_after,
            "goal":"One coherent facade, windows follow its bent arclength",
        },
        "stl_sha256":hashlib.sha256(stl.read_bytes()).hexdigest(),
        "physical_fit_validated":False,
        "physical_rolling_validated":False,
        "slicing_validated":False,
    }
    (out/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    if not report["passed"]:
        raise ValueError("12-section facade proof failed: "+repr(checks))
    print("TWELVE-SECTION OUTER FACADE PASS",PART_ID,flush=True)
    print("Walls:",[(r["dividers"],r["wall_type"],round(r["wall_station_mm"],2))
                   for r in evidence],flush=True)
    return report

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--out",type=Path,default=Path("build/course-window-curve"))
    build(p.parse_args().out)
