"""One closed-D-support curve and three roof alternatives, each with its own version ID."""
from pathlib import Path
from dataclasses import asdict
import math
import hashlib
import json
import cadquery as cq
from brickcad.render import viewer
from brickcad.provenance import design_manifest
from brickcad.verify import intersection, exact_bounds, VOLUME_TOL
from parts.tunnel.design import build_tunnel, Tunnel, ball_sweep
from parts.sloped_curve.design import build_curve, curve_profile, RAIL, RADIUS, RETAINED_TUBES, curved_footprint, receiver_audit, ball_centre, BALL
from parts.play_set.design import export_stl

VARIANTS = {'T02-V1':('circle',2.),'T03-V1':('transition',2.),'T04-V1':('transition',4.)}


CURVE_ID = 'S02-V2'
D_RADIUS = .5


def d_supports(p):
    """Close each partial cylinder with a straight, 2.05 mm cap, not a floor.

    Inner cuts use the footprint's tangent (entire D remains in the footprint).
    Outer cuts use its chord through the circle intersections. The smallest
    remnant cannot fit a hollow cavity + cap and is a solid rounded segment.
    """
    h=RAIL.floor-RAIL.roof
    wall=p.tube_radius-p.tube_inner_radius
    result=[]
    for x,y in p.tubes():
        d=math.hypot(x+32,y-32)
        if (x,y) in RETAINED_TUBES or d+p.tube_radius<RADIUS-RAIL.width/2:
            continue
        inner=d-p.tube_radius<RADIUS-RAIL.width/2
        cut=(RADIUS-RAIL.width/2-d if inner else
             (63.9**2-d*d-p.tube_radius**2)/(2*d))
        angle=math.degrees(math.atan2(y-32,x+32))
        def mask(at):
            offset=at+50 if inner else at-50
            return (cq.Workplane('XY').box(100,100,h,centered=(True,True,False))
                    .translate((offset,0,0)).val()
                    .rotate((0,0,0),(0,0,1),angle).translate((x,y,0)))
        outer=cq.Solid.makeCylinder(p.tube_radius,h,cq.Vector(x,y,0)).intersect(mask(cut))
        hole=cq.Solid.makeCylinder(p.tube_inner_radius,h,cq.Vector(x,y,0)).intersect(
            mask(cut+wall if inner else cut-wall))
        support=outer.cut(hole).clean() if hole.Solids() else outer.clean()
        vertical=[e for e in support.Edges() if e.geomType()=='LINE'
                  and e.BoundingBox().zlen>h-.01]
        support=support.fillet(D_RADIUS,vertical).clean()
        bottom=[e for e in support.Edges() if abs(e.BoundingBox().zmin)<1e-5
                and abs(e.BoundingBox().zmax)<1e-5]
        support=support.fillet(D_RADIUS,bottom).clean()
        assert support.isValid() and len(support.Solids())==1
        # The rounded support must stay inside both original tube OD and footprint.
        assert support.cut(curved_footprint()).Volume()<VOLUME_TOL
        result.append((support,dict(centre_xy_mm=[x,y],inner_boundary=inner,
            cap_offset_mm=cut,cap_wall_mm=wall,hollow=bool(hole.Solids()),
            edge_radius_mm=D_RADIUS,bottom_radius_mm=D_RADIUS)))
    return result


def build_wall_curve():
    curved,p=build_curve(label=CURVE_ID)
    for support,_ in d_supports(p):
        curved=curved.fuse(support).clean()
    assert curved.isValid() and len(curved.Solids())==1
    return curved,p


