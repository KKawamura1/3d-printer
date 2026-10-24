"""Issue #3 / M1: rail--two hidden tunnels--rail assembly verification."""
from dataclasses import asdict, replace
from pathlib import Path
import hashlib
import importlib.metadata
import json
import cadquery as cq
from .ports import straight_ports, mate
from .rail import Rail, build_rail, fit_profile
from .tunnel import Tunnel, build_tunnel
from .render import viewer, mesh, outlines
from .verify import intersection, exact_bounds, VOLUME_TOL


BALL_DIAMETER_MM = 24.26
RUNNING_LIFT_MM = .05  # numerical clearance; not a measured rolling height


def assembly():
    rail, _ = build_rail()
    tunnel, p = build_tunnel()
    r, t = Rail(), Tunnel()
    modules = []
    for name, kind, shape, x, cells, floor, radius in [
        ('approach', 'rail', rail, -64., 4, r.floor, r.radius),
        ('hidden-1', 'tunnel', tunnel, -16., 2, t.floor, t.radius),
        ('hidden-2', 'tunnel', tunnel, 16., 2, t.floor, t.radius),
        ('exit', 'rail', rail, 64., 4, r.floor, r.radius)]:
        modules.append(dict(name=name, kind=kind, shape=shape.translate((x,0,0)),
                            xyz_mm=(x,0.,0.), yaw_deg=0., cells=cells,
                            ports=tuple(port.placed((x,0.,0.))
                                        for port in straight_ports(cells,floor,radius))))
    return modules, replace(p,nx=12)


def swept_ball(diameter_mm=BALL_DIAMETER_MM):
    if not 0 < diameter_mm < float('inf'):
        raise ValueError('Ball diameter must be finite and positive')
    radius = diameter_mm/2
    # Cylinder extends a ball radius past both assembly ends. It contains the
    # complete continuous swept sphere, including both mouths and all seams.
    return cq.Solid.makeCylinder(radius,192+2*radius,
        cq.Vector(-96-radius,0,Tunnel().floor+radius+RUNNING_LIFT_MM), cq.Vector(1,0,0))


def verify(modules):
    joints = [dict(left=a['name'],right=b['name'],**mate(a['ports'][1],b['ports'][0]))
              for a,b in zip(modules,modules[1:])]
    pairs = [dict(a=a['name'],b=b['name'],intersection_mm3=intersection(a['shape'],b['shape']))
             for i,a in enumerate(modules) for b in modules[i+1:]]
    sweep = swept_ball()
    paths = [dict(module=m['name'],intersection_mm3=intersection(m['shape'],sweep)) for m in modules]
    # Real defective CAD controls, not just bad metadata.
    controls = dict(
        raised_tunnel_mm3=intersection(modules[1]['shape'].translate((0,0,1)),sweep),
        sideways_tunnel_mm3=intersection(modules[1]['shape'].translate((0,4,0)),sweep),
        oversized_ball_mm3=intersection(modules[1]['shape'],swept_ball(28.)))
    checks = dict(valid_solids=all(m['shape'].isValid() and len(m['shape'].Solids())==1 for m in modules),
                  ports_match=all(j['compatible'] for j in joints),
                  bodies_separate=all(p['intersection_mm3'] < VOLUME_TOL for p in pairs),
                  continuous_path_clear=all(p['intersection_mm3'] < VOLUME_TOL for p in paths),
                  defects_detected=all(v > VOLUME_TOL for v in controls.values()))
    return dict(checks=checks, joints=joints, body_pairs=pairs, continuous_sweep=paths,
                negative_controls=controls, passed=all(checks.values()))


