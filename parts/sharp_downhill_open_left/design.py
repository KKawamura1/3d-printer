"""Issue #37 individual track design; BRep authoritative, mm, Z up."""
from dataclasses import asdict, replace
from pathlib import Path
import json, math, struct, hashlib
import cadquery as cq
from brickcad.model import brick_from_fit, receiver
from brickcad.connections import make_studs
from brickcad.marking import engrave_west
from brickcad.standards import BALL_TRACK
from brickcad.ports import Port
from brickcad.provenance import design_manifest
from brickcad.verify import intersection, mesh_check, exact_bounds, VOLUME_TOL
from brickcad.render import viewer
from parts.tunnel.e31_fit import add_e31_05_receiver_features

PART_ID = 'SD02-V1'
KIND = 'sharp'
DROP = 19.2
TUNNEL = False
MIRROR = True
STEEP = False
R = 48. if KIND == 'gentle' else 16.
LENGTH = 64. if KIND == 'straight' else (math.pi*R/2 + (32. if KIND == 'sharp' else 0.))
FLOOR = BALL_TRACK.floor
BALL = BALL_TRACK.ball_diameter
DEPTH = 4.75


def xy(s):
    if KIND == 'straight': return (-32+s,0.,1.,0.)
    if KIND == 'sharp':
        if s <= 32: return (-32+s,0.,1.,0.)
        a=math.pi/2-(s-32)/16
        return (16*math.cos(a),-16+16*math.sin(a),math.sin(a),-math.cos(a))
    a=-math.pi/2+s/48
    return (-32+48*math.cos(a),32+48*math.sin(a),-math.sin(a),math.cos(a))


def height(s, branch='low'):
    t=max(0.,min(1.,s/LENGTH))
    if STEEP:
        if branch == 'high': return FLOOR+19.2
        return FLOOR+.65*max(0.,min(15.,27-s))
    return FLOOR+DROP*(1-3*t*t+2*t*t*t)


def slope(s, branch='low'):
    if STEEP: return -.65 if branch=='low' and 12<s<27 else 0.
    t=max(0.,min(1.,s/LENGTH))
    return DROP*(-6*t+6*t*t)/LENGTH


def plane(s):
    x,y,tx,ty=xy(s)
    return cq.Plane(origin=(x,y,0),xDir=(-ty,tx,0),normal=(tx,ty,0))


def wire(s, role, branch='low'):
    f=height(s,branch)
    w=cq.Workplane(plane(s))
    if role in ('outer','mask'):
        top=90 if role=='mask' else (57.6 if TUNNEL else f+12.85)
        return w.polyline([(-15.9,0),(15.9,0),(15.9,top),(-15.9,top)]).close().val()
    # Exact endpoint radius, a wider interior for the inclined sphere envelope.
    distance=min(max(0,s),max(0,LENGTH-s))
    blend=min(1.,distance/5.)
    rad=BALL_TRACK.radius+(14.-BALL_TRACK.radius)*blend
    c=f+rad
    a=rad/math.sqrt(2)
    if not TUNNEL:
        return (w.moveTo(-rad,c).threePointArc((0,f),(rad,c))
                .lineTo(rad,95).lineTo(-rad,95).close().val())
    # Printable pointed roof; circular upper half at the mouth transitions in 5mm.
    roof=f+2*BALL_TRACK.radius+(30.3-2*BALL_TRACK.radius)*blend
    return (w.moveTo(-a,c+a).threePointArc((0,f),(a,c+a))
            .lineTo(.4,roof).lineTo(-.4,roof).close().val())


def stations(a=-.3,b=None):
    if b is None: b=LENGTH+.3
    vals=[a,b]+[i*LENGTH/64 for i in range(65) if a<i*LENGTH/64<b]
    vals += [v for v in (0,1,3,5,12,27,32,LENGTH-5,LENGTH-3,LENGTH-1,LENGTH) if a<v<b]
    return sorted(set(vals))


