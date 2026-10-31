"""S03-V2: regression checks based on verified S01-V5 / S02-V8 datums.

CAD clearance is geometric only; this does not validate real rolling or slicing.
"""
import unittest

import cadquery as cq
from brickcad.ports import mate, straight_ports
from brickcad.standards import BALL_TRACK, DUPLO
from brickcad.verify import VOLUME_TOL, intersection
from parts.steep_sharp_tunnel_left.design import (
    PART_ID, SOURCE_CURVE_ID, SOURCE_DROP_ID, SHAFT_X,
    SteepDrop, build_tunnel, ball_path_collisions,
    swept_ball_path_collisions, ports,
)


class Geometry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = SteepDrop(shaft_x=SHAFT_X)
        cls.shape, cls.p = build_tunnel(cls.d)

    def test_revision_enclosed_top_and_studs(self):
        self.assertEqual((PART_ID, SOURCE_CURVE_ID, SOURCE_DROP_ID),
                         ("S03-V2", "C01-V5", "S01-V5"))
        self.assertTrue(self.shape.isValid())
        self.assertEqual(len(self.shape.Solids()), 1)
        self.assertEqual((self.p.nx, self.p.ny), (2, 2))
        self.assertAlmostEqual(self.p.height, 3 * DUPLO.height)
        self.assertTrue(self.shape.isInside(
            cq.Vector(0., 0., self.p.height - .1)))
        for x, y in self.p.studs():
            self.assertTrue(self.shape.isInside(
                cq.Vector(x + 3.9, y, self.p.height + 1)))

    def test_left_turn_ports_mate_and_height(self):
        high, low = ports(self.d)
        self.assertEqual(high.floor_xyz_mm, (-16., 0., 25.55))
        self.assertEqual(low.floor_xyz_mm, (0., 16., 6.35))
        self.assertEqual(low.outward, (0., 1., 0.))
        self.assertAlmostEqual(
            high.floor_xyz_mm[2] - low.floor_xyz_mm[2], DUPLO.height)
        west, east = straight_ports(2, BALL_TRACK.floor, BALL_TRACK.radius)
        self.assertTrue(mate(
            east.placed((-32., 0., DUPLO.height)), high)["compatible"])
        self.assertTrue(mate(
            low, west.placed((0., 32., 0.), 90))["compatible"])

    def test_walls_receiver_and_ramp_floor(self):
        self.assertTrue(self.shape.isInside(
            cq.Vector(-15.7, 0., self.d.low_centre_z)))
        self.assertFalse(self.shape.isInside(cq.Vector(0., 0., 1.)))
        self.assertTrue(self.shape.isInside(cq.Vector(3.89, 3.89, 1.)))
        self.assertTrue(self.shape.isInside(cq.Vector(0., 0., 6.2)))
        self.assertTrue(self.shape.isInside(
            cq.Vector(0., 0., self.d.low_floor + 1.)))
        self.assertFalse(self.shape.isInside(cq.Vector(
            0., 0., self.d.low_floor +
            self.d.ramp_grade * self.d.ramp_end_x + 1.)))

    def test_clearance_and_oversize_negative_control(self):
        self.assertLess(max(ball_path_collisions(self.shape, self.d)),
                        VOLUME_TOL)
        self.assertLess(max(swept_ball_path_collisions(self.shape, self.d)),
                        VOLUME_TOL)
        ball = cq.Solid.makeSphere(
            14., cq.Vector(0., 0., 26.), angleDegrees1=-90)
        self.assertGreater(intersection(self.shape, ball), VOLUME_TOL)

    def test_grade_follows_s01_s02(self):
        self.assertAlmostEqual(self.d.ramp_grade, .65)
        self.assertAlmostEqual(
            self.d.ramp_grade * (self.d.ramp_end_x - SHAFT_X), 8.45)
        self.assertGreater(
            self.d.drop - self.d.ramp_grade *
            (self.d.ramp_end_x - self.d.ramp_start_x), .99)


if __name__ == "__main__":
    unittest.main()
