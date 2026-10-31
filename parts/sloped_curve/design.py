"""4x4 open quarter-turn, with one DUPLO course of fall; mm, Z up.

The curved receiver sits on z=0; empty inner and outer corner floors are removed.
Lofted BRep sections preserve the measured straight-rail profile at both ends.
"""
from dataclasses import asdict, replace
from pathlib import Path
import hashlib
import json
import math
import struct
import cadquery as cq
from parts.straight_rail.design import Rail, build_rail
from brickcad.standards import DUPLO, BALL_TRACK, fit_profile
from brickcad.model import receiver, build, nominal_brick, brick_from_fit
from brickcad.connections import make_receiver
from brickcad.provenance import design_manifest
from brickcad.marking import engrave_west

PART_ID = "S01-V2"
from brickcad.ports import Port, straight_ports, mate
from brickcad.verify import intersection, exact_bounds, mesh_check, VOLUME_TOL
from brickcad.render import viewer, mesh, outlines

RADIUS = 48.0
DROP = DUPLO.height
BALL = BALL_TRACK.ball_diameter
RAIL = Rail()
# E27-04 selected receiver; no inference of universal clutch force.
CURVE_FIT_PROFILE_ID = 'duplo-e27-play-v1'
RECEIVER_TUBE_DIAMETER = 2*fit_profile(CURVE_FIT_PROFILE_ID).tube_radius
CUT_EDGE_RADIUS = .5  # Only four wall ends; no clipped tube tips remain.
RETAINED_TUBES = ((-16.,-16.), (0.,0.), (16.,16.))
BOTTOM_EDGE_RADIUS = .5


def curve_profile():
    return brick_from_fit(CURVE_FIT_PROFILE_ID, nx=4, ny=4,
                          height=RAIL.height+DROP)



def height(t):
    return DROP * (1 - 3*t*t + 2*t*t*t)


def gradient(t):
    return DROP * (-6*t + 6*t*t) / (math.pi*RADIUS/2)


def section(t):
    """Radial U section with a constant bottom, rounded lip and outer corners."""
    floor = RAIL.floor + height(t)
    top = RAIL.height + height(t)
    half = RAIL.width/2
    # XZ plane local x = radius, local y = height.
    w = (cq.Workplane('XZ').moveTo(RADIUS-half, RAIL.floor-.1)
         .lineTo(RADIUS+half, RAIL.floor-.1)
         .lineTo(RADIUS+half, top)
         .lineTo(RADIUS+RAIL.opening/2, top)
         .threePointArc((RADIUS, floor), (RADIUS-RAIL.opening/2, top))
         .lineTo(RADIUS-half, top).close().val())
    upper = [v for v in w.Vertices() if v.Center().z > top-.01]
    w = w.fillet2D(.5, upper)
    return (w.rotate((0,0,0),(0,0,1),-90+90*t)
            .translate((-32,32,0)))


def curved_footprint():
    """Quarter-annulus: no square corner floors. Preserve the 4x4 cell envelope.

    The 0.075 mm outer skirt is only the difference between a measured 31.65 mm
    rail width and the nominal 31.8 mm body width; it is not a corner platform.
    """
    return (cq.Workplane('XZ').moveTo(RADIUS-RAIL.width/2,0)
            .lineTo(63.9,0).lineTo(63.9,60)
            .lineTo(RADIUS-RAIL.width/2,60).close()
            .revolve(90,(0,0),(0,1)).val()
            .rotate((0,0,0),(0,0,1),-90).translate((-32,32,0)))


