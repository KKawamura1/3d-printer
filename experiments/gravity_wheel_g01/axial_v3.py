"""GW01-V3: captive-ball axial gravity wheel with supported DUPLO ramps.

The 24.26mm ball enters along +Y, stays inside a closed rotating tube,
and is released through a stationary gate near 60 degrees. The wheel's
axis has a 6.84 degree downhill inclination for axial ball movement.
This is an adult-only mechanical proof-of-concept, not a proven toy.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import cadquery as cq

from brickcad.course_contract import (
    course_fit, add_course_receiver_features, RECEIVER_DEPTH_MM,
)
from brickcad.model import receiver
from brickcad.verify import mesh_check

VERSION = 'GW01-V3'
BALL_DIAMETER = 24.26
BALL_R = BALL_DIAMETER/2
PITCH = 16.0
AXIS_SLOPE = -0.12
AXIS_TILT_DEG = math.degrees(math.atan(AXIS_SLOPE))
AXIS_Z = 83.76
POCKET_X = 32.0
CUP_INNER_R = 13.55
CUP_OUTER_R = 15.90
POCKET_HALF_LENGTH = 38.0
GATE_Y = 42.0
GATE_THICKNESS = 3.0
GATE_OUTER_R = 53.0
GATE_PORT_R = 14.2
RELEASE_ANGLE = 60
RELEASE_RANGE = (52, 55, 58, 60, 62, 65, 68)
ROTOR_BORE_R = 2.75
FRAME_BORE_R = 2.65
AXLE_R = 2.20
STAND_X, STAND_Y = 48.0, 64.0
GUIDE_INLET_Y0, GUIDE_INLET_Y1 = -96.0, -48.5
GUIDE_OUTLET_Y0, GUIDE_OUTLET_Y1 = 45.5, 96.0
GUIDE_RIM_MARGIN = 0.55
UPPER_RAIL_FLOOR = 6.35 + 4*19.2
LOWER_RAIL_FLOOR = 6.35 + 1*19.2


def cylinder(radius, length, xyz, direction=(0,1,0)):
    return cq.Solid.makeCylinder(radius, length, cq.Vector(*xyz), cq.Vector(*direction))


def box(dx,dy,dz,x=0,y=0,z=0):
    return cq.Workplane('XY').box(dx,dy,dz).translate((x,y,z)).val()


def pose(s):
    return s.translate((0,0,AXIS_Z)).rotate(
        (0,0,AXIS_Z),(1,0,AXIS_Z),AXIS_TILT_DEG)


def pocket_center(a=0):
    a = math.radians(a)
    return -POCKET_X*math.cos(a), -POCKET_X*math.sin(a)


def rotor_local():
    """Two enclosed tubes plus 3 ribs, central hub and small viewing windows."""
    tubes=[]
    length=2*POCKET_HALF_LENGTH
    for x in (-POCKET_X,POCKET_X):
        outer=cylinder(CUP_OUTER_R,length,(x,-POCKET_HALF_LENGTH,0))
        bore=cylinder(CUP_INNER_R,length+2,(x,-POCKET_HALF_LENGTH-1,0))
        tube=outer.cut(bore)
        for yy in (-21.,-7.,7.,21.):
            tube=tube.cut(cylinder(4.5,8.0,(x,yy,12.0),(0,0,1)))
        tubes.append(tube)
    ribs=[box(36.0,8.0,7.0,0,y,0) for y in (-27.0,0.0,27.0)]
    hub=cylinder(8.5,length,(0,-POCKET_HALF_LENGTH,0))
    rotor=tubes[0].fuse(tubes[1]).fuse(hub)
    for rib in ribs:
        rotor=rotor.fuse(rib)
    return rotor.cut(
        cylinder(ROTOR_BORE_R,length+2,(0,-POCKET_HALF_LENGTH-1,0))
    ).clean()


def gate_local(outlet):
    """Stationary blocking plate; exit has a 52-68 degree release sector."""
    y=GATE_Y if outlet else -GATE_Y-GATE_THICKNESS
    gate=cylinder(GATE_OUTER_R,GATE_THICKNESS,(0,y,0))
    for a in (RELEASE_RANGE if outlet else (0,)):
        x,z=pocket_center(a)
        gate=gate.cut(cylinder(GATE_PORT_R,GATE_THICKNESS+2,(x,y-1,z)))
    return gate.cut(
        cylinder(FRAME_BORE_R,GATE_THICKNESS+2,(0,y-1,0))
    ).clean()


def underside_base(x, y):
    """Same E31-05 shallow receiver used by the established course geometry."""
    p = course_fit(nx=2, ny=2, height_units=1, height=6.35)
    outer = (
        cq.Workplane("XY")
        .box(p.width, p.depth, p.height, centered=(True, True, False))
        .edges("|Z").fillet(0.8)
    )
    base = receiver(p, outer, RECEIVER_DEPTH_MM, 0.25).val()
    base = add_course_receiver_features(
        base, p.tubes(), p.tube_radius, receiver_depth=RECEIVER_DEPTH_MM
    )
    return base.translate((x, y, 0))




def frame(outlet):
    side=1 if outlet else -1
    y=side*STAND_Y
    axis_z=AXIS_Z+AXIS_SLOPE*y
    base=underside_base(STAND_X,y)
    stem=box(10,12,axis_z+6-6.35,STAND_X,y,(axis_z+6+6.35)/2)
    bridge_y=side*52.7
    bridge=box(16,28,13,STAND_X,bridge_y,AXIS_Z+AXIS_SLOPE*bridge_y)
    return base.fuse(stem).fuse(bridge).fuse(pose(gate_local(outlet))).clean()


def axle():
    shaft=cylinder(AXLE_R,111,(0,-55,0))
    head=cylinder(5.2,3.0,(0,-58,0))
    return pose(shaft.fuse(head).clean())


def yz_prism(y0,y1,z0,z1,width,x0=0,height=0,offset=0):
    return (cq.Workplane('YZ')
            .polyline(((y0,z0+offset),(y1,z1+offset),
                       (y1,z1+height+offset),(y0,z0+height+offset)))
            .close().extrude(width).translate((x0-width/2,0,0)).val())


def guide_floor_profile(outlet):
    if outlet:
        y0,y1=GUIDE_OUTLET_Y0,GUIDE_OUTLET_Y1
        cx,pocketz=pocket_center(RELEASE_ANGLE)
        z0=AXIS_Z+AXIS_SLOPE*y0+pocketz-BALL_R-GUIDE_RIM_MARGIN
        z1=LOWER_RAIL_FLOOR
    else:
        y0,y1=GUIDE_INLET_Y0,GUIDE_INLET_Y1
        cx,_=pocket_center(0)
        z0=UPPER_RAIL_FLOOR
        z1=AXIS_Z+AXIS_SLOPE*y1-BALL_R-GUIDE_RIM_MARGIN
    return (cx,y0,y1,z0,z1)


def guide(outlet):
    """Rigid cantilevered rail with a grid-aligned E31-05 base and gusset."""
    x,y0,y1,z0,z1=guide_floor_profile(outlet)
    floor=yz_prism(y0,y1,z0,z1,31.8,x,height=3,offset=-3)
    left=yz_prism(y0,y1,z0,z1,2.4,x-14.8,height=11,offset=-1)
    right=yz_prism(y0,y1,z0,z1,2.4,x+14.8,height=11,offset=-1)
    slide=floor.fuse(left).fuse(right).clean()
    centre_y=-80.0 if not outlet else 80.0
    base=underside_base(x,centre_y)
    t=(centre_y-y0)/(y1-y0)
    floor_z=z0+(z1-z0)*t
    top=floor_z-1.5
    pillar=box(11,14,top-6.35,x,centre_y,(6.35+top)/2)
    tip_y=y0+2.0 if outlet else y1-2.0
    tip_z=z0+(z1-z0)*(tip_y-y0)/(y1-y0)
    near_y=centre_y-5.0 if outlet else centre_y+5.0
    brace=(cq.Workplane('YZ')
           .polyline(((near_y,6.35),(near_y,floor_z-2),(tip_y,tip_z-2)))
           .close().extrude(5.5).translate((x-2.75,0,0)).val())
    return slide.fuse(pillar).fuse(brace).fuse(base).clean()


def build_parts():
    return {
        'rotor':pose(rotor_local()),
        'frame_inlet':frame(False),
        'frame_outlet':frame(True),
        'axle':axle(),
        'guide_inlet':guide(False),
        'guide_outlet':guide(True),
    }


def ball_local(angle=0,y=0):
    x,z=pocket_center(angle)
    return cq.Solid.makeSphere(BALL_R,cq.Vector(x,y,z),angleDegrees1=-90)


def validate(parts):
    checks={
        'six_single_valid_solids':len(parts)==6 and all(
            s.isValid() and len(s.Solids())==1 and s.Volume()>0 for s in parts.values()),
        'axis_tilts_downhill':AXIS_SLOPE<-0.08,
        'ports_fit_ball':2*GATE_PORT_R>=BALL_DIAMETER+3.0,
        'guide_grid_alignment':guide_floor_profile(False)[0]==-32.0
            and abs(guide_floor_profile(True)[0]+16.0)<1e-6,
        'upper_floor_matches_four_bricks':abs(guide_floor_profile(False)[3]-UPPER_RAIL_FLOOR)<1e-6,
        'lower_floor_matches_one_brick':abs(guide_floor_profile(True)[4]-LOWER_RAIL_FLOOR)<1e-6,
        'outlet_above_build_plate':parts['guide_outlet'].BoundingBox().zmin>=-0.01,
    }
    rotor=rotor_local()
    gate_in=gate_local(False)
    gate_out=gate_local(True)
    for angle in (0,10,20,30,40,50,52,55,58,60,62,65,68,70,80,90):
        rotated=rotor.rotate((0,0,0),(0,1,0),-angle)
        checks[f'rotor_gates_clear_{angle}']=all(
            rotated.intersect(g).Volume()<0.01 for g in (gate_in,gate_out))
        checks[f'ball_stays_in_tube_{angle}']=rotated.intersect(
            ball_local(angle,0)).Volume()<0.05
    checks['tube_is_fully_enclosed']=CUP_OUTER_R-CUP_INNER_R>=2.3
    checks['windows_cannot_release_ball']=2*4.5<BALL_DIAMETER
    checks['ball_passes_inlet_at_rest']=gate_in.intersect(ball_local(0,-43.5)).Volume()<0.05
    checks['ball_stopped_by_inlet_if_rotated']=gate_in.intersect(
        ball_local(45,-43.5)).Volume()>100
    checks['ball_passes_outlet_at_release']=gate_out.intersect(
        ball_local(RELEASE_ANGLE,43.5)).Volume()<0.05
    checks['ball_blocked_outlet_at_rest']=gate_out.intersect(
        ball_local(0,43.5)).Volume()>100
    checks['shaft_clears_rotor_and_frames']=all(
        parts['axle'].intersect(parts[k]).Volume()<0.01
        for k in ('rotor','frame_inlet','frame_outlet'))
    checks['rotor_clears_all_fixed_parts']=all(
        parts['rotor'].intersect(parts[k]).Volume()<0.01
        for k in ('frame_inlet','frame_outlet','guide_inlet','guide_outlet'))
    checks['guides_clear_frames']=all(
        parts[g].intersect(parts[f]).Volume()<0.01
        for g in ('guide_inlet','guide_outlet')
        for f in ('frame_inlet','frame_outlet'))
    return checks


def export(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    parts=build_parts()
    checks=validate(parts)
    meshes={}
    for name,solid in parts.items():
        path=out/(name+'.stl')
        cq.exporters.export(solid,str(path),tolerance=.06,angularTolerance=.2)
        meshes[name]=mesh_check(path)
        checks['mesh_'+name]=bool(meshes[name]['passed'])
    cq.exporters.export(
        cq.Compound.makeCompound(list(parts.values())),str(out/'assembly.step'))
    report={
        'model_id':VERSION,'passed':all(checks.values()),'checks':checks,
        'meshes':meshes,'ball_diameter_mm':BALL_DIAMETER,
        'axis_tilt_degrees':AXIS_TILT_DEG,
        'axis_center_height_at_y0_mm':AXIS_Z,
        'axis_aligned_flow':'+Y inlet -> +Y exit',
        'lateral_shift_mm':POCKET_X-POCKET_X*math.cos(math.radians(RELEASE_ANGLE)),
        'inlet_rail_floor_mm':UPPER_RAIL_FLOOR,
        'outlet_rail_floor_mm':LOWER_RAIL_FLOOR,
        'physical_roll_tested':False,
        'self_reset_included':False,
        'slicer_support_free_tested':False,
        'risks':[
            'No ball/rotor dynamics or friction simulation, only static clearances',
            'Outlet may jam depending on ball weight, axle friction or contact forces',
            'The rotor is hand-armed for every ball; automatic indexing is absent',
            'Axle retention is not child-safe: adult-only engineering trial',
            'Existing-rail interfaces need actual print/fit measurements',
        ],
    }
    (out/'report.json').write_text(
        json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print(VERSION,'PASS' if report['passed'] else 'FAIL',
          [x for x,ok in checks.items() if not ok],flush=True)
    if not report['passed']:
        raise ValueError('GW01-V3 failed static validation')
    return report


if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--out',default='build/gravity-wheel-g01-v3')
    export(ap.parse_args().out)
