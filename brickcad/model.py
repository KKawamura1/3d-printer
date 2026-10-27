"""Millimetre, Z-up BRep model. Bottom rim z=0; studs on +Z."""
from dataclasses import dataclass, asdict
import math
import cadquery as cq
from .connections import make_receiver, make_studs
from .standards import FAMILIES, fit_profile


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

    fit_profile_id: str | None = None
    body_offset_xy: tuple[float, float] = (0., 0.)
    receiver_inset_xy: tuple[float, float] | None = None

    def __post_init__(self):
        if any(type(n) is not int or not 2 <= n <= 12 for n in (self.nx, self.ny)):
            raise ValueError('This model supports rectangular bricks with 2..12 studs on each axis')
        if self.family not in ("lego", "duplo"):
            raise ValueError("Unknown brick family")
        vals = {k:v for k,v in asdict(self).items() if k not in ("family", "fit_profile_id", "body_offset_xy", "receiver_inset_xy")}
        if self.body_offset_xy is None:
            raise ValueError('Body offsets require two finite numbers')
        for key in ('body_offset_xy', 'receiver_inset_xy'):
            pair = getattr(self, key)
            if pair is not None and (len(pair) != 2 or not all(math.isfinite(v) for v in pair)):
                raise ValueError('XY dimensions require two finite numbers')
            if pair is not None:
                object.__setattr__(self, key, tuple(pair))
        if self.fit_profile_id is not None and fit_profile(self.fit_profile_id).family != self.family:
            raise ValueError('Fit profile and brick family differ')
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
        if min(self.cavity_xy) <= 0 or any(c >= b-1.6 for c,b in zip(self.cavity_xy,(self.width,self.depth))):
            raise ValueError('Receiver must be open with at least 0.8 mm side walls')
        if self.receiver_inset_xy is not None and any(
                span/2 <= (n-2)*self.pitch/2+self.tube_radius-self.clearance
                for span,n in zip(self.cavity_xy,(self.nx,self.ny))):
            raise ValueError('Receiver tubes extend beyond the cavity')
        if self.tube_radius - self.clearance >= self.pitch / 2:
            raise ValueError('Tubes overlap')
        if any(self.stud_radius-self.clearance >= (span-(n-1)*self.pitch)/2
               for span,n in zip((self.width,self.depth),(self.nx,self.ny))):
            raise ValueError('Stud extends beyond body')

    @property
    def width(self): return self.nx * self.pitch - self.body_gap + self.body_offset_xy[0]

    @property
    def depth(self): return self.ny * self.pitch - self.body_gap + self.body_offset_xy[1]

    @property
    def cavity_xy(self):
        if self.receiver_inset_xy is not None:
            return tuple(n*self.pitch-2*(inset-self.clearance)
                         for n,inset in zip((self.nx,self.ny),self.receiver_inset_xy))
        return tuple(d-2*(self.wall-self.clearance) for d in (self.width,self.depth))

    def studs(self):
        return [((i-(self.nx-1)/2)*self.pitch, (j-(self.ny-1)/2)*self.pitch)
                for i in range(self.nx) for j in range(self.ny)]

    def tubes(self):
        return [((i-(self.nx-2)/2)*self.pitch, (j-(self.ny-2)/2)*self.pitch)
                for i in range(self.nx-1) for j in range(self.ny-1)]


def receiver(p, outer, cavity_height, entry=0.0, footprint=None):
    """Shared open underside; roof and track above it are supplied by the caller."""
    # Legacy footprint overrides remain available to archived experiments.
    # Explicit receiver insets are independent of the body's outside dimensions.
    opening = p.cavity_xy
    if footprint is not None and p.receiver_inset_xy is None:
        opening = tuple(d-2*(p.wall-p.clearance) for d in footprint)
    return make_receiver(outer, p.tubes(), opening, cavity_height,
                         p.tube_radius-p.clearance, p.tube_inner_radius, entry)


def build(p=Brick(), *, corner_radius=0., stud_lip_radius=0., entry=0.):
    outer = cq.Workplane('XY').box(p.width, p.depth, p.height, centered=(True, True, False))
    if corner_radius:
        outer = outer.edges('|Z').fillet(corner_radius).edges('>Z').fillet(corner_radius)
    result = receiver(p, outer, p.height-p.roof, entry)
    studs = make_studs(p.studs(), p.height, p.stud_radius-p.clearance,
                       p.stud_inner_radius, p.stud_height, stud_lip_radius)
    result = result.union(studs)
    shape = result.val().clean()
    if not shape.isValid() or len(shape.Solids()) != 1:
        raise ValueError('CAD result must be one valid connected solid')
    return shape


def nominal_brick(family="lego", nx=4, ny=2):
    """Independent family baseline. DUPLO details are not a uniform 2x scale."""
    if family not in FAMILIES:
        raise ValueError("Unknown brick family")
    standard = FAMILIES[family]
    fit = fit_profile(f'{family}-nominal-v1')
    # Keep the historical mutable wall/clearance API for archived trials.
    return Brick(family=family, nx=nx, ny=ny, pitch=standard.pitch,
                 body_gap=standard.body_gap, height=standard.height,
                 stud_height=standard.stud_height, roof=standard.roof,
                 stud_radius=fit.stud_radius, stud_inner_radius=fit.stud_inner_radius,
                 tube_radius=fit.tube_radius, tube_inner_radius=fit.tube_inner_radius,
                 wall=round(fit.receiver_inset_xy[0]-standard.body_gap/2, 10))


def brick_from_fit(profile_id, nx=4, ny=2, height_units=1, **overrides):
    """New parts choose a version explicitly; dimensions are resolved at build time.

    Body offsets do not move the grid or receiver. Explicit overrides are saved
    alongside the version ID, which denotes a baseline rather than validation.
    """
    from dataclasses import replace
    fit = fit_profile(profile_id)
    if type(height_units) is not int or height_units < 1:
        raise ValueError('height_units must be a positive integer')
    base = nominal_brick(fit.family, nx, ny)
    values = dict(fit_profile_id=profile_id, stud_radius=fit.stud_radius,
                  stud_inner_radius=fit.stud_inner_radius, tube_radius=fit.tube_radius,
                  tube_inner_radius=fit.tube_inner_radius,
                  wall=round(fit.receiver_inset_xy[0]-base.body_gap/2, 10),
                  receiver_inset_xy=fit.receiver_inset_xy, height=base.height*height_units)
    values.update(overrides)
    return replace(base, **values)


def from_profile(values):
    """Start from the correct family preset before applying explicit overrides."""
    from dataclasses import replace
    if values.get('fit_profile_id') is not None:
        values = dict(values)
        profile_id = values.pop('fit_profile_id')
        return brick_from_fit(profile_id, **values)
    return replace(nominal_brick(values.get("family", "lego")), **values)