def loft(role,a=-.3,b=None,branch='low'):
    return cq.Solid.makeLoft([wire(s,role,branch) for s in stations(a,b)],ruled=True)


def build_part(label=PART_ID):
    ny=4 if KIND=='gentle' else 2
    p=replace(brick_from_fit('duplo-e27-play-v1',nx=4,ny=ny,height_units=3 if TUNNEL else (2 if DROP else 1)),tube_radius=6.6)
    clip=cq.Workplane('XY').box(p.width,p.depth,100,centered=(True,True,False)).val()
    mask=loft('mask').intersect(clip)
    outer=loft('outer').intersect(clip)
    body=receiver(p,cq.Workplane(obj=outer),DEPTH,0).val().clean()
    # Reject unsupported near-tangent tube slivers; use complete and useful clipped rings.
    body=body.intersect(mask).clean()
    if STEEP:
        passage=loft('passage',-.3,12,'high').fuse(loft('passage',12,LENGTH+.3,'low'))
        x,y,_,_=xy(12)
        passage=passage.fuse(cq.Solid.makeCylinder(14.,43.5-(height(12)+14),cq.Vector(x,y,height(12)+14)))
        passage=passage.fuse(cq.Solid.makeCone(14.,0.,12.3,cq.Vector(x,y,43.5)))
    else: passage=loft('passage')
    if STEEP:
        body=body.cut(loft('passage',-.3,12.2,'high')).cut(loft('passage',11.8,LENGTH+.3,'low')).clean()
    else: body=body.cut(passage).clean()
    if STEEP: print('passage/body valid',passage.isValid(),body.isValid(),flush=True)
    full=[]
    for x,y in p.tubes():
        if all(mask.isInside(cq.Vector(x+6.85*math.cos(a),y+6.85*math.sin(a),2)) for a in [i*math.pi/4 for i in range(8)]):full.append((x,y))
    if full: body=add_e31_05_receiver_features(body,full,p.tube_radius)
    if TUNNEL:
        studs=make_studs(p.studs(),57.45,p.stud_radius,p.stud_inner_radius,4.65,.5).val().intersect(mask)
        body=body.fuse(studs).clean()
        if STEEP: print('stud body valid',body.isValid(),flush=True)
    # Mark below the running floor, on the inlet face; avoids mating contact below 4.75.
    x,y,_,_=xy(0)
    if MIRROR:
        body=body.mirror('XZ');y=-y
    body=engrave_west(body,label,x=-p.width/2,y=y,z=5.55,size=1.1,depth=.3)
    if not body.isValid() or len(body.Solids())!=1:raise ValueError('Expected one valid connected solid')
    return body,p


def path():
    def point(s,branch='low'):
        x,y,_,_=xy(s)
        z=height(s,branch)+BALL/2*math.sqrt(1+slope(s,branch)**2)+.5
        return cq.Vector(x,-y if MIRROR else y,z)
    if not STEEP:return [point(s) for s in stations(0,LENGTH)]
    return [point(s,'high') for s in stations(0,12)]+[point(s) for s in stations(12,LENGTH)]


def ports():
    out=[]
    for s,name,sign in [(0,'inlet',-1),(LENGTH,'outlet',1)]:
        x,y,tx,ty=xy(s)
        if MIRROR:y=-y;ty=-ty
        out.append(Port(name,(x,y,FLOOR+(DROP if s==0 else 0)),(sign*tx,sign*ty,0.),BALL_TRACK.radius))
    return out