def receiver_audit(shape,p):
    """All 16 lower studs, including studs exposed by the removed floors.

    Keep the existing trial's slight tube interference visible. Any overlap
    outside the tube regions is a blocking defect, not intentional clutch.
    """
    refp = nominal_brick('duplo',4,4)
    reference = build(refp)
    tube_regions = cq.Compound.makeCompound([
        cq.Solid.makeCylinder(p.tube_radius,RAIL.floor-RAIL.roof,cq.Vector(x,y,0))
        for x,y in p.tubes()])
    non_tube = shape.cut(tube_regions)
    insertion = []
    for lift in (5.7,4.5,3.,1.5,0.):
        lower = reference.translate((0,0,-refp.height-lift))
        insertion.append(dict(lift_mm=lift,
            total_intersection_mm3=intersection(shape,lower),
            non_tube_intersection_mm3=intersection(non_tube,lower)))
    studs = []
    for x,y in refp.studs():
        stud = (cq.Workplane('XY',origin=(x,y,0)).circle(refp.stud_radius)
                .circle(refp.stud_inner_radius).extrude(refp.stud_height).val())
        studs.append(dict(x_mm=x,y_mm=y,intersection_mm3=intersection(shape,stud),
                          non_tube_intersection_mm3=intersection(non_tube,stud)))
    # Issue #1's 9.32 mm measured stud diameter is a sensitivity case, not a
    # replacement for the conservative 9.40 mm synthetic reference.
    measured = build(replace(refp,stud_radius=4.66)).translate((0,0,-refp.height))
    # Half-pitch and overinsertion controls use the actual receiving geometry.
    shifted = intersection(shape,reference.translate((8,0,-refp.height)))
    overinsert = intersection(non_tube,reference.translate((0,0,-refp.height+.5)))
    return dict(reference='Synthetic DUPLO 4x4, 16 hollow studs, OD 9.40 mm',
        calibration=dict(source_issue='https://github.com/KKawamura1/3d-printer/issues/1#issuecomment-6525080864',
            source_coupon='E27-04 receiver; 2026-10-30 feedback',wall_mm=p.wall,tube_diameter_mm=2*p.tube_radius,
            full_4x4_cavity_mm=list(p.cavity_xy),
            equivalent_2x2_cavity_mm=2*p.pitch-2*p.receiver_inset_xy[0],
            transfer_validated=False,
            retained_complete_tubes=list(RETAINED_TUBES),
            limitation='Three complete tubes retained, six clipped tubes omitted. E27-04 does not physically validate this curve.'),
        insertion=insertion,studs=studs,
        measured_9p32_stud_intersection_mm3=intersection(shape,measured),
        seating_roof_clearance_mm=RAIL.floor-RAIL.roof-refp.stud_height,
        intentional_tube_radial_interference_mm=p.tube_radius+refp.stud_radius-math.sqrt(2)*8,
        half_pitch_negative_mm3=shifted,overinsert_non_tube_negative_mm3=overinsert,
        rigid_fit_clear=all(v['total_intersection_mm3']<VOLUME_TOL for v in insertion),
        no_blocking_collision=all(v['non_tube_intersection_mm3']<VOLUME_TOL for v in insertion))


def cut_receiver_edges(shape):
    """Vertical corners created by clipping the receiver, excluding tube seams."""
    edges = []
    for edge in shape.Edges():
        b = edge.BoundingBox()
        c = edge.Center()
        radius = math.hypot(c.x+32, c.y-32)
        if (edge.geomType() == 'LINE' and b.zlen > 4.4
                and b.zmax < RAIL.floor-RAIL.roof+1e-5
                and b.xlen < 1e-5 and b.ylen < 1e-5
                and min(abs(radius-(RADIUS-RAIL.width/2)), abs(radius-63.9)) < 1e-4):
            edges.append(edge)
    return edges


