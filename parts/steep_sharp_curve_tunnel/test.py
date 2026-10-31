"""S02-V8: check the two-source 90-degree steep drop tunnel."""
import unittest
import cadquery as cq

from brickcad.ports import mate, straight_ports
from brickcad.standards import BALL_TRACK, DUPLO
from brickcad.verify import VOLUME_TOL, intersection
from parts.steep_sharp_curve_tunnel.design import (
    PART_ID, SOURCE_CURVE_ID, SOURCE_DROP_ID, SHAFT_X,
    build_tunnel, ball_path_collisions, swept_ball_path_collisions, ports,
)
from parts.steep_drop_hole.design import SteepDrop


class SteepSharpCurveTunnelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = SteepDrop(shaft_x=SHAFT_X)
        cls.shape, cls.p = build_tunnel(cls.d)

    def test_grid_roof_studs_and_revision(self):
        self.assertEqual((PART_ID, SOURCE_CURVE_ID, SOURCE_DROP_ID),
                         ("S02-V8", "C01-V5", "S01-V5"))
        self.assertEqual((self.p.nx, self.p.ny), (2, 2))
        self.assertAlmostEqual(self.p.height, 3 * DUPLO.height)
        self.assertTrue(self.shape.isValid())
        self.assertEqual(len(self.shape.Solids()), 1)
        self.assertTrue(self.shape.isInside(
            cq.Vector(0, 0, self.p.height - .1)))
        self.assertTrue(all(self.shape.isInside(
            cq.Vector(x + 3.9, y, self.p.height + 1))
            for x, y in self.p.studs()))

    def test_orthogonal_ports_and_drop(self):
        high, low = ports(self.d)
        for actual, expected in zip(high.floor_xyz_mm, (-16., 0., 25.55)):
            self.assertAlmostEqual(actual, expected)
        for actual, expected in zip(low.floor_xyz_mm, (0., -16., 6.35)):
            self.assertAlmostEqual(actual, expected)
        self.assertAlmostEqual(high.floor_xyz_mm[2] -
                               low.floor_xyz_mm[2], 19.2)
        incoming = straight_ports(2, BALL_TRACK.floor,
                                  BALL_TRACK.radius)[1].placed(
                                      (-32., 0., DUPLO.height))
        outgoing = straight_ports(2, BALL_TRACK.floor,
                                  BALL_TRACK.radius)[0].placed(
                                      (0., -32., 0.), -90)
        self.assertTrue(mate(incoming, high)["compatible"])
        self.assertTrue(mate(low, outgoing)["compatible"])

    def test_no_extra_openings_and_receiver(self):
        self.assertTrue(self.shape.isInside(
            cq.Vector(-15.7, 0., self.d.low_centre_z)))
        self.assertTrue(self.shape.isInside(cq.Vector(0., 0., 6.2)))
        self.assertFalse(self.shape.isInside(cq.Vector(0., 0., 1.)))
        self.assertTrue(self.shape.isInside(cq.Vector(3.89, 3.89, 1.)))

    def test_ball_clearance_continuous(self):
        self.assertLess(max(ball_path_collisions(self.shape, self.d)),
                        VOLUME_TOL)
        self.assertLess(max(swept_ball_path_collisions(self.shape, self.d)),
                        VOLUME_TOL)

    def test_steep_ramp_matches_s01_v5(self):
        # The source part is 33 degrees; the 2x2 rotated exit has a
        # 13mm run-out from the centered shaft (8.45mm vertical change).
        d = self.d
        self.assertAlmostEqual(d.ramp_grade, .65)
        self.assertAlmostEqual(d.ramp_grade * (d.ramp_end_x - SHAFT_X), 8.45)
        self.assertAlmostEqual(
            d.drop - d.ramp_grade * (d.ramp_end_x - d.ramp_start_x), 1.)
        self.assertTrue(self.shape.isInside(
            cq.Vector(0, 0, d.low_floor + 1.)))
        self.assertFalse(self.shape.isInside(
            cq.Vector(0, 0, d.low_floor + 8.45 + 1.)))
        self.assertFalse(self.shape.isInside(
            cq.Vector(0, -d.ramp_end_x, d.low_floor + .2)))
        # Validate the whole ball on both the steep slope and its transition.
        self.assertLess(max(swept_ball_path_collisions(self.shape, d)),
                        VOLUME_TOL)

    def test_oversized_ball_is_blocked(self):
        oversize = cq.Solid.makeSphere(
            14., cq.Vector(0., 0., 26.), angleDegrees1=-90)
        self.assertGreater(intersection(self.shape, oversize), VOLUME_TOL)


if __name__ == "__main__":
    unittest.main()
