"""SB01-V1: manually selected left/right DUPLO marble-run start box.

Three independent, support-oriented print pieces: a gravity V-track body,
a lift-out rocking diverter, and an inverted-print bearing-retainer lid.
All dimensions mm, with z=0 at the DUPLO receiver rim.
"""
from dataclasses import asdict, dataclass, replace
from pathlib import Path
import hashlib
import json
import math
import struct
import cadquery as cq

from brickcad.connections import make_studs
from brickcad.marking import engrave
from brickcad.model import brick_from_fit, receiver
from brickcad.ports import Port
from brickcad.standards import BALL_TRACK, DUPLO, ROUNDED_EDGES
from brickcad.verify import exact_bounds, mesh_check
from parts.tunnel.e31_fit import add_e31_05_receiver_features

PART_ID = 'SB01-V1'


@dataclass(frozen=True)
class StartBox:
    cells: int = 4
    courses: int = 3
    receiver_depth: float = 4.75
    exit_floor: float = BALL_TRACK.floor
    drop: float = DUPLO.height
    passage_width: float = 32.2
    axle_z: float = 40.0
    axle_radius: float = 3.0
    bearing_radius: float = 3.45
    tilt_deg: float = 18.0
    lid_thickness: float = 2.8
    lid_peg_radius: float = 2.30
    socket_radius: float = 2.55
    paddle_half_length: float = 16.0
    paddle_half_width: float = 15.20

    def __post_init__(self):
        if self.cells != 4 or self.courses != 3:
            raise ValueError('V1 has a fixed 4x4x3 footprint')
        if not (self.exit_floor - self.receiver_depth >= 1.6 - 1e-9):
            raise ValueError('Receiver would pierce the exit running floor')
        if not (self.passage_width > BALL_TRACK.ball_diameter + 5.0):
            raise ValueError('Channel too narrow for a 24.26mm marble')
        if not (self.paddle_half_width + .5 < self.passage_width / 2):
            raise ValueError('Rocking paddle needs wall clearance')
        if not (0 < self.tilt_deg <= 22 and self.axle_radius < self.bearing_radius):
            raise ValueError('Invalid pivot clearance/tilt')
        if not (self.axle_z + self.paddle_half_length * math.sin(math.radians(self.tilt_deg)) + 14 < self.courses*DUPLO.height + 4):
            raise ValueError('Rocking paddle interferes with top entry')

    @property
    def half(self):
        return self.cells * DUPLO.pitch / 2

    def floor(self, x):
        return self.exit_floor + self.drop * (1 - min(1, abs(x) / self.half))


def ports(config=StartBox()):
    return (Port('left', (-config.half, 0, config.exit_floor), (-1., 0., 0.), BALL_TRACK.radius),
            Port('right', (config.half, 0, config.exit_floor), (1., 0., 0.), BALL_TRACK.radius))


def _profile(config):
    return replace(brick_from_fit('duplo-e27-play-v1', nx=4, ny=4, height_units=3),
                   tube_radius=6.60)


def _peg_locations():
    return [(x,y) for x in (-16.,16.) for y in (-26.,26.)]


