"""Independent shared smoothstep downhill tunnel path, mouth and windows.

These are geometric primitives used by PR56's configurable D01/W01 builder.
No historical part generator is imported.
"""
from dataclasses import dataclass,replace
import math
import cadquery as cq
from brickcad.course_geometry import smoothstep_fall, smoothstep_rise_expanded
from brickcad.standards import BALL_TRACK,DUPLO
from brickcad.ports import Port
from brickcad.verify import intersection


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
        if abs(self.length-63.8)>1e-6:
            raise ValueError("Only 2x4 tunnel length is validated")
        if self.inside_radius >= (31.8/2-1.6):
            raise ValueError("Insufficient side wall")
        if self.low_floor-self.receiver_depth<1.6-1e-6:
            raise ValueError("Receiver floor too thin")
        if 3*DUPLO.height-(self.low_floor+self.drop+self.inner_roof_above_floor)<1.6-1e-6:
            raise ValueError("Insufficient roof thickness")
        if self.window_width>=BALL_TRACK.ball_diameter:
            raise ValueError("Window may allow ball to escape")


def floor_z(x,d=Downhill()):
    t=max(0.,min(1.,(x+d.length/2)/d.length))
    return d.low_floor+d.drop*(smoothstep_fall(t))


def floor_slope(x,d=Downhill()):
    t=max(0.,min(1.,(x+d.length/2)/d.length))
    return d.drop*(-6*t+6*t*t)/d.length


def _roof_blend(x,d):
    distance=min(abs(x+d.length/2),abs(x-d.length/2))
    u=max(0.,min(1.,(distance-d.circular_lip)/d.roof_transition))
    return min(.995,smoothstep_rise_expanded(u))


def _passage_wire(x,blend,d):
    bottom=floor_z(x,d)
    radius=d.entry_radius+(d.inside_radius-d.entry_radius)*blend
    centre=bottom+radius
    shoulder=radius/math.sqrt(2)
    roof=bottom+(2*d.entry_radius+(d.inner_roof_above_floor-2*d.entry_radius)*blend)
    half_bridge=centre+math.sqrt(2)*radius-roof
    def mix(a,b):
        return a*(1-blend)+b*blend
    end=(mix(radius*math.cos(math.radians(75)),half_bridge),
         mix(centre+radius*math.sin(math.radians(75)),roof))
    mid=(mix(radius*.5,(shoulder+half_bridge)/2),
         mix(centre+radius*math.sqrt(3)/2,(centre+shoulder+roof)/2))
    apex=(0,mix(centre+radius,roof))
    return (cq.Workplane("YZ",origin=(x,0,0))
            .moveTo(-shoulder,centre+shoulder)
            .threePointArc((0,bottom),(shoulder,centre+shoulder))
            .threePointArc(mid,end)
            .threePointArc(apex,(-end[0],end[1]))
            .threePointArc((-mid[0],mid[1]),(-shoulder,centre+shoulder))
            .close().val())


def _cut_passage(d):
    half=d.length/2
    xs=([-half-.6,-half,-half+1,-half+2,-half+3,-half+4]+
        [-half+5+i*((d.length-10)/26) for i in range(27)]+
        [half-4,half-3,half-2,half-1,half,half+.6])
    xs=sorted(set(round(x,4) for x in xs))
    return cq.Solid.makeLoft([_passage_wire(x,_roof_blend(x,d),d) for x in xs],
                             ruled=True)


def _window_cutter(x,d):
    left,right=x-d.window_width/2,x+d.window_width/2
    outline=[(left,floor_z(left,d)+d.window_bottom_offset),
             (right,floor_z(right,d)+d.window_bottom_offset),
             (right,floor_z(right,d)+d.window_shoulder_offset),
             (x,floor_z(x,d)+d.window_apex_offset),
             (left,floor_z(left,d)+d.window_shoulder_offset)]
    return (cq.Workplane("XZ",origin=(0,-17,0)).polyline(outline)
            .close().extrude(-6).val())


def ports(d=Downhill()):
    half=2*DUPLO.pitch
    return (Port("high_west",(-half,0,d.low_floor+d.drop),(-1.,0.,0.),d.entry_radius),
            Port("low_east",(half,0,d.low_floor),(1.,0.,0.),d.entry_radius))


def ball_positions(d=Downhill(),count=33,diameter=BALL_TRACK.ball_diameter):
    radius=diameter/2
    for i in range(count):
        x=-d.length/2+d.length*i/(count-1)
        yield cq.Vector(x,0,floor_z(x,d)+radius*math.sqrt(1+floor_slope(x,d)**2)+.18)


def sampled_ball_intersections(shape,d=Downhill(),count=33):
    radius=BALL_TRACK.ball_diameter/2
    return [intersection(shape,cq.Solid.makeSphere(
        radius,point,angleDegrees1=-90))
        for point in ball_positions(d,count)]
