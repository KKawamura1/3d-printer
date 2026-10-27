"""Measured horizontal ball track and rounded fit trial; millimetres, Z up."""
from dataclasses import asdict, dataclass, replace
import hashlib
import json
import math
import struct
from pathlib import Path
import cadquery as cq
from brickcad.model import brick_from_fit, nominal_brick, receiver, build
from brickcad.standards import BALL_TRACK, ROUNDED_EDGES
from brickcad.provenance import design_manifest
from brickcad.verify import exact_bounds, intersection, mesh_check, place, VOLUME_TOL
from brickcad.render import mesh, outlines, viewer


@dataclass(frozen=True)
class Rail:
    length: float = 63.8
    width: float = BALL_TRACK.width
    height: float = BALL_TRACK.height
    opening: float = BALL_TRACK.opening
    floor: float = BALL_TRACK.floor
    outer_radius: float = 0.8
    lip_radius: float = 0.5
    end_chamfer: float = 0.15
    entry: float = 0.3
    roof: float = 1.6

    def __post_init__(self):
        if any(not math.isfinite(v) or v <= 0 for v in asdict(self).values()):
            raise ValueError('Rail dimensions must be finite and positive')
        if not self.roof+4.5 <= self.floor < self.height:
            raise ValueError('Insufficient insertion depth or floor thickness')
        if not 0 < self.opening < self.width-2*self.outer_radius:
            raise ValueError('Opening leaves insufficient side walls')
        if self.height-self.floor > self.opening/2:
            raise ValueError('Profile must not overhang the opening')
        if self.length != 63.8 or self.width != 31.65:
            raise ValueError('This first trial supports the measured 2x4 footprint only')

    @property
    def radius(self):
        d = self.height-self.floor
        return ((self.opening/2)**2+d*d)/(2*d)


def fit_profile(nx=2):
    # Compatibility entry point; new parts import the version from model directly.
    return brick_from_fit('duplo-rail-trial-v1', nx=nx, ny=2)


def rounded_brick(p):
    return build(p, corner_radius=ROUNDED_EDGES.corner_radius,
                 stud_lip_radius=ROUNDED_EDGES.stud_lip_radius,
                 entry=ROUNDED_EDGES.receiver_entry)


def build_rail(r=Rail()):
    p = brick_from_fit('duplo-straight-rail-trial-v1', nx=4, ny=2,
                       body_offset_xy=(0., r.width-31.8), height=r.height)
    # X uses a separate measured length: pitch positions remain exactly 16 mm.
    outer = cq.Workplane('XY').box(r.length,r.width,r.height,centered=(True,True,False))
    outer = outer.edges('|Z').fillet(r.outer_radius).edges('>Z').fillet(r.outer_radius)
    result = receiver(p,outer,r.floor-r.roof,r.entry,(r.length,r.width))
    groove = cq.Solid.makeCylinder(r.radius,r.length+2,
                cq.Vector(-r.length/2-1,0,r.floor+r.radius),cq.Vector(1,0,0))
    result = result.cut(groove)
    # Long internal lips are rounded. End arcs get a small lead-in, preserving
    # z=floor in the interior and at most 0.15 mm removal at the join.
    lips = [e for e in result.val().Edges() if e.geomType()=='LINE'
            and e.Length()>r.length-2*r.outer_radius-1
            and abs(abs(e.Center().y)-r.opening/2)<.01]
    if len(lips)!=2:
        raise ValueError('Expected two long track lips')
    result = result.newObject(lips).fillet(r.lip_radius)
    for x,ra,rb in [(-r.length/2,r.radius+r.end_chamfer,r.radius),
                    (r.length/2-r.end_chamfer,r.radius,r.radius+r.end_chamfer)]:
        lead=cq.Solid.makeCone(ra,rb,r.end_chamfer,
                cq.Vector(x,0,r.floor+r.radius),cq.Vector(1,0,0))
        result=result.cut(lead)
    shape=result.val().clean()
    if not shape.isValid() or len(shape.Solids())!=1:
        raise ValueError('Rail must be one valid solid')
    return shape,p


