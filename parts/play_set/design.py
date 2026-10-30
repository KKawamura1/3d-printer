"""Eight version-marked course parts and alternatives on an A1 mini bed."""
from pathlib import Path
import hashlib
import json
import struct
import cadquery as cq
from brickcad.verify import mesh_check, exact_bounds, intersection


def plan():
    return [dict(id='S01-V2',kind='sloped_curve',source='sloped_curve',centre_xy_mm=[-34.,-51.],rotation_deg=0),
            dict(id='S02-V2',kind='sloped_curve',source='S02-V2',centre_xy_mm=[34.,-51.],rotation_deg=0),
            dict(id='E01-V2-A',part_id='E01-V2',kind='elbow',source='elbow',centre_xy_mm=[-34.,17.],rotation_deg=0),
            dict(id='E01-V2-B',part_id='E01-V2',kind='elbow',source='elbow',centre_xy_mm=[34.,17.],rotation_deg=0),
            *[dict(id=label,kind='tunnel',source=source,centre_xy_mm=[x,71.],rotation_deg=0)
              for label,source,x in [('T01-V2','tunnel',-54.),('T02-V1','T02-V1',-18.),
                                      ('T03-V1','T03-V1',18.),('T04-V1','T04-V1',54.)]]]


def export_stl(shape, path):
    # 0.02 mm absolute chordal tolerance; force a fresh tessellation.
    # Omit only facets collapsed by the validator's 1e-5 mm vertex identity.
    # Keep every remaining vertex unchanged; no smoothing or hole filling.
    shape.copy(mesh=False).exportStl(str(path),tolerance=.02,angularTolerance=.4,relative=False)
    raw=path.read_bytes();triangles=[]
    for i in range(struct.unpack_from('<I',raw,80)[0]):
        tri=raw[84+50*i:134+50*i]
        v=struct.unpack('<12fH',tri)[3:12]
        if len({tuple(round(x,5) for x in v[j:j+3]) for j in (0,3,6)})==3:
            triangles.append(tri)
    path.write_bytes(raw[:80]+struct.pack('<I',len(triangles))+b''.join(triangles))
    report=mesh_check(path)
    assert report['passed'],report
    assert abs(report['signed_volume_mm3']-shape.Volume())/shape.Volume()<.001
    return report


def package_existing(root, out, alternatives_root=Path("build/pr20-comparison")):
    root=Path(root);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    records=plan();shapes={};reports={}
    folders={k:root/k for k in ('tunnel','elbow','sloped_curve')}
    folders.update({k:Path(alternatives_root)/k for k in ('S02-V2','T02-V1','T03-V1','T04-V1')})
    for kind,folder in folders.items():
        reports[kind]=json.loads((folder/'report.json').read_text())
        assert reports[kind]['passed'],kind
        shapes[kind]=cq.importers.importStep(str(folder/'brick.step')).val()
        assert shapes[kind].isValid() and len(shapes[kind].Solids())==1
    placed=[]
    for record in records:
        x,y=record['centre_xy_mm']
        placed.append(shapes[record['source']].translate((x,y,0)))
        b=placed[-1].BoundingBox()
        # Includes the physical 180 mm bed boundary and planned 2 mm brim.
        assert min(b.xmin,b.ymin)>=-88 and max(b.xmax,b.ymax)<=88
    for i,a in enumerate(placed):
        for b in placed[i+1:]:
            assert intersection(a,b)<1e-7
    plate=cq.Compound.makeCompound(placed)
    assert plate.isValid() and len(plate.Solids())==8
    mesh=export_stl(plate,out/'play-set-8.stl')
    # Reuse each already-exported triangulation for a lightweight batch viewer.
    # The generic inspector gets the actual eight-solid compound, not stand-ins.
    from brickcad.model import brick_from_fit
    from brickcad.render import viewer
    p=brick_from_fit('duplo-e27-play-v1',nx=12,ny=12,height_units=2)
    report=dict(passed=True,physical_fit_validated=False,slicing_validated=False,
                geometry=dict(bounds_mm=exact_bounds(plate),parameters=dict(clearance=0)),
                fit=dict(insertion=[],poses=[]),specimens=records,mesh=mesh,
                stl_tessellation=dict(linear_tolerance_mm=.02,angular_tolerance_radians=.4),
                translation_to_bed_xy_mm=[90,90],maximum_brim_width_mm=2,
                source_parts={kind:dict(stl_sha256=hashlib.sha256((folders[kind]/'brick.stl').read_bytes()).hexdigest(),
                                        volume_mm3=shapes[kind].Volume()) for kind in shapes},
                limitations=['No slicing, timing estimate, or machine commands.',
                             'Body geometry validated; physical fit/feel and rolling require first-print checks.',
                             'Do not use generic stack mode for this eight-solid plate.'])
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    viewer(plate,p,report,out)
    (out/'brick.stl').write_bytes((out/'play-set-8.stl').read_bytes())
    return report


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parts-root',type=Path,default=Path('build/play-set-v2'))
    parser.add_argument('--out',type=Path,default=Path('build/play-set-v2/batch'))
    parser.add_argument('--alternatives-root',type=Path,default=Path('build/pr20-comparison'))
    args=parser.parse_args()
    package_existing(args.parts_root,args.out,args.alternatives_root)
