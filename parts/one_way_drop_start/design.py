"""SB03-V1: fixed 2x2x2 top-drop marble start, one side outlet.

A 25.74 mm vertical circular inlet meets a descending 25.74 mm diameter
horizontal circular passage. The western end is CLOSED: there is just one
outlet, east (+X), at the standard 6.35 mm rail floor datum.

All lengths mm; underside receiver begins at z=0. This is a fresh CAD design,
not a modified historical experiment or a copy of PR72's split path.
"""
from dataclasses import dataclass, asdict, replace
from pathlib import Path
import hashlib
import json
import math
import struct

import cadquery as cq

from brickcad.model import brick_from_fit, receiver
from brickcad.marking import engrave
from brickcad.ports import Port
from brickcad.standards import BALL_TRACK, DUPLO, ROUNDED_EDGES
from brickcad.verify import exact_bounds, intersection, mesh_check, VOLUME_TOL
from parts.tunnel.e31_fit import add_e31_05_receiver_features

PART_ID = 'SB03-V1'


@dataclass(frozen=True)
class OneWayDrop:
    cells: int = 2
    courses: int = 2
    inlet_diameter: float = BALL_TRACK.opening
    passage_radius: float = BALL_TRACK.radius
    outlet_floor: float = BALL_TRACK.floor
    receiver_depth: float = 4.75
    # A 0.15 mm/mm uninterrupted descent from the blind western end to +X.
    slope: float = 0.15
    # The western channel is capped by 1.9 mm of the outer wall.
    blind_end_x: float = -14.0
    # The top bore must intersect the horizontal circular passage, without
    # erasing its sloping floor (floor around z=9 mm at x=0).
    inlet_bottom_z: float = 19.0

    def __post_init__(self):
        if (self.cells, self.courses) != (2, 2):
            raise ValueError('SB03-V1 must be 2x2x2')
        if abs(self.inlet_diameter - BALL_TRACK.opening) > 1e-7:
            raise ValueError('Keep round inlet identical to the standard opening')
        if abs(self.passage_radius - BALL_TRACK.radius) > 1e-7:
            raise ValueError('Keep standard circular outlet section')
        if abs(self.outlet_floor - BALL_TRACK.floor) > 1e-7:
            raise ValueError('Outlet floor must match the rail datum')
        if self.outlet_floor - self.receiver_depth < 1.6 - 1e-7:
            raise ValueError('Outlet floor too thin over the receiver')
        if not (0.12 <= self.slope <= .20):
            raise ValueError('Floor must descend visibly towards its only outlet')
        if not (-14.1 <= self.blind_end_x <= -13.9):
            raise ValueError('Blind wall must retain at least 1.8mm thickness')
        if not (17 <= self.inlet_bottom_z <= 20):
            raise ValueError('Round bore must open into (not below) the floor')

    @property
    def half(self):
        return self.cells * DUPLO.pitch/2

    def floor(self,x):
        return self.outlet_floor+self.slope*(self.half-x)


def ports(config=OneWayDrop()):
    return (Port('east', (config.half, 0., config.outlet_floor),
                 (1., 0., 0.), config.passage_radius),)


def _channel(config):
    """Full circular passage with a sealed western dead-end, open east port."""
    xs=(config.blind_end_x,-13.,-11.,-8.,-4.,0.,4.,8.,12.,
        config.half,config.half+1.)
    wires=[cq.Workplane('YZ',origin=(x,0.,config.floor(x)+config.passage_radius))
           .circle(config.passage_radius).val() for x in xs]
    return cq.Solid.makeLoft(wires,ruled=True)


def build_one_way_drop(config=OneWayDrop()):
    p=replace(brick_from_fit('duplo-e27-play-v1',nx=2,ny=2,height_units=2),
              tube_radius=6.60)
    outer=(cq.Workplane('XY')
           .box(p.width,p.depth,p.height,centered=(True,True,False))
           .edges('|Z').fillet(ROUNDED_EDGES.corner_radius)
           .edges('>Z').chamfer(.35))
    body=receiver(p,outer,config.receiver_depth,ROUNDED_EDGES.receiver_entry)
    body=body.cut(_channel(config))
    bore=cq.Solid.makeCylinder(config.inlet_diameter/2,
             p.height-config.inlet_bottom_z+1.,
             cq.Vector(0,0,config.inlet_bottom_z),cq.Vector(0,0,1))
    body=body.cut(bore)
    # There are deliberately no top studs: every +/-8 stud overlaps the
    # central 25.74mm round entry. Do not create clipped, unsafe studs.
    shape=add_e31_05_receiver_features(body.val().clean(),p.tubes(),p.tube_radius,
                                        receiver_depth=config.receiver_depth)
    if not shape.isValid() or len(shape.Solids())!=1:
        raise ValueError('SB03 requires a single valid BRep')
    shape=engrave(shape,PART_ID,x=0,y=-p.depth/2,z=10.)
    if not shape.isValid() or len(shape.Solids())!=1:
        raise ValueError('Engraving must preserve one solid')
    return shape,p


