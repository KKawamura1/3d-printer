"""GW02-V1: two opposed gravity-driven flip cups, XZ-plane motion.

Upper cup accepts a 24.26 mm ball from +X, rotates ~180 degrees about Y,
then faces -X at the lower position. A fixed annular shroud limits early
release; its two sloped ports admit/release the ball. Static PoC only.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import cadquery as cq
from brickcad.course_contract import course_fit, add_course_receiver_features, RECEIVER_DEPTH_MM
from brickcad.model import receiver

VERSION = 'GW02-V1'
BALL_D = 24.26
BALL_R = BALL_D / 2
AXIS_Z = 81.0
POCKET_X, POCKET_Z = 10.0, 35.0
TUBE_SLOPE_DEG = 10.0
TUBE_LENGTH = 42.0
TUBE_OUT_R, TUBE_IN_R = 16.0, 13.65
SHROUD_IN_R, SHROUD_OUT_R = 62.1, 67.0
PORT_R = 15.0
AXLE_R, BORE_R = 2.45, 2.85


def vec(x, y, z):
    return cq.Vector(x, y, z)


def box(dx, dy, dz, cx=0, cy=0, cz=0):
    return cq.Workplane('XY').box(dx, dy, dz).translate((cx, cy, cz)).val()


def cyl(r, length, pos, direction=(0,1,0)):
    return cq.Solid.makeCylinder(r, length, vec(*pos), vec(*direction))


def rotate(shape, angle):
    return shape.rotate((0,0,0), (0,1,0), angle)


def tube_vectors():
    a = math.radians(TUBE_SLOPE_DEG)
    return math.cos(a), math.sin(a)


def mouth_at(angle):
    dx, dz = tube_vectors()
    shape_pt = vec(POCKET_X + TUBE_LENGTH/2*dx, 0, POCKET_Z + TUBE_LENGTH/2*dz)
    a = math.radians(angle)
    return vec(shape_pt.x*math.cos(a)+shape_pt.z*math.sin(a),0,
               -shape_pt.x*math.sin(a)+shape_pt.z*math.cos(a))


def rotor_local():
    dx, dz = tube_vectors()
    p = (POCKET_X, 0, POCKET_Z)
    start = (p[0]-dx*TUBE_LENGTH/2, 0, p[2]-dz*TUBE_LENGTH/2)
    out = cyl(TUBE_OUT_R,TUBE_LENGTH,start,(dx,0,dz))
    bore_start = (start[0]+dx*3,0,start[2]+dz*3)
    bore = cyl(TUBE_IN_R,TUBE_LENGTH-1,bore_start,(dx,0,dz))
    spoke = (cq.Workplane('XZ').polyline([
        (-5,-5),(5,-5),(POCKET_X+6, POCKET_Z),
        (POCKET_X-6,POCKET_Z),
    ]).close().extrude(9,both=True).val())
    hub = cyl(8.5, 40, (0,-20,0))
    cup = out.fuse(spoke)
    full = cup.fuse(rotate(cup,180)).fuse(hub)
    full = full.cut(bore).cut(rotate(bore,180))
    return full.cut(cyl(BORE_R,44,(0,-22,0))).clean()


def duplo_pad(x, y):
    """Shared E31-05 receiver underside; not a local fit approximation."""
    p=course_fit(nx=2, ny=2, height_units=1, height=6.35)
    outer=(cq.Workplane('XY').box(p.width,p.depth,p.height,centered=(True,True,False))
           .edges('|Z').fillet(0.8))
    pad=receiver(p,outer,RECEIVER_DEPTH_MM,0.25).val()
    pad=add_course_receiver_features(pad,p.tubes(),p.tube_radius,
                                     receiver_depth=RECEIVER_DEPTH_MM)
    return pad.translate((x,y,0))


def shroud_local():
    ring = cyl(SHROUD_OUT_R, 40, (0,-20,0)).cut(
        cyl(SHROUD_IN_R,42,(0,-21,0)))
    mouth = mouth_at(0)
    dx,dz = tube_vectors()
    # Both intake and discharge run down-left, after a half-turn of the cup.
    upper_start = (mouth.x-8*dx,0,mouth.z-8*dz)
    lower_start = (-mouth.x+8*dx,0,-mouth.z+8*dz)
    ring = ring.cut(cyl(PORT_R,85,upper_start,(dx,0,dz)))
    ring = ring.cut(cyl(PORT_R,85,lower_start,(-dx,0,-dz)))
    # Stationary legs are out of the central running lane.
    for x,y in ((48.0,-26.0),(-48.0,26.0)):
        leg=box(13,20,36.0,x,y,-57.0)
        pad=duplo_pad(x,32.0 if y>0 else -32.0).translate((0,0,-AXIS_Z))
        ring=ring.fuse(leg).fuse(pad)
    return ring.clean()


def stand(side):
    """Fixed bearing stand on the shared E31-05 DUPLO receiver."""
    y=side*32
    foot=duplo_pad(0,y)
    pillar=box(11,10,AXIS_Z-6.35,0,y,(AXIS_Z+6.35)/2)
    bearing=cyl(7.5,8,(0,y-4,AXIS_Z))
    block=foot.fuse(pillar).fuse(bearing)
    return block.cut(cyl(BORE_R,12,(0,y-6,AXIS_Z))).clean()


def axle():
    return cyl(AXLE_R,74,(0,-37,AXIS_Z)).fuse(cyl(5.5,3,(0,-40,AXIS_Z))).clean()


def pose(shape):
    return shape.translate((0,0,AXIS_Z))


def parts():
    return {
        'rotor':pose(rotor_local()),
        'shroud':pose(shroud_local()),
        'stand_front':stand(-1),
        'stand_back':stand(1),
        'axle':axle(),
    }


def static_checks(models):
    checks={
        'valid_five_parts':len(models)==5 and all(s.isValid() and len(s.Solids())==1 for s in models.values()),
        'ball_fits_bore':2*TUBE_IN_R>=BALL_D+2.5,
        'mouths_180_opposed':abs((mouth_at(0)+mouth_at(180)).Length)<1e-6,
        'upper_ball_center_above_lower':2*POCKET_Z>2*BALL_D,
        'shroud_clears_rotor': all(
            rotate(rotor_local(),a).intersect(shroud_local()).Volume()<0.05
            for a in range(0,181,15)),
        'shaft_clears_rotor':models['rotor'].intersect(models['axle']).Volume()<0.1,
        'shaft_clears_bearings':all(models[f'stand_{s}'].intersect(models['axle']).Volume()<0.1
                    for s in ('front','back')),
    }
    return checks


def export(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    ps=parts(); checks=static_checks(ps)
    for label,shape in ps.items():
        cq.exporters.export(shape,str(out/(label+'.stl')),tolerance=.09,angularTolerance=.2)
    cq.exporters.export(cq.Compound.makeCompound(list(ps.values())),str(out/'assembly.step'))
    report={'model_id':VERSION,'passed':all(checks.values()),'checks':checks,
            'physical_fit_validated':False,'gravity_motion_validated':False,
            'inlet_outlet_guides_included':False,
            'notes':'Bench PoC: no inlet/outlet guide tracks, index detent or axle lock; do not give to children'}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS' if report['passed'] else 'FAIL', [k for k,v in checks.items() if not v]);return report

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',default='build/gravity-wheel-g02-v1')
    export(ap.parse_args().out)
