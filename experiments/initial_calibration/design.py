"""One-bed 2x2 fit experiment. Compensation is in radial mm, not scale %."""
from dataclasses import replace, asdict
from pathlib import Path
import json
import csv
import hashlib
import cadquery as cq
from brickcad.model import build, nominal_brick
from brickcad.verify import geometry_report, mesh_check, fit_report, exact_bounds
from brickcad.render import viewer

VALUES = (-0.04, 0.0, 0.04, 0.08, 0.12)

def specification(stud_clearance, receiver_clearance, nx=2, ny=2, family="duplo"):
    """Independent male/female settings, usable by the existing build command."""
    b = nominal_brick(family, nx=nx, ny=ny)
    return replace(b, stud_radius=b.stud_radius-stud_clearance,
                   wall=b.wall-receiver_clearance,
                   tube_radius=b.tube_radius-receiver_clearance, clearance=0.0)

def coupon(index, stud_clearance, receiver_clearance, family="duplo", body_height=None):
    p = specification(stud_clearance, receiver_clearance, family=family)
    if body_height is None: body_height = 6.4 if family=='duplo' else p.height
    p = replace(p,height=body_height)
    raw = build(p)
    assert geometry_report(p, raw)['passed']
    # 1..5 shallow vertical tally grooves on the OUTSIDE front wall only.
    # Stop well above the first layers and well below the roof/contact face.
    shape = raw
    for i in range(index):
        x = (i-(index-1)/2)*1.5
        tool = cq.Workplane('XY').box(0.7,0.4,2.0).translate((x,-p.depth/2,p.height/2)).val()
        shape = shape.cut(tool)
    assert shape.isValid() and len(shape.Solids()) == 1
    assert abs(raw.Volume()-shape.Volume()-index*0.7*0.2*2.0)<1e-5
    assert all(abs(a-b)<1e-6 for a,b in zip(exact_bounds(raw),exact_bounds(shape)))
    return p, shape

