"""SB02-V1: no moving parts, 4x2x2 marble start box with a round top drop-hole.

Use exact BALL_TRACK opening diameter for the vertical entry. A narrow central
ridge forks the ball into continuous circular troughs at standard floor ports.
All lengths in mm; Z is up, receiver rim z=0.
"""
from dataclasses import dataclass, asdict, replace
from pathlib import Path
import hashlib
import json
import math
import struct
import cadquery as cq
from brickcad.model import brick_from_fit, receiver
from brickcad.connections import make_studs
from brickcad.marking import engrave
from brickcad.ports import Port
from brickcad.standards import BALL_TRACK, DUPLO, ROUNDED_EDGES
from brickcad.verify import exact_bounds, intersection, mesh_check, VOLUME_TOL
from parts.tunnel.e31_fit import add_e31_05_receiver_features

PART_ID = 'SB02-V1'

@dataclass(frozen=True)
class SplitStart:
    cells_x: int = 4
    cells_y: int = 2
    courses: int = 2
    entry_diameter: float = BALL_TRACK.opening  # same standard round rail/tunnel opening
    receiver_depth: float = 4.75
    exit_floor: float = BALL_TRACK.floor
    center_ridge_floor: float = 14.0
    passage_radius: float = BALL_TRACK.radius
    hole_bottom: float = 23.0  # intersection with circular tunnel void, not the running floor

    def __post_init__(self):
        if (self.cells_x, self.cells_y, self.courses) != (4, 2, 2):
            raise ValueError('SB02-V1 footprint is fixed to 4x2x2')
        if abs(self.entry_diameter - BALL_TRACK.opening) > 1e-7:
            raise ValueError('Top entry must use existing circular opening exactly')
        if abs(self.passage_radius - BALL_TRACK.radius) > 1e-7:
            raise ValueError('Both outlet channels must use existing rail section')
        if self.exit_floor-self.receiver_depth < 1.6 - 1e-8:
            raise ValueError('Insufficient floor above receiver')
        if not self.exit_floor+5 <= self.center_ridge_floor <= 14.5:
            raise ValueError('Ridge must split the ball while clearing top roof')
        if self.hole_bottom < self.center_ridge_floor + 7:
            raise ValueError('Entry cutter would flatten the splitter ridge')

    @property
    def half(self):
        return self.cells_x * DUPLO.pitch / 2

    def floor(self, x):
        s = min(1., abs(x)/self.half)
        return self.center_ridge_floor+(self.exit_floor-self.center_ridge_floor)*s

    def floor_gradient(self, x):
        return (self.center_ridge_floor-self.exit_floor)/self.half * (-1 if x>0 else 1)


def ports(config=SplitStart()):
    return (Port('west',(-config.half,0.,config.exit_floor),(-1.,0.,0.),config.passage_radius),
            Port('east',(config.half,0.,config.exit_floor),(1.,0.,0.),config.passage_radius))


def _channel(config):
    """Shared circular channel along both slopes; center is a sharp V ridge."""
    stations = [-config.half-1., -config.half,-24.,-16.,-8.,0.,8.,16.,24.,config.half,config.half+1.]
    wires = [cq.Workplane('YZ',origin=(x,0,config.floor(x)+config.passage_radius))
             .circle(config.passage_radius).val() for x in stations]
    return cq.Solid.makeLoft(wires,ruled=True)


def build_split_start(config=SplitStart()):
    p=replace(brick_from_fit('duplo-e27-play-v1',nx=4,ny=2,height_units=2),tube_radius=6.60)
    outer=cq.Workplane('XY').box(p.width,p.depth,p.height,centered=(True,True,False))
    outer=outer.edges('|Z').fillet(ROUNDED_EDGES.corner_radius)
    outer=outer.edges('>Z').chamfer(.35)
    body=receiver(p,outer,config.receiver_depth,ROUNDED_EDGES.receiver_entry)
    body=body.cut(_channel(config))
    # Circular top entry meets the curved passage; its cylindrical wall does not
    # extend down to the ridge, avoiding a flat resting platform for the ball.
    bore=cq.Solid.makeCylinder(config.entry_diameter/2,p.height-config.hole_bottom+2.,
                 cq.Vector(0,0,config.hole_bottom),cq.Vector(0,0,1))
    body=body.cut(bore)
    # The 4 outermost studs form the wall/hole/wall upper layout.
    outer_studs=[(x,y) for x,y in p.studs() if abs(x)>16.]
    body=body.union(make_studs(outer_studs,p.height,p.stud_radius,p.stud_inner_radius,
                              DUPLO.stud_height,ROUNDED_EDGES.stud_lip_radius))
    shape=add_e31_05_receiver_features(body.val().clean(),p.tubes(),p.tube_radius,
                                        receiver_depth=config.receiver_depth)
    if not shape.isValid() or len(shape.Solids()) != 1:
        raise ValueError('SB02 must be one valid connected BRep')
    shape=engrave(shape,PART_ID,x=0,y=-p.depth/2,z=10.)
    return shape,p


