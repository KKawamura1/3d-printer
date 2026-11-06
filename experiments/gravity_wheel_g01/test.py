"""Static CAD and rotation-envelope checks for GW01-V1."""
import unittest
from experiments.gravity_wheel_g01.design import build_parts, validate, BALL_TRACK, AXIS_Z


class GravityWheelCADTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parts = build_parts()
        cls.checks = validate(cls.parts)

    def test_all_six_solids_and_static_clearances(self):
        self.assertTrue(all(self.checks.values()), self.checks)

    def test_ball_and_rail_alignment(self):
        self.assertAlmostEqual(BALL_TRACK.ball_diameter, 24.26)
        self.assertAlmostEqual(AXIS_Z - 1.3 - BALL_TRACK.ball_diameter / 2,
                               6.35 + 2 * 19.2)

    def test_guard_windows_cannot_pass_ball(self):
        from experiments.gravity_wheel_g01.design import BALL_R
        self.assertLess(7.0, BALL_R)


if __name__ == "__main__":
    unittest.main()
