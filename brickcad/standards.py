"""Versioned design inputs, independent of CAD and of printer compensation.

Existing versions reproduce historical designs; none is a universal fit winner.
All lengths are millimetres. Add a new ID when adopting different dimensions.
"""
from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class FamilyStandard:
    id: str
    family: str
    pitch: float
    height: float
    body_gap: float
    stud_height: float
    roof: float


LEGO = FamilyStandard('lego-grid-v1', 'lego', 8., 9.6, .2, 1.8, 1.2)
DUPLO = FamilyStandard('duplo-grid-v1', 'duplo', 16., 19.2, .2, 4.5, 1.6)
FAMILIES = MappingProxyType({s.family: s for s in (LEGO, DUPLO)})


@dataclass(frozen=True)
class FitProfile:
    id: str
    family: str
    stud_radius: float
    stud_inner_radius: float
    tube_radius: float
    tube_inner_radius: float
    # Distance from the virtual cell boundary to the receiver's inner faces.
    # It stays fixed when the OUTSIDE body dimensions are compensated.
    receiver_inset_xy: tuple[float, float]
    evidence: str


FIT_PROFILES = MappingProxyType({p.id: p for p in (
    FitProfile('lego-nominal-v1', 'lego', 2.4, 0., 3.25, 2.4, (1.6, 1.6),
               'Synthetic nominal reference; docs/design.md'),
    FitProfile('duplo-nominal-v1', 'duplo', 4.7, 3.25, 6.55, 4.7, (3.3, 3.3),
               'Synthetic nominal reference; docs/duplo.md'),
    FitProfile('duplo-rail-trial-v1', 'duplo', 4.6, 3.25, 6.65, 4.7, (3.26, 3.26),
               'Historical rail/tunnel trial; not a calibrated universal fit'),
    FitProfile('duplo-straight-rail-trial-v1', 'duplo', 4.6, 3.25, 6.65, 4.7, (3.185, 3.26),
               'Historical straight rail: measured body width also changed X cavity; preserved'),
    FitProfile('duplo-curve-trial-v1', 'duplo', 4.6, 3.25, 6.75, 4.7, (3.3, 3.3),
               'PR14 ID03 receiver on the clipped curve; transfer unvalidated'),
    FitProfile('duplo-xy-trial-v1', 'duplo', 4.7, 3.2, 6.75, 4.7, (3.3, 3.3),
               'PR14 ID03 receiver + stud trial; combined transfer unvalidated'),
)})


def fit_profile(profile_id):
    try:
        return FIT_PROFILES[profile_id]
    except KeyError:
        raise ValueError(f'Unknown fit profile: {profile_id!r}') from None


@dataclass(frozen=True)
class ChannelStandard:
    id: str
    ball_diameter: float
    width: float
    height: float
    opening: float
    floor: float

    @property
    def radius(self):
        depth = self.height-self.floor
        return ((self.opening/2)**2+depth**2)/(2*depth)


BALL_TRACK = ChannelStandard('duplo-ball-track-v1', 24.26, 31.65, 19.13, 25.74, 6.35)


@dataclass(frozen=True)
class EdgeFinish:
    id: str
    corner_radius: float
    stud_lip_radius: float
    receiver_entry: float


ROUNDED_EDGES = EdgeFinish('duplo-rounded-v1', .8, .5, .3)
