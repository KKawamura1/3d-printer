"""Targeted S01-V1 geometry tests; not a slicer or physical rolling test."""
import unittest
import cadquery as cq
from brickcad.ports import mate, straight_ports
from brickcad.standards import BALL_TRACK
from brickcad.verify import VOLUME_TOL, intersection
from parts.steep_drop_hole.design import (
    PART_ID, SteepDrop, build_steep_drop, ports, sampled_ball_collisions,
)


class SteepDropHoleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = SteepDrop()
        cls.shape, cls.p = build_steep_drop(cls.d)

    def test_dimensions_and_exposed_top(self):
        self.assertEqual(PART_ID, "S01-V1")
        self.assertEqual((self.p.nx, self.p.ny), (2, 2))
        self.assertAlmostEqual(self.p.height, 38.4)
        self.assertTrue(self.shape.isValid())
        self.assertEqual(len(self.shape.Solids()), 1)
        self.assertFalse(self.shape.isInside(
            cq.Vector(self.d.shaft_x, 0, self.p.height - .1)))
        self.assertAlmostEqual(self.d.high_centre_z +
                               self.d.section_radius - self.p.height,
                               12.8906338, delta=.05)

    def test_ports_match_horizontal_tracks_at_two_heights(self):
        high, low = ports(self.d)
        for actual, expected in zip(high.floor_xyz_mm, (-16., 0., 25.55)):
            self.assertAlmostEqual(actual, expected)
        for actual, expected in zip(low.floor_xyz_mm, (16., 0., 6.35)):
            self.assertAlmostEqual(actual, expected)
        left, right = straight_ports(2, BALL_TRACK.floor, BALL_TRACK.radius)
        self.assertTrue(mate(right.placed((-32., 0., 19.2)), high)["compatible"])
        self.assertTrue(mate(low, left.placed((32., 0., 0.)))["compatible"])

    def test_receiver_and_ball_clearance(self):
        self.assertAlmostEqual(self.p.tube_radius, 6.60)
        self.assertEqual(self.p.cavity_xy, (25.4, 25.4))
        self.assertTrue(self.shape.isInside(cq.Vector(0, 0, 6.2)))
        self.assertFalse(self.shape.isInside(cq.Vector(0, 0, 1.)))
        self.assertTrue(self.shape.isInside(cq.Vector(3.89, 3.89, 1.)))
        self.assertLess(max(sampled_ball_collisions(self.shape, self.d)),
                        VOLUME_TOL)

    def test_negative_control_oversized_ball(self):
        ball = cq.Solid.makeSphere(
            14., cq.Vector(self.d.shaft_x, 0, 26.),
            angleDegrees1=-90)
        self.assertGreater(intersection(self.shape, ball), VOLUME_TOL)


if __name__ == "__main__":
    unittest.main()
