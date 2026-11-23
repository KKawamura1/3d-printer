"""GW02-V3 static design checks (NOT a dynamic impact/release simulation)."""
import math
import unittest
import cadquery as cq
from experiments.gravity_wheel_g02 import open_cup_v3 as gw


class GW02V3Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parts = gw.build_parts()
        cls.checks = gw.static_checks(cls.parts)

    def test_all_checks_and_five_printable_parts(self):
        self.assertTrue(all(self.checks.values()),
                        [name for name, ok in self.checks.items() if not ok])
        self.assertEqual(len(self.parts), 5)
        self.assertNotIn("shroud", self.parts)

    def test_centrifugal_force_points_away_from_mouth(self):
        # An outlet pointing radially OUT would encourage premature release.
        self.assertLess(gw.centrifugal_outlet_projection_mm(), -2)
        # At the stop the ball's tangential velocity should point at the mouth.
        self.assertGreater(gw.tangential_exit_alignment(), .99)

    def test_lip_retains_level_ball_but_allows_lifted_corridor(self):
        cup = gw.cup_local()
        self.assertLess(gw.SLOT_WIDTH, gw.BALL_D - 2)
        self.assertLess(cup.intersect(gw.ball_at()).Volume(), .1)
        self.assertGreater(cup.intersect(gw.ball_at(18)).Volume(), 10)
        self.assertLess(cup.intersect(gw.ball_at(18, gw.RELEASE_LIFT_MM)).Volume(), .1)
        for x in (0, 8, 12, 16, 20, 26):
            lift = min(gw.RELEASE_LIFT_MM, max(0.0, x-1) * gw.RELEASE_LIFT_MM / 8)
            with self.subTest(x=x):
                self.assertLess(cup.intersect(gw.ball_at(x, lift)).Volume(), .1)

    def test_rotor_has_no_ball_overlap_at_loading_position(self):
        self.assertTrue(gw.rotor_local().isValid())
        self.assertEqual(len(gw.rotor_local().Solids()), 1)
        self.assertLess(gw.rotor_local().intersect(gw.ball_local()).Volume(), .1)

    def test_stopper_clearance_for_all_three_angles(self):
        rotor = gw.rotor_local()
        for selected in gw.STOP_ANGLES:
            with self.subTest(angle=selected):
                pin = gw.stopper(selected)
                self.assertLess(
                    gw.world(gw.rotate(rotor, selected - 15)).intersect(pin).Volume(), .1)
                self.assertGreater(
                    gw.world(gw.rotate(rotor, selected + 3)).intersect(pin).Volume(), .5)

    def test_gravity_drop_and_supported_stop_window(self):
        self.assertAlmostEqual(2*gw.POCKET_Z, 70)
        lowest = 180 - math.degrees(math.atan2(gw.POCKET_X, gw.POCKET_Z))
        self.assertTrue(160 < lowest < 170)
        with self.assertRaises(ValueError):
            gw.stopper(155)


if __name__ == "__main__":
    unittest.main()
