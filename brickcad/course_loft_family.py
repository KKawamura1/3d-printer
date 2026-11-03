"""Independent setting-driven swept-section CAD for straight/R16/R48 channels.

A path, floor elevation, enclosure and handedness are the only shape variables.
This module MUST NOT import or call any historical parts.*.design export/builder.
The originals are used only in separate *tests* as immutable CAD oracles.
"""
from dataclasses import dataclass, replace
from pathlib import Path
import hashlib
import json
import math
import struct

import cadquery as cq
from brickcad.connections import make_studs
from brickcad.marking import engrave, engrave_west
from brickcad.model import brick_from_fit, receiver
from brickcad.standards import BALL_TRACK
from brickcad.verify import exact_bounds, mesh_check
from parts.tunnel.e31_fit import add_e31_05_receiver_features

RECEIVER_DEPTH = 4.75
CHANNEL_HALF_WIDTH = 15.9
SLIT_RING_CLEARANCE = 6.85


@dataclass(frozen=True)
class LoftSettings:
    route: str
    drop_mm: float
    tunnel: bool
    mirror: bool
    mark_face: str
    label_z_mm: float
    label_x_mm: float = -16.0

    @classmethod
    def from_dict(cls, raw):
        allowed = {"route", "drop_mm", "tunnel", "mirror", "mark_face",
                   "label_z_mm", "label_x_mm"}
        if not isinstance(raw, dict) or set(raw) - allowed:
            raise ValueError("Unsupported loft course settings")
        required = allowed - {"label_x_mm"}
        if not required.issubset(raw):
            raise ValueError("Missing required loft course settings")
        obj = cls(**raw)
        if obj.route not in ("straight", "gentle", "sharp"):
            raise ValueError("Unknown course centreline")
        if type(obj.drop_mm) not in (int, float) or obj.drop_mm not in (0, 19.2):
            raise ValueError("Only level or one-course downhill is validated")
        if type(obj.tunnel) is not bool or type(obj.mirror) is not bool:
            raise ValueError("Tunnel and mirror must be boolean")
        if (obj.tunnel and (obj.route, obj.drop_mm) != ("sharp", 19.2)):
            raise ValueError("Loft tunnel currently verified for sloped sharp curve only")
        if obj.route == "straight" and obj.mirror:
            raise ValueError("Straight path does not have a left/right variant")
        if obj.mark_face not in ("south", "west"):
            raise ValueError("Only visible south/west exterior markings supported")
        if obj.mark_face == "west" and obj.route != "gentle":
            raise ValueError("West marking only for gentle-curve body")
        if obj.mark_face == "south" and obj.route == "gentle":
            raise ValueError("Gentle curve requires its exposed west face")
        if not (math.isfinite(obj.label_z_mm) and 0 < obj.label_z_mm <= 15):
            raise ValueError("Invalid marking location")
        return obj

    @property
    def radius(self):
        return 48. if self.route == "gentle" else 16.

    @property
    def length(self):
        return 64. if self.route == "straight" else (
            math.pi*self.radius/2 + (32. if self.route == "sharp" else 0.))


def xy(s, config):
    if config.route == "straight":
        return (-32+s, 0., 1., 0.)
    if config.route == "sharp":
        if s <= 32:
            return (-32+s, 0., 1., 0.)
        a = math.pi/2-(s-32)/16
        return (16*math.cos(a), -16+16*math.sin(a), math.sin(a), -math.cos(a))
    a = -math.pi/2+s/48
    return (-32+48*math.cos(a), 32+48*math.sin(a), -math.sin(a), math.cos(a))


def height(s, config):
    t = max(0., min(1., s/config.length))
    return BALL_TRACK.floor+config.drop_mm*(1-3*t*t+2*t*t*t)


def section_plane(s, config):
    x,y,tx,ty = xy(s, config)
    return cq.Plane(origin=(x,y,0), xDir=(-ty,tx,0), normal=(tx,ty,0))


