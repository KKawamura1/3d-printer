"""Targeted S01-V8 roofed steep-drop CAD tests; no slicing/dynamics guarantee."""
import unittest
from unittest.mock import patch
import cadquery as cq
from brickcad.ports import mate, straight_ports
from brickcad.standards import BALL_TRACK
from brickcad.verify import VOLUME_TOL, intersection
from parts.tunnel.e31_fit import SLOT_END_Z, SLOT_END_RADIUS
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
        self.assertEqual(PART_ID, "S01-V8")
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
        self.assertAlmostEqual(d.ramp_grade, .25)
        self.assertAlmostEqual(d.ramp_end_x, 13.)
        self.assertAlmostEqual(path[2].z - path[3].z, 3.75)
        self.assertAlmostEqual(path[-1].z, d.low_centre_z)
        self.assertAlmostEqual(path[3].z, d.low_centre_z + ramp_normal_clearance(d))
        # The landing zone is no longer a flat empty pit.
        self.assertTrue(self.shape.isInside(cq.Vector(d.shaft_x, 0, d.low_floor + 1.)))
        self.assertFalse(self.shape.isInside(cq.Vector(
            d.shaft_x, 0, d.low_floor + 3.75 + 1.)))
        self.assertFalse(self.shape.isInside(cq.Vector(
            d.ramp_end_x, 0, d.low_floor + .2)))
        # Whole-sphere tests along the ramp protect against overhead clipping.
        self.assertLess(max(sampled_ball_collisions(self.shape, d)), VOLUME_TOL)
        self.assertLess(max(continuous_ball_path_intersections(self.shape, d)),
                        VOLUME_TOL)

    def test_both_mouths_keep_circular_openings_for_tunnel_connections(self):
        # The 33-degree V5 wedge clipped the mouth visually and caused
        # snagging when joined to a tunnel. V4 must retain circular ports.
        import math
        r = self.d.section_radius
        # Probe near the *visible faces*, not just farther inside the bore.
        section_centres = (
            (-15.8, self.d.high_centre_z),
            (-15.5, self.d.high_centre_z),
            (15.5, self.d.low_centre_z),
            (15.8, self.d.low_centre_z),
        )
        for x, zc in section_centres:
            for i in range(16):
                theta = 2. * math.pi * i / 16
                y_in = (r - .3) * math.cos(theta)
                z_in = zc + (r - .3) * math.sin(theta)
                y_out = (r + .3) * math.cos(theta)
                z_out = zc + (r + .3) * math.sin(theta)
                with self.subTest(x=x, angle_index=i):
                    self.assertFalse(self.shape.isInside(
                        cq.Vector(x, y_in, z_in)))
                    self.assertTrue(self.shape.isInside(
                        cq.Vector(x, y_out, z_out)))

    def test_e31_slot_shortening_preserves_all_four_tube_roofs(self):
        self.assertAlmostEqual(SLOT_END_Z, 3.50)
        self.assertAlmostEqual(SLOT_END_RADIUS, .65)
        self.assertGreaterEqual(
            self.d.receiver_depth - (SLOT_END_Z + SLOT_END_RADIUS), .59)
        # Full receiver tube is below the track floor; the four slots must
        # remain open but stop before the ceiling of the underside cavity.
        for x, y in ((6.5, 0.), (-6.5, 0.), (0., 6.5), (0., -6.5)):
            with self.subTest(x=x, y=y):
                self.assertFalse(self.shape.isInside(cq.Vector(x, y, 2.25)))
                self.assertTrue(self.shape.isInside(cq.Vector(x, y, 4.20)))
                self.assertTrue(self.shape.isInside(cq.Vector(x, y, 4.80)))

    def test_standard_final_south_marking_removes_real_outer_wall(self):
        # The label is engraved *after* all material unions. Rebuild the
        # identical shape without text to prove the actual final recess.
        with patch("parts.steep_drop_hole.design.engrave",
                   side_effect=lambda shape, label, **kwargs: shape) as marking:
            from parts.steep_drop_hole.design import build_steep_drop
            blank, _ = build_steep_drop(self.d)
        marking.assert_called_once()
        _, kwargs = marking.call_args
        self.assertEqual(kwargs, dict(x=0., y=-self.p.depth / 2, z=12.))
        # No size/depth overrides: shared engrave() defaults are 3.0 / 0.4.
        self.assertGreater(blank.Volume() - self.shape.Volume(), .2)
        cut = blank.cut(self.shape).clean()
        self.assertGreater(cut.Volume(), .2)
        bounds = cut.BoundingBox()
        self.assertAlmostEqual(bounds.ymin, -self.p.depth / 2, delta=.05)
        self.assertLessEqual(bounds.ymax, -self.p.depth / 2 + .41)

    def test_full_supports_do_not_intersect_the_enclosed_track(self):
        # This model has a roof over the studs and a 1.6 mm floor over the
        # receiver, so no contour-trimmed support is needed at those planes.
        for x, y in self.p.studs():
            with self.subTest(stud=(x, y)):
                self.assertTrue(self.shape.isInside(
                    cq.Vector(x + 3.9, y, self.p.height + 1.)))
                self.assertFalse(self.shape.isInside(
                    cq.Vector(x, y, self.p.height + 1.)))
        self.assertTrue(self.shape.isInside(
            cq.Vector(0., 0., self.d.low_floor - .1)))

    def test_negative_control_oversized_ball(self):
        ball = cq.Solid.makeSphere(
            14., cq.Vector(self.d.shaft_x, 0, 26.),
            angleDegrees1=-90)
        self.assertGreater(intersection(self.shape, ball), VOLUME_TOL)


if __name__ == "__main__":
    unittest.main()
