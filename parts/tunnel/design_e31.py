"""Two-course DUPLO tunnel: T04-style circular mouths and E31-05 receiving fit."""
from dataclasses import dataclass, asdict, replace
from pathlib import Path
import hashlib
import json
import math
import struct
import cadquery as cq
from brickcad.model import receiver, nominal_brick, build, brick_from_fit
from parts.straight_rail.design import Rail
from brickcad.standards import BALL_TRACK, ROUNDED_EDGES
from brickcad.connections import make_studs
from parts.tunnel.e31_fit import add_e31_05_receiver_features
from brickcad.provenance import design_manifest
from brickcad.marking import engrave

PART_ID = "T01-V4"
from brickcad.render import viewer, mesh, outlines, preview
from brickcad.verify import intersection, exact_bounds, mesh_check, place, VOLUME_TOL


@dataclass(frozen=True)
class Tunnel:
    floor: float = BALL_TRACK.floor
    radius: float = BALL_TRACK.radius
    ceiling: float = 34.8
    cavity_height: float = 4.75
    entry: float = .3
    ball_diameter: float = BALL_TRACK.ball_diameter

    def __post_init__(self):
        if any(not math.isfinite(v) or v <= 0 for v in asdict(self).values()):
            raise ValueError('Dimensions must be finite and positive')
        tangent = self.floor+self.radius+self.radius/math.sqrt(2)
        if not tangent < self.ceiling < 36.8:
            raise ValueError('Ceiling must leave a roof and lie above the tangent')
        if not 4.5 < self.cavity_height <= self.floor-1.6:
            raise ValueError('Receiver needs insertion clearance and a 1.6 mm floor')
        if self.radius >= 15.9-1.6-self.entry:
            raise ValueError('Channel leaves insufficient side wall')

    @property
    def bridge_width(self):
        return 2*(self.floor+self.radius+math.sqrt(2)*self.radius-self.ceiling)


def passage_wire(x, blend, t):
    """Same circular floor; blend=0 circular roof, blend=1 original roof."""
    cy=t.floor+t.radius; a=t.radius/math.sqrt(2); b=t.bridge_width/2
    def mix(cx,cz,tx,tz):
        return (cx*(1-blend)+tx*blend,cz*(1-blend)+tz*blend)
    end=mix(t.radius*math.cos(math.radians(75)),cy+t.radius*math.sin(math.radians(75)),b,t.ceiling)
    mid=mix(t.radius*.5,cy+t.radius*math.sqrt(3)/2,(a+b)/2,(cy+a+t.ceiling)/2)
    apex=(0,(cy+t.radius)*(1-blend)+t.ceiling*blend)
    w=cq.Workplane('YZ',origin=(x,0,0)).moveTo(-a,cy+a).threePointArc((0,t.floor),(a,cy+a))
    if blend==1:
        w=w.lineTo(b,t.ceiling).lineTo(-b,t.ceiling).lineTo(-a,cy+a)
    else:
        w=w.threePointArc(mid,end).threePointArc(apex,(-end[0],end[1])).threePointArc((-mid[0],mid[1]),(-a,cy+a))
    return w.close().val()