def build_curve(*, softened=True, tube_diameter=RECEIVER_TUBE_DIAMETER, label=PART_ID):
    p = replace(curve_profile(),tube_radius=tube_diameter/2)
    base = cq.Workplane('XY').box(p.width,p.depth,RAIL.floor,centered=(True,True,False))
    base = base.edges('|Z').fillet(.8).edges('>Z').fillet(.5)
    # Keep complete tubes only. Clipped tube fragments created sharp tips and
    # previously required fillets that caused slicer warnings.
    base = make_receiver(base,RETAINED_TUBES,p.cavity_xy,RAIL.floor-RAIL.roof,
                         p.tube_radius,p.tube_inner_radius,0)
    loft = cq.Solid.makeLoft([section(i/24) for i in range(25)], ruled=False)
    # Trim at physical body faces, preserving the 0.1 mm cell-boundary inset.
    footprint = cq.Workplane('XY').box(p.width,p.depth,60,centered=(True,True,False)).val()
    shape = base.union(loft.intersect(footprint)).val().intersect(curved_footprint()).clean()
    if softened:
        # Four wall ends remain; the sixteen clipped-tube corners no longer exist.
        if len(cut_receiver_edges(shape)) != 4:
            raise ValueError('Expected four receiver wall ends, no partial tube tips')
        shape = shape.fillet(CUT_EDGE_RADIUS, cut_receiver_edges(shape)).clean()
        bottom_edges = [e for e in shape.Edges()
                        if abs(e.BoundingBox().zmin) < 1e-5
                        and abs(e.BoundingBox().zmax) < 1e-5]
        shape = shape.fillet(BOTTOM_EDGE_RADIUS, bottom_edges).clean()
    if not shape.isValid() or len(shape.Solids()) != 1:
        raise ValueError('Sloped curve must be one valid solid')
    return engrave_west(shape,label,x=-p.width/2,y=-16,z=12.),p


def finish_audit(shape):
    """Compare rounding against the same receiver diameter before rounding.

    The 9.40 mm synthetic studs provide a conservative contact envelope. This
    proves retained-tube material preservation in that envelope, not clutch force.
    """
    old,p = build_curve(softened=False)
    removed = old.cut(shape)
    added = shape.cut(old)
    above_entry = cq.Solid.makeBox(100,100,50,cq.Vector(-50,-50,BOTTOM_EDGE_RADIUS))
    track = cq.Solid.makeBox(100,100,50,cq.Vector(-50,-50,RAIL.floor-RAIL.roof))
    reference = build(nominal_brick('duplo',4,4)).translate((0,0,-19.2))
    tube_mask = cq.Compound.makeCompound([cq.Solid.makeCylinder(p.tube_radius,5,cq.Vector(x,y,.5)) for x,y in RETAINED_TUBES])
    def contact_delta(delta):
        if not delta.Solids():
            return 0.0
        clipped = delta.intersect(above_entry)
        if not clipped.Solids():
            return 0.0
        clipped = clipped.intersect(tube_mask)
        return intersection(clipped,reference) if clipped.Solids() else 0.0
    return dict(cut_edge_radius_mm=CUT_EDGE_RADIUS,bottom_edge_radius_mm=BOTTOM_EDGE_RADIUS,
        clipped_vertical_corners=len(cut_receiver_edges(old)),
        removed_volume_mm3=removed.Volume(),added_volume_mm3=added.Volume(),
        removed_contact_above_entry_mm3=contact_delta(removed),
        added_contact_above_entry_mm3=contact_delta(added),
        changed_track_mm3=sum(intersection(delta,track) for delta in (removed,added) if delta.Solids()),
        comparison_tube_diameter_mm=2*p.tube_radius,
        physical_touch_validated=False,
        limitation='Three full tubes only; four wall ends R0.50 and bottom R0.50. Tube contact above z=0.50 preserved, remaining wall-end rounding may remove wall contact. Tactile, slicer and retention transfer untested.')


def ports():
    return (Port('high-west',(-32.,-16.,RAIL.floor+DROP),(-1.,0.,0.),RAIL.radius),
            Port('low-north',(16.,32.,RAIL.floor),(0.,1.,0.),RAIL.radius))


def ball_centre(t):
    a = -math.pi/2 + math.pi*t/2
    # A sphere on an incline sits above floor+r. This is a static test envelope,
    # not a solved rolling trajectory or a prescribed dynamics result.
    z = RAIL.floor+height(t)+BALL/2*math.sqrt(1+gradient(t)**2)+.1
    return cq.Vector(-32+RADIUS*math.cos(a),32+RADIUS*math.sin(a),z)


