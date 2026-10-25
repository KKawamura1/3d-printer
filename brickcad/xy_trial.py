"""Conditional 2x2 fit candidate: compensate body extents, preserve mating geometry."""
from dataclasses import asdict, replace
from pathlib import Path
from types import SimpleNamespace
import hashlib
import json
import math
import zipfile
import cadquery as cq
from .experiment import export_stl
from .model import nominal_brick, receiver
from .render import viewer, preview
from .verify import exact_bounds, fit_report, intersection, place

DEFAULT_PROFILE=Path(__file__).resolve().parents[1]/'profiles/duplo-xy-fit-trial-01.json'


def build(profile):
    dims=[profile[k] for k in ('body_x_mm','body_y_mm','stud_diameter_mm','stud_hole_mm')]
    if not all(math.isfinite(v) and v>0 for v in dims):
        raise ValueError('Dimensions must be finite and positive')
    if not (31.8<=dims[0]<=32.1 and 31.8<=dims[1]<=32.1):
        raise ValueError('Only local 2x2 body compensation is supported')
    if not (9.36<=dims[2]<=9.44 and 6.35<=dims[3]<=6.50):
        raise ValueError('Use stud dimensions within the current experiment range')
    p=replace(nominal_brick('duplo',2,2),stud_radius=dims[2]/2,stud_inner_radius=dims[3]/2)
    outer=cq.Workplane('XY').box(dims[0],dims[1],p.height,centered=(True,True,False))
    outer=outer.edges('|Z').fillet(.8).edges('>Z').fillet(.8)
    # Receiver uses the unchanged 31.8x31.8 reference footprint: cavity remains
    # exactly 25.40 square. Only the *outer* faces move outward.
    body=receiver(p,outer,p.height-p.roof,.3,footprint=(31.8,31.8))
    studs=cq.Workplane('XY',origin=(0,0,p.height)).pushPoints(p.studs()).circle(p.stud_radius).circle(p.stud_inner_radius).extrude(p.stud_height)
    studs=studs.edges('>Z').fillet(.5)
    s=body.union(studs).val().clean()
    assert s.isValid() and len(s.Solids())==1
    assert all(abs(a-b)<1e-6 for a,b in zip(exact_bounds(s),[dims[0],dims[1],23.7]))
    return p,s


def export(out=Path('build/duplo-xy-fit-trial-01'),profile_path=DEFAULT_PROFILE):
    profile=json.loads(Path(profile_path).read_text())
    p,s=build(profile);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    m=export_stl(s,out/'brick.stl')
    cq.exporters.export(s,str(out/'brick.step'))
    restored=cq.importers.importStep(str(out/'brick.step')).val()
    step=restored.isValid() and len(restored.Solids())==1 and abs(restored.Volume()-s.Volume())<1e-4
    assert step
    fit=fit_report(p,s)
    fit_clear=(not any(r['collision'] for r in fit['insertion']) and
        not any(r['collision'] for r in fit['poses'] if 'negative_control' not in r['name']))
    assert fit['negative_controls_passed']
    # Record CAD body adjacency as well as both directions against synthetic
    # DUPLO and rotated self-assembly. Contact volume does not predict clutch.
    adjacent=[]
    for x,y in [(32,0),(0,32)]:
        v=intersection(s,place(s,(x,y,0)))
        adjacent.append(dict(offset_xyz_mm=[x,y,0],intersection_mm3=v))
        assert v<1e-7
    expected=dict(body_xy_mm=[profile['body_x_mm']-.2043,profile['body_y_mm']-.0671],
        underside_span_xy_mm=[25.4-.1871,25.4-.0571],
        stud_diameter_mm=profile['stud_diameter_mm']-.065,
        status='Conditional offset-model illustrations, not verified predictions or measurement records')
    report=dict(passed=True,physical_fit_validated=False,slicing_validated=False,
        profile=profile,fit_geometrically_clear=fit_clear,geometry=dict(parameters=dict(family='duplo',nx=2,ny=2,clearance=0,
            body_x_mm=profile['body_x_mm'],body_y_mm=profile['body_y_mm'],
            height_mm=19.2,stud_height_mm=4.5,stud_pitch_xy_mm=[16,16],
            stud_diameter_mm=2*p.stud_radius,stud_hole_mm=2*p.stud_inner_radius,
            underside_span_xy_mm=[25.4,25.4],tube_outer_mm=13.1,tube_inner_mm=9.4,
            side_wall_xy_mm=[(profile['body_x_mm']-25.4)/2,(profile['body_y_mm']-25.4)/2],
            roof_mm=1.6,corner_radius_mm=.8,stud_lip_radius_mm=.5,entry_chamfer_mm=.3),
            bounds_mm=exact_bounds(s)),mesh=m,step_roundtrip_passed=step,fit=fit,
        adjacent=adjacent,conditional_estimates=expected,
        limitations=['The ongoing 14-coupon print has no physical results yet.',
            'Body offsets come from seven earlier coupons in one job; scale versus offset is unresolved.',
            'Preserving cavity dimensions does not preserve stiffness, heat history or toolpaths.',
            'No pitch, stud XY ellipticity, tube or Z compensation is inferred.',
            'Print at rotation 0 degrees; CAD X must match printer X. Do not auto-rotate or scale.',
            'Reconfirm Inner wall in the final slice and remeasure all mating directions.'])
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    (out/'profile.json').write_text(json.dumps(profile,ensure_ascii=False,indent=2)+'\n')
    # Viewer dimensions describe the actual corrected body; fit calculations
    # retain independent nominal mating references at 16mm pitch.
    vp=SimpleNamespace(**{**asdict(p),'width':profile['body_x_mm'],'depth':profile['body_y_mm']})
    viewer(s,vp,report,out);preview(s,vp,out)
    hashes={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in out.iterdir() if f.is_file() and f.name!='sha256.json'}
    (out/'sha256.json').write_text(json.dumps(hashes,indent=2)+'\n')
    print('XY TRIAL PASS',report['geometry']['bounds_mm'],flush=True)
    return report


def package(out,destination):
    destination=Path(destination);destination.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as z:
        for name in ('brick.stl','brick.step','report.json','profile.json','sha256.json','preview.png','viewer.html'):
            z.write(Path(out)/name,name)
        z.write(Path(__file__).resolve().parents[1]/'docs/duplo-xy-fit-trial-01.md','README.md')


if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--profile',type=Path,default=DEFAULT_PROFILE)
    ap.add_argument('--out',type=Path,default=Path('build/duplo-xy-fit-trial-01'))
    ap.add_argument('--zip',type=Path)
    args=ap.parse_args();export(args.out,args.profile)
    if args.zip:package(args.out,args.zip)
