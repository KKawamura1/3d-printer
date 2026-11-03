"""Regression tests for S03-V8's mirrored geometry and readable marking."""
import unittest

import cadquery as cq
from brickcad.ports import mate, straight_ports
from brickcad.marking import engrave
from parts.tunnel.e31_fit import SLOT_END_Z, SLOT_END_RADIUS
from brickcad.standards import BALL_TRACK, DUPLO
from brickcad.verify import VOLUME_TOL, intersection
from parts.steep_drop_hole.design import SteepDrop
from parts.steep_sharp_curve_tunnel import design as right
from parts.steep_sharp_tunnel_left.design import (
    PART_ID, SOURCE_RIGHT_ID, SOURCE_DROP_ID, SHAFT_X,
    build_tunnel, ports, circular_mouth_checks,
    ball_path_collisions, swept_ball_path_collisions,
)


class MirroredSteepSharpTunnelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = SteepDrop(shaft_x=SHAFT_X)
        cls.shape, cls.p = build_tunnel(cls.d)

    def test_both_versions_share_one_geometric_source(self):
        self.assertEqual((PART_ID, SOURCE_RIGHT_ID, SOURCE_DROP_ID),
                         ("S03-V8", "S02-V14", "S01-V6"))
        bare_right, _ = right.build_tunnel(self.d, label=None)
        bare_left = bare_right.mirror("XZ")
        self.assertTrue(bare_left.isValid())
        self.assertEqual(len(bare_left.Solids()), 1)
        marked = engrave(bare_left, PART_ID,
                         x=0., y=-self.p.depth / 2, z=18.)
        self.assertLess(abs(marked.Volume() - self.shape.Volume()), .01)

    def test_south_engraving_is_cut_after_mirror(self):
        blank, _ = right.build_tunnel(self.d, label=None)
        mirrored = blank.mirror("XZ")
        self.assertGreater(mirrored.Volume() - self.shape.Volume(), .2)
        marked = engrave(mirrored, PART_ID,
                         x=0., y=-self.p.depth / 2, z=18.)
        self.assertAlmostEqual(marked.Volume(), self.shape.Volume(), places=3)

    def test_ports_connect_and_hole_stays_circular(self):
        high, low = ports(self.d)
        for observed, expected in zip(high.floor_xyz_mm, (-16., 0., 25.55)):
            self.assertAlmostEqual(observed, expected)
        for observed, expected in zip(low.floor_xyz_mm, (0., 16., 6.35)):
            self.assertAlmostEqual(observed, expected)
        self.assertEqual(low.outward, (0., 1., 0.))
        west, east = straight_ports(2, BALL_TRACK.floor, BALL_TRACK.radius)
        self.assertTrue(mate(east.placed((-32., 0., DUPLO.height)),
                             high)["compatible"])
        self.assertTrue(mate(low, west.placed((0., 32., 0.), 90))["compatible"])
        self.assertTrue(all(circular_mouth_checks(
            self.shape, self.d).values()))

    def test_fit_studs_roof_and_no_extra_ports(self):
        self.assertEqual((self.p.nx, self.p.ny), (2, 2))
        self.assertAlmostEqual(self.p.height, 57.6)
        self.assertTrue(self.shape.isInside(
            cq.Vector(-15.7, 0., self.d.low_centre_z)))
        self.assertTrue(self.shape.isInside(
            cq.Vector(0., 0., self.p.height - .1)))
        self.assertFalse(self.shape.isInside(cq.Vector(0., 0., 1.)))
        self.assertTrue(self.shape.isInside(cq.Vector(3.89, 3.89, 1.)))
        self.assertTrue(all(self.shape.isInside(
            cq.Vector(x + 3.9, y, self.p.height + 1.))
            for x, y in self.p.studs()))

    def test_mirrored_e31_short_slot_and_support(self):
        self.assertAlmostEqual(SLOT_END_Z, 3.50)
        self.assertAlmostEqual(SLOT_END_Z + SLOT_END_RADIUS, 4.15)
        self.assertGreaterEqual(self.d.receiver_depth -
                                (SLOT_END_Z + SLOT_END_RADIUS), .6 - 1e-6)
        self.assertFalse(self.shape.isInside(cq.Vector(6.2, 0., 3.9)))
        self.assertTrue(self.shape.isInside(cq.Vector(6.2, 0., 4.4)))

    def test_gentle_slope_and_ball_clearance(self):
        self.assertAlmostEqual(self.d.ramp_grade, .25)
        self.assertAlmostEqual(
            self.d.ramp_grade * self.d.ramp_end_x, 3.25)
        self.assertLess(max(ball_path_collisions(self.shape, self.d)),
                        VOLUME_TOL)
        self.assertLess(max(swept_ball_path_collisions(self.shape, self.d)),
                        VOLUME_TOL)
        oversized = cq.Solid.makeSphere(
            14., cq.Vector(0., 0., 26.), angleDegrees1=-90)
        self.assertGreater(intersection(self.shape, oversized), VOLUME_TOL)


if __name__ == "__main__":
    unittest.main()
