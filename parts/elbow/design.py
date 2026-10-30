"""M1: enclosed 90-degree DUPLO tunnel. Exact revolved section, not sampled cuts."""
from dataclasses import asdict, replace
from pathlib import Path
import hashlib
import json
import math
import struct
import cadquery as cq
from brickcad.model import receiver, brick_from_fit
from brickcad.connections import make_studs
from brickcad.provenance import design_manifest
from brickcad.marking import engrave

PART_ID = "E01-V2"
from parts.straight_rail.design import fit_profile, build_rail
from parts.tunnel.design import Tunnel
from brickcad.ports import Port, straight_ports, mate
from brickcad.verify import intersection, exact_bounds, mesh_check, VOLUME_TOL
from brickcad.render import viewer, mesh, outlines


TURN_RADIUS = 48.0
TURN_CENTRE = (-32.0, 32.0, 0.0)
BALL_DIAMETER = 24.26
LIFT = .05  # numerical clearance only; not a physical rolling result


def revolve(section):
    """XZ radial section around Z, from south to east, then place on cell grid."""
    return (section.revolve(90, (0, 0), (0, 1)).val()
            .rotate((0, 0, 0), (0, 0, 1), -90).translate(TURN_CENTRE))


def ports(t=Tunnel()):
    return (Port('west', (-32., -16., t.floor), (-1., 0., 0.), t.radius),
            Port('north', (16., 32., t.floor), (0., 1., 0.), t.radius))


def centre(angle_deg, radius, t=Tunnel()):
    a = math.radians(angle_deg)
    return cq.Vector(-32 + TURN_RADIUS*math.cos(a),
                     32 + TURN_RADIUS*math.sin(a), t.floor+radius+LIFT)


def ball_sweep(diameter=BALL_DIAMETER, t=Tunnel()):
    """Exact union of balls along the full circular path, including end caps."""
    if not math.isfinite(diameter) or not 0 < diameter < 2*TURN_RADIUS:
        raise ValueError('Ball diameter must be finite, positive and below turn diameter')
    r = diameter/2
    torus = revolve(cq.Workplane('XZ').moveTo(TURN_RADIUS, t.floor+r+LIFT).circle(r))
    for angle in (-90, 0):
        torus = torus.fuse(cq.Solid.makeSphere(r, centre(angle, r, t), angleDegrees1=-90))
    return torus.clean()


def build_elbow(t=Tunnel()):
    p = brick_from_fit('duplo-e27-play-v1', nx=4, ny=4, height_units=2)
    outer = cq.Workplane('XY').box(p.width, p.depth, p.height, centered=(True, True, False))
    outer = outer.edges('|Z').fillet(.8).edges('>Z').fillet(.8)
    result = receiver(p, outer, t.cavity_height, 0)
    result = result.edges('<Z').fillet(.5)
    # Same circular floor and self-supporting 45-degree roof as straight tunnel.
    a, b = t.radius/math.sqrt(2), t.bridge_width/2
    cy = t.floor+t.radius
    section = (cq.Workplane('XZ').moveTo(TURN_RADIUS-a, cy+a)
               .threePointArc((TURN_RADIUS, t.floor), (TURN_RADIUS+a, cy+a))
               .lineTo(TURN_RADIUS+b, t.ceiling)
               .lineTo(TURN_RADIUS-b, t.ceiling).close())
    result = result.cut(revolve(section))
    # Lead-ins only at the physical mouths; no fillet across internal sweep seams.
    mouths = [e for e in result.val().Edges()
              if (abs(e.Center().x+p.width/2)<1e-5 or abs(e.Center().y-p.depth/2)<1e-5)
              and e.BoundingBox().zmin>t.floor-.01
              and e.BoundingBox().zmax<t.ceiling+.01]
    if len(mouths) != 8:
        raise ValueError(f'Expected eight mouth edges, got {len(mouths)}')
    result = result.newObject(mouths).fillet(t.entry)
    studs = make_studs(p.studs(), p.height, p.stud_radius, p.stud_inner_radius, p.stud_height, .5)
    shape = result.union(studs).val().clean()
    if not shape.isValid() or len(shape.Solids()) != 1:
        raise ValueError('Elbow must be one valid solid')
    return engrave(shape,PART_ID,x=0,y=-p.depth/2,z=10.), p


def assembly(shape):
    rail, _ = build_rail()
    approach = rail.translate((-64, -16, 0))
    exit_rail = rail.rotate((0, 0, 0), (0, 0, 1), 90).translate((16, 64, 0))
    return approach, shape, exit_rail


def course_sweep(t=Tunnel()):
    r = BALL_DIAMETER/2
    z = t.floor+r+LIFT
    return ball_sweep(t=t).fuse(
        cq.Solid.makeCylinder(r,64+r,cq.Vector(-96-r,-16,z),cq.Vector(1,0,0)),
        cq.Solid.makeCylinder(r,64+r,cq.Vector(16,32,z),cq.Vector(0,1,0))).clean()


