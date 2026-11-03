"""SC02-V12 / SC02L-V6: 4x4 right R48 downhill tunnel, one DUPLO-course drop.

Reuse S01's rolling floor and the three intact lower receivers. Restore four
footprint-clipped receiver supports without the previously problematic vertical
fillets. Flat full-height top has footprint-clipped hollow studs. The circular
mouths evolve into a higher teardrop roof.
"""
from dataclasses import asdict, replace
from pathlib import Path
import hashlib
import json
import math
import struct

import cadquery as cq

from brickcad.provenance import design_manifest
from brickcad.verify import exact_bounds, intersection, mesh_check, precise_volume, VOLUME_TOL
from brickcad.standards import DUPLO
from brickcad.connections import make_studs
from brickcad.marking import engrave_west
from parts.sloped_curve.design import (
    BALL, DROP, RADIUS, RAIL, RETAINED_TUBES, build_curve, curved_footprint,
    gradient, height, ports,
)
from parts.tunnel.e31_fit import (
    add_e31_05_receiver_features, SLOT_END_Z, SLOT_END_RADIUS,
)

PART_ID = "SC02-V12"
LEFT_PART_ID = "SC02L-V6"
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
# Low, exterior west face below the high tunnel mouth: no studs or running track.
MARK_Y = -16.0
MARK_Z = 12.0
MARK_DEPTH = 0.4
MARK_SIZE = 3.0


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


def build_part(*, side="right", marked=True):
    """Build one unmarked right-hand BRep; mirror before side-specific marking."""
    if side not in ("right", "left"):
        raise ValueError(f"Unknown curve direction: {side}")
    # The source open curve carries a temporary ID; the cover union fills its recess.
    # Only the completed, unmarked tunnel BRep is mirrored and then engraved.
    base, p = build_curve(label=PART_ID, tube_diameter=2*TUBE_RADIUS)
    enclosure, passage = make_cover()
    shape = base.fuse(enclosure).cut(passage).clean()
    shape = _restore_clipped_receivers(shape, p)
    # The E31-05 split/bead is installed only on three full rings.
    # On cut rings the bead would protrude beyond the curved footprint.
    shape = add_e31_05_receiver_features(shape, RETAINED_TUBES, TUBE_RADIUS, receiver_depth=RAIL.floor - RAIL.roof)
    shape = _add_flat_clipped_studs(shape, p)
    # Do not mirror an engraved part: the left label must not become mirror text.
    if side == "left":
        shape = shape.mirror("XZ")
    if marked:
        label = PART_ID if side == "right" else LEFT_PART_ID
        shape = engrave_west(shape, label, x=-p.width/2,
                             y=MARK_Y if side == "right" else -MARK_Y,
                             z=MARK_Z, size=MARK_SIZE, depth=MARK_DEPTH)
    if not shape.isValid() or len(shape.Solids()) != 1:
        raise ValueError('SC02 requires one connected valid BRep')
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


def variant_ports(side="right"):
    if side == "right":
        return ports()
    if side != "left":
        raise ValueError(f"Unknown curve direction: {side}")
    return tuple(replace(port,
        floor_xyz_mm=(port.floor_xyz_mm[0], -port.floor_xyz_mm[1],
                      port.floor_xyz_mm[2]),
        outward=(port.outward[0], -port.outward[1], port.outward[2]))
        for port in ports())


def circular_mouth_checks(shape, p):
    """16-angle solid probes just inside each exterior port's circular lip."""
    r = RAIL.radius
    checks = {}
    for side in ("high_west", "low_north"):
        clear, rim = True, True
        for i in range(16):
            a = math.tau * i / 16
            lateral, vertical = math.cos(a), math.sin(a)
            if side == "high_west":
                inner = cq.Vector(-p.width/2+.4, -16+(r-.3)*lateral,
                                  RAIL.floor+DROP+r+(r-.3)*vertical)
                outer = cq.Vector(-p.width/2+.4, -16+(r+.3)*lateral,
                                  RAIL.floor+DROP+r+(r+.3)*vertical)
            else:
                inner = cq.Vector(16+(r-.3)*lateral, p.depth/2-.4,
                                  RAIL.floor+r+(r-.3)*vertical)
                outer = cq.Vector(16+(r+.3)*lateral, p.depth/2-.4,
                                  RAIL.floor+r+(r+.3)*vertical)
            clear = clear and not shape.isInside(inner)
            rim = rim and shape.isInside(outer)
        checks[f"{side}_circular_clear"] = clear
        checks[f"{side}_circular_rim"] = rim
    return checks