def wire(s, role, config):
    floor = height(s, config)
    w = cq.Workplane(section_plane(s, config))
    if role in ("outer", "mask"):
        top = 90 if role == "mask" else (57.6 if config.tunnel else floor+12.85)
        return w.polyline([(-15.9,0),(15.9,0),(15.9,top),(-15.9,top)]).close().val()

    distance = min(max(0,s),max(0,config.length-s))
    # 1mm circular entry/exit lip for slope+sharp tunnel; old open rails
    # retain their original linear 5mm radius blend.
    if config.tunnel:
        u = max(0.,min(1.,(distance-1.)/4.))
        blend = min(.995,3*u*u-2*u*u*u)
    else:
        blend = min(1.,distance/5.)
    radius = BALL_TRACK.radius+(14.-BALL_TRACK.radius)*blend
    centre = floor+radius
    a = radius/math.sqrt(2)
    if not config.tunnel:
        return (w.moveTo(-radius,centre).threePointArc((0,floor),(radius,centre))
                .lineTo(radius,95).lineTo(-radius,95).close().val())

    roof = floor+2*BALL_TRACK.radius+(30.3-2*BALL_TRACK.radius)*blend
    bridge = centre+math.sqrt(2)*radius-roof
    def mixed(circle,teardrop):
        return circle*(1-blend)+teardrop*blend
    end = (mixed(radius*math.cos(math.radians(75)),bridge),
           mixed(centre+radius*math.sin(math.radians(75)),roof))
    mid = (mixed(radius*.5,(a+bridge)/2),
           mixed(centre+radius*math.sqrt(3)/2,(centre+a+roof)/2))
    apex = (0,mixed(centre+radius,roof))
    return (w.moveTo(-a,centre+a).threePointArc((0,floor),(a,centre+a))
            .threePointArc(mid,end)
            .threePointArc(apex,(-end[0],end[1]))
            .threePointArc((-mid[0],mid[1]),(-a,centre+a)).close().val())


def stations(config, a=-.3, b=None):
    if b is None:
        b = config.length+.3
    length = config.length
    vals = [a,b]+[i*length/64 for i in range(65) if a<i*length/64<b]
    vals += [v for v in (0,1,3,5,12,27,32,length-5,length-3,length-1,length)
             if a<v<b]
    return sorted(set(vals))


def loft(config, role, a=-.3, b=None):
    return cq.Solid.makeLoft([wire(s,role,config) for s in stations(config,a,b)],
                             ruled=True)


def build_course(config, *, label=None):
    """Construct independent BRep. Engrave only after all unions/mirroring."""
    config = (LoftSettings.from_dict(config) if isinstance(config, dict) else config)
    ny = 4 if config.route == "gentle" else 2
    p = replace(brick_from_fit("duplo-e27-play-v1",nx=4,ny=ny,
                height_units=3 if config.tunnel else (2 if config.drop_mm else 1)),
                tube_radius=6.6)
    clip = cq.Workplane("XY").box(p.width,p.depth,100,
              centered=(True,True,False)).val()
    mask = loft(config,"mask").intersect(clip)
    outer = loft(config,"outer").intersect(clip)
    body = receiver(p,cq.Workplane(obj=outer),RECEIVER_DEPTH,0).val().clean()
    body = body.intersect(mask).clean()
    body = body.cut(loft(config,"passage")).clean()

    # Keep clipped supports. Add E31 beads/slots ONLY to complete tubes.
    full = []
    for x,y in p.tubes():
        if all(mask.isInside(cq.Vector(x+SLIT_RING_CLEARANCE*math.cos(a),
                        y+SLIT_RING_CLEARANCE*math.sin(a),2))
               for a in [i*math.pi/4 for i in range(8)]):
            full.append((x,y))
    if full:
        body = add_e31_05_receiver_features(
            body,full,p.tube_radius,receiver_depth=RECEIVER_DEPTH)

    if config.tunnel:
        raw_studs = make_studs(p.studs(),57.45,p.stud_radius,
                               p.stud_inner_radius,4.65,.5).val().intersect(mask)
        attached = []
        for fragment in raw_studs.Solids():
            if fragment.Volume() < 3.0:
                continue
            if body.intersect(fragment).Volume() < .20:
                continue
            attached.append(fragment)
        if not attached:
            raise ValueError("Roof has no attached clipped studs")
        for fragment in attached:
            body = body.fuse(fragment).clean()
        if not body.isValid() or len(body.Solids()) != 1:
            raise ValueError("Clipped roof studs must form a valid solid")

    if config.mirror:
        body = body.mirror("XZ")
    if label is not None:
        if config.mark_face == "west":
            inlet_y = xy(0,config)[1]
            if config.mirror:
                inlet_y = -inlet_y
            body = engrave_west(body,label,x=-p.width/2,
                                y=inlet_y,z=config.label_z_mm)
        else:
            body = engrave(body,label,x=config.label_x_mm,
                           y=-p.depth/2,z=config.label_z_mm)
    if not body.isValid() or len(body.Solids()) != 1:
        raise ValueError("Configured loft must be a single connected BRep")
    return body,p