def build_body(config=StartBox()):
    p = _profile(config)
    outer = cq.Workplane('XY').box(p.width, p.depth, p.height, centered=(True,True,False))
    outer = outer.edges('|Z').fillet(ROUNDED_EDGES.corner_radius)
    body = receiver(p, outer, config.receiver_depth, ROUNDED_EDGES.receiver_entry)

    # A roofless through-trough, descending by one course to either side.
    # The XZ wire extrudes along +Y, leaving tall guide walls on both sides.
    a = config.passage_width / 2
    tool = (cq.Workplane('XZ', origin=(0,-a,0))
            .polyline([(-config.half-1,config.exit_floor-.6),
                       (-config.half,config.exit_floor),
                       (0,config.exit_floor+config.drop),
                       (config.half,config.exit_floor),
                       (config.half+1,config.exit_floor-.6),
                       (config.half+1,p.height+8),
                       (-config.half-1,p.height+8)])
            .close().extrude(-config.passage_width))
    body = body.cut(tool)

    # Open topped, round-bottom axle seats: lift lever in from above, then cap.
    seat = cq.Solid.makeCylinder(config.bearing_radius, p.depth+2,
             cq.Vector(0,-p.depth/2-1,config.axle_z), cq.Vector(0,1,0))
    slot = (cq.Workplane('XY').box(2*config.bearing_radius,p.depth+2,
                                   p.height-config.axle_z+2,
                                   centered=(True,True,False))
            .translate((0,0,config.axle_z)).val())
    body = body.cut(seat).cut(slot)
    # Two wall-attached, vertical hard stops arrest the rocker around +/-22deg.
    # They sit outside a marble's 12.13mm radius from the centreline, and are
    # built upward from the floor so no floating material needs support.
    for x in (-13.,13.):
        stop = (cq.Workplane('XY')
                .box(3.8,2.0,15.0,centered=(True,True,False))
                .translate((x,-15.2,17.0)))
        body = body.union(stop)
    for x,y in _peg_locations():
        socket = cq.Solid.makeCylinder(config.socket_radius, 5.5,
                       cq.Vector(x,y,p.height-5.2), cq.Vector(0,0,1))
        body = body.cut(socket)

    # Only roof-free rim studs; the lid has through-holes around these.
    studs = [(x,y) for x,y in p.studs() if abs(y)>20]
    tall_studs = make_studs(studs,p.height,p.stud_radius,p.stud_inner_radius,
                            p.stud_height+config.lid_thickness,
                            ROUNDED_EDGES.stud_lip_radius)
    body = body.union(tall_studs)
    shape = add_e31_05_receiver_features(body.val().clean(),p.tubes(),p.tube_radius,
                                          receiver_depth=config.receiver_depth)
    if not shape.isValid() or len(shape.Solids()) != 1:
        raise ValueError('Start box body must be one valid solid')
    shape = engrave(shape,PART_ID,x=0,y=-p.depth/2,z=14.)
    return shape,p


def build_lid(config=StartBox()):
    """Assembled pose, with pegs below the frame; rotate 180 X to print."""
    p = _profile(config)
    frame = cq.Workplane('XY').box(p.width,p.depth,config.lid_thickness,
                                    centered=(True,True,False))
    # Large open center prevents roof collisions at the rocking ramp and
    # allows a child to place the ball at the central diverter.
    aperture = cq.Workplane('XY').box(52.,35.,config.lid_thickness+2,
                        centered=(True,True,False)).translate((0,0,-1))
    frame = frame.cut(aperture)
    for x,y in [p.studs()[i] for i in range(len(p.studs())) if abs(p.studs()[i][1])>20]:
        hole = cq.Solid.makeCylinder(p.stud_radius+.3,config.lid_thickness+2,
                         cq.Vector(x,y,-1),cq.Vector(0,0,1))
        frame = frame.cut(hole)
    for x,y in _peg_locations():
        peg = cq.Solid.makeCylinder(config.lid_peg_radius,4.6,
                        cq.Vector(x,y,-4.6),cq.Vector(0,0,1))
        frame = frame.union(peg)
    shape=frame.val().clean()
    if not shape.isValid() or len(shape.Solids()) != 1:
        raise ValueError('Lid must be one valid solid')
    return shape


def build_lever(config=StartBox()):
    """Unrotated rocking paddle around Y; shaft has a printable flat underside."""
    # A central platform provides an unambiguous left/right incline.
    # The paddle top entirely covers the axle: a ball cannot catch on the
    # shaft just after falling through the top opening.
    paddle = cq.Workplane('XY').box(2*config.paddle_half_length,
                  2*config.paddle_half_width,5.85,centered=(True,True,False)).translate((0,0,-2.65))
    axle = cq.Solid.makeCylinder(config.axle_radius,72.,
                         cq.Vector(0,-42.,0),cq.Vector(0,1,0))
    # Shave 0.35mm off the axle bottom: one stable, support-free print face.
    low = cq.Workplane('XY').box(100,100,10).translate((0,0,-7.65)).val()
    axle = axle.cut(low)
    paddle = paddle.union(axle)
    grip = (cq.Workplane('XY').box(8.,9.,16.,centered=(True,True,False))
            .translate((0,-41.5,0)))
    lever = paddle.union(grip).val().clean()
    if not lever.isValid() or len(lever.Solids()) != 1:
        raise ValueError('Lever must be one valid solid')
    return lever


