"""SC02-V4: 4x4 right R48 downhill tunnel, one DUPLO-course drop.

Reuse S01's rolling floor and the three intact lower receivers. Restore four
footprint-clipped receiver supports without the previously problematic vertical
fillets. Flat full-height top has footprint-clipped hollow studs. The circular
mouths evolve into a higher teardrop roof.
"""
from dataclasses import asdict
from pathlib import Path
import hashlib
import json
import math
import struct

import cadquery as cq

from brickcad.provenance import design_manifest
from brickcad.verify import exact_bounds, intersection, mesh_check, VOLUME_TOL
from brickcad.standards import DUPLO
from brickcad.connections import make_studs
from parts.sloped_curve.design import (
    BALL, DROP, RADIUS, RAIL, RETAINED_TUBES, build_curve, curved_footprint,
    gradient, height, ports,
)
from parts.tunnel.e31_fit import add_e31_05_receiver_features

PART_ID = "SC02-V4"
TOP_Z = 3 * DUPLO.height  # 57.6 mm: 2 courses cannot clear the high ball inlet
# Restore four useful partial supports; omit two corners (no material / thin sliver).
CLIPPED_RECEIVER_TUBES = ((0.,-16.),(-16.,0.),(16.,0.),(0.,16.))
TOP_STUD_OVERLAP = .15
TUBE_RADIUS = 6.60  # E31-05 trial; retention unvalidated on this curved base
INNER_ROOF_ABOVE_FLOOR = 30.30
MOUTH_LIP_MM = 1.0
TRANSITION_MM = 4.0
RUNNING_CLEARANCE_MM = 0.18
SAMPLES = 49


def _zshift(t):
    return height(min(1.0, max(0.0, t)))


def _blend(t):
    s = RADIUS * math.pi / 2
    d = min(t, 1-t)*s
    u = max(0.0, min(1.0, (d - MOUTH_LIP_MM) / TRANSITION_MM))
    return min(.995, u*u*(3-2*u))


def _position(wire, t):
    """Map an XZ radial section to the 4x4 quarter-turn path."""
    return (wire.rotate((0,0,0),(0,0,1),-90+90*t)
            .translate((-32,32,0)))


def _outer_wire(t):
    """Cover overlaps S01's two rounded rail lips by 0.7mm."""
    half = RAIL.width/2
    base = RAIL.floor - .75  # overlap the curved running-floor solid
    top = TOP_Z  # horizontal top, no downhill top surface
    wire = cq.Workplane('XZ').polyline([
        (RADIUS-half,base),(RADIUS+half,base),
        (RADIUS+half,top),(RADIUS-half,top)
    ]).close().val()
    return _position(wire,t)


def _passage_wire(t):
    """Unchanging circular floor; mouths circular, central roof teardrop."""
    z = _zshift(t)
    floor = RAIL.floor + z
    r = RAIL.radius
    cy = floor + r
    a = r / math.sqrt(2)
    roof = floor + INNER_ROOF_ABOVE_FLOOR
    b = cy + math.sqrt(2)*r - roof
    blend = _blend(t)
    def mix(x, y):
        return (1-blend)*x + blend*y
    end = (mix(r*math.cos(math.radians(75)), b),
           mix(cy+r*math.sin(math.radians(75)), roof))
    mid = (mix(.5*r, (a+b)/2),
           mix(cy+r*math.sqrt(3)/2, (cy+a+roof)/2))
    apex = (0, mix(cy+r,roof))
    wire = (cq.Workplane('XZ').moveTo(RADIUS-a,cy+a)
            .threePointArc((RADIUS,floor),(RADIUS+a,cy+a))
            .threePointArc((RADIUS+mid[0],mid[1]),(RADIUS+end[0],end[1]))
            .threePointArc((RADIUS+apex[0],apex[1]),(RADIUS-end[0],end[1]))
            .threePointArc((RADIUS-mid[0],mid[1]),(RADIUS-a,cy+a))
            .close().val())
    return _position(wire,t)


def _stations():
    dt = 1.0/(RADIUS*math.pi/2)
    items = [-.02,0.0,dt,2*dt,3*dt,4*dt,5*dt]
    items += [i/32 for i in range(1,32)]
    items += [1-5*dt,1-4*dt,1-3*dt,1-2*dt,1-dt,1.0,1.02]
    return sorted(set(round(x,7) for x in items))


def make_cover():
    stations = _stations()
    envelope = cq.Solid.makeLoft([_outer_wire(t) for t in stations], ruled=True)
    passage = cq.Solid.makeLoft([_passage_wire(t) for t in stations], ruled=True)
    # Passage Boolean cuts the merged solid to the same S01 floor datum.
    clipping = cq.Workplane('XY').box(
        63.8,63.8,90,centered=(True,True,False)).val()
    return envelope.intersect(clipping).intersect(curved_footprint()).clean(), passage


