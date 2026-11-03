"""Prototype only: PR55 first underside-roof layer support experiment.
Runs with cadquery, trimesh, numpy. Generated coupons are not production parts.
"""
from pathlib import Path
import json
import numpy as np
import cadquery as cq
import trimesh

OUT = Path("build/issue37-floor-bridge")
BODY, CAVITY, DEPTH, ROOF = 31.8, 25.4, 4.75, 2.0
TUBE_OD_R, TUBE_INNER_R = 6.60, 5.25
RIB_WIDTH, RIB_KEEP_OUT_R, RIB_HEIGHT = 1.20, 7.50, 4.85

def apply_e31_slots(shape, end_z):
    """Same 4-slot E31-05 cutter, with variable end height."""
    for deg in (0, 90, 180, 270):
        channel = (cq.Workplane("XY").box(4,1.1,end_z+.1,
                    centered=(True,True,False)).translate((6,0,-.1)).val())
        round_end = cq.Solid.makeCylinder(.65,4,cq.Vector(4,0,end_z),cq.Vector(1,0,0))
        mouth = (cq.Workplane("YZ")
                .polyline([(-.75,-.1),(.75,-.1),(.55,.8),(-.55,.8)])
                .close().extrude(4).translate((4,0,0)).val())
        cutter=channel.fuse(round_end).fuse(mouth)
        shape=shape.cut(cutter.rotate((0,0,0),(0,0,1),deg))
    return shape.clean()

def rib_shape():
    along_x=(cq.Workplane("XY").box(CAVITY+.4,RIB_WIDTH,RIB_HEIGHT,
               centered=(True,True,False)).val())
    along_y=(cq.Workplane("XY").box(RIB_WIDTH,CAVITY+.4,RIB_HEIGHT,
               centered=(True,True,False)).val())
    tube_keepout=cq.Solid.makeCylinder(RIB_KEEP_OUT_R,RIB_HEIGHT+.2,
                                      cq.Vector(0,0,-.1))
    return along_x.fuse(along_y).cut(tube_keepout).clean()

def coupon(short=False, ribs=False):
    body=(cq.Workplane("XY").box(BODY,BODY,DEPTH+ROOF,
          centered=(True,True,False)).cut(
          cq.Workplane("XY").box(CAVITY,CAVITY,DEPTH,
          centered=(True,True,False))))
    tube=(cq.Workplane("XY").circle(TUBE_OD_R).circle(TUBE_INNER_R)
          .extrude(DEPTH))
    shape=body.union(tube).val().clean()
    bead=cq.Solid.makeTorus(TUBE_OD_R,.2,cq.Vector(0,0,2.25),cq.Vector(0,0,1))
    shape=apply_e31_slots(shape.fuse(bead).clean(), 3.5 if short else 4.4)
    if ribs: shape=shape.fuse(rib_shape()).clean()
    assert shape.isValid() and len(shape.Solids())==1
    return shape

def compare_chords(ribs):
    """Approximation at Z4.6; ignores E31 slot notch. Not a slicer measurement."""
    gaps=[]
    xs=np.linspace(-12.7,12.7,509)
    for y in np.arange(-12,12.01,.5):
        radii=np.hypot(xs,y)
        covered=(radii>=TUBE_INNER_R)&(radii<=TUBE_OD_R)
        if ribs:
            covered |= (((abs(xs)<=RIB_WIDTH/2)|(abs(y)<=RIB_WIDTH/2))
                        &(radii>=RIB_KEEP_OUT_R))
        runs=[]; n=0
        for empty in ~covered:
            if empty:n+=1
            else:
                if n:runs.append(n)
                n=0
        if n:runs.append(n)
        gaps.append(max(runs,default=0)*.05)
    return dict(mean_max_mm=round(float(np.mean(gaps)),2),
                worst_mm=round(max(gaps),2),
                scan_lines_over_20mm=sum(x>20 for x in gaps),
                scan_lines=len(gaps))

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    # Mating stud keepouts at (+/-8,+/-8), R4.7, height4.5.
    ribs=rib_shape()
    collisions=[ribs.intersect(cq.Solid.makeCylinder(
        4.7,4.5,cq.Vector(x,y,0))).Volume()
        for x in (-8,8) for y in (-8,8)]
    assert max(collisions)<1e-5
    cases=[("A_original",False,False),("B_short_slots",True,False),
           ("C_ribs_only",False,True),("D_both",True,True)]
    arranged=[]; report=[]
    for i,(name,short,has_ribs) in enumerate(cases):
        shape=coupon(short,has_ribs)
        path=OUT/(name+".stl")
        cq.exporters.export(shape,str(path),tolerance=.04,angularTolerance=.2)
        mesh=trimesh.load_mesh(path,process=True)
        assert mesh.is_watertight
        report.append(dict(case=name,split_slot_end_mm=3.5 if short else 4.4,
                           split_slot_highest_mm=4.15 if short else 5.05,
                           support_ribs=has_ribs,**compare_chords(has_ribs)))
        mesh.apply_translation((39.8+(i%2)*39.8,39.8+(i//2)*39.8,0))
        arranged.append(mesh)
    trimesh.util.concatenate(arranged).export(OUT/"four_up.stl")
    (OUT/"report.json").write_text(json.dumps(dict(
        detail="CAD/analytic comparison only, no support-OFF re-slice or physical print",
        studs_rib_collision_volume_mm3=max(collisions),cases=report),
        indent=2,ensure_ascii=False))
    print((OUT/"report.json").read_text())

if __name__=="__main__":
    main()
