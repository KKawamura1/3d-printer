"""C02R-V1 comparison: protect the proven lower C01 path, not just free space."""
import unittest

import cadquery as cq

from brickcad.standards import BALL_TRACK, DUPLO
from brickcad.verify import VOLUME_TOL
from parts.sharp_curve.design import SharpCurve, build_curve, ball_intersections
from experiments.c02_upper_relief.design import (
    PART_ID, RELIEF_CENTER_Z, RELIEF_RADIUS, build_relief,
)


class C02UpperReliefTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.curve = SharpCurve()
        cls.shape, cls.p = build_relief(cls.curve)
        cls.open_shape, _ = build_curve(cls.curve)

    def test_body_and_ball_clearance(self):
        self.assertEqual(PART_ID, "C02R-V1")
        self.assertEqual((self.p.nx, self.p.ny), (2, 2))
        self.assertAlmostEqual(self.p.height, 2 * DUPLO.height)
        self.assertTrue(self.shape.isValid())
        self.assertEqual(len(self.shape.Solids()), 1)
        self.assertLess(
            max(ball_intersections(self.shape, self.curve, samples=19)),
            VOLUME_TOL)
        self.assertGreater(
            max(ball_intersections(self.shape, self.curve, diameter=28., samples=5)),
            VOLUME_TOL)

    def test_c01_groove_bottom_is_unchanged(self):
        # At all x,y in the sample grid and z<8.5, the smooth extra relief
        # cannot cut into C01's original open-rail channel or receiver.
        self.assertAlmostEqual(RELIEF_CENTER_Z - RELIEF_RADIUS, 8.5)
        for x in (-12., -8., -4., 0., 4., 8., 12.):
            for y in (-12., -8., -4., 0., 4., 8., 12.):
                for z in (6.5, 7.0, 8.0):
                    pt = cq.Vector(x, y, z)
                    self.assertEqual(
                        self.shape.isInside(pt),
                        self.open_shape.isInside(pt),
                        (x, y, z))

    def test_tunnel_extra_relief_and_protected_walls(self):
        self.assertFalse(self.shape.isInside(cq.Vector(0, 12.5, 20)))
        self.assertFalse(self.shape.isInside(cq.Vector(12.5, 0, 20)))
        self.assertTrue(self.shape.isInside(cq.Vector(0, 14.2, 20)))
        self.assertTrue(self.shape.isInside(cq.Vector(14.2, 0, 20)))
        self.assertTrue(self.shape.isInside(cq.Vector(0, 0, 37.4)))
        self.assertTrue(self.shape.isInside(cq.Vector(-15.8, 0, 33)))
        self.assertTrue(self.shape.isInside(cq.Vector(0, -15.8, 33)))

    def test_studs_and_receiver(self):
        for x, y in self.p.studs():
            self.assertTrue(self.shape.isInside(cq.Vector(x, y, 38.3)))
            self.assertFalse(self.shape.isInside(cq.Vector(x, y, 41.)))
            self.assertTrue(self.shape.isInside(cq.Vector(x + 4., y, 41.)))
        self.assertFalse(self.shape.isInside(cq.Vector(0, 0, 1)))
        self.assertTrue(self.shape.isInside(cq.Vector(4, 4, 1)))


if __name__ == "__main__":
    unittest.main()
