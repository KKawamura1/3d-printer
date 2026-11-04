"""Sightline-driven D01-style viewing windows on canonical PR56 CAD.

Unlike the prior fixed-X, fixed-Z windows, every pointed aperture is based on
a sampled ball-centre trajectory. The window follows the local slope, faces
the actual channel, and is checked for an unobstructed optical ray from the
exterior of the tunnel to the rolling ball. Angles for the R48 curved-rail
walls follow the bend; they are not cut into arbitrary cube corners.

Each source builds an immutable NEW version. The untouched original CAD mesh
and previous window candidates remain accessible as separate versions.
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
from brickcad.course_windows import original_unmarked, mark_variant
from brickcad.course_configured_special import build_course as special_build
from brickcad.course_loft_family import (
    LoftSettings, xy as sharp_xy, height as sharp_height,
)
from brickcad.standards import BALL_TRACK
from brickcad.verify import exact_bounds
from scripts.course_catalog import load_registry

# Version-bump all geometry changes, including the one-sided comparison.
VISIBLE_DUAL_IDS = {
    "E01-V3": "E01-V7", "E01L-V1": "E01L-V5",
    "SC02-V12": "SC02-V16", "SC02L-V6": "SC02L-V10",
    "SD03-V11": "SD03-V15", "SD04-V10": "SD04-V15",
    "S01-V8": "S01-V11",
}
VISIBLE_SINGLE_IDS = {"SD04-V10": "SD04-V16"}

# A 3-point arc fraction plan is arclength-even. On the *square* E01 housing
# the curved track crosses the interior: divide it between adjacent front
# and east faces. On the true SC02 curved shell, use radial cuts along its
# outer and inner walls so the windows progress WITH the ball's path.
E01_FRONT = (.14, .32, .50)
E01_EXIT = (.50, .68, .86)
CURVED_SAMPLES = (.18, .50, .82)
SHARP_SAMPLES = (.18, .50, .82)
SHARP_SECONDARY = (.18, .50)  # Inside 90deg corner has no third usable wall.

# D01-V3 style: narrow pointed vertical windows, bottom tracks each floor.
WINDOW_WIDTH = 6.0
SMALL_WIDTH = 5.0
BOTTOM_ABOVE_FLOOR = 6.8
SHOULDER_ABOVE_FLOOR = 17.8
PEAK_ABOVE_FLOOR = 21.8
# At least this much continuous left/right material (approximate measured
# along the observation face). Source is unmodified between window cutouts.
MIN_RIB_MM = 2.0


@dataclass(frozen=True)
class Sightline:
    face: str
    t: float
    track_xyz: tuple
    origin_xyz: tuple
    inward_xy: tuple
    width_mm: float
    floor_mm: float
    window_bottom: float
    window_shoulder: float
    window_peak: float


def family(source_id):
    if source_id.startswith("E01"): return "E01"
    if source_id.startswith("SC02"): return "SC02"
    if source_id.startswith(("SD03","SD04")): return "SD"
    if source_id.startswith("S01"): return "S01"
    raise ValueError("Unknown rail centreline: " + source_id)


def canonical_model(source_id):
    models = {m["id"]:m for m in load_registry()["models"]}
    model = models.get(source_id)
    if (source_id not in VISIBLE_DUAL_IDS or model is None
            or model["course"]["enclosure"] != "tunnel"
            or model["course"]["windows"] != 0):
        raise ValueError("Not a known enclosed PR56 model: " + source_id)
    return model


def track_at(source_id, t, recipe):
    """Return true XY ball centreline and floor height at arc-length fraction."""
    if not 0 <= t <= 1:
        raise ValueError("Path sample outside rail")
    kind = family(source_id)
    if kind in ("E01","SC02"):
        theta = (-math.pi/2) + t*(math.pi/2)
        x = -32. + 48.*math.cos(theta)
        y = 32. + 48.*math.sin(theta)
        if recipe["direction"] == "left":
            y = -y
        floor = BALL_TRACK.floor
        if kind == "SC02":
            floor += 19.2*smoothstep_fall(t)
        return x,y,floor
    if kind == "SD":
        settings = LoftSettings.from_dict(recipe)
        s = settings.length*t
        x,y,_,_ = sharp_xy(s,settings)
        if settings.mirror:
            y = -y
        return x,y,sharp_height(s,settings)
    # S01: descending vertical shaft, not a horizontal 2x2 straight
    # channel. One tall aperture per face must reveal the falling path.
    return -2.,0.,BALL_TRACK.floor+19.2*(1-t)


def _slot(source_id, t, recipe, *, face, radial=None):
    x,y,floor = track_at(source_id,t,recipe)
    if source_id == "S01-V8":
        floor = BALL_TRACK.floor
    z = floor+BALL_TRACK.radius
    if face == "south":
        n = (0.,1.)
        start = (x,-34.0 if family(source_id)=="E01" else -18.5)
    elif face == "north":
        n = (0.,-1.)
        start = (x,34.0 if family(source_id)=="E01" else 18.5)
    elif face == "east":
        n = (-1.,0.)
        start = (34.0,y)
    elif face in ("arc_outer","arc_inner"):
        kind = family(source_id)
        if kind != "SC02":
            raise ValueError("Radial viewing reserved for the genuine R48 wall")
        theta = -math.pi/2+math.pi/2*t
        radial_direction = (math.cos(theta),math.sin(theta))
        if recipe["direction"] == "left":
            radial_direction = (radial_direction[0],-radial_direction[1])
        if face == "arc_outer":
            start = (-32.+65.5*radial_direction[0],
                     (32. if recipe["direction"]=="right" else -32.)
                     +65.5*radial_direction[1])
            n = (-radial_direction[0],-radial_direction[1])
        else:
            start = (-32.+30.5*radial_direction[0],
                     (32. if recipe["direction"]=="right" else -32.)
                     +30.5*radial_direction[1])
            n = radial_direction
    elif face == "sharp_outer":
        # The sharp corner exterior has radial radius 31.9mm relative to
        # (0,-16). Only the last path checkpoint is in the 90deg bend.
        config = LoftSettings.from_dict(recipe)
        s=config.length*t
        theta=math.pi/2-(s-32.)/16.
        radial_direction=(math.cos(theta),math.sin(theta))
        if config.mirror:
            radial_direction=(radial_direction[0],-radial_direction[1])
        cy=16. if config.mirror else -16.
        start=(33.*radial_direction[0],cy+33.*radial_direction[1])
        n=(-radial_direction[0],-radial_direction[1])
    else:
        raise ValueError("Unsupported observation face: "+face)
    width=5. if source_id=="S01-V8" else WINDOW_WIDTH
    if source_id=="S01-V8":
        b,shoulder,peak=13.,40.,43.
    else:
        b=floor+BOTTOM_ABOVE_FLOOR
        shoulder=floor+SHOULDER_ABOVE_FLOOR
        peak=floor+PEAK_ABOVE_FLOOR
    return Sightline(
        face=face,t=t,track_xyz=(x,y,z),
        origin_xyz=(start[0],start[1],z),
        inward_xy=n,width_mm=width,floor_mm=floor,
        window_bottom=b,window_shoulder=shoulder,window_peak=peak)


def view_plan(source_id, recipe, *, sides=2):
    """Windows across the COMPLETE running course, not a cluster in one corner."""
    if sides not in (1,2):
        raise ValueError("Only one or two viewing sides")
    kind=family(source_id)
    left = recipe.get("direction")=="left"
    if kind=="E01":
        return [
            [_slot(source_id,t,recipe,face="north" if left else "south")
             for t in E01_FRONT],
            [_slot(source_id,t,recipe,face="east") for t in E01_EXIT],
        ][:sides]
    if kind=="SC02":
        return [
            [_slot(source_id,t,recipe,face="arc_outer") for t in CURVED_SAMPLES],
            [_slot(source_id,t,recipe,face="arc_inner") for t in CURVED_SAMPLES],
        ][:sides]
    if kind=="SD":
        # Two stations on the straight inlet and one on the curved exit.
        # Opposite side remains on the straight; there is no strong inner
        # corner wall for the last one.
        outer_face="north" if recipe["mirror"] else "south"
        inner_face="south" if recipe["mirror"] else "north"
        return [
            [_slot(source_id,t,recipe,face=outer_face) for t in SHARP_SAMPLES[:2]]
            +[_slot(source_id,SHARP_SAMPLES[2],recipe,face="sharp_outer")],
            [_slot(source_id,t,recipe,face=inner_face) for t in SHARP_SECONDARY],
        ][:sides]
    return [
        [_slot(source_id,.5,recipe,face="south")],
        [_slot(source_id,.5,recipe,face="north")],
    ][:sides]


def _cutter(view):
    """Pentagon on the local wall's tangent and vertical plane; cut inward."""
    nx,ny=view.inward_xy
    # Right-handed plane: local Y is +Z, irrespective of wall azimuth.
    plane=cq.Plane(
        origin=(view.origin_xyz[0],view.origin_xyz[1],0.),
        xDir=(-ny,nx,0.),normal=(nx,ny,0.))
    w=view.width_mm/2
    points=[(-w,view.window_bottom),(w,view.window_bottom),
            (w,view.window_shoulder),(0,view.window_peak),
            (-w,view.window_shoulder)]
    dx=view.track_xyz[0]-view.origin_xyz[0]
    dy=view.track_xyz[1]-view.origin_xyz[1]
    path_len=dx*nx+dy*ny
    if path_len<3. or path_len>75.:
        raise ValueError("Viewport does not face this segment of rail")
    # The final 0.4mm removes the last possible opaque material before the
    # ball centre. At all times the cut starts >6mm ABOVE the running floor.
    return cq.Workplane(plane).polyline(points).close().extrude(path_len+.4).val()