def export(out=Path('build/pitagora-m1')):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    modules,p=assembly()
    compound=cq.Compound.makeCompound([m['shape'] for m in modules])
    report=verify(modules)
    cq.exporters.export(compound,str(out/'assembly.step'))
    restored=cq.importers.importStep(str(out/'assembly.step')).val()
    report['checks']['step_roundtrip']=restored.isValid() and len(restored.Solids())==4 and abs(restored.Volume()-compound.Volume())<1e-4
    report.update(schema_version=1,kind='pitagora-m1',physical_fit_validated=False,
                  physical_rolling_validated=False,ball_diameter_mm=BALL_DIAMETER_MM,
                  running_lift_mm=RUNNING_LIFT_MM,
                  part_parameters=dict(rail=asdict(Rail()),tunnel=asdict(Tunnel()),
                                       fit_trial=asdict(fit_profile())),
                  source_files={name:hashlib.sha256((Path(__file__).parent/name).read_bytes()).hexdigest()
                                for name in ('pitagora.py','ports.py','rail.py','tunnel.py','model.py','render.py','viewer.html')},
                  geometry=dict(bounds_mm=exact_bounds(compound),parameters=asdict(p)),
                  modules=[{k:([asdict(x) for x in v] if k=='ports' else v)
                            for k,v in m.items() if k!='shape'} for m in modules],
                  environment={k:importlib.metadata.version(k) for k in ('cadquery','cadquery-ocp')},
                  files={'assembly.step':hashlib.sha256((out/'assembly.step').read_bytes()).hexdigest()},
                  limitations=['Horizontal course needs incoming momentum; no dynamics or friction model.',
                               '0.2 mm mouth gaps are nominal grid gaps, not interlocking joints.',
                               'Revised fit profile is unvalidated; existing receiver interference remains.',
                               'Support bricks and genuine rail interfaces are not included in this assembly.',
                               'Continuous swept cylinder is a conservative rigid clearance check, not a guarantee of rolling.'])
    report['passed']=all(report['checks'].values())
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    # Keep assembly-specific controls separate from the generic stacking viewer.
    render_report={**report,'fit':dict(insertion=[],poses=[])}
    viewer(compound,p,render_report,out)
    html=(out/'viewer.html').read_text()
    import re
    html=html.replace('<style>','<style>\n[hidden]{display:none!important}')
    html=html.replace('CAD・STL検証:', 'CAD assembly:')
    html=re.sub(r'<label>表示<select id="mode">.*?</select></label>',
        '<label>表示<select id="mode"><option value="single">Assembly</option><option value="section">Longitudinal section</option><option value="exploded">Exploded along X</option><option value="balls">Ball envelope at seams</option><option value="ballsection">Cutaway with ball envelopes</option></select></label>',html)
    html=re.sub(r'<label>組み合わせ.*?</label>','',html)
    html=re.sub(r'<label>上ブロック.*?</label>','',html)
    html=html.replace('<button id="under">','<select id="pose" hidden><option value="aligned">aligned</option></select><input id="lift" hidden value="0"><output id="liftText" hidden></output><button id="under">')
    extras={}
    exploded=cq.Compound.makeCompound([m['shape'].translate(((i-1.5)*12,0,0)) for i,m in enumerate(modules)])
    balls=cq.Compound.makeCompound([cq.Solid.makeSphere(BALL_DIAMETER_MM/2,
        cq.Vector(x,0,Tunnel().floor+BALL_DIAMETER_MM/2+RUNNING_LIFT_MM),angleDegrees1=-90)
        for x in (-32.,0.,32.)])
    for key,shape in [('exploded',exploded),('balls',balls)]:
        v,f=mesh(shape);extras[key]=dict(vertices=v,faces=f,edges=outlines(shape))
    html=html.replace('const canvas=', 'data.extra='+json.dumps(extras,separators=(',',':'))+';\nconst canvas=')
    html=html.replace("const source=mode.value==='section'?data.section:data;",
        "if(['balls','ballsection'].includes(mode.value))scene.push({t:[0,0,0,0],color:[45,153,212],ball:true});const source=['section','ballsection'].includes(mode.value)?data.section:mode.value==='exploded'?data.extra.exploded:data;")
    html=html.replace('const vv=source.vertices','const src=obj.ball?data.extra.balls:source;const vv=src.vertices')
    html=html.replace('for(const f of source.faces)','for(const f of src.faces)')
    html=html.replace('for(const segment of source.edges)','for(const segment of (obj.ball?data.extra.balls:source).edges)')
    html=html.replace("'Brick CAD inspector · '","'Pitagora M1 assembly · '")
    html=html.replace('<a href="preview.png">断面・4方向画像</a>','<a href="assembly.step">Assembly STEP (not a print plate)</a>')
    html=re.sub(r'<p><small>干渉値.*?</small></p>', '<p><small>Rigid continuous path: 24.26 mm ball, numerical lift 0.05 mm. CAD PASS only. Physical fit and rolling untested. Exploded view is illustrative; its clearance is not calculated.</small></p>',html)
    (out/'viewer.html').write_text(html)
    print('PITAGORA M1', 'PASS' if report['passed'] else 'FAIL',report['checks'],flush=True)
    if not report['passed']:raise RuntimeError('M1 assembly verification failed')
    return report


if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,default=Path('build/pitagora-m1'))
    export(ap.parse_args().out)
