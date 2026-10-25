"""Issue #1: isolate stud hole size, then tune OD with a selected hole size."""
from dataclasses import asdict
from pathlib import Path
import csv
import hashlib
import json
import math
import zipfile
import cadquery as cq
from .experiment import coupon, export_stl
from .render import viewer
from .verify import exact_bounds, fit_report


def plan(stage='holes', hole=None):
    if stage not in ('holes', 'diameters'):
        raise ValueError('Unknown stage')
    if stage == 'holes' and hole is not None:
        raise ValueError('Hole stage uses the four predefined hole diameters')
    if stage == 'diameters' and (hole is None or not math.isfinite(hole) or not 6.35 <= hole <= 6.50):
        raise ValueError('Select a hole diameter in 6.35..6.50 after slicing stage 1')
    # Same rotation, symmetrical duplicate positions, no auto-arranging on import.
    cases = [(9.40, h, 1) for h in (6.50, 6.45, 6.40, 6.35)] if stage == 'holes' else [
        (d, hole, rep) for rep, ds in [(1, (9.36, 9.40, 9.44)), (2, (9.44, 9.40, 9.36))] for d in ds]
    cols = 2 if stage == 'holes' else 3
    return [dict(id=f'{i+1:02}', stage=stage, replicate=rep,
        stud_diameter_mm=d, stud_hole_diameter_mm=h, annular_wall_mm=(d-h)/2,
        tube_diameter_mm=13.10, wall_mm=3.20, rotation_deg=0,
        bed_center_xy_mm=[90+(i % cols-(cols-1)/2)*42,111-(i//cols)*42])
        for i, (d,h,rep) in enumerate(cases)]


def generate(out, stage='holes', hole=None):
    records=plan(stage,hole)
    out=Path(out)
    # Prevent mixing a new parameter selection with stale models/reports.
    if out.exists() and any(out.iterdir()):
        raise ValueError('Use an empty output directory')
    out.mkdir(parents=True,exist_ok=True)
    shapes=[]
    for r in records:
        print('Generating',r['id'],r['stud_diameter_mm'],r['stud_hole_diameter_mm'],flush=True)
        p,s=coupon(r)
        name=f"{r['id']}-OD{r['stud_diameter_mm']:.2f}-ID{r['stud_hole_diameter_mm']:.2f}.stl"
        result=export_stl(s,out/name)
        step=out/Path(name).with_suffix('.step')
        cq.exporters.export(s,str(step))
        restored=cq.importers.importStep(str(step)).val()
        assert restored.isValid() and len(restored.Solids())==1
        assert abs(restored.Volume()-s.Volume())<1e-4
        r.update(file=name,parameters=asdict(p),step_roundtrip_passed=True,**result)
        # A viewer per actual variant; collision status is descriptive, not a clutch test.
        vout=out/r['id'];vout.mkdir()
        report=dict(passed=True,physical_fit_validated=False,
            geometry=dict(parameters=asdict(p),bounds_mm=exact_bounds(s)),fit=fit_report(p,s))
        viewer(s,p,report,vout)
        (vout/'brick.stl').write_bytes((out/name).read_bytes())
        (vout/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        x,y=r['bed_center_xy_mm'];shapes.append(s.translate((x-90,y-90,0)))
    for i,a in enumerate(shapes):
        for b in shapes[i+1:]: assert a.intersect(b).Volume()<1e-7
    plate=cq.Compound.makeCompound(shapes)
    assert plate.isValid() and len(plate.Solids())==len(records)
    plate_mesh=export_stl(plate,out/'plate.stl')
    cq.exporters.export(plate,str(out/'plate.step'))
    restored=cq.importers.importStep(str(out/'plate.step')).val()
    assert restored.isValid() and len(restored.Solids())==len(records)
    assert abs(restored.Volume()-plate.Volume())<1e-4
    bounds=exact_bounds(plate)
    assert bounds[0]+10<180 and bounds[1]+10<180
    report=dict(schema_version=1,stage=stage,passed=True,physical_fit_validated=False,
        slicing_validated=False,source_issue='https://github.com/KKawamura1/3d-printer/issues/1',
        selected_hole_mm=hole,bounds_mm=bounds,plate_mesh=plate_mesh,step_roundtrip_passed=True,
        variants=records,bed_size_mm=[180,180],bed_center_mm=[90,90],spacing_mm=42,
        limitations=['Inner wall generation must be checked in Bambu Studio, for each stud and diameter.',
            'Hole changes also change stiffness; toolpath causality is not isolated.',
            'No physical fit, hole compatibility or repeatability has been validated.',
            'Placement/exclusion zones and sliced brim must be checked before printing.'])
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    with (out/'slicing-and-fit.csv').open('w',newline='') as f:
        w=csv.writer(f)
        w.writerow(['id','stud_diameter_mm','hole_diameter_mm','slicer_version','middle_layer_z_mm',
            'stud_-X-Y_role','stud_-X+Y_role','stud_+X-Y_role','stud_+X+Y_role',
            'seated','inverted_retention','removable','after_10_cycles','notes'])
        for r in records:w.writerow([r['id'],r['stud_diameter_mm'],r['stud_hole_diameter_mm']]+['']*12)
    with (out/'measurements.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['id','stud','local_axis','repeat','diameter_mm','notes'])
        for r in records:
            for stud in ('-X-Y','-X+Y','+X-Y','+X+Y'):
                for axis in ('X','Y'):
                    for repeat in range(1,4):w.writerow([r['id'],stud,axis,repeat,'',''])
    setup=dict(actual_print_performed=False,slicing_validated=False,printer='Bambu Lab A1 mini',
        nozzle_mm=.4,material='Bambu PLA Basic',reference_part=None,gcode_sha256=None,
        project_3mf_sha256=None,actual_settings={},actual_centers_and_rotations_verified=False,
        expected_settings=dict(slicer_version='2.8.02.61',layer_height_mm=.20,wall_loops=2,
            wall_generator='Classic',outer_wall_line_width_mm=.42,inner_wall_line_width_mm=.45,
            outer_wall_speed_mm_s=200,sparse_infill_pattern='Grid',sparse_infill_percent=15,
            filament_flow_ratio=.98,xy_contour_compensation_mm=0,xy_hole_compensation_mm=0,
            print_sequence='by layer'))
    (out/'setup.json').write_text(json.dumps(setup,indent=2)+'\n')
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()}
    (out/'sha256.json').write_text(json.dumps(hashes,indent=2)+'\n')
    print('PASS',bounds,flush=True)
    return report


def package(out,destination):
    destination=Path(destination);destination.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as z:
        for path in sorted(Path(out).iterdir()):
            if path.is_file():z.write(path,path.name)
        z.write(Path(__file__).resolve().parents[1]/'docs/duplo-stud-inner-wall.md','README.md')


if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--stage',choices=['holes','diameters'],default='holes')
    ap.add_argument('--hole',type=float,help='Stage 2 only: hole diameter selected after slicing stage 1')
    ap.add_argument('--out',type=Path,default=Path('build/duplo-stud-holes'))
    ap.add_argument('--zip',type=Path)
    args=ap.parse_args()
    generate(args.out,args.stage,args.hole)
    if args.zip:package(args.out,args.zip)