def course(shape):
    rail,_ = build_rail()
    support = build(nominal_brick('duplo',4,2)).translate((-64,-16,0))
    return (rail.translate((-64,-16,DROP)),shape,
            rail.rotate((0,0,0),(0,0,1),90).translate((16,64,0)),support,
            build(nominal_brick('duplo',4,4)).translate((0,0,-19.2)))


def verify(shape,p):
    left,right = straight_ports(4,RAIL.floor,RAIL.radius)
    west,north = ports()
    joints = [mate(right.placed((-64,-16,DROP)),west),
              mate(north,left.placed((16,64,0),90))]
    pieces = course(shape)
    pairs = [intersection(a,b) for i,a in enumerate(pieces[:3]) for b in pieces[i+1:3]]
    support_fit = intersection(pieces[0],pieces[3])
    support_other = [intersection(pieces[i],pieces[3]) for i in (1,2)]
    samples = []
    for i in range(49):
        t = i/48
        sphere = cq.Solid.makeSphere(BALL/2,ball_centre(t),angleDegrees1=-90)
        samples.append(dict(t=t,intersection_mm3=sum(intersection(s,sphere) for s in pieces[:3])))
    floor = []
    for i in range(1,24):
        t = i/24; c = ball_centre(t)
        floor.append(shape.isInside(cq.Vector(c.x,c.y,RAIL.floor+height(t)-.2)))
    # Deliberately put a ball 2 mm too low on the slope; the test must detect it.
    blocked = intersection(shape,cq.Solid.makeSphere(BALL/2,ball_centre(.5)-cq.Vector(0,0,2),angleDegrees1=-90))
    footprint = cq.Workplane('XY').box(63.8,63.8,60,centered=(True,True,False)).val()
    outside = shape.cut(footprint).Volume()
    audit = receiver_audit(shape,p)
    finish = finish_audit(shape)
    corner_floor = [shape.isInside(cq.Vector(x,y,6.1)) for x,y in [(-16,16),(24,-24),(-24,24)]]
    checks = dict(valid_brep=shape.isValid(),one_solid=len(shape.Solids())==1,
        footprint=outside<VOLUME_TOL,
        ports_match=all(j['compatible'] for j in joints),
        wrong_height_rejected=not mate(right.placed((-64,-16,0)),west)['compatible'],
        wrong_grid_rejected=not mate(right.placed((-64,-8,DROP)),west)['compatible'],
        bodies_clear=max(pairs+support_other)<VOLUME_TOL,
        existing_support_fit_envelope=0<=support_fit<2,
        sampled_ball_clear=max(v['intersection_mm3'] for v in samples)<VOLUME_TOL,
        continuous_floor_samples=all(floor),low_ball_detected=blocked>VOLUME_TOL,
        receiver_holes=all(not shape.isInside(cq.Vector(x,y,1)) for x,y in p.tubes()),
        unused_corner_floors_removed=not any(corner_floor),
        receiver_no_blocking_collision=audit['no_blocking_collision'],
        all_16_studs_checked=len(audit['studs'])==16,
        wall_ends_rounded_without_partial_tube_tips=finish['clipped_vertical_corners']==4
            and finish['cut_edge_radius_mm']==.5 and finish['removed_volume_mm3']>1,
        complete_tube_contact_material_preserved=max(finish['removed_contact_above_entry_mm3'],finish['added_contact_above_entry_mm3'])<VOLUME_TOL,
        track_geometry_preserved=finish['changed_track_mm3']<VOLUME_TOL,
        receiver_trial_interference_only=0<audit['intentional_tube_radial_interference_mm']<=13.5/2+4.7-math.sqrt(2)*8+1e-6,
        receiver_half_pitch_detected=audit['half_pitch_negative_mm3']>VOLUME_TOL,
        receiver_overinsert_detected=audit['overinsert_non_tube_negative_mm3']>VOLUME_TOL)
    return dict(checks=checks,joints=joints,body_intersections_mm3=pairs,
                ball_samples=samples,low_ball_negative_control_mm3=blocked,
                support_fit_intersection_mm3=support_fit,outside_footprint_mm3=outside,receiver_audit=audit,
                receiver_finish=finish)