def assembled(config=StartBox(), side='left'):
    """Return body, lid and lever in chosen installed pose (for clearance)."""
    if side not in ('left','right'):
        raise ValueError('side must be left or right')
    body,p=build_body(config)
    lid=build_lid(config).translate((0,0,p.height))
    # +Y rotation tips positive X down, negative X up.
    angle = config.tilt_deg if side == 'right' else -config.tilt_deg
    lever=build_lever(config).rotate((0,0,0),(0,1,0),angle).translate((0,0,config.axle_z))
    return body,lid,lever


def _stl(shape,path,tolerance=.035):
    cq.exporters.export(shape,str(path),tolerance=tolerance,angularTolerance=.20)
    raw=path.read_bytes()
    triangles=[]
    for i in range(struct.unpack_from('<I',raw,80)[0]):
        tri=raw[84+50*i:134+50*i]
        coords=struct.unpack('<12fH',tri)[3:12]
        if len({tuple(coords[j:j+3]) for j in (0,3,6)})==3:
            triangles.append(tri)
    path.write_bytes(raw[:80]+struct.pack('<I',len(triangles))+b''.join(triangles))
    return mesh_check(path)


def export(out=Path('build/switch-start-box')):
    config=StartBox()
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    body,p=build_body(config)
    lid=build_lid(config)
    lever=build_lever(config)
    # Body as-built; lid flipped so its flat face sits on the bed, pegs rise.
    lid_print=lid.rotate((0,0,0),(1,0,0),180).translate((0,0,config.lid_thickness))
    # The lever's planar bottom can rest on the bed without printed support.
    lever_print=lever.translate((0,0,2.65))
    parts={'brick.stl':body,'lid.stl':lid_print,'lever.stl':lever_print}
    meshes={name:_stl(shape,out/name) for name,shape in parts.items()}
    checks={'valid_solids':all(s.isValid() and len(s.Solids())==1 for s in parts.values()),
            'closed_meshes':all(m['passed'] for m in meshes.values()),
            'one_course_drop':abs(config.floor(0)-config.floor(config.half)-DUPLO.height)<1e-8,
            'minimum_floor_1p6':config.exit_floor-config.receiver_depth>=1.6-1e-8,
            'stud_fit':(p.stud_radius,p.stud_inner_radius,p.tube_radius,p.cavity_xy)==(4.7,3.2,6.6,(57.4,57.4)),
            'two_side_ports':len(ports(config))==2}
    report={'part_id':PART_ID,'passed':all(checks.values()),'parameters':asdict(config),
            'fit_profile_id':p.fit_profile_id,'ports':[asdict(v) for v in ports(config)],
            'checks':checks,'mesh':{'passed':all(m['passed'] for m in meshes.values()),'files':meshes},'body_bounds_mm':exact_bounds(body),
            'assembly':'Insert rocking axle into top slots; insert four lid pegs into matching sockets. Feed at center and tilt external grip to select left/right.',
            'print_orientations':'Body upright; lid inverted (pegs up); lever paddle flat down.',
            'physical_rolling_validated':False,'physical_fit_validated':False,
            'physical_lever_retention_validated':False,'slicer_support_free_validated':False,
            'limitations':['Roofless inspection hatch rather than fixed central funnel.',
                           'Printed socket/pegs are friction-fit: inspect and secure before child use.',
                           'Wall stops limit the rocker to two tilt sides; no tactile snap detent in V1.',
                           'Rigid geometry tests do not prove rolling, clutch or operating force.'],
            'sha256_stl':{name:hashlib.sha256((out/name).read_bytes()).hexdigest() for name in parts}}
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(PART_ID,'PASS' if report['passed'] else 'FAIL',checks,flush=True)
    if not report['passed']:raise RuntimeError('Start box geometry verification failed')
    return report


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',type=Path,default=Path('build/switch-start-box'))
    export(parser.parse_args().out)