def verify(shape, t=Tunnel()):
    sweep = course_sweep(t)
    pieces = assembly(shape)
    path = [intersection(s, sweep) for s in pieces]
    pairs = [intersection(a, b) for i, a in enumerate(pieces) for b in pieces[i+1:]]
    left, right = straight_ports(4, t.floor, t.radius)
    west, north = ports(t)
    joints = [mate(right.placed((-64, -16, 0)), west),
              mate(north, left.placed((16, 64, 0), 90))]
    oversized = intersection(shape, ball_sweep(28., t))
    # Actual-geometry negative controls: a 1 mm floor step and lateral blockage.
    step = intersection(shape.translate((0, 0, 1)), sweep)
    shifted = intersection(shape.translate((4, 0, 0)), sweep)
    floor = [shape.isInside(centre(a, 0, t) - cq.Vector(0, 0, .15))
             for a in (-80, -60, -45, -30, -10)]
    checks = dict(valid_brep=shape.isValid(), one_solid=len(shape.Solids()) == 1,
                  continuous_ball_path_clear=max(path)<VOLUME_TOL,
                  assembly_bodies_clear=max(pairs)<VOLUME_TOL,
                  ports_match=all(j['compatible'] for j in joints),
                  floor_present=all(floor), oversize_detected=oversized>VOLUME_TOL,
                  floor_step_detected=step>VOLUME_TOL, lateral_shift_detected=shifted>VOLUME_TOL)
    return dict(checks=checks, joints=joints, sweep_intersections_mm3=path,
                body_intersections_mm3=pairs,
                negative_controls_mm3=dict(oversize_28=oversized, floor_step_1=step, lateral_shift_4=shifted))