def render(shape,p,report,out):
    import re
    # Do not carry the fine STL triangulation into the interactive viewer.
    shape = shape.copy(mesh=False)
    viewer(shape,p,{**report,'fit':dict(insertion=[],poses=[])},out)
    html = (out/'viewer.html').read_text()
    pieces = course(shape)
    balls = cq.Compound.makeCompound([cq.Solid.makeSphere(BALL/2,ball_centre(t),angleDegrees1=-90)
                                      for t in (0,.25,.5,.75,1)])
    exploded = cq.Compound.makeCompound([pieces[0].translate((-12,0,6)),shape,
                                         pieces[2].translate((0,12,0)),pieces[3],pieces[4].translate((0,0,-6))])
    extras = {}
    for name,solid in [('course',cq.Compound.makeCompound(list(pieces))),('exploded',exploded),('receiver',cq.Compound.makeCompound([shape,pieces[4]])),
                       ('receiver_exploded',cq.Compound.makeCompound([shape,pieces[4].translate((0,0,-8))])),('balls',balls)]:
        v,f = mesh(solid); extras[name] = dict(vertices=v,faces=f,edges=outlines(solid))
    html = html.replace('const canvas=','data.extra='+json.dumps(extras,separators=(',',':'))+';\nconst canvas=')
    html = re.sub(r'<label>表示<select id="mode">.*?</select></label>',
        '<label>表示<select id="mode"><option value="single">Sloped curve</option><option value="section">Section</option><option value="balls">Curve + balls</option><option value="course">Rail connections + support</option><option value="exploded">Exploded course</option><option value="receiver">Seated on 4x4</option><option value="receiver_exploded">4x4 insertion exploded</option></select></label>',html)
    html = re.sub(r'<label>組み合わせ.*?</label>','',html)
    html = re.sub(r'<label>上ブロック.*?</label>','',html)
    html = html.replace('<style>','<style>\n[hidden]{display:none!important}')
    html = html.replace('<button id="under">','<select id="pose" hidden><option value="aligned">aligned</option></select><input id="lift" hidden value="0"><output id="liftText" hidden></output><button id="under">')
    html = html.replace("const source=mode.value==='section'?data.section:data;",
        "if(mode.value==='balls')scene.push({t:[0,0,0,0],color:[45,153,212],envelope:true});const source=mode.value==='section'?data.section:data.extra[mode.value==='balls'?'single':mode.value]||data;")
    html = html.replace('const vv=source.vertices','const src=obj.envelope?data.extra.balls:source;const vv=src.vertices')
    html = html.replace('for(const f of source.faces)','for(const f of src.faces)')
    html = html.replace('for(const segment of source.edges)','for(const segment of (obj.envelope?data.extra.balls:source).edges)')
    html = html.replace("'Brick CAD inspector · '","'DUPLO 4x4 descending curve · '")
    html = html.replace('<a href="preview.png">断面・4方向画像</a>','<a href="assembly.step">Course STEP</a>')
    html = re.sub(r'<p><small>干渉値.*?</small></p>',
        '<p><small>4x4 / R48 / drop 19.2 mm / high west to low north. Static samples only; fit and rolling untested.</small></p>',html)
    (out/'viewer.html').write_text(html)


