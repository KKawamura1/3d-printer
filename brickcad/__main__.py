import argparse
from dataclasses import asdict, replace
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
import cadquery as cq
from .model import Brick, build, nominal_brick, from_profile
from .provenance import design_manifest
from .verify import geometry_report, fit_report, mesh_check, intersection, place, VOLUME_TOL
from .render import preview, viewer


def save_json(path, data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')


def export(p,out):
    out.mkdir(parents=True,exist_ok=True)
    shape=build(p)
    cq.exporters.export(shape,str(out/'brick.stl'),tolerance=0.01,angularTolerance=0.1)
    cq.exporters.export(shape,str(out/'brick.step'))
    g=geometry_report(p,shape)
    m=mesh_check(out/'brick.stl')
    restored=cq.importers.importStep(str(out/'brick.step')).val()
    step_ok=restored.isValid() and len(restored.Solids())==1 and abs(restored.Volume()-shape.Volume())<1e-5
    fit=fit_report(p,shape)
    fit_clear = (not any(row['collision'] for row in fit['insertion'])
                 and not any(row['collision'] for row in fit['poses'] if 'negative_control' not in row['name']))
    mesh_dims = [hi-lo for lo,hi in zip(*m['bounds_mm'])]
    mesh_agrees = (all(abs(a-b)<1e-4 for a,b in zip(mesh_dims,g['bounds_mm']))
                   and abs(m['signed_volume_mm3']-shape.Volume())/shape.Volume()<0.001)
    report=dict(schema_version=1, design=design_manifest(p), geometry=g, mesh=m, step_roundtrip_passed=step_ok, fit=fit,
                physical_fit_validated=False, fit_geometrically_clear=fit_clear, mesh_matches_cad=mesh_agrees,
                environment={k:importlib.metadata.version(k) for k in ('cadquery','cadquery-ocp','numpy','matplotlib')},
                files={name:hashlib.sha256((out/name).read_bytes()).hexdigest() for name in ('brick.stl','brick.step')},
                passed=g['passed'] and m['passed'] and mesh_agrees and step_ok and fit_clear and fit['negative_controls_passed'])
    save_json(out/'parameters.json',asdict(p))
    save_json(out/'report.json',report)
    preview(shape,p,out)
    viewer(shape,p,report,out)
    print(f"{'PASS' if report['passed'] else 'FAIL'} {out} | CAD {shape.Volume():.3f} mm^3 | STL {m['triangles']} triangles")
    if not report['passed']: raise RuntimeError('Geometric validation failed; see report.json')
    return report


def sweep(p,out):
    out.mkdir(parents=True,exist_ok=True)
    ref=build(nominal_brick(p.family,p.nx,p.ny))
    rows=[]
    for c in (-0.04,0.0,0.04,0.08,0.12):
        spec=replace(p,clearance=c)
        shape=build(spec)
        name=f'clearance_{c:+.2f}'.replace('.','p')
        stl=out/f'{name}.stl'
        cq.exporters.export(shape,str(stl),tolerance=0.01,angularTolerance=0.1)
        mesh=mesh_check(stl)
        geometry=geometry_report(spec,shape)
        if not mesh['passed'] or not geometry['passed']: raise RuntimeError(f'Sweep CAD/mesh failed: {c}')
        row=dict(id=name,radial_clearance_mm=c,file=stl.name,parameters=asdict(spec),mesh_passed=mesh['passed'])
        for label,lower,upper in [('self',shape,shape),('reference_lower',ref,shape),('reference_upper',shape,ref)]:
            v=intersection(lower,place(upper,(0,0,p.height)))
            row[label]=dict(intersection_mm3=v,collision=v>VOLUME_TOL)
        rows.append(row)
        print(f'SWEEP {c:+.2f} mm: '+', '.join(f'{k}={row[k]["intersection_mm3"]:.5f} mm^3' for k in ('self','reference_lower','reference_upper')))
    save_json(out/'sweep.json',dict(physical_fit_validated=False,reference='synthetic nominal geometry, not genuine brick',variants=rows))
    save_json(out/'measurement-template.json',dict(printer=None,nozzle_mm=None,material=None,layer_height_mm=None,slicer_version=None,print_settings={},reference_part=None,results=[dict(id=r['id'],stud_diameter_mm=None,body_x_mm=None,body_y_mm=None,printed_on_reference=None,reference_on_printed=None,printed_on_printed=None,notes='unprinted') for r in rows]))


def main():
    parser=argparse.ArgumentParser(description='Build, verify, render and calibrate brick CAD (mm).')
    parser.add_argument('command',choices=['build','sweep','all'])
    parser.add_argument('--profile',type=Path,default=Path('profiles/duplo-first-print.json'))
    parser.add_argument('--out',type=Path,default=Path('build/duplo-2x4'))
    args=parser.parse_args()
    p=from_profile(json.loads(args.profile.read_text()))
    if args.command in ('build','all'):export(p,args.out)
    if args.command in ('sweep','all'):sweep(p,args.out/'calibration')


if __name__=='__main__':main()

