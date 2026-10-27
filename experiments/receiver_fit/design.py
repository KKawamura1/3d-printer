"""Three independent underside trials, preserving the successful 14-coupon top."""
from dataclasses import asdict
from pathlib import Path
import csv
import hashlib
import json
import zipfile
import cadquery as cq
from experiments.full_height_fit.design import coupon, export_stl
from brickcad.model import nominal_brick, receiver
from parts.straight_rail.design import rounded_brick
from brickcad.render import viewer
from brickcad.verify import exact_bounds, fit_report


def plan():
    return [
        dict(id='01', condition='A-baseline', cavity_y_mm=25.40, tube_diameter_mm=13.10),
        dict(id='02', condition='B-Y-wall', cavity_y_mm=25.34, tube_diameter_mm=13.10),
        dict(id='03', condition='C-tube', cavity_y_mm=25.40, tube_diameter_mm=13.50),
    ]


def build(record):
    # Reuse the same engraving and arrows as the 14-coupon job.
    p, marked = coupon(dict(record, stud_diameter_mm=9.40,
                           stud_hole_diameter_mm=6.40, wall_mm=3.20))
    raw = rounded_brick(p)
    outer = cq.Workplane('XY').box(p.width, p.depth, p.height, centered=(True,True,False))
    outer = outer.edges('|Z').fillet(.8).edges('>Z').fillet(.8)
    # footprint here controls only the cavity; the exterior is fixed at 31.8 square.
    body = receiver(p, outer, p.height-p.roof, .3,
                    (p.width, record['cavity_y_mm']+2*p.wall))
    studs = (cq.Workplane('XY',origin=(0,0,p.height)).pushPoints(p.studs())
             .circle(p.stud_radius).circle(p.stud_inner_radius).extrude(p.stud_height))
    studs = studs.edges('>Z').fillet(.5)
    shape = body.union(studs).val().cut(raw.cut(marked)).clean()
    assert shape.isValid() and len(shape.Solids()) == 1
    assert all(abs(a-b)<1e-6 for a,b in zip(exact_bounds(shape),[31.8,31.8,23.7]))
    return p, shape


def generate(out):
    out=Path(out)
    if out.exists() and any(out.iterdir()):
        raise ValueError('Use an empty output directory')
    out.mkdir(parents=True,exist_ok=True)
    records=plan(); placed=[]
    for index,r in enumerate(records):
        print('Generating',r['condition'],flush=True)
        p,s=build(r)
        folder=out/r['id'];folder.mkdir()
        mesh=export_stl(s,folder/'brick.stl')
        cq.exporters.export(s,str(folder/'brick.step'))
        restored=cq.importers.importStep(str(folder/'brick.step')).val()
        assert restored.isValid() and len(restored.Solids())==1
        assert abs(restored.Volume()-s.Volume())<1e-4
        # fit_report's wall-gap shorthand assumes an isotropic cavity.
        fit=fit_report(p,s)
        fit.pop('self_wall_gap_mm')
        fit['self_wall_gap_xy_mm']=[0.,(r['cavity_y_mm']-25.40)/2]
        report=dict(passed=True,physical_fit_validated=False,slicing_validated=False,
                    geometry=dict(parameters=asdict(p),bounds_mm=exact_bounds(s)),
                    cavity_xy_mm=[25.40,r['cavity_y_mm']],fit=fit,
                    step_roundtrip_passed=True,**mesh)
        viewer(s,p,report,folder)
        (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        r.update(file=r["id"]+'/brick.stl',rotation_deg=0,
                 bed_center_xy_mm=[48+42*index,90],report=report)
        placed.append(s.translate((-42+42*index,0,0)))
    plate=cq.Compound.makeCompound(placed)
    assert plate.isValid() and len(plate.Solids())==3
    for i,a in enumerate(placed):
        for b in placed[i+1:]:assert a.intersect(b).Volume()<1e-7
    mesh=export_stl(plate,out/'plate.stl')
    cq.exporters.export(plate,str(out/'plate.step'))
    restored=cq.importers.importStep(str(out/'plate.step')).val()
    assert restored.isValid() and len(restored.Solids())==3
    assert abs(restored.Volume()-plate.Volume())<1e-4
    report=dict(passed=True,physical_fit_validated=False,slicing_validated=False,
                variants=records,bounds_mm=exact_bounds(plate),plate_mesh=mesh,
                step_roundtrip_passed=True,bed_size_mm=[180,180],
                source_issue='https://github.com/KKawamura1/3d-printer/issues/1',
                limitations=['Rigid intersections are disclosed, not a clutch-force prediction.',
                             'One coupon per condition; position and process variation are not isolated.',
                             'No final slicing or physical validation has occurred.'])
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    with (out/'measurements.csv').open('w',newline='') as f:
        writer=csv.writer(f)
        writer.writerow(['id','condition','inner_x_mm','inner_y_mm','tube_od_mm',
                         'genuine_into_underside_seating','bend_X','bend_Y','removal',
                         'printed_10_into_underside','printed_13_into_underside',
                         'after_10_cycles','stud_inner_wall_4of4','notes'])
        for r in records:writer.writerow([r['id'],r['condition']]+['']*12)
    setup=dict(actual_print_performed=False,physical_fit_validated=False,
               printer='Bambu Lab A1 mini',nozzle_mm=.4,material='Bambu PLA Basic',
               required_rotation_deg=0,scale_percent=100,
               expected_settings=dict(layer_height_mm=.20,wall_loops=2,wall_generator='Classic',
                 outer_wall_line_width_mm=.42,inner_wall_line_width_mm=.45,
                 sparse_infill_percent=15,sparse_infill_pattern='Grid',filament_flow_ratio=.98,
                 xy_contour_compensation_mm=0,xy_hole_compensation_mm=0,print_sequence='by layer'),
               actual_settings={},project_3mf_sha256=None,gcode_sha256=None)
    (out/'setup.json').write_text(json.dumps(setup,indent=2)+'\n')
    files={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest()
           for p in out.rglob('*') if p.is_file()}
    (out/'sha256.json').write_text(json.dumps(files,indent=2)+'\n')
    return report


def package(out,destination):
    destination=Path(destination);destination.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as archive:
        for p in sorted(Path(out).rglob('*')):
            if p.is_file():archive.write(p,p.relative_to(out))
        archive.write(Path(__file__).with_name('README.md'),'README.md')


if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,default=Path('build/duplo-receiver-trial-01'))
    ap.add_argument('--zip',type=Path)
    args=ap.parse_args()
    generate(args.out)
    if args.zip:package(args.out,args.zip)