def generate(out=None, family='duplo', full_height=False):
    if out is None: out = Path('build/sim2real-duplo' if family=='duplo' else 'build/sim2real')
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    base=nominal_brick(family,2,2)
    body_height=base.height if full_height or family=='lego' else 6.4
    spacing = base.width + 4.2
    positions = [(-spacing,-spacing/2),(0,-spacing/2),(spacing,-spacing/2),(-spacing/2,spacing/2),(spacing/2,spacing/2)]
    placed=[]; records=[]
    for index,(c,xy) in enumerate(zip(VALUES,positions),1):
        p, shape = coupon(index,c,c,family=family,body_height=body_height)
        single = out/f'{index}-coupon.stl'
        cq.exporters.export(shape,str(single),tolerance=0.015,angularTolerance=0.12)
        check = mesh_check(single)
        assert check['passed']
        assert abs(check['signed_volume_mm3']-shape.Volume())/shape.Volume()<0.001
        # Intentional interference at negative offsets is data, not a failed export.
        fit = fit_report(p, shape)
        records.append(dict(id=index,stud_clearance_mm=c,receiver_clearance_mm=c,
                            stud_diameter_mm=2*p.stud_radius,wall_mm=p.wall,
                            tube_outer_diameter_mm=2*p.tube_radius,
                            position_xy_mm=xy,parameters=asdict(p),
                            volume_mm3=shape.Volume(),mesh=check,fit=fit))
        placed.append(shape.translate((*xy,0)))
    compound=cq.Compound.makeCompound(placed)
    assert compound.isValid() and len(compound.Solids())==5
    for i,a in enumerate(placed):
        for b in placed[i+1:]:
            assert a.intersect(b).Volume()<1e-6
    cq.exporters.export(compound,str(out/'plate.stl'),tolerance=0.015,angularTolerance=0.12)
    cq.exporters.export(compound,str(out/'plate.step'))
    assert mesh_check(out/'plate.stl')['passed']
    restored=cq.importers.importStep(str(out/'plate.step')).val()
    assert len(restored.Solids())==5 and abs(restored.Volume()-compound.Volume())<1e-5
    # Text STL also allows storage through GitHub's text-only connector.
    cq.exporters.export(compound,str(out/'plate-ascii.stl'),tolerance=0.025,angularTolerance=0.16,opt={'ascii':True})
    report=dict(schema_version=1,family=family,body_height_mm=body_height,full_height=full_height,physical_fit_validated=False,passed=True,
                layout='Five disconnected coupons, no common base, studs up. Keep at 100% scale.',
                bounds_mm=exact_bounds(compound),volume_mm3=compound.Volume(),
                mass_at_1p24_g_cm3=compound.Volume()*1.24/1000,
                variants=records,
                files={n:hashlib.sha256((out/n).read_bytes()).hexdigest() for n in ('plate.stl','plate.step','plate-ascii.stl')})
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    with (out/'measurements.csv').open('w') as f:
        w=csv.writer(f); w.writerow(['id','stud_clearance_mm','receiver_clearance_mm','genuine_on_printed','printed_on_genuine','stud_diameter_x_mm','stud_diameter_y_mm','body_x_mm','body_y_mm','notes'])
        for r in records:w.writerow([r['id'],r['stud_clearance_mm'],r['receiver_clearance_mm']]+['']*7)
    (out/'setup.json').write_text(json.dumps(dict(family=family,printer=None,nozzle_mm=None,material=None,layer_height_mm=None,slicer=None,settings={},reference_part=None,selected_stud_id=None,selected_receiver_id=None),indent=2)+'\n')
    # Reuse the real WebGL viewer for each coupon; fit poses remain meaningful.
    for r in records:
        p,shape=coupon(r['id'],r['stud_clearance_mm'],r['receiver_clearance_mm'],family=family,body_height=body_height)
        folder=out/f"view-{r['id']}"; folder.mkdir(exist_ok=True)
        single_report=dict(passed=True,physical_fit_validated=False,fit=r['fit'], geometry=dict(bounds_mm=exact_bounds(shape), parameters=asdict(p)))
        viewer(shape,p,single_report,folder)
        html=(folder/'viewer.html').read_text().replace('<a href="preview.png">断面・4方向画像</a> · ','')
        (folder/'viewer.html').write_text(html)
        (folder/'brick.stl').write_bytes((out/f"{r['id']}-coupon.stl").read_bytes())
        (folder/'report.json').write_text(json.dumps(single_report))
    plate_report=dict(passed=True,physical_fit_validated=False,fit=dict(poses=[],insertion=[]),geometry=dict(bounds_mm=exact_bounds(compound),parameters=dict(clearance='independent; see report.json')))
    viewer(compound,replace(nominal_brick(family,nx=8,ny=6),height=body_height),plate_report,out)
    html=(out/'viewer.html').read_text().replace('<option value="stack">上下の組み合わせ</option>','').replace('<a href="preview.png">断面・4方向画像</a> · ','')
    html=html.replace('</style>', 'label:has(#pose),label:has(#lift){display:none}</style>')
    html=html.replace('干渉値は選択した姿勢・追加高さ0mmのBRep計算結果です。スライダー移動中の再計算は行いません。摩擦力・印刷収縮・変形のシミュレーションは含みません。', '5 separate coupons. Count side grooves for IDs 1-5. Test studs and underside separately against genuine DUPLO. Print at 100% scale.')
    (out/'viewer.html').write_text(html.replace('<h1>', '<h1>Sim2Real 2x2 / 5 coupons — '))
    print(json.dumps({k:report[k] for k in ('bounds_mm','volume_mm3','mass_at_1p24_g_cm3','passed')}))
    return report

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description='2x2 physical fit calibration; default DUPLO')
    parser.add_argument('out',nargs='?',type=Path,default=None)
    parser.add_argument('--family',choices=['duplo','lego'],default='duplo')
    parser.add_argument('--full-height',action='store_true',help='Use regular body height instead of the compact DUPLO test height')
    args=parser.parse_args()
    generate(args.out,family=args.family,full_height=args.full_height)
