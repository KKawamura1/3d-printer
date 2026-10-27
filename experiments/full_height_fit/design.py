"""Issue #1: full-height, independently varied 16-coupon DUPLO experiment."""
from dataclasses import asdict, replace
from pathlib import Path
import csv
import hashlib
import json
import struct
import zipfile
import cadquery as cq
from brickcad.model import nominal_brick
from parts.straight_rail.design import rounded_brick
from brickcad.render import viewer
from brickcad.verify import exact_bounds, mesh_check, fit_report

LAYOUT = (('C','S20','C','T30'), ('W16','C','S32','C'),
          ('C','S36','C','W24'), ('T50','C','S48','C'))  # back (+Y) to front
VARIANTS = {'C': (9.40,13.10,3.20), 'S20': (9.20,13.10,3.20),
 'S32': (9.32,13.10,3.20), 'S36': (9.36,13.10,3.20),
 'S48': (9.48,13.10,3.20), 'T30': (9.40,13.30,3.20),
 'T50': (9.40,13.50,3.20), 'W16': (9.40,13.10,3.16),
 'W24': (9.40,13.10,3.24)}
DIGITS = ('abcedf','bc','abged','abgcd','fgbc','afgcd','afgecd','abc','abcdefg','abfgcd')


def plan():
    records=[]; controls=0
    for row, names in enumerate(LAYOUT):
        for col,name in enumerate(names):
            angle=0
            if name=='C':
                angle=(controls % 2)*90; controls+=1
            s,t,w=VARIANTS[name]
            records.append(dict(id=f'{len(records)+1:02}',variant=name,row_from_back=row+1,
                column_from_left=col+1,bed_center_xy_mm=[27+42*col,153-42*row],
                rotation_deg=angle,stud_diameter_mm=s,tube_diameter_mm=t,wall_mm=w,
                local_x_in_bed='+X' if angle==0 else '+Y',
                local_y_in_bed='+Y' if angle==0 else '-X'))
    return records


def coupon(record):
    p=replace(nominal_brick('duplo',2,2),stud_radius=record['stud_diameter_mm']/2,
              tube_radius=record['tube_diameter_mm']/2,wall=record['wall_mm'],
              stud_inner_radius=record.get('stud_hole_diameter_mm',6.50)/2)
    raw=rounded_brick(p); tools=[]
    # Seven-segment ID recessed 0.25 mm into -Y exterior, z=9..14.
    # All marks lie above the bottom 4.5 mm mating zone and below the top rim.
    segments={'a':(0,2.4,2.8,.6),'g':(0,0,2.8,.6),'d':(0,-2.4,2.8,.6),
              'f':(-1.1,1.2,.6,2.4),'b':(1.1,1.2,.6,2.4),
              'e':(-1.1,-1.2,.6,2.4),'c':(1.1,-1.2,.6,2.4)}
    for pos,digit in enumerate(record['id']):
        for seg in DIGITS[int(digit)]:
            x,z,w,h=segments[seg]
            tools.append(cq.Workplane('XY').box(w,.5,h).translate((x+(pos-.5)*4,-p.depth/2,11.5+z)).val())
    # Local +X: arrow on -Y face. Local +Y: arrow on +X face.
    arrow=[(-3,-.3),(1.5,-.3),(1.5,-1),(3,0),(1.5,1),(1.5,.3),(-3,.3)]
    tools.append(cq.Workplane('XZ',origin=(0,-p.depth/2+.25,16)).polyline(arrow).close().extrude(.5).val())
    tools.append(cq.Workplane('YZ',origin=(p.width/2-.25,0,16)).polyline(arrow).close().extrude(.5).val())
    shape=raw
    for tool in tools:
        shape=shape.cut(tool).clean()
    assert shape.isValid() and len(shape.Solids())==1
    assert all(abs(a-b)<1e-6 for a,b in zip(exact_bounds(shape),[31.8,31.8,23.7]))
    # Exact proof that engraving leaves the insertion/contact band unchanged.
    contact=cq.Workplane('XY').box(40,40,5,centered=(True,True,False)).val()
    assert raw.cut(shape).intersect(contact).Volume()<1e-7
    return p,shape


def export_stl(shape,path):
    shape.exportStl(str(path),tolerance=.03,angularTolerance=.2,relative=False)
    data=path.read_bytes(); tris=[]; removed=0
    for i in range(struct.unpack_from('<I',data,80)[0]):
        tri=data[84+50*i:134+50*i]; v=struct.unpack('<12fH',tri)[3:12]
        if len({tuple(v[j:j+3]) for j in (0,3,6)})==3: tris.append(tri)
        else: removed+=1
    path.write_bytes(data[:80]+struct.pack('<I',len(tris))+b''.join(tris))
    check=mesh_check(path)
    assert check['passed'],check
    assert abs(check['signed_volume_mm3']-shape.Volume())/shape.Volume()<.001
    return dict(mesh=check,collapsed_triangles_removed=removed)