def _sample_visible(original, altered, view):
    """Check a real through-wall optical ray, not only an excavated volume."""
    x,y,z=view.track_xyz
    a=view.origin_xyz
    start=(a[0],a[1],z)
    target=(x,y,z)
    if original.isInside(cq.Vector(*target)):
        return False,"track_centre_blocked_in_unmodified_cad"
    # Verify that our ray passed actual wall material (not a floating
    # window in empty space), and every point from exterior to ball is clear.
    solids_seen=0
    obstructed=[]
    for i in range(1,31):
        p=cq.Vector(*(start[k]+(target[k]-start[k])*i/31 for k in range(3)))
        if original.isInside(p):
            solids_seen+=1
        if altered.isInside(p):
            obstructed.append(i)
    return (solids_seen>0 and not obstructed), {
        "original_opaque_samples":solids_seen,
        "remaining_opaque_samples":obstructed,
        "track_xyz_mm":target,
    }


def _apply_windows(shape, original, views):
    result=shape
    records=[]
    for view in views:
        cutter=_cutter(view)
        previous_volume=result.Volume()
        updated=result.cut(cutter).clean()
        removed=previous_volume-updated.Volume()
        if (removed<9 or not updated.isValid()
                or len(updated.Solids())!=1):
            raise ValueError(
                f"{view.face} t={view.t:.2f}: invalid through-window cut, "
                f"removed {removed:.1f}mm3")
        clear,evidence=_sample_visible(original,updated,view)
        if not clear:
            raise ValueError(
                f"{view.face} t={view.t:.2f}: ball not visible: {evidence}")
        # Under each aperture, the outer side material at floor+3mm must
        # remain intact to guard against a ball escaping sideways.
        nx,ny=view.inward_xy
        guard=cq.Vector(view.origin_xyz[0]+nx*2.,
                        view.origin_xyz[1]+ny*2.,
                        view.floor_mm+3.)
        if not result.isInside(guard) or not updated.isInside(guard):
            raise ValueError(f"{view.face}: insufficient side guard below view")
        result=updated
        records.append({
            "face":view.face,"progress_t":view.t,
            "track_xyz_mm":list(view.track_xyz),
            "window_at_xyz_mm":list(view.origin_xyz),
            "width_mm":view.width_mm,
            "bottom_z_mm":view.window_bottom,
            "shoulder_z_mm":view.window_shoulder,
            "peak_z_mm":view.window_peak,
            "removed_mm3":round(removed,2),
            "ball_visible_from_outside":True,
            "optical_evidence":evidence,
        })
    return result,records