def center_samples(config=SplitStart(), count=15):
    """Static ball centers; actual gravity/friction behavior requires real tests."""
    radius=BALL_TRACK.ball_diameter/2
    incline=(config.center_ridge_floor-config.exit_floor)/config.half
    for i in range(count):
        x=-config.half+2*config.half*i/(count-1)
        yield cq.Vector(x,0.,config.floor(x)+radius*math.sqrt(1+incline**2)+.18)


def ball_clearance(config, shape, count=15):
    r=BALL_TRACK.ball_diameter/2
    values=[]
    for center in center_samples(config,count):
        ball=cq.Solid.makeSphere(r,center,angleDegrees1=-90)
        values.append(dict(x_mm=center.x,z_mm=center.z,intersection_mm3=intersection(shape,ball)))
    return values


def _normalize_binary_stl(stl):
    raw=Path(stl).read_bytes();n=struct.unpack_from('<I',raw,80)[0]
    kept=[]
    for i in range(n):
        tri=raw[84+50*i:134+50*i]
        v=struct.unpack('<12fH',tri)[3:12]
        if len({tuple(v[j:j+3]) for j in (0,3,6)})==3:kept.append(tri)
    Path(stl).write_bytes(raw[:80]+struct.pack('<I',len(kept))+b''.join(kept))


def export(out=Path('build/passive-split-box')):
    config=SplitStart();shape,p=build_split_start(config)
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    stl=out/'brick.stl'
    cq.exporters.export(shape,str(stl),tolerance=.025,angularTolerance=.15)
    _normalize_binary_stl(stl)
    cq.exporters.export(shape,str(out/'brick.step'))
    mesh=mesh_check(stl)
    checks={
        'brep_single_solid':shape.isValid() and len(shape.Solids())==1,
        'closed_stl':mesh['passed'],
        'outlet_floor_level':config.floor(config.half)==BALL_TRACK.floor,
        'top_hole_diameter':config.entry_diameter==BALL_TRACK.opening,
        'receiver_floor_at_exit':config.exit_floor-config.receiver_depth>=1.6-1e-6,
        'outlet_ports':len(ports(config))==2,
        'ball_path_clear':max(p['intersection_mm3'] for p in ball_clearance(config,shape,15))<VOLUME_TOL,
    }
    report={
        'part_id':PART_ID,'passed':all(checks.values()),'parameters':asdict(config),
        'checks':checks,'mesh':mesh,'fit_profile_id':p.fit_profile_id,
        'ports':[asdict(port) for port in ports(config)],
        'bounds_mm':exact_bounds(shape),
        'ball_path':ball_clearance(config,shape,15),
        'geometry_note':'Top opening equals BALL_TRACK.opening; central ridge slopes into two circular outlet sections.',
        'physical_rolling_validated':False,'physical_fit_validated':False,
        'support_free_slicing_validated':False,
        'limitations':['No moving parts; left/right is influenced by entry offset, not truly random.',
                       'Static sphere samples do not guarantee falling/rolling or exit speed.',
                       'Slicer bridging at roof and printed/printed holding force require validation.'],
        'sha256_stl':hashlib.sha256(stl.read_bytes()).hexdigest()
    }
    (out/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print(PART_ID,'PASS' if report['passed'] else 'FAIL',checks,flush=True)
    if not report['passed']:raise RuntimeError('SB02 geometry verification failed')
    return report

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',type=Path,default=Path('build/passive-split-box'))
    export(parser.parse_args().out)