def build_tunnel(t=Tunnel(), *, roof='transition', transition=4., label=None):
    # Reproduce the E31-05 receiver dimensions in a shallow tunnel base.
    # E31 coupon receiver is taller, so physical retention must be retested.
    p=replace(brick_from_fit('duplo-e27-play-v1', nx=2, ny=2, height_units=2),
              tube_radius=6.60)
    outer=cq.Workplane('XY').box(p.width,p.depth,p.height,centered=(True,True,False))
    outer=outer.edges('|Z').fillet(ROUNDED_EDGES.corner_radius).edges('>Z').fillet(ROUNDED_EDGES.corner_radius)
    result=receiver(p,outer,t.cavity_height,ROUNDED_EDGES.receiver_entry)
    # E31-05 used a 0.30 mm lower entry chamfer, not the old 0.50 mm fillet.
    # YZ section, X is the passage axis. Circular bottom is identical to rail 01.
    # Circular arc to 45 degrees, then 45-degree roof slopes and a short bridge.
    cy=t.floor+t.radius
    a=t.radius/math.sqrt(2)
    b=t.bridge_width/2
    cut=(cq.Workplane('YZ',origin=(-p.width/2-1,0,0))
         .moveTo(-a,cy+a).threePointArc((0,t.floor),(a,cy+a))
         .lineTo(b,t.ceiling).lineTo(-b,t.ceiling).close().extrude(p.width+2))
    if roof not in ('teardrop','circle','transition'):
        raise ValueError('Unknown roof')
    if roof=='circle':
        cut=cq.Workplane('YZ',origin=(-p.width/2-1,0,cy)).circle(t.radius).extrude(p.width+2)
    elif roof=='transition':
        if not 1<=transition<=6:
            raise ValueError('Transition must be 1 to 6 mm')
        # 1 mm circular lip, smoothstep roof rise over a defined axial length.
        stations=[(-p.width/2-1,0),(-p.width/2+1,0)]
        for i in range(1,9):
            u=i/8;stations.append((-p.width/2+1+transition*u,3*u*u-2*u*u*u))
        stations += [(-x,b) for x,b in reversed(stations)]
        cut=cq.Solid.makeLoft([passage_wire(x,b,t) for x,b in stations],ruled=True)
    result=result.cut(cut)
    # Rounded lead-in on both passage mouths, including the lower circular arc.
    mouths=[e for e in result.val().Edges()
            if abs(abs(e.Center().x)-p.width/2)<1e-5
            and e.BoundingBox().zmin>t.floor-.01
            and e.BoundingBox().zmax<t.ceiling+.01
            and e.BoundingBox().ymin>-t.radius-.01
            and e.BoundingBox().ymax<t.radius+.01]
    if roof=='teardrop' and len(mouths)!=8:
        raise ValueError(f'Expected four section edges at each mouth, got {len(mouths)}')
    if mouths:
        result=result.newObject(mouths).fillet(t.entry)
    studs=make_studs(p.studs(), p.height, p.stud_radius-p.clearance,
                     p.stud_inner_radius, p.stud_height, lip_radius=ROUNDED_EDGES.stud_lip_radius)
    shape=result.union(studs).val().clean()
    shape=add_e31_05_receiver_features(shape,p.tubes(),p.tube_radius)
    if not shape.isValid() or len(shape.Solids())!=1:
        raise ValueError('Tunnel must be one valid solid')
    shape=engrave(shape,label or PART_ID,x=0,y=-p.depth/2,z=10.)
    return shape,p


def ball_sweep(shape,p,t,diameter):
    """Continuous straight swept-sphere volume, conservatively extended beyond mouths."""
    r=diameter/2
    sweep=cq.Solid.makeCylinder(r,p.width+2*r,
        cq.Vector(-p.width/2-r,0,t.floor+r+.05),cq.Vector(1,0,0))
    return intersection(shape,sweep)


def fit_checks(shape,p):
    refp=nominal_brick('duplo',2,2); ref=build(refp)
    rows=[]
    for pair,lower,upper,height in [('reference/printed',ref,shape,refp.height),
            ('printed/reference',shape,ref,p.height),('printed/printed',shape,shape,p.height)]:
        for lift in (5.7,4.5,3.,1.5,0.):
            vol=intersection(lower,place(upper,(0,0,height+lift)))
            rows.append(dict(pair=pair,lift_mm=lift,intersection_mm3=vol,collision=vol>VOLUME_TOL))
    poses=[]
    for name,x,y,z,a in [('one_stud_offset',16,0,38.4,0),('cross_90',0,0,38.4,90),
            ('half_pitch_negative_control',8,0,38.4,0),('overinsert_negative_control',0,0,38.1,0)]:
        v=intersection(shape,place(shape,(x,y,z),a))
        poses.append(dict(name=name,xyz_mm=[x,y,z],rotation_deg=a,intersection_mm3=v,collision=v>VOLUME_TOL))
    return dict(reference='synthetic DUPLO nominal, not an OEM scan',insertion=rows,poses=poses)


