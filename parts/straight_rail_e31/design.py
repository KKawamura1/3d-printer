"""R01-V1: legacy measured open straight rail with shallow E31-05 receiver."""
from dataclasses import asdict, replace
from pathlib import Path
import hashlib
import json
import struct
import cadquery as cq
from brickcad.marking import engrave
from brickcad.model import brick_from_fit, receiver
from brickcad.provenance import design_manifest
from brickcad.standards import BALL_TRACK, ROUNDED_EDGES
from brickcad.verify import VOLUME_TOL, exact_bounds, intersection, mesh_check, precise_volume
from parts.straight_rail.design import Rail
from parts.tunnel.e31_fit import (
    BEAD_MINOR_RADIUS, BEAD_Z, SLOT_END_RADIUS, SLOT_WIDTH,
    add_e31_05_receiver_features, slot_end_z_for_receiver_depth,
)

PART_ID = "R01-V1"
RECEIVER_DEPTH_MM = 4.75


def build_rail():
    """Retain historical channel and outer surface, update underside and marking."""
    r = Rail()
    cavity = r.floor - r.roof
    if abs(cavity - RECEIVER_DEPTH_MM) > 1e-6:
        raise ValueError("R01-V1 requires 4.75 mm receiver")
    p = replace(brick_from_fit(
        "duplo-e27-play-v1", nx=4, ny=2, height_units=1,
        body_offset_xy=(0., r.width-31.8), height=r.height,
    ), tube_radius=6.60)
    outer = cq.Workplane("XY").box(r.length,r.width,r.height,centered=(True,True,False))
    outer = outer.edges("|Z").fillet(r.outer_radius).edges(">Z").fillet(r.outer_radius)
    result = receiver(p,outer,cavity,r.entry,(r.length,r.width))
    groove = cq.Solid.makeCylinder(r.radius,r.length+2,
        cq.Vector(-r.length/2-1,0,r.floor+r.radius),cq.Vector(1,0,0))
    result = result.cut(groove)
    lips = [e for e in result.val().Edges() if e.geomType()=="LINE"
            and e.Length()>r.length-2*r.outer_radius-1
            and abs(abs(e.Center().y)-r.opening/2)<.01]
    if len(lips)!=2:
        raise ValueError(f"Expected two historical channel lips; got {len(lips)}")
    result = result.newObject(lips).fillet(r.lip_radius)
    for x,ra,rb in ((-r.length/2,r.radius+r.end_chamfer,r.radius),
                    (r.length/2-r.end_chamfer,r.radius,r.radius+r.end_chamfer)):
        lead = cq.Solid.makeCone(ra,rb,r.end_chamfer,
            cq.Vector(x,0,r.floor+r.radius),cq.Vector(1,0,0))
        result=result.cut(lead)
    shape=add_e31_05_receiver_features(
        result.val().clean(),p.tubes(),p.tube_radius,receiver_depth=cavity)
    if not shape.isValid() or len(shape.Solids())!=1:
        raise ValueError("Invalid one-solid E31 receiver")
    return engrave(shape,PART_ID,x=0,y=-r.width/2,z=10.),p


def swept_ball_intersection(shape,diameter):
    """Continuous straight corridor check, not a rolling dynamics simulation."""
    r=Rail()
    radius=diameter/2
    cylinder=cq.Solid.makeCylinder(radius,r.length+2*radius,
        cq.Vector(-r.length/2-radius,0,r.floor+radius+.05),cq.Vector(1,0,0))
    return intersection(shape,cylinder)


def filter_collapsed_triangles(path):
    raw=path.read_bytes()
    count=struct.unpack_from("<I",raw,80)[0]
    if len(raw)!=84+50*count:
        raise ValueError("Invalid binary STL")
    good=[]
    for i in range(count):
        tri=raw[84+50*i:134+50*i]
        v=struct.unpack("<12fH",tri)[3:12]
        if len({tuple(v[j:j+3]) for j in (0,3,6)})==3:
            good.append(tri)
    path.write_bytes(raw[:80]+struct.pack("<I",len(good))+b"".join(good))
    return count-len(good)