def ball_path_samples(config, count=17):
    """Floor-following static rolling samples; not a dynamics simulation."""
    r=BALL_TRACK.ball_diameter/2
    for j in range(count):
        x=(config.blind_end_x+r+.12)+(config.half-config.blind_end_x-r-.12)*j/(count-1)
        # Only centers inside the brick; outlet passing is checked separately.
        yield cq.Vector(x,0.,config.floor(x)+r*math.sqrt(1+config.slope**2)+.15)


def ball_path_intersections(config,shape,count=17):
    r=BALL_TRACK.ball_diameter/2
    return [intersection(shape,cq.Solid.makeSphere(r,c,angleDegrees1=-90))
            for c in ball_path_samples(config,count)]


def drop_intersections(config,shape):
    """Check the free-fall center over the round entry until floor approach."""
    r=BALL_TRACK.ball_diameter/2
    bottom=config.floor(0)+r*math.sqrt(1+config.slope**2)+.15
    values=[]
    for dz in (0.,2.,4.,6.,8.,10.,12.,14.,16.):
        center=cq.Vector(0,0,bottom+dz)
        values.append(intersection(shape,cq.Solid.makeSphere(r,center,angleDegrees1=-90)))
    return values


def _normalize_binary_stl(path):
    raw=path.read_bytes();n=struct.unpack_from('<I',raw,80)[0]
    kept=[]
    for i in range(n):
        tri=raw[84+50*i:134+50*i]
        vs=struct.unpack('<12fH',tri)[3:12]
        if len({tuple(vs[j:j+3]) for j in (0,3,6)})==3:kept.append(tri)
    path.write_bytes(raw[:80]+struct.pack('<I',len(kept))+b''.join(kept))


def export(out=Path('build/one-way-drop-start')):
    config=OneWayDrop();shape,p=build_one_way_drop(config)
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    stl=out/'brick.stl'
    cq.exporters.export(shape,str(stl),tolerance=.025,angularTolerance=.15)
    _normalize_binary_stl(stl)
    cq.exporters.export(shape,str(out/'brick.step'))
    mesh=mesh_check(stl)
    samples=ball_path_intersections(config,shape)
    fall=drop_intersections(config,shape)
    checks={
        'single_valid_brep':shape.isValid() and len(shape.Solids())==1,
        'closed_mesh':mesh['passed'],
        'standard_round_inlet':config.inlet_diameter==BALL_TRACK.opening,
        'standard_single_outlet':len(ports(config))==1 and config.floor(config.half)==BALL_TRACK.floor,
        'closed_west_wall':shape.isInside(cq.Vector(-15.,0.,config.floor(-15.)+config.passage_radius)),
        'open_east_port':not shape.isInside(cq.Vector(15.7,0.,config.floor(15.7)+config.passage_radius)),
        'running_floor_thickness':config.outlet_floor-config.receiver_depth>=1.6-1e-8,
        'downhill_to_east':config.floor(-12)>config.floor(0)>config.floor(12)>config.floor(16),
        'static_ball_path_clear':max(samples)<VOLUME_TOL,
        'static_center_drop_clear':max(fall)<VOLUME_TOL,
    }
    report={'part_id':PART_ID,'passed':all(checks.values()),
        'parameters':asdict(config),'checks':checks,'mesh':mesh,
        'fit_profile_id':p.fit_profile_id,'ports':[asdict(v) for v in ports(config)],
        'bounds_mm':exact_bounds(shape),
        'sampled_ball_collisions_mm3':samples,'sampled_drop_collisions_mm3':fall,
        'physical_rolling_validated':False,'physical_fit_validated':False,
        'support_free_slicing_validated':False,
        'limitations':['Static ball positions only; no rebound/velocity/rollout model.',
                       'Full circular inner passage may create overhangs; inspect Bambu Studio supports OFF.',
                       'The closed western end can trap a misaligned/rebounding ball: test repeatedly.',
                       '2x2 top opening consumes all top stud locations; top studs intentionally absent.'],
        'sha256_stl':hashlib.sha256(stl.read_bytes()).hexdigest()}
    (out/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print(PART_ID,'PASS' if report['passed'] else 'FAIL',checks,flush=True)
    if not report['passed']:
        raise RuntimeError('One-way drop geometry verification failed')
    return report


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',type=Path,default=Path('build/one-way-drop-start'))
    export(parser.parse_args().out)
