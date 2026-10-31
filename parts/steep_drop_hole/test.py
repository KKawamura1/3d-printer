"""Targeted S01-V5 roofed steep-drop CAD tests; no slicing/dynamics guarantee."""
import unittest
import cadquery as cq
from brickcad.ports import mate, straight_ports
from brickcad.standards import BALL_TRACK
from brickcad.verify import VOLUME_TOL, intersection
from parts.steep_drop_hole.design import (
    PART_ID, SteepDrop, build_steep_drop, ports, sampled_ball_collisions,
    continuous_ball_path_intersections, ramp_normal_clearance, rolling_ball_path,
)


class SteepDropHoleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = SteepDrop()
        cls.shape, cls.p = build_steep_drop(cls.d)

    def test_dimensions_and_enclosed_roof(self):
        self.assertEqual(PART_ID, "S01-V5")
        self.assertEqual((self.p.nx, self.p.ny), (2, 2))
        self.assertAlmostEqual(self.p.height, 57.6)
        self.assertTrue(self.shape.isValid())
        self.assertEqual(len(self.shape.Solids()), 1)
        self.assertTrue(self.shape.isInside(
            cq.Vector(self.d.shaft_x, 0, self.p.height - .1)))
        self.assertLess(self.d.high_centre_z + self.d.section_radius,
                        self.p.height - self.d.roof_thickness)
        self.assertTrue(all(self.shape.isInside(
            cq.Vector(x + 3.9, y, self.p.height + 1.))
            for x, y in self.p.studs()))

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
        self.assertLess(max(continuous_ball_path_intersections(
            self.shape, self.d)), VOLUME_TOL)

    def test_downhill_ramp_and_clearance_at_real_ball_size(self):
        d = self.d
        path = rolling_ball_path(d)
        self.assertGreater(d.ramp_grade, 0)
        self.assertAlmostEqual(d.ramp_grade, .65)
        self.assertAlmostEqual(d.ramp_end_x, 13.)
        self.assertAlmostEqual(path[2].z - path[3].z, 9.75)
        self.assertAlmostEqual(
            d.drop - d.ramp_grade * (d.ramp_end_x - d.ramp_start_x), 1.)
        self.assertGreater(d.ramp_grade, .6)
        self.assertAlmostEqual(path[-1].z, d.low_centre_z)
        self.assertAlmostEqual(path[3].z, d.low_centre_z + ramp_normal_clearance(d))
        # The landing zone is no longer a flat empty pit.
        self.assertTrue(self.shape.isInside(cq.Vector(d.shaft_x, 0, d.low_floor + 1.)))
        self.assertFalse(self.shape.isInside(cq.Vector(
            d.shaft_x, 0, d.low_floor +
            d.ramp_grade * (d.ramp_end_x - d.shaft_x) + 1.)))
        self.assertFalse(self.shape.isInside(cq.Vector(
            d.ramp_end_x, 0, d.low_floor + .2)))
        # Whole-sphere tests along the ramp protect against overhead clipping.
        self.assertLess(max(sampled_ball_collisions(self.shape, d)), VOLUME_TOL)
        self.assertLess(max(continuous_ball_path_intersections(self.shape, d)),
                        VOLUME_TOL)

    def test_negative_control_oversized_ball(self):
        ball = cq.Solid.makeSphere(
            14., cq.Vector(self.d.shaft_x, 0, 26.),
            angleDegrees1=-90)
        self.assertGreater(intersection(self.shape, ball), VOLUME_TOL)


if __name__ == "__main__":
    unittest.main()