def _unmarked(model):
    sid=model["id"]
    if sid=="S01-V8":
        shape,fit,checks=special_build(
            sid,"drop",model["source"]["recipe"],mark=False)
        if not all(checks.values()):
            raise ValueError("Original S01 CAD validation failed")
        return shape,fit
    return original_unmarked(model)


def build_visible_window_variant(source_id, out, *, sides=2):
    model=canonical_model(source_id)
    if sides==1 and source_id not in VISIBLE_SINGLE_IDS:
        raise ValueError("Only approved comparison has one-sided windows")
    part_id=(VISIBLE_DUAL_IDS if sides==2 else VISIBLE_SINGLE_IDS)[source_id]
    out=Path(out)
    out.mkdir(parents=True,exist_ok=True)
    with audited_production_course(part_id) as audit:
        original,fit=_unmarked(model)
        bounds_before=exact_bounds(original)
        planned=view_plan(source_id,model["source"]["recipe"],sides=sides)
        shape=original
        reports=[]
        for views in planned:
            shape,details=_apply_windows(shape,original,views)
            reports.append(details)
        if source_id=="S01-V8":
            shape=engrave_course(shape,part_id,x=0.,y=-fit.depth/2,z=12.)
        else:
            shape=mark_variant(shape,model,part_id,fit)
    bounds_after=exact_bounds(shape)
    if (not shape.isValid() or len(shape.Solids())!=1 or
            any(abs(x-y)>.11 for x,y in zip(bounds_before,bounds_after))):
        raise ValueError("Window design modified the original bounding box")
    stl,mesh=export_geometry(
        shape,out,tolerance=.02 if family(source_id)=="SC02" else .01,
        angular_tolerance=.15 if family(source_id)=="SC02" else .1)
    checks={
        "one_connected_solid":shape.isValid() and len(shape.Solids())==1,
        "external_bounds_unchanged":all(
            abs(x-y)<.11 for x,y in zip(bounds_before,bounds_after)),
        "each_window_has_ball_sightline":all(
            row["ball_visible_from_outside"] for face in reports for row in face),
        "all_requested_walls_have_windows":len(reports)==sides and
            all(len(face)>=1 for face in reports),
        "watertight_mesh":mesh["passed"],
        "mesh_matches_cad_volume":(
            abs(mesh["signed_volume_mm3"]-shape.Volume()) /
            shape.Volume()<.001),
    }
    report={
        "part_id":part_id,"source_model_id":source_id,
        "passed":all(checks.values()),"checks":checks,"mesh":mesh,
        "geometry":{
            "bounds_mm":bounds_after,"volume_mm3":shape.Volume(),
            "window_count_per_face":[len(face) for face in reports],
            "windows":reports,
            "track_visibility_mode":"unobstructed_outer_wall_to_ball_centre",
            "window_shape":"D01-style vertical pointed pentagon",
            "height_follows_ball_track":True,
        },
        "production_contract":PRODUCTION_CONTRACT,
        "contract_evidence":audit.manifest(),
        "slicing_validated":False,"physical_fit_validated":False,
        "physical_rolling_validated":False,
    }
    (out/"report.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    if not report["passed"]:
        raise ValueError("Visible course CAD checks failed: "+repr(checks))
    return {
        "id":part_id,"source_model_id":source_id,
        "issue37_no":model["issue37_no"],
        "course":{**model["course"],
                  "windows":sum(len(face) for face in reports)},
        "stl":str(stl),
        "stl_sha256":hashlib.sha256(stl.read_bytes()).hexdigest(),
        "source_reference":model["source"]["reference"],
        "production_contract":PRODUCTION_CONTRACT,
        "contract_evidence":audit.manifest(),
        "report":report,
        "slicing_validated":False,"physical_fit_validated":False,
        "physical_rolling_validated":False,
    }