def export(kind='rail', out=Path('build/duplo-rail-trial-01')):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    r=Rail();p=fit_profile()
    if kind=='rail': shape,p=build_rail(r)
    else: shape=rounded_brick(p)
    cq.exporters.export(shape,str(out/'brick.stl'),tolerance=.01,angularTolerance=.1)
    # OCC sphere-corner poles can emit triangles whose float32 vertices coincide.
    # Drop only exactly collapsed triangles; no smoothing or mesh repair.
    stl=out/'brick.stl';raw=stl.read_bytes();triangles=[];collapsed=0
    for i in range(struct.unpack_from('<I',raw,80)[0]):
        tri=raw[84+50*i:134+50*i];v=struct.unpack('<12fH',tri)[3:12]
        if len({tuple(v[j:j+3]) for j in (0,3,6)})<3:collapsed+=1
        else:triangles.append(tri)
    stl.write_bytes(raw[:80]+struct.pack('<I',len(triangles))+b''.join(triangles))
    cq.exporters.export(shape,str(out/'brick.step'))
    restored=cq.importers.importStep(str(out/'brick.step')).val()
    step=restored.isValid() and len(restored.Solids())==1 and abs(shape.Volume()-restored.Volume())<1e-4
    m=mesh_check(out/'brick.stl')
    bounds=exact_bounds(shape)
    expected=[r.length,r.width,r.height] if kind=='rail' else [p.width,p.depth,p.height+p.stud_height]
    refp=nominal_brick('duplo',p.nx,p.ny)
    from brickcad.model import build
    ref=build(refp)
    insertion=[]
    for lift in (5.7,4.5,3.,1.5,0.):
        v=intersection(ref,place(shape,(0,0,refp.height+lift)))
        insertion.append(dict(pair='reference/printed',lift_mm=lift,intersection_mm3=v,collision=v>VOLUME_TOL))
    if kind=='brick':
        for lift in (5.7,4.5,3.,1.5,0.):
            v=intersection(shape,place(ref,(0,0,p.height+lift)))
            insertion.append(dict(pair='printed/reference',lift_mm=lift,intersection_mm3=v,collision=v>VOLUME_TOL))
    poses=[]
    for name,x,y,z,a in [('one_stud_offset',16,0,19.2,0),('cross_90',0,0,19.2,90),
                         ('half_pitch_negative_control',8,0,19.2,0),('overinsert_negative_control',0,0,18.9,0)]:
        v=intersection(ref,place(shape,(x,y,z),a))
        poses.append(dict(name=name,xyz_mm=[x,y,z],rotation_deg=a,intersection_mm3=v,collision=v>VOLUME_TOL))
    checks=dict(valid_brep=shape.isValid(),one_solid=len(shape.Solids())==1,
        dimensions=all(abs(a-b)<1e-6 for a,b in zip(bounds,expected)),step_roundtrip=step,
        mesh=m['passed'],mesh_volume=abs(m['signed_volume_mm3']-shape.Volume())/shape.Volume()<.001,
        open_bottom=not shape.isInside(cq.Vector(4,0,.5)),
        negative_controls=all(x['collision'] for x in poses if 'negative_control' in x['name']))
    ball=[]
    if kind=='rail':
        checks['floor_present']=shape.isInside(cq.Vector(0,0,r.floor-.1))
        checks['channel_open']=not shape.isInside(cq.Vector(0,0,r.floor+.1))
        checks['tube_holes']=all(not shape.isInside(cq.Vector(x,y,1)) for x,y in p.tubes())
        checks['tube_walls']=all(shape.isInside(cq.Vector(x+5.5,y,1)) for x,y in p.tubes())
        for x in [-r.length/2+i*r.length/12 for i in range(13)]:
            sphere=cq.Solid.makeSphere(BALL_TRACK.ball_diameter/2,cq.Vector(x,0,r.floor+BALL_TRACK.ball_diameter/2+.05),angleDegrees1=-90)
            v=intersection(shape,sphere);ball.append(dict(x_mm=x,intersection_mm3=v))
        checks['sampled_ball_path_clear']=all(x['intersection_mm3']<VOLUME_TOL for x in ball)
    # Tube 13.30 intentionally grips nominal 9.40 studs by ~0.036 mm radially.
    # This is a physical trial, so rigid collisions are reported, never hidden.
    gap=math.sqrt(2)*8-p.tube_radius-4.7
    checks['fit_within_trial_envelope']=gap>=-.05 and insertion[0]['intersection_mm3']<VOLUME_TOL
    report=dict(schema_version=1,kind=kind,passed=all(checks.values()),
        design=design_manifest(p, channel=r if kind=='rail' else None,
                               channel_standard=BALL_TRACK if kind=='rail' else None,
                               finish=ROUNDED_EDGES if kind=='brick' else None),
        geometry=dict(bounds_mm=bounds,volume_mm3=shape.Volume(),parameters=asdict(p),checks=checks),
        rail=asdict(r) if kind=='rail' else None,groove_radius_mm=r.radius if kind=='rail' else None,
        mesh=m,collapsed_stl_triangles_removed=collapsed,step_roundtrip_passed=step,physical_fit_validated=False,
        fit_geometrically_clear=not any(x['collision'] for x in insertion),
        intentional_fit_trial=True,nominal_tube_gap_mm=gap,
        fit=dict(reference='synthetic DUPLO nominal; no OEM measurement',insertion=insertion,poses=poses),
        ball_path=ball,limitations=['Rigid interference retained; PASS covers geometry and trial envelope, not free fit or clutch force.',
        'Ball diameter is approximate; 13 static samples at floor + radius + 0.05 mm, not dynamics.',
        'Horizontal track requires incoming momentum; joints and rolling remain untested.'],
        files={n:hashlib.sha256((out/n).read_bytes()).hexdigest() for n in ('brick.stl','brick.step')})
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    (out/'parameters.json').write_text(json.dumps(dict(brick=asdict(p),rail=asdict(r) if kind=='rail' else None),indent=2)+'\n')
    # Reuse the inspected viewer, with a genuine lower reference brick in assembly.
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    cut=shape.cut(cq.Workplane('XY').box(p.width+2,p.depth+2,50,centered=(True,False,False)).val())
    fig=plt.figure(figsize=(12,8),facecolor='#f5f7fa')
    for i,(title,items,elev,azim) in enumerate([
        ('Track / rounded edges' if kind=='rail' else 'Rounded 2x2',[(shape,'#dc493c')],28,-55),
        ('Underside / shared receiver',[(shape,'#dc493c')],-35,-55),
        ('CAD section',[(cut,'#dc493c')],12,0),
        ('Synthetic reference + trial',[(ref,'#dc493c'),(shape.translate((0,0,19.2)),'#2783b5')],22,-50)],1):
        ax=fig.add_subplot(2,2,i,projection='3d')
        for item,color in items:
            v,f=mesh(item)
            ax.add_collection3d(Poly3DCollection([[v[k] for k in face] for face in f],facecolors=color,linewidths=0,shade=True))
        ax.set(xlim=(-p.width/2-2,p.width/2+2),ylim=(-p.depth/2-2,p.depth/2+2),zlim=(0,45 if i==4 else 25))
        ax.set_box_aspect((p.width,p.depth,45 if i==4 else 25));ax.view_init(elev,azim);ax.set_title(title)
    fig.suptitle('DUPLO horizontal rail trial 01' if kind=='rail' else 'DUPLO rounded fit trial 02')
    fig.tight_layout();fig.savefig(out/'preview.png',dpi=140);plt.close(fig)
    viewer(shape,p,report,out)
    html=(out/'viewer.html').read_text()
    verts,faces=mesh(ref)
    payload=json.dumps(dict(vertices=verts,faces=faces,edges=outlines(ref)),separators=(',',':'))
    html=html.replace('const canvas=',f'data.lower={payload}; data.height=19.2;\nconst canvas=')
    html=html.replace("const source=mode.value==='section'?data.section:data;", "const source=mode.value==='section'?data.section:data;")
    html=html.replace("const vv=source.vertices", "const src=mode.value==='stack'&&obj===scene[0]?data.lower:source;const vv=src.vertices")
    html=html.replace('for(const f of source.faces)', 'for(const f of src.faces)')
    html=html.replace('for(const segment of source.edges)', "for(const segment of (mode.value==='stack'&&obj===scene[0]?data.lower:source).edges)")
    html=html.replace("x.pair==='printed/printed'&&x.lift_mm===0", "x.lift_mm===0")
    html=html.replace('CAD・STL検証:', 'CAD・STL検証 (fit trial):')
    (out/'viewer.html').write_text(html)
    print(kind, 'PASS' if report['passed'] else 'FAIL', bounds, 'rigid tube gap', gap, flush=True)
    if not report['passed']:raise RuntimeError(checks)
    return report


if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--kind',choices=['rail','brick'],default='rail');ap.add_argument('--out',type=Path,default=Path('build/duplo-rail-trial-01'))
    args=ap.parse_args();export(args.kind,args.out)

