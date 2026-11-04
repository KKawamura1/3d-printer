"""One-face architectural window rhythm pilot: SD04-V17.

This experiment is deliberately *not* a generic window count/line-of-sight
optimizer. It tests one coherent facade on the straight 32 mm run of the
existing SD04 (2x4 sloped left-sharp tunnel). All three pointed arches are
identical in local proportions and evenly spaced, with identical edge
margins. The slope is sampled continuously under the five polygon vertices,
following the already validated D01 geometry language.

The curved 90-degree exit and the opposite side are unperforated.
The facade is on SOUTH (-Y), opposite the circular bend exit visible on NORTH (+Y). No other
catalogue variants or existing PR73 plate meshes are modified.
"""
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import cadquery as cq

from brickcad.course_artifacts import export_geometry
from brickcad.course_contract import (
    PRODUCTION_CONTRACT, audited_production_course, engrave_course,
)
from brickcad.course_loft_family import LoftSettings, build_course, height
from brickcad.standards import BALL_TRACK
from brickcad.verify import exact_bounds
from scripts.course_catalog import load_registry

PART_ID = "SD04-V18"
SOURCE_ID = "SD04-V10"
# The straight section is x=-32..0. This layout is centred EXACTLY in it.
# Left/right free margin = 5.25 mm; adjacent solid rib = 2.5 mm.
CENTRES_X_MM = (-24.0, -16.0, -8.0)
WIDTH_MM = 5.5
STRAIGHT_SECTION = (-32.0, 0.0)
FRONT_WALL_Y = -15.9  # place the attractive facade on -Y, AWAY from the round exit
CUT_START_Y = FRONT_WALL_Y - 1.6
CUT_DEPTH_MM = -18.0  # from -Y exterior into the passage, not across back wall
BOTTOM_OFFSET_MM = 7.0
SHOULDER_OFFSET_MM = 18.0
APEX_OFFSET_MM = 22.0
MIN_RIB_MM = 2.5
MIN_EDGE_MARGIN_MM = 5.0
WINDOW_COUNT = 3


@dataclass(frozen=True)
class Window:
    centre_x: float
    outline_xz: tuple
    floor_z: float


def recipe():
    model = next(m for m in load_registry()["models"] if m["id"] == SOURCE_ID)
    r = model["source"]["recipe"]
    cfg = LoftSettings.from_dict(r)
    if (cfg.route, cfg.drop_mm, cfg.tunnel, cfg.mirror) != ("sharp", 19.2, True, True):
        raise ValueError("SD04-V10 recipe no longer represents the known left-sharp tunnel")
    return cfg


def floor_at(x, cfg):
    if x < STRAIGHT_SECTION[0] or x > STRAIGHT_SECTION[1]:
        raise ValueError("Window must remain on the straight inlet facade")
    return height(x - STRAIGHT_SECTION[0], cfg)


def design_windows(cfg=None):
    """Three ordered, identically proportioned pointed arches on ONE facade."""
    cfg = cfg or recipe()
    positions = CENTRES_X_MM
    if len(positions) != WINDOW_COUNT:
        raise ValueError("Window-count mismatch")
    if any(positions[i+1] <= positions[i] for i in range(len(positions)-1)):
        raise ValueError("Windows must read from inlet to curve")
    pitches = [b-a for a,b in zip(positions, positions[1:])]
    if max(pitches) - min(pitches) > 1e-6:
        raise ValueError("Irregular visual rhythm")
    left_margin = positions[0]-WIDTH_MM/2-STRAIGHT_SECTION[0]
    right_margin = STRAIGHT_SECTION[1]-(positions[-1]+WIDTH_MM/2)
    if min(left_margin,right_margin) < MIN_EDGE_MARGIN_MM:
        raise ValueError("Too little facade margin")
    if abs(left_margin-right_margin) > 1e-6:
        raise ValueError("Facade end margins are not symmetrical")
    if min(pitches)-WIDTH_MM < MIN_RIB_MM-1e-6:
        raise ValueError("Window divisions too thin")
    windows = []
    for x in positions:
        l,r = x-WIDTH_MM/2, x+WIDTH_MM/2
        # D01's distinctive pointed pentagon. The entire outline follows
        # floor_z(x), not merely its centre point or a fixed global height.
        outline = (
            (l, floor_at(l,cfg)+BOTTOM_OFFSET_MM),
            (r, floor_at(r,cfg)+BOTTOM_OFFSET_MM),
            (r, floor_at(r,cfg)+SHOULDER_OFFSET_MM),
            (x, floor_at(x,cfg)+APEX_OFFSET_MM),
            (l, floor_at(l,cfg)+SHOULDER_OFFSET_MM),
        )
        if min(p[1] for p in outline) < 19.0:
            raise ValueError("Window would intersect underside receiver")
        if max(p[1] for p in outline) > 51.5:
            raise ValueError("Roof or studs could be weakened by a window")
        windows.append(Window(x, outline, floor_at(x,cfg)))
    return tuple(windows)


def cut_pentagon(window):
    # XZ plane negative extrusion points in +Y; cut from the visible
    # south exterior to just past the existing channel's ball centreline.
    return (cq.Workplane("XZ",origin=(0,CUT_START_Y,0))
            .polyline(window.outline_xz).close()
            .extrude(CUT_DEPTH_MM).val())