def verify(shape,p):
    pts=path();r=BALL/2
    # Union of endpoint spheres and cylinders is the EXACT sweep of a sphere
    # along this explicitly defined continuous polyline (not just samples).
    sphere_errors=[intersection(shape,cq.Solid.makeSphere(r,c,angleDegrees1=-90)) for c in pts]
    segment_errors=[]
    for a,b in zip(pts,pts[1:]):
        v=b-a
        segment_errors.append(intersection(shape,cq.Solid.makeCylinder(r,v.Length,a,v.normalized())))
    mid=pts[len(pts)//2]
    negative=intersection(shape,cq.Solid.makeSphere(r,mid-cq.Vector(0,0,3),angleDegrees1=-90))
    checks=dict(valid_brep=shape.isValid(),one_solid=len(shape.Solids())==1,
        continuous_sphere_path_clear=max(sphere_errors+segment_errors)<VOLUME_TOL,
        lowered_ball_detected=negative>VOLUME_TOL,
        drop_matches_grid=abs(ports()[0].floor_xyz_mm[2]-ports()[1].floor_xyz_mm[2]-DROP)<1e-6,
        receiver_depth=abs(FLOOR-DEPTH-1.6)<1e-6,
        full_roof=(not TUNNEL or all(shape.isInside(cq.Vector(x,-y if MIRROR else y,57.5)) for x,y,_,_ in [xy(LENGTH*t) for t in (.1,.3,.5,.7,.9)])),
        maximum_height=abs(shape.BoundingBox().zmax-(62.1 if TUNNEL else FLOOR+DROP+12.85))<.1)

    return checks,dict(sphere_intersections_mm3=sphere_errors,segment_intersections_mm3=segment_errors,lowered_ball_mm3=negative,centres_mm=[c.toTuple() for c in pts],definition='Exact continuous capsule sweep along the reported polyline; not a solved gravity trajectory')


def export(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    shape,p=build_part();checks,clearance=verify(shape,p)
    stl=out/'brick.stl';shape.exportStl(str(stl),tolerance=.03,angularTolerance=.2,relative=False)
    raw=stl.read_bytes();triangles=[]
    for i in range(struct.unpack_from('<I',raw,80)[0]):
        tri=raw[84+50*i:134+50*i];v=struct.unpack('<12fH',tri)[3:12]
        if len({tuple(v[j:j+3]) for j in (0,3,6)})==3:triangles.append(tri)
    stl.write_bytes(raw[:80]+struct.pack('<I',len(triangles))+b''.join(triangles))
    cq.exporters.export(shape,str(out/'brick.step'))
    restored=cq.importers.importStep(str(out/'brick.step')).val()
    m=mesh_check(stl);checks['mesh_closed']=m['passed']
    delta=shape.cut(restored).Volume()+restored.cut(shape).Volume()
    checks['step_roundtrip']=restored.isValid() and len(restored.Solids())==1 and abs(delta)<.01
    report=dict(part_id=PART_ID,passed=all(checks.values()),checks=checks,mesh=m,clearance=clearance,ports=[asdict(v) for v in ports()],design=design_manifest(p),bounds_mm=exact_bounds(shape),physical_fit_validated=False,physical_rolling_validated=False,slicer_support_free_validated=False,sha256_stl=hashlib.sha256(stl.read_bytes()).hexdigest())
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    viewer_report={**report,'geometry':dict(bounds_mm=exact_bounds(shape),parameters=asdict(p)),
                   'fit':dict(insertion=[],poses=[])}
    for name,dx,angle in [('aligned',0,0),('cross_90',0,90),('half_pitch_negative_control',8,0)]:
        upper=shape.rotate((0,0,0),(0,0,1),angle).translate((dx,0,p.height))
        overlap=intersection(shape,upper)
        row=dict(name=name,xyz_mm=[dx,0,p.height],rotation_deg=angle,intersection_mm3=overlap,collision=overlap>VOLUME_TOL)
        if name=='aligned':viewer_report['fit']['insertion'].append(dict(row,pair='printed/printed',lift_mm=0))
        else:viewer_report['fit']['poses'].append(row)
    viewer(shape.copy(mesh=False),p,viewer_report,out)
    print(PART_ID,checks,flush=True)
    if not report['passed']:raise ValueError('CAD verification failed')
    return report

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True)
    export(ap.parse_args().out)