def verify(shape, p, *, side="right"):
    # The geometry probes are shared with the right source by reflecting
    # the left part back; the engraved text check runs on the actual variant.
    core = shape if side == "right" else shape.mirror("XZ")
    label = PART_ID if side == "right" else LEFT_PART_ID
    mark_y = MARK_Y if side == "right" else -MARK_Y
    centers = [ball_centre(i/(SAMPLES-1)) for i in range(SAMPLES)]
    collisions = [intersection(core,cq.Solid.makeSphere(BALL/2,c,angleDegrees1=-90))
                  for c in centers]
    test_low = intersection(core,cq.Solid.makeSphere(
        BALL/2,ball_centre(.5)-cq.Vector(0,0,2),angleDegrees1=-90))
    bounds = exact_bounds(shape)
    high,low = ports()
    # Regression: a cover fused *after* the label would fill these glyphs.
    # Reconstruct the exact cutting volume and confirm that it is empty.
    mark_plane = cq.Plane(origin=(-p.width/2+MARK_DEPTH, mark_y, MARK_Z),
                          xDir=(0,-1,0), normal=(-1,0,0))
    mark_tool = (cq.Workplane(mark_plane)
                 .text(label, MARK_SIZE, MARK_DEPTH+.05, font='DejaVu Sans',
                       kind='bold', combine=False).val())
    plain_wall = cq.Solid.makeBox(.5, 20., 7.,
        cq.Vector(-p.width/2, mark_y-10., MARK_Z-3.5))
    control_volume = intersection(plain_wall, mark_tool)
    checks = {
        'engraved_id_has_wall_negative_control':control_volume > .2,
        'engraved_id_recess_remains_open':intersection(shape, mark_tool)
                                           < .02 * control_volume,
        'valid_brep':shape.isValid(),
        'one_solid':len(shape.Solids())==1,
        'four_by_four_envelope':abs(bounds[0]-63.8)<.03 and abs(bounds[1]-63.8)<.03,
        'flat_top_with_studs_height':abs(bounds[2]-(TOP_Z+p.stud_height))<.03,
        'flat_top':all(core.isInside(cq.Vector(x,y,TOP_Z-.08)) and
                       not core.isInside(cq.Vector(x,y,TOP_Z+.08))
                       for x,y in RETAINED_TUBES),
        'clipped_receiver_supports_present':all(core.isInside(
            cq.Vector(x+5.7,y,1.)) for x,y in CLIPPED_RECEIVER_TUBES),
        'ten_top_stud_shells':sum(_stud_shell_present(core,x,y)
            for x,y in p.studs())==10,
        'ports_one_course_drop':abs(high.floor_xyz_mm[2]-low.floor_xyz_mm[2]-DROP)<1e-6,
        'sampled_ball_clear':max(collisions)<VOLUME_TOL,
        'too_low_ball_interferes':test_low>VOLUME_TOL,
        'mouths_open':all(not core.isInside(ball_centre(t)) for t in (0,1)),
        'roof_present':core.isInside(_roof_probe(.5)),
        'corners_removed':all(not core.isInside(cq.Vector(x,y,6.1))
                              for x,y in [(-24,24),(24,-24),(-16,16)]),
        'e31_only_three_complete_tubes':len(RETAINED_TUBES)==3
            and len(CLIPPED_RECEIVER_TUBES)==4
            and abs(p.tube_radius-TUBE_RADIUS)<1e-6,
    }
    checks.update(circular_mouth_checks(core, p))
    checks['e31_slot_ceiling_margin'] = (
        RAIL.floor - RAIL.roof - (SLOT_END_Z + SLOT_END_RADIUS) >= .59)
    return checks, bounds, collisions, test_low


