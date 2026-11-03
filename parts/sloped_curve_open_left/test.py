"""Left side is generated from SC03's unmarked CAD, then marked independently."""
import inspect
import json
import unittest
from pathlib import Path
import cadquery as cq
from brickcad.verify import intersection, VOLUME_TOL
from brickcad.marking import engrave_west
from parts.sloped_curve_open_right import design as right
from parts.sloped_curve_open_left import design as left


class Geometry(unittest.TestCase):
    def test_shared_version_and_exact_unmarked_reflection(self):
        self.assertEqual(left.SOURCE_VERSION, right.PART_ID)
        right_solid, _ = right.build_part(label=None)
        left_solid, _ = left.build_part(label=None)
        expected = right_solid.mirror('XZ')
        self.assertTrue(left_solid.isValid())
        self.assertAlmostEqual(left_solid.Volume(), expected.Volume(), delta=.01)
        self.assertLess(
            left_solid.cut(expected).Volume()+expected.cut(left_solid).Volume(),
            .05)

    def test_left_path_ports_clearance_and_floor(self):
        shape, params = left.build_part()
        checks, _ = left.verify(shape, params)
        self.assertTrue(all(checks.values()), checks)
        for a, b in zip(right.path(), left.path()):
            self.assertAlmostEqual(a.x, b.x)
            self.assertAlmostEqual(a.y, -b.y)
            self.assertAlmostEqual(a.z, b.z)
        for a, b in zip(right.ports(), left.ports()):
            self.assertAlmostEqual(a.floor_xyz_mm[0], b.floor_xyz_mm[0])
            self.assertAlmostEqual(a.floor_xyz_mm[1], -b.floor_xyz_mm[1])
            self.assertAlmostEqual(a.floor_xyz_mm[2], b.floor_xyz_mm[2])
        for fraction in (.15, .35, .65, .85):
            s = left.LENGTH*fraction
            x, y, _, _ = left.xy(s)
            self.assertTrue(shape.isInside(cq.Vector(x, y, left.height(s)-.15)))
        centres = left.path()
        oversize = cq.Solid.makeSphere(
            14., centres[len(centres)//2], angleDegrees1=-90)
        self.assertGreater(intersection(shape, oversize), VOLUME_TOL)

    def test_left_cut_support_and_final_readable_marking(self):
        shape, p = left.build_part()
        unmarked, _ = left.build_part(label=None)
        footprint = left.loft('mask').intersect(
            cq.Workplane('XY').box(
                p.width, p.depth, 100, centered=(True, True, False)).val())
        for x, y in p.tubes():
            ring = (cq.Workplane('XY', origin=(x, y, .8))
                    .circle(p.tube_radius).circle(p.tube_inner_radius)
                    .extrude(.5).val())
            trimmed = ring.intersect(footprint)
            if 1. < trimmed.Volume() < ring.Volume()-1.:
                self.assertGreater(intersection(shape, trimmed),
                                   .55*trimmed.Volume(), (x, y))
        params = inspect.signature(engrave_west).parameters
        size, depth = params['size'].default, params['depth'].default
        self.assertEqual((size, depth), (3., .4))
        self.assertEqual(left.PART_ID, json.loads(
            (Path(__file__).parent/'cad-build.json').read_text())['version'])
        _, y, _, _ = left.xy(0)
        plane = cq.Plane(
            origin=(-p.width/2+depth, y, left.LABEL_Z),
            xDir=(0, -1, 0), normal=(-1, 0, 0))
        cutter = (cq.Workplane(plane)
                  .text(left.PART_ID, size, depth+.05,
                        font='DejaVu Sans', kind='bold', combine=False).val())
        self.assertGreater(intersection(unmarked, cutter), .2)
        self.assertLess(intersection(shape, cutter), .10)
        self.assertGreater(unmarked.Volume()-shape.Volume(), .2)