def export(out=Path("build/straight-rail-e31")):
    out=Path(out)
    out.mkdir(parents=True,exist_ok=True)
    r=Rail()
    shape,p=build_rail()
    stl,step=out/"brick.stl",out/"brick.step"
    cq.exporters.export(shape,str(stl),tolerance=.01,angularTolerance=.1)
    collapsed=filter_collapsed_triangles(stl)
    cq.exporters.export(shape,str(step))
    restored=cq.importers.importStep(str(step)).val()
    bounds=exact_bounds(shape)
    mesh=mesh_check(stl)
    step_ok=(restored.isValid() and len(restored.Solids())==1
       and max(abs(a-b) for a,b in zip(bounds,exact_bounds(restored)))<.02
       and abs(precise_volume(restored)-precise_volume(shape))/shape.Volume()<1e-5)
    ball=swept_ball_intersection(shape,BALL_TRACK.ball_diameter)
    negative=swept_ball_intersection(shape,28.)
    margin=RECEIVER_DEPTH_MM-(slot_end_z_for_receiver_depth(RECEIVER_DEPTH_MM)+SLOT_END_RADIUS)
    checks={
        "valid_brep":shape.isValid(),"one_solid":len(shape.Solids())==1,
        "dimensions":all(abs(a-b)<.01 for a,b in zip(bounds,(r.length,r.width,r.height))),
        "mesh":mesh["passed"],"mesh_volume":abs(mesh["signed_volume_mm3"]-shape.Volume())/shape.Volume()<.001,
        "step_roundtrip":step_ok,"e31_tube_radius":abs(p.tube_radius-6.60)<1e-7,
        "e31_short_slot":slot_end_z_for_receiver_depth(RECEIVER_DEPTH_MM)==3.50,
        "e31_roof_margin":margin>=.60-1e-6,"three_tubes":len(p.tubes())==3,
        "floor_present":shape.isInside(cq.Vector(0,0,r.floor-.1)),
        "channel_open":not shape.isInside(cq.Vector(0,0,r.floor+.1)),
        "receiver_open":not shape.isInside(cq.Vector(8,0,.5)),
        "continuous_ball_clear":ball<VOLUME_TOL,"oversize_negative":negative>VOLUME_TOL,
    }
    report={
        "schema_version":1,"part_id":PART_ID,"kind":"straight_rail_open",
        "passed":all(checks.values()),"mesh":mesh,
        "geometry":{"bounds_mm":bounds,"volume_mm3":shape.Volume(),
                    "parameters":asdict(p),"checks":checks},
        "design":design_manifest(p,channel=r,channel_standard=BALL_TRACK,finish=ROUNDED_EDGES),
        "e31_05_receiver":{
            "tube_od_mm":13.20,"bead_minor_radius_mm":BEAD_MINOR_RADIUS,"bead_z_mm":BEAD_Z,
            "slot_width_mm":SLOT_WIDTH,"slot_end_z_mm":3.50,
            "slot_end_radius_mm":SLOT_END_RADIUS,"receiver_depth_mm":RECEIVER_DEPTH_MM,
            "roof_margin_mm":margin,"deep_brick_slot_unchanged_mm":4.40,
        },
        "marking":{"label":PART_ID,"font":"DejaVu Sans Bold",
                   "size_mm":3.0,"depth_mm":.4,"side":"-Y"},
        "ball_sweep":{"diameter_mm":BALL_TRACK.ball_diameter,
                      "intersection_mm3":ball,"negative_diameter_mm":28.,
                      "negative_intersection_mm3":negative},
        "collapsed_stl_triangles_removed":collapsed,
        "physical_fit_validated":False,"slicing_validated":False,
        "limitations":["Measured channel retained; E31-05 underside is not physically tested.",
                       "CAD geometry does not verify slicer bridging, clutch force, or momentum."],
        "files":{name:hashlib.sha256((out/name).read_bytes()).hexdigest()
                 for name in ("brick.stl","brick.step")},
    }
    (out/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    if not report["passed"]:
        raise RuntimeError(f"{PART_ID} CAD checks failed: {checks}")
    print("CAD VERIFIED",PART_ID,checks,flush=True)
    return report


if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",type=Path,default=Path("build/straight-rail-e31"))
    export(parser.parse_args().out)