def export(out=Path('build/pr20-comparison'), *, only=None):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    shapes={}; reports={}
    for label,(roof,length) in VARIANTS.items():
        if only and label not in only: continue
        print('BUILD',label,flush=True)
        s,p=build_tunnel(roof=roof,transition=length,label=label)
        t=Tunnel();clear=ball_sweep(s,p,t,24.26);blocked=ball_sweep(s,p,t,28.)
        assert clear<VOLUME_TOL and blocked>VOLUME_TOL
        # Central/face roof probes distinguish the three intended alternatives.
        cy=t.floor+t.radius
        assert s.isInside(cq.Vector(-15.,0,cy+t.radius+.1))
        assert not s.isInside(cq.Vector(-15.,0,cy+t.radius-.1))
        if roof=='transition':
            assert not s.isInside(cq.Vector(0,0,t.ceiling-.1))
        shapes[label]=(s,p)
        reports[label]=dict(roof=roof,circular_lip_mm=1. if roof=='transition' else None,
            transition_length_mm=length if roof=='transition' else None,
            continuous_ball_path_mm3=clear,oversize_negative_mm3=blocked,
            minimum_roof_mm=p.height-(t.ceiling if roof=='transition' else cy+t.radius),
            minimum_side_wall_mm=p.depth/2-t.radius-t.entry)
    print('BUILD '+CURVE_ID,flush=True)
    s,p=build_wall_curve(); shapes[CURVE_ID]=(s,p)
    audit=receiver_audit(s,p)
    audit['calibration']['retained_complete_tubes']=list(RETAINED_TUBES)
    audit['calibration']['limitation']='Three full tubes, four closed D tubes and one solid segment; no corner floors. Physical fit and slicing untested.'
    assert audit['no_blocking_collision']
    hits=[intersection(s,cq.Solid.makeSphere(BALL/2,ball_centre(i/48),angleDegrees1=-90)) for i in range(49)]
    assert max(hits)<VOLUME_TOL
    baseline,_=build_curve();upper=cq.Solid.makeBox(100,100,60,cq.Vector(-50,-50,RAIL.floor+.01))
    # IDs differ on the inlet face; compare upper rail outside the label strip.
    label_mask=cq.Solid.makeBox(1,24,5,cq.Vector(-32,-28,9.5))
    delta=s.cut(baseline).fuse(baseline.cut(s)).cut(label_mask).intersect(upper)
    assert not delta.Solids() or delta.Volume()<VOLUME_TOL
    reports[CURVE_ID]=dict(complete_tubes=3,closed_d_tubes=4,solid_segments=1,
        supports=[r for _,r in d_supports(p)],square_wall_base=False,corner_floors_restored=False,
        receiver_audit=audit,ball_samples=49,ball_intersection_mm3=max(hits),
        added_volume_mm3=s.Volume()-baseline.Volume(),upper_track_delta_mm3=delta.Volume() if delta.Solids() else 0.)
    for label,(s,p) in shapes.items():
        folder=out/label;folder.mkdir(exist_ok=True)
        assert s.isValid() and len(s.Solids())==1
        cq.exporters.export(s,str(folder/'brick.step'))
        mesh=export_stl(s,folder/'brick.stl')
        restored=cq.importers.importStep(str(folder/'brick.step')).val()
        assert restored.isValid() and len(restored.Solids())==1 and abs(restored.Volume()-s.Volume())/s.Volume()<1e-7
        r=dict(passed=True,id=label,geometry=dict(bounds_mm=exact_bounds(s),parameters=asdict(p)),
            fit=dict(insertion=[],poses=[]),mesh=mesh,details=reports[label],
            design=design_manifest(p),source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            physical_fit_validated=False,slicing_validated=False,physical_rolling_validated=False)
        (folder/'report.json').write_text(json.dumps(r,indent=2)+'\n')
        if label==CURVE_ID:
            from parts.sloped_curve.design import render, course
            cq.exporters.export(cq.Compound.makeCompound(list(course(s))),str(folder/'assembly.step'))
            render(s,p,r,folder)
        else:
            viewer(s,p,r,folder)
        print('EXPORTED',label,s.Volume(),flush=True)
    return shapes

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--only',nargs='+')
    args=parser.parse_args()
    export(only=args.only)