def _restore_clipped_receivers(shape, p):
    """Add useful clipped underside rings; reject the near-tangent sliver.

    F-version S01 taught that R0.70 on clipped vertical tube ends caused Bambu
    Studio floating-cantilever warnings. Leave those ends square, not rounded.
    Add a 0.25 mm Z overlap with the existing S01 receiver roof for safe union.
    The four partial rings are structural trials, NOT physically E31-calibrated.
    """
    clip = curved_footprint()
    for x, y in CLIPPED_RECEIVER_TUBES:
        ring = (cq.Workplane('XY', origin=(x,y,0))
                .circle(p.tube_radius).circle(p.tube_inner_radius)
                .extrude(RAIL.floor - RAIL.roof + .25).val())
        partial = ring.intersect(clip)
        if not partial.Solids() or partial.Volume() < 20:
            raise ValueError(f'Empty/sliver clipped receiver at {(x,y)}')
        shape = shape.fuse(partial).clean()
    return shape


def _add_flat_clipped_studs(shape, p):
    """Studs begin 0.15 mm inside the planar roof to prevent coplanar unions.

    Trimming by the same quarter-annulus prevents unsupported outside studs
    without adding any towers in the empty 4x4 corners.
    """
    studs = make_studs(
        p.studs(), TOP_Z - TOP_STUD_OVERLAP,
        p.stud_radius - p.clearance, p.stud_inner_radius,
        p.stud_height + TOP_STUD_OVERLAP, lip_radius=.5).val()
    # The base quarter-annulus stops at z=60, so lift its XY extrusion mask
    # before clipping 57.6–62.1 mm high studs.
    clipped = studs.intersect(curved_footprint().translate(
        (0,0,p.stud_height+1.)))
    if not clipped.Solids():
        raise ValueError('All top studs removed by footprint')
    return shape.fuse(clipped).clean()


def build_part():
    base, p = build_curve(label=PART_ID, tube_diameter=2*TUBE_RADIUS)
    enclosure, passage = make_cover()
    shape = base.fuse(enclosure).cut(passage).clean()
    shape = _restore_clipped_receivers(shape, p)
    # The E31-05 split/bead is installed only on three full rings.
    # On cut rings the bead would protrude beyond the curved footprint.
    shape = add_e31_05_receiver_features(shape, RETAINED_TUBES, TUBE_RADIUS)
    shape = _add_flat_clipped_studs(shape, p)
    if not shape.isValid() or len(shape.Solids()) != 1:
        raise ValueError('SC02-V4 requires one connected valid BRep')
    return shape, p


def ball_centre(t, diameter=BALL):
    angle = math.pi*(-.5+.5*t)
    r = diameter/2
    z = RAIL.floor + _zshift(t) + r*math.sqrt(1+gradient(t)**2) + RUNNING_CLEARANCE_MM
    return cq.Vector(-32+RADIUS*math.cos(angle),
                     32+RADIUS*math.sin(angle),z)


def _roof_probe(t):
    angle = math.pi*(-.5+.5*t)
    z = RAIL.floor + _zshift(t) + INNER_ROOF_ABOVE_FLOOR + .9
    return cq.Vector(-32+RADIUS*math.cos(angle),
                     32+RADIUS*math.sin(angle),z)


def _stud_shell_present(shape, x, y):
    """A hollow stud has NO solid at its center; test the cylindrical wall."""
    z = TOP_Z + 1.0
    return any(shape.isInside(cq.Vector(x+4*math.cos(a),y+4*math.sin(a),z))
               for a in (0.,math.pi/4,math.pi/2,3*math.pi/4,math.pi,
                         5*math.pi/4,3*math.pi/2,7*math.pi/4))


def verify(shape, p):
    centers = [ball_centre(i/(SAMPLES-1)) for i in range(SAMPLES)]
    collisions = [intersection(shape,cq.Solid.makeSphere(BALL/2,c,angleDegrees1=-90))
                  for c in centers]
    test_low = intersection(shape,cq.Solid.makeSphere(
        BALL/2,ball_centre(.5)-cq.Vector(0,0,2),angleDegrees1=-90))
    bounds = exact_bounds(shape)
    high,low = ports()
    checks = {
        'valid_brep':shape.isValid(),
        'one_solid':len(shape.Solids())==1,
        'four_by_four_envelope':abs(bounds[0]-63.8)<.03 and abs(bounds[1]-63.8)<.03,
        'flat_top_with_studs_height':abs(bounds[2]-(TOP_Z+p.stud_height))<.03,
        'flat_top':all(shape.isInside(cq.Vector(x,y,TOP_Z-.08)) and
                       not shape.isInside(cq.Vector(x,y,TOP_Z+.08))
                       for x,y in RETAINED_TUBES),
        'clipped_receiver_supports_present':all(shape.isInside(
            cq.Vector(x+5.7,y,1.)) for x,y in CLIPPED_RECEIVER_TUBES),
        'ten_top_stud_shells':sum(_stud_shell_present(shape,x,y)
            for x,y in p.studs())==10,
        'ports_one_course_drop':abs(high.floor_xyz_mm[2]-low.floor_xyz_mm[2]-DROP)<1e-6,
        'sampled_ball_clear':max(collisions)<VOLUME_TOL,
        'too_low_ball_interferes':test_low>VOLUME_TOL,
        'mouths_open':all(not shape.isInside(ball_centre(t)) for t in (0,1)),
        'roof_present':shape.isInside(_roof_probe(.5)),
        'corners_removed':all(not shape.isInside(cq.Vector(x,y,6.1))
                              for x,y in [(-24,24),(24,-24),(-16,16)]),
        'e31_only_three_complete_tubes':len(RETAINED_TUBES)==3
            and len(CLIPPED_RECEIVER_TUBES)==4
            and abs(p.tube_radius-TUBE_RADIUS)<1e-6,
    }
    return checks, bounds, collisions, test_low