def export(out=Path('build/duplo-elbow-trial-01')):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    t = Tunnel(); shape, p = build_elbow(t)
    report = verify(shape, t)
    cq.exporters.export(shape, str(out/'brick.stl'), tolerance=.03, angularTolerance=.2)
    # Match existing pole-triangle cleanup: remove only float32-collapsed facets.
    stl = out/'brick.stl'; raw = stl.read_bytes(); tris = []
    for i in range(struct.unpack_from('<I', raw, 80)[0]):
        tri = raw[84+50*i:134+50*i]; v = struct.unpack('<12fH', tri)[3:12]
        if len({tuple(v[j:j+3]) for j in (0, 3, 6)}) == 3: tris.append(tri)
    removed = struct.unpack_from('<I', raw, 80)[0]-len(tris)
    stl.write_bytes(raw[:80]+struct.pack('<I', len(tris))+b''.join(tris))
    cq.exporters.export(shape, str(out/'brick.step'))
    restored = cq.importers.importStep(str(out/'brick.step')).val()
    compound = cq.Compound.makeCompound(list(assembly(shape)))
    cq.exporters.export(compound, str(out/'assembly.step'))
    mesh_report = mesh_check(stl)
    report['checks'].update(
        dimensions=all(abs(a-b)<1e-6 for a, b in zip(exact_bounds(shape), (63.8, 63.8, 42.9))),
        mesh=mesh_report['passed'],
        mesh_volume=abs(mesh_report['signed_volume_mm3']-shape.Volume())/shape.Volume()<.001,
        step_roundtrip=restored.isValid() and len(restored.Solids())==1
                       and abs(restored.Volume()-shape.Volume())/shape.Volume()<1e-7
                       and all(abs(a-b)<1e-5 for a,b in zip(exact_bounds(restored),exact_bounds(shape))),
        tube_holes=all(not shape.isInside(cq.Vector(x, y, 1)) for x, y in p.tubes()),
        tube_walls=all(shape.isInside(cq.Vector(x+5.5, y, 1)) for x, y in p.tubes()),
        hollow_studs=all(not shape.isInside(cq.Vector(x, y, 41)) for x, y in p.studs()))
    report.update(schema_version=1, kind='duplo-elbow-trial-01', passed=all(report['checks'].values()),
        geometry=dict(bounds_mm=exact_bounds(shape), volume_mm3=shape.Volume(), parameters=asdict(p)),
        tunnel=asdict(t), turn_radius_mm=TURN_RADIUS, ports=[asdict(v) for v in ports(t)],
        ball_diameter_mm=BALL_DIAMETER, running_lift_mm=LIFT, mesh=mesh_report,
        stl_tessellation=dict(linear_tolerance_mm=.03,angular_tolerance_radians=.2),
        step_volume_delta_mm3=restored.Volume()-shape.Volume(),
        step_volume_relative_tolerance=1e-7,
        collapsed_stl_triangles_removed=removed,
        physical_fit_validated=False, physical_rolling_validated=False,
        design=design_manifest(p, channel=t),
        finish_detail=dict(outer_corner_radius_mm=.8,stud_lip_radius_mm=.5,receiver_bottom_radius_mm=.5,mouth_radius_mm=.3),
        receiver_profile='duplo-e27-play-v1: E27-04 receiver, top 9.40/6.40; transfer not physically validated',
        limitations=['Horizontal bend requires incoming momentum; no dynamics/friction model.',
                     'Curvature may lose speed or cause wall contact; test both directions in real print.',
                     'E27 fit transferred to 4x4; larger structure and top process variation remain unverified.',
                     'Internal roof bridge and overhangs need slicer/physical inspection.',
                     '0.05 mm lift is numerical, not a measured trajectory; CAD PASS is not physical PASS.'],
        source_files={n:hashlib.sha256((Path(__file__).resolve().parents[2]/n).read_bytes()).hexdigest()
                      for n in ('parts/elbow/design.py','parts/straight_rail/design.py','parts/tunnel/design.py','brickcad/ports.py','brickcad/model.py','brickcad/standards.py','brickcad/connections.py','brickcad/render.py','brickcad/viewer.html')},
        files={n:hashlib.sha256((out/n).read_bytes()).hexdigest() for n in ('brick.stl','brick.step','assembly.step')})
    (out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    render(shape, p, report, out)
    print('ELBOW', 'PASS' if report['passed'] else 'FAIL', report['checks'], flush=True)
    if not report['passed']: raise RuntimeError('Elbow verification failed')
    return report


def render(shape, p, report, out):
    """Keep generic brick viewer intact, add elbow-specific assembly/cutaway views."""
    import re
    viewer(shape, p, {**report, 'fit':dict(insertion=[], poses=[])}, out)
    html = (out/'viewer.html').read_text()
    # Horizontal cut removes roof and shows the complete curved passage.
    cutter = cq.Workplane('XY', origin=(0, 0, 19.2)).box(200,200,100,centered=(True,True,False)).val()
    pieces = assembly(shape)
    extras = {}
    balls = cq.Compound.makeCompound([cq.Solid.makeSphere(BALL_DIAMETER/2, centre(a,BALL_DIAMETER/2),
                                        angleDegrees1=-90) for a in (-75,-45,-15)])
    exploded = cq.Compound.makeCompound([pieces[0].translate((-12,0,0)),shape,pieces[2].translate((0,12,0))])
    for key, solid in [('cutaway',shape.cut(cutter)),('course',cq.Compound.makeCompound(list(pieces))),
                       ('exploded',exploded),('balls',balls),('sweep',ball_sweep())]:
        v, f = mesh(solid); extras[key] = dict(vertices=v,faces=f,edges=outlines(solid))
    html = html.replace('const canvas=', 'data.extra='+json.dumps(extras,separators=(',',':'))+';\nconst canvas=')
    html = re.sub(r'<label>表示<select id="mode">.*?</select></label>',
        '<label>表示<select id="mode"><option value="single">Tunnel</option><option value="section">Section Y</option><option value="cutaway">Roof removed</option><option value="balls">Cutaway + balls</option><option value="sweep">Cutaway + continuous sweep</option><option value="course">Rail connections</option><option value="exploded">Exploded course</option></select></label>',html)
    html = re.sub(r'<label>組み合わせ.*?</label>', '', html)
    html = re.sub(r'<label>上ブロック.*?</label>', '', html)
    html = html.replace('<style>', '<style>\n[hidden]{display:none!important}')
    html = html.replace('<button id="under">','<select id="pose" hidden><option value="aligned">aligned</option></select><input id="lift" hidden value="0"><output id="liftText" hidden></output><button id="under">')
    html = html.replace("const source=mode.value==='section'?data.section:data;",
        "if(['balls','sweep'].includes(mode.value))scene.push({t:[0,0,0,0],color:[45,153,212],envelope:true});const source=mode.value==='section'?data.section:['balls','sweep'].includes(mode.value)?data.extra.cutaway:data.extra[mode.value]||data;")
    html = html.replace('const vv=source.vertices', "const src=obj.envelope?data.extra[mode.value==='sweep'?'sweep':'balls']:source;const vv=src.vertices")
    html = html.replace('for(const f of source.faces)', 'for(const f of src.faces)')
    html = html.replace('for(const segment of source.edges)', "for(const segment of (obj.envelope?data.extra[mode.value==='sweep'?'sweep':'balls']:source).edges)")
    html = html.replace("'Brick CAD inspector · '", "'DUPLO 90-degree tunnel · '")
    html = html.replace('<a href="preview.png">断面・4方向画像</a>', '<a href="assembly.step">Course STEP</a>')
    html = re.sub(r'<p><small>干渉値.*?</small></p>', '<p><small>90-degree horizontal tunnel / R48 / ball 24.26 mm. Roof removed only in cutaway views. Incoming momentum required. Fit and rolling untested.</small></p>', html)
    (out/'viewer.html').write_text(html)


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument('--out',type=Path,default=Path('build/duplo-elbow-trial-01'))
    export(ap.parse_args().out)