def _remove_degenerate_triangles(stl):
    raw = stl.read_bytes()
    if len(raw) < 84 or len(raw) != 84+50*struct.unpack_from("<I",raw,80)[0]:
        raise ValueError("Malformed binary STL")
    kept = []
    for i in range(struct.unpack_from("<I",raw,80)[0]):
        tri = raw[84+50*i:134+50*i]
        v = struct.unpack("<12fH",tri)[3:12]
        if len({tuple(v[j:j+3]) for j in (0,3,6)}) == 3:
            kept.append(tri)
    if len(kept) < struct.unpack_from("<I",raw,80)[0]:
        stl.write_bytes(raw[:80]+struct.pack("<I",len(kept))+b"".join(kept))


def export_course(model_id, config, out):
    """CAD/STL artifacts are generated by this kernel, not the old exporters."""
    out = Path(out)
    out.mkdir(parents=True,exist_ok=True)
    shape,p = build_course(config,label=model_id)
    stl = out/"brick.stl"
    cq.exporters.export(shape,str(stl),tolerance=.01,angularTolerance=.1)
    _remove_degenerate_triangles(stl)
    cq.exporters.export(shape,str(out/"brick.step"))
    m = mesh_check(stl)
    bounds = exact_bounds(shape)
    nominal = (p.width,p.depth,p.height+(p.stud_height if config["tunnel"] else 0))
    checks = {
        "valid_single_solid":shape.isValid() and len(shape.Solids()) == 1,
        "nominal_dimensions":all(abs(a-b)<1e-4 for a,b in zip(bounds,nominal)),
        "shallow_receiver_has_floor":BALL_TRACK.floor-RECEIVER_DEPTH>=1.60-1e-6,
        "mesh":m["passed"],
        "mesh_volume":abs(m["signed_volume_mm3"]-shape.Volume())/
                      shape.Volume() < .001,
    }
    report = {"part_id":model_id,"passed":all(checks.values()),
              "checks":checks,"mesh":m,
              "geometry":{"bounds_mm":bounds,"volume_mm3":shape.Volume()},
              "source_engine":"brickcad.course_loft_family",
              "physical_fit_validated":False,
              "physical_rolling_validated":False,
              "slicing_validated":False}
    (out/"report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
    manifest = {"schema_version":1,"mode":"independent_configured_geometry",
                "model_id":model_id,"geometry_verified":report["passed"],
                "source_engine":"brickcad.course_loft_family",
                "stl_sha256":hashlib.sha256(stl.read_bytes()).hexdigest(),
                "recipe":config,"physical_fit_validated":False,
                "physical_rolling_validated":False,"slicing_validated":False}
    (out/"course-manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n")
    if not report["passed"]:
        raise ValueError("Configured course failed CAD checks: "+str(checks))
    return report