def check_3mf(path):
    """Read the serialized package back, validate its mesh and bed transform."""
    import tempfile
    import xml.etree.ElementTree as ET
    ns={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
    with zipfile.ZipFile(path) as z:
        root=ET.fromstring(z.read('3D/3dmodel.model'))
    assert root.attrib['unit']=='millimeter'
    items=root.findall('m:build/m:item',ns)
    assert len(items)==1 and items[0].attrib['transform']=='1 0 0 0 1 0 0 0 1 90 90 0'
    verts=[tuple(float(v.attrib[k]) for k in ('x','y','z')) for v in root.findall('.//m:vertex',ns)]
    faces=[tuple(int(t.attrib[k]) for k in ('v1','v2','v3')) for t in root.findall('.//m:triangle',ns)]
    # Every triangle must remain wholly inside one planned coupon footprint.
    occupied=set()
    centers=[(r['bed_center_xy_mm'][0]-90,r['bed_center_xy_mm'][1]-90) for r in plan()]
    for face in faces:
        points=[verts[i] for i in face]
        cx=sum(v[0] for v in points)/3; cy=sum(v[1] for v in points)/3
        n=min(range(16),key=lambda i:(centers[i][0]-cx)**2+(centers[i][1]-cy)**2)
        assert all(abs(x-centers[n][0])<=15.90001 and abs(y-centers[n][1])<=15.90001 for x,y,z in points)
        occupied.add(n)
    assert len(occupied)==16
    with tempfile.TemporaryDirectory() as folder:
        target=Path(folder)/'roundtrip.stl'
        with target.open('wb') as f:
            f.write(bytes(80)+struct.pack('<I',len(faces)))
            for face in faces:
                f.write(struct.pack('<12fH',0,0,0,*(c for i in face for c in verts[i]),0))
        check=mesh_check(target)
    assert check['passed'],check
    return dict(passed=True,bed_transform_verified=True,occupied_coupons=16,mesh=check)


def generate(out=Path('build/duplo-experiment-01')):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    records=plan(); placed=[]
    for r in records:
        print('Generating',r['id'],r['variant'],flush=True)
        p,s=coupon(r);name=f"{r['id']}-{r['variant']}.stl"
        r.update(parameters=asdict(p),volume_mm3=s.Volume(),file=name,**export_stl(s,out/name))
        x,y=r['bed_center_xy_mm']
        placed.append(s.rotate((0,0,0),(0,0,1),r['rotation_deg']).translate((x-90,y-90,0)))
        if r['id']=='01':
            sample=out/'sample';sample.mkdir(exist_ok=True)
            report=dict(passed=True,physical_fit_validated=False,geometry=dict(parameters=asdict(p),bounds_mm=exact_bounds(s)),fit=fit_report(p,s))
            viewer(s,p,report,sample)
            (sample/'brick.stl').write_bytes((out/name).read_bytes())
            (sample/'report.json').write_text(json.dumps(report))
    plate=cq.Compound.makeCompound(placed)
    assert plate.isValid() and len(plate.Solids())==16
    assert all(abs(a-b)<1e-6 for a,b in zip(exact_bounds(plate),[157.8,157.8,23.7]))
    for i,a in enumerate(placed):
        for b in placed[i+1:]: assert a.intersect(b).Volume()<1e-7
    plate_mesh=export_stl(plate,out/'plate.stl')
    cq.exporters.export(plate,str(out/'plate.step'))
    restored=cq.importers.importStep(str(out/'plate.step')).val()
    assert restored.isValid() and len(restored.Solids())==16
    assert abs(restored.Volume()-plate.Volume())<1e-4
    # Standard model-only 3MF: one build item preserves relative positions.
    # It deliberately carries no Bambu print settings or G-code.
    import xml.etree.ElementTree as ET
    ns='http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
    ET.register_namespace('',ns)
    model=ET.Element('model',unit='millimeter',xmlns=ns)
    resources=ET.SubElement(model,'resources');obj=ET.SubElement(resources,'object',id='1',type='model')
    mesh=ET.SubElement(obj,'mesh');vertices=ET.SubElement(mesh,'vertices');triangles=ET.SubElement(mesh,'triangles')
    verts,faces=plate.tessellate(.015,.12)
    for v in verts: ET.SubElement(vertices,'vertex',x=str(v.x),y=str(v.y),z=str(v.z))
    for a,b,c in faces:
        if (verts[b]-verts[a]).cross(verts[c]-verts[a]).Length>1e-12:
            ET.SubElement(triangles,'triangle',v1=str(a),v2=str(b),v3=str(c))
    build=ET.SubElement(model,'build');ET.SubElement(build,'item',objectid='1',transform='1 0 0 0 1 0 0 0 1 90 90 0')
    with zipfile.ZipFile(out/'plate.3mf','w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('3D/3dmodel.model',ET.tostring(model,encoding='utf-8',xml_declaration=True))
        z.writestr('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
        z.writestr('_rels/.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    package_check=check_3mf(out/'plate.3mf')
    assert abs(package_check['mesh']['signed_volume_mm3']-plate.Volume())/plate.Volume()<.001
    with (out/'measurements.csv').open('w') as f:
        w=csv.writer(f);w.writerow(['id','variant','feature','local_axis','location','repeat','value_mm','approximate','notes'])
        for r in records:
            for feature,locations in [('stud_diameter',['-X-Y','-X+Y','+X-Y','+X+Y']),('body',['center']),('inner_wall_span',['center']),('tube_outer_diameter',['center'])]:
                for loc in locations:
                    for axis in ('X','Y'):
                        for repeat in (1,2,3):w.writerow([r['id'],r['variant'],feature,axis,loc,repeat,'','',''])
    setup=dict(actual_print_performed=False,source_issue=1,printer='Bambu Lab A1 mini',nozzle_mm=.4,
      material='Bambu PLA Basic',slicer_version_expected='2.8.02.61',actual_slicer_version=None,
      expected_settings=dict(layer_height=.2,wall_loops=2,outer_wall_line_width=.42,inner_wall_line_width=.45,
      outer_wall_speed=200,wall_generator='classic',sparse_infill_pattern='grid',sparse_infill_density='15%',
      filament_flow_ratio=.98,xy_contour_compensation=0,xy_hole_compensation=0,elefant_foot_compensation=0,
      seam_position='aligned',apply_scarf_seam_on_circles=1,enable_circle_compensation=0,
      print_sequence='by layer',enable_support=0,brim_type='auto_brim',brim_width=5),
      actual_settings={},reference_part=None,gcode_sha256=None,project_3mf_sha256=None,
      actual_centers_and_rotations_verified=False,fit_results=[dict(id=r['id'],genuine_on_printed=None,printed_on_genuine=None,notes=None) for r in records])
    (out/'setup.json').write_text(json.dumps(setup,indent=2)+'\n')
    report=dict(schema_version=1,passed=True,physical_fit_validated=False,bounds_mm=exact_bounds(plate),
      bed_size_mm=[180,180],bed_center_mm=[90,90],spacing_mm=42,brim_envelope_mm=[167.8,167.8],
      minimum_brim_to_bed_edge_mm=6.1,minimum_between_5mm_brims_mm=.2,
      step_roundtrip_passed=True,model_3mf_roundtrip=package_check,plate_mesh=plate_mesh,variants=records,
      solid_volume_mm3=plate.Volume(),solid_mass_at_1p24_g_cm3=plate.Volume()*1.24/1000,
      limitations=['Mass is solid CAD volume, not sliced consumption.',
      'Single treatment replicates remain confounded with position; controls estimate combined within-job variation.',
      'No coupon lies at bed X=90; old central-position hypothesis is not directly tested.',
      'No slicing, printable/exclusion-area or actual clutch-force validation has been performed.'])
    report['files']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file() and p.name!='report.json'}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    # Plate viewer coordinates remain centered for the existing orbit controls.
    viewer(plate,replace(nominal_brick('duplo',10,10),height=19.2),
           dict(passed=True,physical_fit_validated=False,geometry=dict(bounds_mm=exact_bounds(plate),parameters={'clearance':'independent; see report.json'}),fit=dict(poses=[],insertion=[])),out)
    html=(out/'viewer.html').read_text().replace('<option value="stack">上下の組み合わせ</option>','')
    (out/'viewer.html').write_text(html)
    print('PASS',report['bounds_mm'],flush=True)
    return report

def package(out, destination):
    """Ship generated models and measurement forms, without browser intermediates."""
    destination=Path(destination);destination.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(destination.with_name(destination.stem+'_plate_stl.zip'),'w',zipfile.ZIP_DEFLATED) as archive:
        archive.write(Path(out)/'plate.stl','plate.stl')
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(Path(out).iterdir()):
            if path.is_file() and path.name!='plate.stl' and path.suffix in ('.stl','.step','.3mf','.json','.csv'):
                archive.write(path,path.name)
        archive.write(Path(__file__).with_name('README.md'),'README.md')


if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,default=Path('build/duplo-experiment-01'))
    ap.add_argument('--zip',type=Path,help='Also package printable models and measurement forms')
    args=ap.parse_args();generate(args.out)
    if args.zip: package(args.out,args.zip)