def export(out=Path('build/duplo-sloped-curve-trial-02')):
    out = Path(out); out.mkdir(parents=True,exist_ok=True)
    shape,p = build_curve()
    report = verify(shape,p)
    shape.copy(mesh=False).exportStl(str(out/'brick.stl'),tolerance=.03,angularTolerance=.2,relative=False)
    raw=(out/'brick.stl').read_bytes(); triangles=[]
    for i in range(struct.unpack_from('<I',raw,80)[0]):
        tri=raw[84+50*i:134+50*i];v=struct.unpack('<12fH',tri)[3:12]
        if len({tuple(round(x,5) for x in v[j:j+3]) for j in (0,3,6)})==3:
            triangles.append(tri)
    (out/'brick.stl').write_bytes(raw[:80]+struct.pack('<I',len(triangles))+b''.join(triangles))
    cq.exporters.export(shape,str(out/'brick.step'))
    cq.exporters.export(cq.Compound.makeCompound(list(course(shape))),str(out/'assembly.step'))
    restored = cq.importers.importStep(str(out/'brick.step')).val()
    m = mesh_check(out/'brick.stl')
    report['checks'].update(mesh=m['passed'],mesh_volume=abs(m['signed_volume_mm3']-shape.Volume())/shape.Volume()<.001,
        step_roundtrip=restored.isValid() and len(restored.Solids())==1
        and abs(restored.Volume()-shape.Volume())/shape.Volume()<1e-7)
    report.update(kind='duplo-sloped-curve-trial-02',passed=all(report['checks'].values()),
        geometry=dict(bounds_mm=[m['bounds_mm'][1][i]-m['bounds_mm'][0][i] for i in range(3)],
                      brep_conservative_bounds_mm=exact_bounds(shape),volume_mm3=shape.Volume(),parameters=asdict(p)),
        drop_mm=DROP,turn_radius_mm=RADIUS,rail=asdict(RAIL),ports=[asdict(v) for v in ports()],
        ball_diameter_mm=BALL,max_slope_degrees=math.degrees(math.atan(abs(gradient(.5)))),
        physical_fit_validated=False,physical_rolling_validated=False,physical_touch_validated=False,mesh=m,
        design=design_manifest(p,channel=RAIL),retained_complete_tubes=list(RETAINED_TUBES),
        stl_tessellation=dict(linear_tolerance_mm=.03,angular_tolerance_radians=.2),
        limitations=['49 static sphere samples, not continuous clearance or rolling dynamics.',
            '4x4 envelope and port grid inferred from user; middle curvature is our design.',
            'E27-04 receiver dimensions transferred; only three complete tubes retained. All six clipped tube fragments omitted.',
            'Four remaining wall ends and bottom rounded R0.50; previous 20-corner F/D geometry not reused. Final slicer and tactile checks still required.',
            'E27-04 2x2 receiver was preferred; this 4x4 partial-footprint receiver remains untested.',
            'No upper studs: Gap infill / Inner wall stud calibration is not applicable to this part.',
            'Synthetic 9.40 mm studs retain known 0.136 mm radial tube trial interference; no other blocking collision.',
            'Raised approach on nominal support retains known 0.036 mm radial trial interference.',
            'Spline BRep bounding box is conservative; footprint also checked by solid subtraction.',
            'Prior F diagnostic does not validate this revised geometry. Inspect final slice without supports.',
            'Slicer inspection and a real print are required; internal ceiling is a bridge.'],
        source_files={n:hashlib.sha256((Path(__file__).resolve().parents[2]/n).read_bytes()).hexdigest()
                      for n in ('parts/sloped_curve/design.py','parts/straight_rail/design.py','brickcad/model.py','brickcad/standards.py','brickcad/connections.py','brickcad/ports.py','brickcad/render.py','brickcad/viewer.html')},
        files={n:hashlib.sha256((out/n).read_bytes()).hexdigest() for n in ('brick.stl','brick.step','assembly.step')})
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    render(shape,p,report,out)
    print('SLOPED CURVE',report['passed'],report['checks'],flush=True)
    if not report['passed']: raise RuntimeError('Sloped curve verification failed')
    return report


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument('--out',type=Path,default=Path('build/duplo-sloped-curve-trial-02'))
    export(ap.parse_args().out)