def optical_probe(shape_before,shape_after,window):
    """A centred eye-to-ball ray must have passed through real outer wall."""
    x=window.centre_x
    z=window.floor_z+BALL_TRACK.radius
    ball=(x,0.,z)
    if shape_before.isInside(cq.Vector(*ball)):
        raise ValueError("Original channel does not contain the ball centre")
    old_wall=0
    for i in range(1,31):
        y=CUT_START_Y+(0.-CUT_START_Y)*i/31.
        p=cq.Vector(x,y,z)
        old_wall+=int(shape_before.isInside(p))
        if shape_after.isInside(p):
            raise ValueError(f"Window at x={x} does not reveal ball centre")
    if old_wall < 1:
        raise ValueError("Window was cut into empty space rather than the tunnel wall")
    # continuous low guard under the side view; positive X/-X receiver,
    # top roof and studs must not be affected by this cut.
    guard=cq.Vector(x,-14.,window.floor_z+3.)
    if not shape_before.isInside(guard) or not shape_after.isInside(guard):
        raise ValueError("The lower ball-retaining wall was cut away")
    return {"original_opaque_samples":old_wall,
            "remaining_opaque_samples":0,
            "ball_centre_mm":list(ball)}


def build(output):
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    cfg=recipe()
    windows=design_windows(cfg)
    with audited_production_course(PART_ID) as audit:
        # Reuse the exact independent PR56 shared CAD path. This includes
        # E31-05 fitting and all studs; no old historical design module.
        original,fit=build_course(cfg,label=None)
        external_bounds=exact_bounds(original)
        current=original
        evidence=[]
        for w in windows:
            cutter=cut_pentagon(w)
            changed=current.cut(cutter).clean()
            removed=current.Volume()-changed.Volume()
            if not changed.isValid() or len(changed.Solids())!=1 or removed<18:
                raise ValueError(f"Window x={w.centre_x} invalid (volume={removed:.2f})")
            proof=optical_probe(original,changed,w)
            evidence.append({
                "centre_x_mm":w.centre_x,
                "outline_xz_mm":[list(pair) for pair in w.outline_xz],
                "floor_z_mm":w.floor_z,
                "removed_mm3":removed,
                "ball_visible":True,
                "optical_proof":proof,
            })
            current=changed
        # Existing engraving stays near the SOUTH lower edge (Z=12), safely
        # below the lowest pointed window (Z>25); neither overlaps.
        current=engrave_course(current,PART_ID,x=-16.,
                               y=-fit.depth/2,z=12.)
    bounds=exact_bounds(current)
    if not current.isValid() or len(current.Solids())!=1:
        raise ValueError("Prototyped architecture has invalid body")
    if any(abs(a-b)>.11 for a,b in zip(bounds,external_bounds)):
        raise ValueError("Experimental windows changed external brick dimensions")
    stl,mesh=export_geometry(current,output,tolerance=.01,angular_tolerance=.1)
    checks={
        "three_window_facade":len(evidence)==3,
        "even_pitch":all(abs((CENTRES_X_MM[i+1]-CENTRES_X_MM[i])-8)<.001
                         for i in range(2)),
        "equal_edge_margins":True,
        "same_local_pentagon_proportions":True,
        "monotonic_slope_following":all(
            evidence[i]["floor_z_mm"]>evidence[i+1]["floor_z_mm"]
            for i in range(2)),
        "independent_ball_sightlines":all(w["ball_visible"] for w in evidence),
        "one_valid_solid":current.isValid() and len(current.Solids())==1,
        "nominal_bounds_kept":all(abs(a-b)<.11
                                  for a,b in zip(bounds,external_bounds)),
        "watertight_stl":mesh["passed"],
        "mesh_cad_volume_agreement":abs(
            mesh["signed_volume_mm3"]-current.Volume())/
            current.Volume()<.001,
    }
    report={
        "id":PART_ID,"source_id":SOURCE_ID,
        "passed":all(checks.values()),
        "checks":checks,"mesh":mesh,
        "production_contract":PRODUCTION_CONTRACT,
        "contract_evidence":audit.manifest(),
        "geometry":{
            "windows":evidence,
            "bounds_mm":bounds,
            "volume_mm3":current.Volume(),
            "front_face":"south (-Y)",
            "other_faces_unperforated":True,
            "window_count":WINDOW_COUNT,
            "opening_width_mm":WIDTH_MM,
            "pitch_mm":8.,
            "solid_rib_mm":8.-WIDTH_MM,
            "edge_margin_mm":5.25,
            "aesthetic_goal":"Three equally spaced pentagonal windows in one row",
        },
        "stl_sha256":hashlib.sha256(stl.read_bytes()).hexdigest(),
        "physical_fit_validated":False,
        "physical_rolling_validated":False,
        "slicing_validated":False,
    }
    (output/"report.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    if not report["passed"]:
        raise ValueError("SD04 facade experiment failed: "+repr(checks))
    print("ONE-FACE WINDOW RHYTHM PASSED: "+PART_ID,flush=True)
    print("Three windows:",CENTRES_X_MM,"rib",8.-WIDTH_MM,
          "end margins",5.25,flush=True)
    return report


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out",type=Path,default=Path("build/course-window-rhythm"))
    opts=p.parse_args()
    build(opts.out)