def export(out=Path('build/sloped-curve-tunnel'), *, side="right"):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    shape,p = build_part(side=side)
    checks,bounds,collisions,test_low = verify(shape,p,side=side)
    label = PART_ID if side == "right" else LEFT_PART_ID
    mark_y = MARK_Y if side == "right" else -MARK_Y
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
    step_valid_solid = restored.isValid() and len(restored.Solids()) == 1
    # STEP on the mirrored loft drifts by ~0.154 mm^3 (1.73 ppm),
    # despite a valid single BRep solid and unchanged envelope. Retain
    # PR61 adaptive volume integration and require BOTH small relative and
    # absolute differences, plus the independent bounds/mesh checks.
    source_precise_volume = precise_volume(shape)
    restored_precise_volume = precise_volume(restored)
    step_volume_error_mm3 = abs(restored_precise_volume - source_precise_volume)
    step_volume_rel_error = step_volume_error_mm3 / source_precise_volume
    step_bounds_delta = [abs(a-b) for a,b in zip(exact_bounds(restored), bounds)]
    step_ok = (step_valid_solid and step_volume_rel_error < 5e-6
               and step_volume_error_mm3 < .30
               and all(d < .02 for d in step_bounds_delta))
    checks.update(mesh_closed=mesh['passed'], step_roundtrip=step_ok)
    report={
        'part_id':label,'passed':all(checks.values()),'checks':checks,
        'geometry':{'bounds_mm':bounds,'volume_mm3':shape.Volume(),
                    'parameters':asdict(p)},
        'design':design_manifest(p,channel=RAIL),
        'marking':{'text':label,'face':'west (-X), below high mouth',
                   'y_mm':mark_y,'z_mm':MARK_Z,'depth_mm':MARK_DEPTH,
                   'size_mm':MARK_SIZE, 'font':'DejaVu Sans Bold',
                   'applied_after_cover_studs_and_mirroring':True},
        'direction':side,
        'mirror':{'source':PART_ID, 'plane':'XZ',
                  'order':'mirror unmarked geometry, then engrave'}
                 if side == 'left' else None,
        'curve':{'radius_mm':RADIUS,'turn_deg':90,'drop_mm':DROP,
                 'mouth':'circular','interior_roof':'teardrop',
                 'transition_mm':TRANSITION_MM,'circular_lip_mm':MOUTH_LIP_MM,
                 'inner_roof_above_floor_mm':INNER_ROOF_ABOVE_FLOOR},
        'ports':[asdict(x) for x in variant_ports(side)],
        'top':{'plane_z_mm':TOP_Z,'stud_height_mm':p.stud_height,
               'top_clip':'curved 4x4 footprint','hollow_stud_shell_count':10,
               'physical_fit_validated':False},
        'receiver_supports':{'whole_tubes':list(RETAINED_TUBES),
                  'clipped_tubes':list(CLIPPED_RECEIVER_TUBES),
                  'vertical_cut_edge_fillets':False,
                  'physical_support_and_fit_validated':False},
        'e31_05':{'tube_od_mm':13.20,'split_slots':4,'tube_count':len(RETAINED_TUBES),
                  'partial_tube_beads':False,'physical_transfer_validated':False},
        'step_roundtrip':{'valid_solid':step_valid_solid,
                          'relative_volume_error':step_volume_rel_error,
                          'bounds_delta_mm':step_bounds_delta,
                          'absolute_volume_error_mm3':step_volume_error_mm3,
                          'absolute_volume_tolerance_mm3':.30,
                          'relative_volume_tolerance':5e-6,
                          'volume_integration':'brickcad.verify.precise_volume',
                          'max_bound_delta_mm':.02},
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
    print(label,'PASS' if report['passed'] else 'FAIL',checks,
          'STEP diagnostic',report['step_roundtrip'],flush=True)
    if not report['passed']:
        raise RuntimeError(f'{label} CAD verification failed')
    return report


if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument('--out',type=Path,default=Path('build/sloped-curve-tunnel'))
    ap.add_argument('--side',choices=('right','left'),default='right')
    args=ap.parse_args()
    export(args.out,side=args.side)
