"""Millimetre, Z-up BRep model. Bottom rim z=0; studs on +Z."""
from dataclasses import dataclass, asdict
import math
import cadquery as cq


@dataclass(frozen=True)
class Brick:
    family: str = "lego"
    nx: int = 4
    ny: int = 2
    pitch: float = 8.0
    body_gap: float = 0.2  # total gap between neighbouring bodies
    height: float = 9.6
    stud_radius: float = 2.4
    stud_height: float = 1.8
    stud_inner_radius: float = 0.0  # 0 = solid stud; >0 = hollow stud with closed roof below
    wall: float = 1.5
    roof: float = 1.2
    tube_radius: float = 3.25
    tube_inner_radius: float = 2.4
    clearance: float = 0.0  # radial: shrink studs AND enlarge receiver space

    def __post_init__(self):
        if any(type(n) is not int or not 2 <= n <= 12 for n in (self.nx, self.ny)):
            raise ValueError('This model supports rectangular bricks with 2..12 studs on each axis')
        if self.family not in ("lego", "duplo"):
            raise ValueError("Unknown brick family")
        vals = {k:v for k,v in asdict(self).items() if k != "family"}
        if any(not math.isfinite(v) for v in vals.values()):
            raise ValueError('All dimensions must be finite')
        for key in ('pitch', 'height', 'stud_radius', 'stud_height', 'wall', 'roof', 'tube_radius', 'tube_inner_radius'):
            if vals[key] <= 0:
                raise ValueError(f'{key} must be positive')
        if self.stud_inner_radius < 0 or (self.stud_inner_radius and self.stud_radius-self.clearance-self.stud_inner_radius < 0.8):
            raise ValueError('Hollow stud requires at least 0.8 mm wall')
        if not 0 <= self.body_gap < self.pitch:
            raise ValueError('Invalid body gap')
        if not -0.10 <= self.clearance <= 0.20:
            raise ValueError('Supported radial clearance is -0.10..0.20 mm')
        if not 0 < self.roof < self.height - self.stud_height:
            raise ValueError('Roof leaves insufficient insertion depth')
        if self.wall - self.clearance < 0.8:
            raise ValueError('Effective side wall below 0.8 mm')
        if self.tube_radius - self.clearance - self.tube_inner_radius < 0.6:
            raise ValueError('Effective tube wall below 0.6 mm')
        if not 0 < self.stud_radius - self.clearance < self.pitch / 2:
            raise ValueError('Invalid effective stud radius')
        if self.wall >= min(self.width, self.depth) / 2:
            raise ValueError('Cavity is closed')
        if self.tube_radius - self.clearance >= self.pitch / 2:
            raise ValueError('Tubes overlap')
        if self.stud_radius - self.clearance >= (self.pitch-self.body_gap)/2:
            raise ValueError('Stud extends beyond body')

    @property
    def width(self): return self.nx * self.pitch - self.body_gap

    @property
    def depth(self): return self.ny * self.pitch - self.body_gap

    def studs(self):
        return [((i-(self.nx-1)/2)*self.pitch, (j-(self.ny-1)/2)*self.pitch)
                for i in range(self.nx) for j in range(self.ny)]

    def tubes(self):
        return [((i-(self.nx-2)/2)*self.pitch, (j-(self.ny-2)/2)*self.pitch)
                for i in range(self.nx-1) for j in range(self.ny-1)]


def build(p=Brick()):
    outer = cq.Workplane('XY').box(p.width, p.depth, p.height, centered=(True, True, False))
    # Cavity open through the bottom; tube tops are fused to the roof.
    cavity = cq.Workplane('XY').box(p.width-2*(p.wall-p.clearance),
                                  p.depth-2*(p.wall-p.clearance), p.height-p.roof,
                                  centered=(True, True, False))
    result = outer.cut(cavity)
    studs = cq.Workplane('XY', origin=(0, 0, p.height)).pushPoints(p.studs()).circle(p.stud_radius-p.clearance)
    if p.stud_inner_radius:
        studs = studs.circle(p.stud_inner_radius)
    studs = studs.extrude(p.stud_height)
    result = result.union(studs)
    for x, y in p.tubes():
        tube = (cq.Workplane('XY', origin=(x, y, 0)).circle(p.tube_radius-p.clearance)
                .circle(p.tube_inner_radius).extrude(p.height-p.roof))
        result = result.union(tube)
    shape = result.val().clean()
    if not shape.isValid() or len(shape.Solids()) != 1:
        raise ValueError('CAD result must be one valid connected solid')
    return shape


def nominal_brick(family="lego", nx=4, ny=2):
    """Independent family baseline. DUPLO details are not a uniform 2x scale."""
    if family == "lego":
        return Brick(nx=nx, ny=ny)
    if family == "duplo":
        return Brick(family="duplo", nx=nx, ny=ny, pitch=16.0, body_gap=0.2,
                     height=19.2, stud_radius=4.7, stud_height=4.5,
                     stud_inner_radius=3.25, wall=3.2, roof=1.6,
                     tube_radius=6.55, tube_inner_radius=4.7)
    raise ValueError("Unknown brick family")


def from_profile(values):
    """Start from the correct family preset before applying explicit overrides."""
    from dataclasses import replace
    return replace(nominal_brick(values.get("family", "lego")), **values)
