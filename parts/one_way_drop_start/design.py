"""SB03-V2: 2x2x2 top-drop start using a smooth R16 vertical 90-degree turn.

The R16 arc is inspired by the C01 2x2 flat sharp curve, placed in the XZ
plane. A single continuous circular-section loft provides a vertical entry
and a tangent horizontal eastern exit; no flat floor impact or moving parts.
Top opening and outlet match BALL_TRACK; Z=0 is the receiver underside.
Static geometry does not establish physical rolling performance.
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

PART_ID = 'SB03-V2'


@dataclass(frozen=True)
class OneWayDrop:
    cells: int = 2
    courses: int = 2
    inlet_diameter: float = BALL_TRACK.opening
    passage_radius: float = BALL_TRACK.radius
    outlet_floor: float = BALL_TRACK.floor
    receiver_depth: float = 4.75
    bend_radius: float = DUPLO.pitch  # R16, C01-like sharp turn
    loft_steps: int = 24
    inlet_extension: float = 2.0
    outlet_extension: float = 1.4

    def __post_init__(self):
        if (self.cells, self.courses) != (2, 2):
            raise ValueError('SB03-V2 must be 2x2x2')
        if abs(self.inlet_diameter - BALL_TRACK.opening) > 1e-7:
            raise ValueError('Inlet must use standard circular opening')
        if abs(self.passage_radius - BALL_TRACK.radius) > 1e-7:
            raise ValueError('Outlet section must use standard radius')
        if abs(self.outlet_floor - BALL_TRACK.floor) > 1e-7:
            raise ValueError('Outlet floor must match standard datum')
        if self.outlet_floor-self.receiver_depth < 1.6-1e-7:
            raise ValueError('Floor too thin over underside receiver')
        if abs(self.bend_radius - DUPLO.pitch) > 1e-7:
            raise ValueError('SB03-V2 requires R16')
        if not isinstance(self.loft_steps,int) or not 12<=self.loft_steps<=48:
            raise ValueError('Use 12..48 stations for the smooth loft')
        if not 1.<=self.inlet_extension<=3.:
            raise ValueError('Inlet tangent must extend beyond top')
        if not .6<=self.outlet_extension<=3.:
            raise ValueError('Exit tangent must extend beyond east face')
        if self.inlet_tangent_z >= self.courses*DUPLO.height:
            raise ValueError('Entry tangent above the roof')

    @property
    def half(self):
        return self.cells*DUPLO.pitch/2

    @property
    def outlet_axis_z(self):
        return self.outlet_floor+self.passage_radius

    @property
    def inlet_tangent_z(self):
        return self.outlet_axis_z+self.bend_radius

def ports(config=OneWayDrop()):
    return (Port('east', (config.half, 0., config.outlet_floor),
                 (1., 0., 0.), config.passage_radius),)


def centerline(config=OneWayDrop(), progress=0.):
    """Circular R16 path from vertical-down to horizontal-east."""
    if not 0.<=progress<=1.:
        raise ValueError('Arc progress outside 0..1')
    theta=math.pi+math.pi/2*progress
    r=config.bend_radius
    return cq.Vector(r+r*math.cos(theta),0.,
                     config.inlet_tangent_z+r*math.sin(theta))


def _section(x,z,tangent_x,tangent_z,radius):
    """Consistent circle orientation avoids twists between loft stations."""
    plane=cq.Plane(origin=(x,0.,z),xDir=(0.,1.,0.),
                   normal=(tangent_x,0.,tangent_z))
    return cq.Workplane(plane).circle(radius).val()


def _channel(config):
    """Single uninterrupted loft prevents bore/torus boolean seam defects.

    The centreline uses the same R16 as C01, rotated to the vertical XZ plane.
    Two straight tangent portions lead into and out of the quarter-circle.
    """
    top=config.courses*DUPLO.height
    inlet_r=config.inlet_diameter/2
    wires=[_section(0.,z,0.,-1.,inlet_r) for z in
           (top+config.inlet_extension,top+.2,top,top-.8)]
    wires.append(_section(0.,config.inlet_tangent_z,0.,-1.,
                          config.passage_radius))
    for i in range(1,config.loft_steps+1):
        t=i/config.loft_steps
        theta=math.pi+math.pi/2*t
        p=centerline(config,t)
        wires.append(_section(p.x,p.z,-math.sin(theta),math.cos(theta),
                              config.passage_radius))
    for x in (config.half+.3,config.half+config.outlet_extension):
        wires.append(_section(x,config.outlet_axis_z,1.,0.,
                              config.passage_radius))
    return cq.Solid.makeLoft(wires,ruled=False)

def build_one_way_drop(config=OneWayDrop()):
    p=replace(brick_from_fit('duplo-e27-play-v1',nx=2,ny=2,height_units=2),
              tube_radius=6.60)
    outer=(cq.Workplane('XY')
           .box(p.width,p.depth,p.height,centered=(True,True,False))
           .edges('|Z').fillet(ROUNDED_EDGES.corner_radius)
           .edges('>Z').chamfer(.35))
    body=receiver(p,outer,config.receiver_depth,ROUNDED_EDGES.receiver_entry)
    body=body.cut(_channel(config))
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


def ball_path_samples(config=OneWayDrop(), count=25):
    """Static ball centres following the 90-degree R16 centreline."""
    if count<3:
        raise ValueError('Need >=3 sample points')
    for i in range(count):
        yield centerline(config,i/(count-1))


def ball_path_intersections(config,shape,count=25):
    radius=BALL_TRACK.ball_diameter/2
    return [intersection(shape,cq.Solid.makeSphere(
        radius,c,angleDegrees1=-90))
        for c in ball_path_samples(config,count)]


def inlet_ball_intersections(config,shape):
    """Clearance of the sphere above and at the bend entrance."""
    radius=BALL_TRACK.ball_diameter/2
    return [intersection(shape,cq.Solid.makeSphere(
        radius,cq.Vector(0.,0.,config.inlet_tangent_z+dz),
        angleDegrees1=-90)) for dz in (0.,1.,2.,4.,8.,12.)]

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
    fall=inlet_ball_intersections(config,shape)
    top_z=p.height-.1
    hole_r=config.inlet_diameter/2
    arc_start,arc_end=centerline(config,0),centerline(config,1)
    checks={
        'single_valid_brep':shape.isValid() and len(shape.Solids())==1,
        'closed_mesh':mesh['passed'],
        'standard_round_inlet':config.inlet_diameter==BALL_TRACK.opening,
        'round_top_opening':not shape.isInside(cq.Vector(hole_r-.3,0,top_z))
                         and shape.isInside(cq.Vector(hole_r+.8,0,top_z)),
        'standard_east_port':len(ports(config))==1
            and abs(arc_end.z-config.outlet_axis_z)<1e-7,
        'west_wall_sealed':shape.isInside(cq.Vector(-15.,0.,25.)),
        'receiver_floor_preserved':config.outlet_floor-config.receiver_depth>=1.6-1e-8,
        'vertical_inlet_tangent':abs(arc_start.x)<1e-7,
        'horizontal_east_tangent':abs(arc_end.x-config.half)<1e-7,
        'arc_ball_clear':max(samples)<VOLUME_TOL,
        'vertical_entry_ball_clear':max(fall)<VOLUME_TOL,
    }
    report={'part_id':PART_ID,'passed':all(checks.values()),
        'parameters':asdict(config),'checks':checks,'mesh':mesh,
        'fit_profile_id':p.fit_profile_id,
        'ports':[asdict(v) for v in ports(config)],
        'bounds_mm':exact_bounds(shape),
        'arc_centres_xyz_mm':[[v.x,v.y,v.z] for v in ball_path_samples(config)],
        'sampled_ball_collisions_mm3':samples,
        'sampled_inlet_collisions_mm3':fall,
        'physical_rolling_validated':False,'physical_fit_validated':False,
        'support_free_slicing_validated':False,
        'limitations':[
            'Static sphere clearance does not guarantee real rolling speed or low rebound.',
            'The ball falls before it touches the curved wall: collisions are not simulated.',
            'R16 is a tight bend for the 24.26mm ball; check for jams with actual prints.',
            'Inner curved ceiling and unsupported spans require a slicer/print test.',
            'Central hole consumes all top stud positions; deliberately studless.'],
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