def export(out=Path('build/sloped-curve-tunnel')):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    shape,p = build_part()
    checks,bounds,collisions,test_low = verify(shape,p)
    stl=out/'brick.stl'
    cq.exporters.export(shape,str(stl),tolerance=.03,angularTolerance=.2)
    raw=stl.read_bytes(); triangles=[]
    for i in range(struct.unpack_from('<I',raw,80)[0]):
        tri=raw[84+50*i:134+50*i];v=struct.unpack('<12fH',tri)[3:12]
        if len({tuple(v[j:j+3]) for j in (0,3,6)})==3:
            triangles.append(tri)
    stl.write_bytes(raw[:80]+struct.pack('<I',len(triangles))+b''.join(triangles))
    cq.exporters.export(shape,str(out/'brick.step'))
    mesh=mesh_check(stl)
    restored=cq.importers.importStep(str(out/'brick.step')).val()
    checks.update(mesh_closed=mesh['passed'],
                  step_roundtrip=restored.isValid() and len(restored.Solids())==1
                  and abs(restored.Volume()-shape.Volume())/shape.Volume()<1e-6)
    report={
        'part_id':PART_ID,'passed':all(checks.values()),'checks':checks,
        'geometry':{'bounds_mm':bounds,'volume_mm3':shape.Volume(),
                    'parameters':asdict(p)},
        'design':design_manifest(p,channel=RAIL),
        'curve':{'radius_mm':RADIUS,'turn_deg':90,'drop_mm':DROP,
                 'mouth':'circular','interior_roof':'teardrop',
                 'transition_mm':TRANSITION_MM,'circular_lip_mm':MOUTH_LIP_MM,
                 'inner_roof_above_floor_mm':INNER_ROOF_ABOVE_FLOOR},
        'ports':[asdict(x) for x in ports()],
        'top':{'plane_z_mm':TOP_Z,'stud_height_mm':p.stud_height,
               'top_clip':'curved 4x4 footprint','hollow_stud_shell_count':10,
               'physical_fit_validated':False},
        'receiver_supports':{'whole_tubes':list(RETAINED_TUBES),
                  'clipped_tubes':list(CLIPPED_RECEIVER_TUBES),
                  'vertical_cut_edge_fillets':False,
                  'physical_support_and_fit_validated':False},
        'e31_05':{'tube_od_mm':13.20,'split_slots':4,'tube_count':len(RETAINED_TUBES),
                  'partial_tube_beads':False,'physical_transfer_validated':False},
        'mesh':mesh,'sampled_ball_intersections_mm3':collisions,
        'low_ball_negative_mm3':test_low,'physical_fit_validated':False,
        'physical_rolling_validated':False,'slicer_support_free_validated':False,
        'limitations':['Finite ball stations are NOT a continuous swept-sphere proof.',
                       'Curved roof and E31-05 retention require slicing and real tests.',
                       'Horizontal top is at 57.6 mm (3 DUPLO courses) to clear the high inlet; not physically a 2-course block.',
                       'Four clipped underside supports restore footprint contact, but may need slicer revision.',
                       'No round-over on clipped vertical receiver ends (known floating-cantilever warning).',
                       'Ten top hollow studs are footprint-clipped; their attachment/fit needs printing.',
                       'E31-05 features only on three full underside tubes, not clipped supports.'],
        'sha256_stl':hashlib.sha256(stl.read_bytes()).hexdigest(),
    }
    (out/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print(PART_ID,'PASS' if report['passed'] else 'FAIL',checks,flush=True)
    if not report['passed']:
        raise RuntimeError('Sloped curve tunnel CAD verification failed')
    return report


if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument('--out',type=Path,default=Path('build/sloped-curve-tunnel'))
    export(ap.parse_args().out)
