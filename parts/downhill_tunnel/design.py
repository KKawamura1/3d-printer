"""D01-V2: DUPLO 2x4, three-course enclosed straight downhill with side observation windows.

All dimensions mm. Z is up. The high/low floor ports differ by one 19.2 mm course.
The E31-05 receiver is an unvalidated transfer from a calibration coupon.
"""
from dataclasses import asdict, dataclass, replace
from pathlib import Path
import hashlib
import json
import math
import struct
import cadquery as cq

from brickcad.connections import make_studs
from brickcad.marking import engrave
from brickcad.model import brick_from_fit, receiver
from brickcad.ports import Port
from brickcad.standards import BALL_TRACK, DUPLO, ROUNDED_EDGES
from brickcad.verify import exact_bounds, intersection, mesh_check, VOLUME_TOL
from parts.tunnel.e31_fit import add_e31_05_receiver_features

PART_ID = "D01-V2"


@dataclass(frozen=True)
class Downhill:
    length: float = 63.8
    drop: float = DUPLO.height
    low_floor: float = BALL_TRACK.floor
    entry_radius: float = BALL_TRACK.radius
    inside_radius: float = 14.0
    inner_roof_above_floor: float = 30.3
    receiver_depth: float = 4.75
    circular_lip: float = 1.0
    roof_transition: float = 4.0
    window_width: float = 8.0
    window_bottom_offset: float = 7.0
    window_shoulder_offset: float = 18.0
    window_apex_offset: float = 22.0

    def __post_init__(self):
        if abs(self.length - 63.8) > 1e-6:
            raise ValueError("D01-V2 length is fixed to the DUPLO 2x4 grid")
        if self.inside_radius >= (31.8/2 - 1.6):
            raise ValueError("Inner radius leaves insufficient side wall")
        if self.low_floor - self.receiver_depth < 1.6 - 1e-6:
            raise ValueError("Receiver must retain a 1.6mm lower floor")
        if (3*DUPLO.height - (self.low_floor + self.drop +
                                self.inner_roof_above_floor)) < 1.6 - 1e-6:
            raise ValueError("Upper inlet roof too thin")
        if self.window_width >= BALL_TRACK.ball_diameter:
            raise ValueError("Ball could escape through a window")


def floor_z(x, d=Downhill()):
    t = max(0., min(1., (x + d.length / 2) / d.length))
    return d.low_floor + d.drop*(1 - 3*t*t + 2*t*t*t)


def floor_slope(x, d=Downhill()):
    t = max(0., min(1., (x + d.length / 2) / d.length))
    return d.drop*(-6*t + 6*t*t) / d.length


def _roof_blend(x, d):
    distance = min(abs(x + d.length/2), abs(x - d.length/2))
    u = max(0., min(1., (distance - d.circular_lip)/d.roof_transition))
    return min(.995, 3*u*u - 2*u*u*u)


def _passage_wire(x, blend, d):
    """Circular lower sweep, gradually growing into print-oriented high teardrop."""
    bottom = floor_z(x, d)
    radius = d.entry_radius + (d.inside_radius - d.entry_radius)*blend
    centre = bottom + radius
    shoulder = radius / math.sqrt(2)
    roof = bottom + (2*d.entry_radius +
                     (d.inner_roof_above_floor - 2*d.entry_radius)*blend)
    half_bridge = centre + math.sqrt(2)*radius - roof

    def mix(a, b):
        return a*(1-blend)+b*blend

    end = (mix(radius*math.cos(math.radians(75)), half_bridge),
           mix(centre+radius*math.sin(math.radians(75)), roof))
    mid = (mix(radius*.5, (shoulder+half_bridge)/2),
           mix(centre+radius*math.sqrt(3)/2, (centre+shoulder+roof)/2))
    apex = (0, mix(centre+radius, roof))
    return (cq.Workplane("YZ", origin=(x,0,0))
            .moveTo(-shoulder, centre+shoulder)
            .threePointArc((0,bottom),(shoulder,centre+shoulder))
            .threePointArc(mid,end)
            .threePointArc(apex,(-end[0],end[1]))
            .threePointArc((-mid[0],mid[1]),(-shoulder,centre+shoulder))
            .close().val())


def _cut_passage(d):
    # End sections run beyond the outer body, leaving genuinely open mouths.
    half = d.length/2
    xs = ([-half-.6,-half,-half+1,-half+2,-half+3,-half+4] +
          [-half+5+i*((d.length-10)/26) for i in range(27)] +
          [half-4,half-3,half-2,half-1,half,half+.6])
    xs = sorted(set(round(x,4) for x in xs))
    return cq.Solid.makeLoft([_passage_wire(x,_roof_blend(x,d),d)
                              for x in xs], ruled=True)


def _window_cutter(x, d):
    """One 8mm-wide, pitched, pointed-top opening in the negative-Y side wall."""
    left, right = x-d.window_width/2, x+d.window_width/2
    outline = [(left, floor_z(left,d)+d.window_bottom_offset),
               (right,floor_z(right,d)+d.window_bottom_offset),
               (right,floor_z(right,d)+d.window_shoulder_offset),
               (x, floor_z(x,d)+d.window_apex_offset),
               (left,floor_z(left,d)+d.window_shoulder_offset)]
    # XZ workplane positive normal points toward -Y, so extrude inward with -6.
    return (cq.Workplane("XZ",origin=(0,-17,0)).polyline(outline)
            .close().extrude(-6).val())