def export(out=Path('build/duplo-tunnel-trial-01')):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    t=Tunnel(); shape,p=build_tunnel(t)
    cq.exporters.export(shape,str(out/'brick.stl'),tolerance=.008,angularTolerance=.10)
    raw=(out/'brick.stl').read_bytes();tris=[];collapsed=0
    for i in range(struct.unpack_from('<I',raw,80)[0]):
        tri=raw[84+50*i:134+50*i];v=struct.unpack('<12fH',tri)[3:12]
        if len({tuple(v[j:j+3]) for j in (0,3,6)})<3:collapsed+=1
        else:tris.append(tri)
    (out/'brick.stl').write_bytes(raw[:80]+struct.pack('<I',len(tris))+b''.join(tris))
    cq.exporters.export(shape,str(out/'brick.step'))
    restored=cq.importers.importStep(str(out/'brick.step')).val()
    m=mesh_check(out/'brick.stl');fit=fit_checks(shape,p)
    sweep=ball_sweep(shape,p,t,t.ball_diameter)
    negative=ball_sweep(shape,p,t,28.)
    bounds=exact_bounds(shape)
    checks=dict(valid_brep=shape.isValid(),one_solid=len(shape.Solids())==1,
        dimensions=all(abs(a-b)<1e-6 for a,b in zip(bounds,[31.8,31.8,42.9])),
        mesh=m['passed'],mesh_volume=abs(m['signed_volume_mm3']-shape.Volume())/shape.Volume()<.001,
        step_roundtrip=restored.isValid() and len(restored.Solids())==1 and abs(restored.Volume()-shape.Volume())<1e-4,
        continuous_ball_path_clear=sweep<VOLUME_TOL,oversize_ball_detected=negative>VOLUME_TOL,
        floor_present=shape.isInside(cq.Vector(0,0,t.floor-.1)),
        floor_open=not shape.isInside(cq.Vector(0,0,t.floor+.1)),
        bottom_open=not shape.isInside(cq.Vector(4,0,.5)),
        tube_hole=not shape.isInside(cq.Vector(0,0,1)),tube_wall=shape.isInside(cq.Vector(3.89,3.89,1)),
        roof_present=shape.isInside(cq.Vector(0,0,37.6)),
        stud_floors=all(shape.isInside(cq.Vector(x,y,38.3)) for x,y in p.studs()),
        negative_controls=all(r['collision'] for r in fit['poses'] if 'negative_control' in r['name']),
        fit_dimensions_match_e31_05=(p.stud_radius==4.7 and p.stud_inner_radius==3.2 and p.tube_radius==6.60 and p.cavity_xy==(25.4,25.4)),
        fit_within_trial_envelope=math.sqrt(2)*8-p.tube_radius-4.7>=-.14,
        initial_insertion_clear=all(not r['collision'] for r in fit['insertion'] if r['lift_mm']==5.7))
    report=dict(schema_version=1,kind='tunnel',passed=all(checks.values()),
        design=design_manifest(p, channel=t, channel_standard=BALL_TRACK, finish=ROUNDED_EDGES),
        geometry=dict(bounds_mm=bounds,volume_mm3=shape.Volume(),parameters=asdict(p),checks=checks),
        tunnel=asdict(t),bridge_width_mm=t.bridge_width,roof_thickness_mm=p.height-t.ceiling,
        mesh=m,collapsed_stl_triangles_removed=collapsed,
        finish_detail=dict(outer_corner_radius_mm=.8,stud_lip_radius_mm=.5,receiver_entry_chamfer_mm=.3,mouth_radius_mm=.3),
        e31_05_receiver=dict(tube_od_mm=13.20,bead_minor_radius_mm=.20,bead_z_mm=2.25,
                             slot_width_mm=1.10,slot_end_z_mm=4.40,
                             transfer_to_shallow_tunnel_unvalidated=True),
        roof_style=dict(mouth='circular',inner='high_teardrop',circular_lip_mm=1.,transition_mm=4.),
        stl_tessellation=dict(linear_tolerance_mm=.03,angular_tolerance_radians=.2),
        ball_sweep=dict(diameter_mm=t.ball_diameter,centre_z_mm=t.floor+t.ball_diameter/2+.05,
            intersection_mm3=sweep,negative_diameter_mm=28.,negative_intersection_mm3=negative),
        physical_fit_validated=False,fit_geometrically_clear=not any(r['collision'] for r in fit['insertion']),
        intentional_fit_trial=True,fit=fit,
        limitations=['E31-05 bead and slots transferred to shallow 4.75 mm tunnel receiver; physical fit/retention unverified.',
            'Ball diameter is approximate; swept clearance is rigid geometry, not a rolling simulation.',
            'Circular entrance transitions to higher teardrop roof over 4 mm; bridge and support-free slicing unverified.',
            'Horizontal passage requires incoming momentum. Rail joints and physical fit untested.'],
        files={name:hashlib.sha256((out/name).read_bytes()).hexdigest() for name in ['brick.stl','brick.step']})
    (out/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    (out/'parameters.json').write_text(json.dumps(dict(brick=asdict(p),tunnel=asdict(t)),indent=2)+'\n')
    preview(shape,p,out);viewer(shape,p,report,out)
    # Section through x=0 reveals the complete tunnel opening in YZ.
    section=shape.cut(cq.Workplane('XY').box(50,50,60,centered=(False,True,False)).val())
    html=(out/'viewer.html').read_text()
    import re
    # Keep the generic viewer unchanged; only replace this generated instance's section.
    data=json.loads(re.search(r'const data=(.*?);\nconst canvas=',html,re.S).group(1))
    v,f=mesh(section);data['section']=dict(vertices=v,faces=f,edges=outlines(section))
    ref=build(nominal_brick('duplo',2,2))
    v,f=mesh(ref);data['reference']=dict(vertices=v,faces=f,edges=outlines(ref))
    html=re.sub(r'const data=.*?;\nconst canvas=',lambda m:'const data='+json.dumps(data,separators=(',',':'))+';\nconst canvas=',html,count=1,flags=re.S)
    html=html.replace('CAD断面（y &lt; 0）','CAD断面（x &lt; 0）')
    html=html.replace('<option value="stack">','<option value="sandwich">DUPLO 2×2</option><option value="stack">')
    html=html.replace('function draw(){','function draw(){pose.disabled=lift.disabled=mode.value===\'sandwich\';')
    html=html.replace("const source=mode.value==='section'?data.section:data;",
        "if(mode.value==='sandwich'){scene.unshift({t:[0,0,-19.2,0],color:[80,185,105],reference:true});scene.push({t:[0,0,38.4,0],color:[45,153,212],reference:true})}const source=mode.value==='section'?data.section:data;")
    html=html.replace('const vv=source.vertices','const src=obj.reference?data.reference:source;const vv=src.vertices')
    html=html.replace('for(const f of source.faces)','for(const f of src.faces)')
    html=html.replace('for(const segment of source.edges)','for(const segment of (obj.reference?data.reference:source).edges)')
    html=html.replace("section:[0,.15]","section:[-Math.PI/2,0]")
    html=html.replace("'Brick CAD inspector · '","'DUPLO tunnel trial 01 · '")
    (out/'viewer.html').write_text(html)
    print('TUNNEL', 'PASS' if report['passed'] else 'FAIL',bounds,'bridge',t.bridge_width,
          'brep_volume',shape.Volume(),'mesh_volume',m['signed_volume_mm3'],checks,flush=True)
    if not report['passed']:raise RuntimeError('Tunnel verification failed')
    return report


if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,default=Path('build/duplo-tunnel-trial-01'))
    export(ap.parse_args().out)

