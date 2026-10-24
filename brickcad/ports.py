"""Minimal ball-path ports: mm, Z up, outward unit normals, DUPLO grid planes.

The point is the running-floor datum on the virtual cell boundary, not the
recessed physical mouth. These are geometric contracts, not fitted connectors.
"""
from dataclasses import dataclass, replace
import math


@dataclass(frozen=True)
class Port:
    name: str
    floor_xyz_mm: tuple[float, float, float]
    outward: tuple[float, float, float]
    section_radius_mm: float
    face_inset_mm: float = .1

    def __post_init__(self):
        if len(self.floor_xyz_mm) != 3 or len(self.outward) != 3:
            raise ValueError('Port vectors require three coordinates')
        values = (*self.floor_xyz_mm, *self.outward,
                  self.section_radius_mm, self.face_inset_mm)
        if not all(math.isfinite(v) for v in values):
            raise ValueError('Port dimensions must be finite')
        if self.section_radius_mm <= 0 or self.face_inset_mm < 0:
            raise ValueError('Invalid section radius or face inset')
        if not math.isclose(math.hypot(*self.outward), 1, abs_tol=1e-9):
            raise ValueError('Outward normal must have unit length')

    def placed(self, xyz=(0., 0., 0.), yaw_deg=0.):
        if len(xyz) != 3 or not all(math.isfinite(v) for v in (*xyz, yaw_deg)):
            raise ValueError('Placement must be finite XYZ and yaw')
        c, s = math.cos(math.radians(yaw_deg)), math.sin(math.radians(yaw_deg))
        def rotate(v):
            return (c*v[0]-s*v[1], s*v[0]+c*v[1], v[2])
        return replace(self, floor_xyz_mm=tuple(a+b for a,b in zip(rotate(self.floor_xyz_mm), xyz)),
                       outward=rotate(self.outward))


def straight_ports(length_cells, floor_mm, radius_mm):
    if not isinstance(length_cells, int) or length_cells < 1:
        raise ValueError('Length must be a positive integer of 16 mm cells')
    return tuple(Port(name, (sign*length_cells*8., 0., floor_mm),
                      (sign, 0., 0.), radius_mm)
                 for name, sign in [('left', -1.), ('right', 1.)])


def mate(a, b, tolerance_mm=1e-6):
    if not math.isfinite(tolerance_mm) or tolerance_mm < 0:
        raise ValueError('Tolerance must be finite and nonnegative')
    delta = math.dist(a.floor_xyz_mm, b.floor_xyz_mm)
    opposed = math.dist(a.outward, tuple(-v for v in b.outward)) < 1e-6
    same_section = abs(a.section_radius_mm-b.section_radius_mm) <= tolerance_mm
    return dict(compatible=delta <= tolerance_mm and opposed and same_section,
                datum_distance_mm=delta, normals_opposed=opposed,
                same_section=same_section, mouth_gap_mm=a.face_inset_mm+b.face_inset_mm)
