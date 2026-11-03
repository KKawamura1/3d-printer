"""Issue #60 regression checks for the SC03/SC05 shared R48 open downhill."""
import inspect
import json
import math
from pathlib import Path
import unittest
import cadquery as cq
from brickcad.verify import intersection, VOLUME_TOL
from brickcad.marking import engrave_west
from parts.tunnel.e31_fit import SLOT_END_Z, SLOT_END_RADIUS, BEAD_MINOR_RADIUS
from parts.sloped_curve_open_right.design import (
    PART_ID, MIRROR, LABEL_Z, DEPTH, DROP, LENGTH, build_part,
    verify, path, ports, xy, height, loft,
)


class Geometry(unittest.TestCase):
    def test_continuous_clearance_and_support(self):
        shape, params = build_part()
        checks, _ = verify(shape, params)
        self.assertTrue(all(checks.values()), checks)
        centres = path()
        oversize = cq.Solid.makeSphere(
            14., centres[len(centres)//2], angleDegrees1=-90)
        self.assertGreater(intersection(shape, oversize), VOLUME_TOL)
        for fraction in (.15, .35, .65, .85):
            s = LENGTH*fraction
            x, y, _, _ = xy(s)
            self.assertTrue(shape.isInside(
                cq.Vector(x, -y if MIRROR else y, height(s)-.15)),
                "missing track floor at s="+str(s))

    def test_cut_tube_support_and_shortened_slots(self):
        shape, params = build_part()
        footprint = loft('mask').intersect(
            cq.Workplane('XY').box(
                params.width, params.depth, 100,
                centered=(True, True, False)).val())
        if MIRROR:
            footprint = footprint.mirror('XZ')
        for x, y in params.tubes():
            ring = (cq.Workplane('XY', origin=(x, y, .8))
                    .circle(params.tube_radius)
                    .circle(params.tube_inner_radius).extrude(.5).val())
            trimmed = ring.intersect(footprint)
            if 1. < trimmed.Volume() < ring.Volume()-1.:
                self.assertGreater(intersection(shape, trimmed),
                                   .55*trimmed.Volume(), (x, y))
        # PR58 B: the rounded end must stay below the underside ceiling.
        self.assertAlmostEqual(SLOT_END_Z, 3.50)
        self.assertAlmostEqual(SLOT_END_RADIUS, .65)
        self.assertGreater(DEPTH - (SLOT_END_Z + SLOT_END_RADIUS), .59)

    def test_standard_engraving_is_recessed_on_final_face(self):
        shape, params = build_part()
        unmarked, _ = build_part(label=None)
        sig = inspect.signature(engrave_west).parameters
        size, depth = sig['size'].default, sig['depth'].default
        self.assertEqual(size, 3.)
        self.assertEqual(depth, .4)
        self.assertGreater(LABEL_Z - size/2, 6.35)
        self.assertEqual(
            PART_ID, json.loads(
                (Path(__file__).parent/'cad-build.json').read_text())['version'])
        _, y, _, _ = xy(0)
        if MIRROR:
            y = -y
        plane = cq.Plane(
            origin=(-params.width/2 + depth, y, LABEL_Z),
            xDir=(0, -1, 0), normal=(-1, 0, 0))
        cutter = (cq.Workplane(plane)
                  .text(PART_ID, size, depth+.05,
                        font='DejaVu Sans', kind='bold', combine=False).val())
        self.assertGreater(cutter.Volume(), 1.)
        self.assertGreater(intersection(unmarked, cutter), .2)
        self.assertLess(intersection(shape, cutter), .10)
        self.assertGreater(unmarked.Volume()-shape.Volume(), .2)

    def test_mirror_unmarked_before_engraving(self):
        original, _ = build_part(label=None, mirror=False)
        reflected, _ = build_part(label=None, mirror=True)
        expected = original.mirror('XZ')
        self.assertTrue(reflected.isValid())
        self.assertAlmostEqual(reflected.Volume(), expected.Volume(), delta=.01)
        self.assertLess(
            reflected.cut(expected).Volume()+expected.cut(reflected).Volume(),
            .05)
        for a, b in zip(path(mirror=False), path(mirror=True)):
            self.assertAlmostEqual(a.x, b.x)
            self.assertAlmostEqual(a.y, -b.y)
            self.assertAlmostEqual(a.z, b.z)
        for a, b in zip(ports(mirror=False), ports(mirror=True)):
            self.assertAlmostEqual(a.floor_xyz_mm[0], b.floor_xyz_mm[0])
            self.assertAlmostEqual(a.floor_xyz_mm[1], -b.floor_xyz_mm[1])
            self.assertAlmostEqual(a.floor_xyz_mm[2], b.floor_xyz_mm[2])

    def test_port_drop(self):
        self.assertAlmostEqual(
            ports()[0].floor_xyz_mm[2]-ports()[1].floor_xyz_mm[2], DROP)