def ports(d=Downhill()):
    half = 2*DUPLO.pitch
    return (Port("high_west", (-half,0,d.low_floor+d.drop),
                 (-1.,0.,0.),d.entry_radius),
            Port("low_east", (half,0,d.low_floor),
                 (1.,0.,0.),d.entry_radius))


def build_downhill(d=Downhill()):
    p = replace(brick_from_fit("duplo-e27-play-v1", nx=4, ny=2, height_units=3),
                tube_radius=6.60)
    outer = cq.Workplane("XY").box(p.width,p.depth,p.height,
                                    centered=(True,True,False))
    outer = outer.edges("|Z").fillet(ROUNDED_EDGES.corner_radius)
    # A chamfer avoids non-manifold STL tessellation at the four top fillet poles.
    outer = outer.edges(">Z").chamfer(.5)
    body = receiver(p,outer,d.receiver_depth,ROUNDED_EDGES.receiver_entry)
    body = body.cut(_cut_passage(d))
    for x in (-16.,0.,16.):
        body = body.cut(_window_cutter(x,d))
    studs = make_studs(p.studs(),p.height,p.stud_radius-p.clearance,
                       p.stud_inner_radius,p.stud_height,
                       ROUNDED_EDGES.stud_lip_radius)
    shape = body.union(studs).val().clean()
    shape = add_e31_05_receiver_features(shape,p.tubes(),p.tube_radius)
    if not shape.isValid() or len(shape.Solids()) != 1:
        raise ValueError("D01-V2 must be a single valid connected BRep")
    # Engraving stays on the windowed side, below the running passage.
    shape = engrave(shape,PART_ID,x=0,y=-p.depth/2,z=9.)
    return shape,p


def ball_positions(d=Downhill(), count=33, diameter=BALL_TRACK.ball_diameter):
    r = diameter/2
    for i in range(count):
        x = -d.length/2 + d.length*i/(count-1)
        # Numerical loft/path clearance check, not a dynamics or rolling model.
        yield cq.Vector(x,0,floor_z(x,d)+r*math.sqrt(1+floor_slope(x,d)**2)+.18)


def sampled_ball_intersections(shape,d=Downhill(),count=33):
    r = BALL_TRACK.ball_diameter/2
    return [intersection(shape,cq.Solid.makeSphere(
            r,center,angleDegrees1=-90))
            for center in ball_positions(d,count)]


def export(out=Path("build/downhill-tunnel")):
    d=Downhill()
    shape,p=build_downhill(d)
    out=Path(out)
    out.mkdir(parents=True,exist_ok=True)
    stl=out/"brick.stl"
    cq.exporters.export(shape,str(stl),tolerance=.03,angularTolerance=.2)
    raw=stl.read_bytes()
    tris=[]
    for i in range(struct.unpack_from("<I",raw,80)[0]):
        tri=raw[84+50*i:134+50*i]
        coords=struct.unpack("<12fH",tri)[3:12]
        if len({tuple(coords[j:j+3]) for j in (0,3,6)})==3:
            tris.append(tri)
    stl.write_bytes(raw[:80]+struct.pack("<I",len(tris))+b"".join(tris))
    cq.exporters.export(shape,str(out/"brick.step"))
    mesh=mesh_check(stl)
    collisions=sampled_ball_intersections(shape,d)
    bounds=exact_bounds(shape)
    checks={
        "single_valid_solid":shape.isValid() and len(shape.Solids())==1,
        "size_2x4x3":all(abs(a-b)<.01 for a,b in zip(bounds,(63.8,31.8,62.1))),
        "mesh_closed":mesh["passed"],
        "sampled_ball_path_clear":max(collisions)<VOLUME_TOL,
        "lower_floor_present":shape.isInside(cq.Vector(0,0,6.2)),
        "windows_open":all(not shape.isInside(
            cq.Vector(x,-15.2,floor_z(x,d)+12)) for x in (-16.,0.,16.)),
        "windows_have_lower_guard":all(shape.isInside(
            cq.Vector(x,-15.2,floor_z(x,d)+4)) for x in (-16.,0.,16.))
    }
    report={
        "part_id":PART_ID,"passed":all(checks.values()),
        "parameters":asdict(d),"bounds_mm":bounds,
        "fit_profile_id":p.fit_profile_id,
        "e31_05":dict(tube_od_mm=13.2,bead_radius_mm=.2,split_slots=4),
        "ports":[asdict(port) for port in ports(d)],
        "checks":checks,"mesh":mesh,"sampled_ball_collisions_mm3":collisions,
        "sampling_limitation":"33 finite sphere stations; continuous collision and real rolling unverified",
        "physical_fit_validated":False,
        "physical_rolling_validated":False,
        "slicer_support_free_validated":False,
        "safety_limitation":"Open side windows, edges and E31 receiver require adult inspection and print validation",
        "sha256_stl":hashlib.sha256(stl.read_bytes()).hexdigest()
    }
    (out/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print("D01-V2", "PASS" if report["passed"] else "FAIL",checks,flush=True)
    if not report["passed"]:
        raise RuntimeError("D01-V2 geometry verification failed")
    return report


if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",type=Path,default=Path("build/downhill-tunnel"))
    export(parser.parse_args().out)
