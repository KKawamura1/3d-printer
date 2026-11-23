"""GW02-V2: open cup, three-position impact stop, and real CAD clearances."""
import math
import unittest
import cadquery as cq
from experiments.gravity_wheel_g02 import open_cup_v2 as gw


class GW02V2Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parts = gw.build_parts()
        cls.checks = gw.static_checks(cls.parts)

    def test_all_static_checks(self):
        self.assertTrue(all(self.checks.values()),
                        [name for name, ok in self.checks.items() if not ok])

    def test_ball_captive_window(self):
        self.assertLess(gw.SLOT_WIDTH, gw.BALL_D - 5)
        self.assertGreater(2 * gw.CUP_IN_R - gw.BALL_D, 2.5)
        ball = gw.ball_local()
        self.assertLess(gw.rotor_local().intersect(ball).Volume(), .1)

    def test_inlet_outlet_axes_flip(self):
        self.assertEqual(len(gw.build_parts()), 5)
        self.assertNotIn("shroud", self.parts)
        center = cq.Vector(gw.POCKET_X, 0, gw.POCKET_Z)
        inverted = cq.Vector(-gw.POCKET_X, 0, -gw.POCKET_Z)
        self.assertAlmostEqual(center.z - inverted.z, 70.0)

    def test_stop_positions_and_contact_lead(self):
        for target in gw.STOP_ANGLES:
            p = gw.stop_point(target)
            self.assertAlmostEqual(math.hypot(*p), gw.STOP_R, places=5)
            pin = gw.stopper(target)
            rotor = gw.rotor_local()
            early = gw.world(gw.rotate(rotor, target - 15))
            contact = gw.world(gw.rotate(rotor, target + 3))
            self.assertLess(early.intersect(pin).Volume(), .1)
            self.assertGreater(contact.intersect(pin).Volume(), .5)

    def test_stop_is_removable_and_angle_checked(self):
        with self.assertRaises(ValueError):
            gw.stopper(155)
        self.assertIsNotNone(gw.stopper(160))
        self.assertIsNotNone(gw.stopper(170))
        self.assertIsNotNone(gw.stopper(180))

    def test_160_to_180_energy_window(self):
        # Closest to the ball's lowest point is ~164 degrees, so a 160
        # degree stop can be more forgiving than a full 180 degree stop.
        lowest = 180 - math.degrees(math.atan2(gw.POCKET_X, gw.POCKET_Z))
        self.assertGreater(lowest, 160)
        self.assertLess(lowest, 170)
        self.assertGreater(gw.POCKET_Z - (-gw.POCKET_Z), 0)


if __name__ == "__main__":
    unittest.main()
