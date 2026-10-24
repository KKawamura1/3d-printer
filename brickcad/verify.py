"""Geometric checks, not a friction/elasticity/printing simulation."""
from collections import Counter
from dataclasses import asdict
import math
import struct
import cadquery as cq
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from .model import Brick, build, nominal_brick

VOLUME_TOL = 1e-5  # mm^3; numerical classification only, NOT a print tolerance


def intersection(a, b):
    return max(0.0, a.intersect(b).Volume())


def place(shape, xyz=(0, 0, 9.6), angle=0):
    return shape.rotate((0, 0, 0), (0, 0, 1), angle).translate(xyz)


def mesh_check(path):
    """Read actual binary STL; weld float32 vertices at 1e-5 mm, inspect edges."""
    data = path.read_bytes()
    count = struct.unpack_from('<I', data, 80)[0]
    if len(data) != 84 + 50*count:
        raise ValueError('Invalid binary STL length')
    edges, directed = Counter(), Counter()
    signed_volume, degenerate = 0.0, 0
    bounds = [[math.inf]*3, [-math.inf]*3]
    for i in range(count):
        v = struct.unpack_from('<12fH', data, 84+50*i)[3:12]
        pts = [v[j:j+3] for j in (0, 3, 6)]
        keys = [tuple(round(x, 5) for x in p) for p in pts]
        if len(set(keys)) != 3: degenerate += 1
        for p in pts:
            for k in range(3):
                bounds[0][k] = min(bounds[0][k], p[k])
                bounds[1][k] = max(bounds[1][k], p[k])
        for a,b in zip(keys, keys[1:]+keys[:1]):
            edges[tuple(sorted((a,b)))] += 1
            directed[(a,b)] += 1
        a,b,c = pts
        signed_volume += (a[0]*(b[1]*c[2]-b[2]*c[1]) +
                          a[1]*(b[2]*c[0]-b[0]*c[2]) +
                          a[2]*(b[0]*c[1]-b[1]*c[0]))/6
    bad = sum(n != 2 for n in edges.values())
    winding = sum(directed[(a,b)] != directed[(b,a)] for a,b in edges)
    return dict(triangles=count, nonmanifold_edges=bad, inconsistent_edges=winding,
                degenerate_triangles=degenerate, signed_volume_mm3=signed_volume,
                bounds_mm=bounds, passed=count>0 and not(bad or winding or degenerate) and signed_volume>0)


def exact_bounds(shape):
    """Avoid tessellation cache inflating CadQuery's default bounding box."""
    box = Bnd_Box()
    BRepBndLib.AddOptimal_s(shape.wrapped, box, False, False)
    x0,y0,z0,x1,y1,z1 = box.Get()
    return [x1-x0, y1-y0, z1-z0]


def geometry_report(p, shape):
    expected = [p.width, p.depth, p.height+p.stud_height]
    actual = exact_bounds(shape)
    # Independent analytical volume of shell, studs and tube annuli.
    cavity_w = p.width-2*(p.wall-p.clearance)
    cavity_d = p.depth-2*(p.wall-p.clearance)
    volume = (p.width*p.depth*p.height - cavity_w*cavity_d*(p.height-p.roof)
              + p.nx*p.ny*math.pi*((p.stud_radius-p.clearance)**2-p.stud_inner_radius**2)*p.stud_height
              + (p.nx-1)*(p.ny-1)*math.pi*((p.tube_radius-p.clearance)**2-p.tube_inner_radius**2)*(p.height-p.roof))
    checks = {
        'valid_brep': shape.isValid(), 'one_solid': len(shape.Solids()) == 1,
        'dimensions': all(abs(a-b)<1e-6 for a,b in zip(actual,expected)),
        'analytical_volume': abs(shape.Volume()-volume)<1e-5,
        'bottom_open': not shape.isInside(cq.Vector(p.pitch/4, 0, 0.1)),
        'roof_present': shape.isInside(cq.Vector(0, 0, p.height-p.roof/2)),
        'stud_centres': all(shape.isInside(cq.Vector(x,y,p.height+p.stud_height/2)) == (p.stud_inner_radius == 0) for x,y in p.studs()),
        'stud_walls': all(shape.isInside(cq.Vector(x+(p.stud_inner_radius+p.stud_radius-p.clearance)/2,y,p.height+p.stud_height/2)) for x,y in p.studs()),
        'stud_floors': all(shape.isInside(cq.Vector(x,y,p.height-p.roof/2)) for x,y in p.studs()),
        'tube_holes': all(not shape.isInside(cq.Vector(x,y,1)) for x,y in p.tubes()),
        'tube_walls': all(shape.isInside(cq.Vector(x+(p.tube_inner_radius+p.tube_radius-p.clearance)/2,y,1)) for x,y in p.tubes()),
    }
    return dict(parameters=asdict(p), bounds_mm=actual, volume_mm3=shape.Volume(),
                analytical_volume_mm3=volume, checks=checks, passed=all(checks.values()))


def fit_report(p, shape):
    # Reference is an independently instantiated nominal design, NOT a measured genuine brick.
    ref_p = nominal_brick(p.family, p.nx, p.ny)
    ref = build(ref_p)
    rows = []
    for label, lower, upper in [('printed/printed',shape,shape), ('reference/printed',ref,shape), ('printed/reference',shape,ref)]:
        for dz in (max(p.stud_height,ref_p.stud_height)+1.2, max(p.stud_height,ref_p.stud_height), p.stud_height*2/3, p.stud_height/3, 0.0):
            seat_height = ref_p.height if label == 'reference/printed' else p.height
            vol = intersection(lower, place(upper,(0,0,seat_height+dz)))
            rows.append(dict(pair=label, lift_mm=dz, intersection_mm3=vol, collision=vol>VOLUME_TOL))
    poses = []
    cross_shift = p.pitch/2 if p.nx % 2 != p.ny % 2 else 0
    for label, xyz, angle in [('one_stud_offset',(p.pitch,0,p.height),0),
                              ('cross_90',(cross_shift,cross_shift,p.height),90),
                              ('half_pitch_negative_control',(p.pitch/2,0,p.height),0),
                              ('overinsert_negative_control',(0,0,p.height-0.3),0)]:
        v = intersection(shape,place(shape,xyz,angle))
        poses.append(dict(name=label,xyz_mm=xyz,rotation_deg=angle,intersection_mm3=v,collision=v>VOLUME_TOL))
    # Nearest nominal wall/tube to a stud. Positive = geometric air gap.
    r = p.stud_radius-p.clearance
    wall_gap = p.pitch/2-p.body_gap/2-(p.wall-p.clearance)-r
    tube_gap = math.sqrt(2)*(p.pitch/2)-(p.tube_radius-p.clearance)-r
    return dict(reference=f'synthetic {p.family} nominal model; not an OEM scan',
                reference_parameters=asdict(ref_p),
                limitation='Rigid geometry only: no clutch force, elasticity, shrinkage, slicer or FEA prediction',
                numerical_volume_tolerance_mm3=VOLUME_TOL,
                self_wall_gap_mm=wall_gap,self_tube_gap_mm=tube_gap,
                insertion=rows, poses=poses,
                negative_controls_passed=all(x['collision'] for x in poses if 'negative_control' in x['name']))
