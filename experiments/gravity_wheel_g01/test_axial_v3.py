"""Static CAD invariants for GW01-V3 captured-ball axial-flow prototype."""
import math
import unittest

import cadquery as cq

from experiments.gravity_wheel_g01.axial_v3 import (
    BALL_DIAMETER, BALL_R, CUP_INNER_R, CUP_OUTER_R, RELEASE_ANGLE,
    UPPER_RAIL_FLOOR, LOWER_RAIL_FLOOR, AXIS_TILT_DEG, AXIS_SLOPE,
    build_parts, validate, gate_local, guide_floor_profile,
    rotor_local, ball_local, pocket_center,
)


class GW01V3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parts = build_parts()
        cls.checks = validate(cls.parts)

    def test_standalone_parts_and_all_static_checks(self):
        self.assertTrue(all(self.checks.values()),
                        [name for name, ok in self.checks.items() if not ok])
        self.assertEqual(len(self.parts), 6)

    def test_rotation_retains_ball_while_fixed_gate_controls_release(self):
        rotor = rotor_local()
        for angle in (0, 15, 30, 45, 52, 55, 60, 65, 68, 80, 90):
            moved = rotor.rotate((0, 0, 0), (0, 1, 0), -angle)
            self.assertLess(moved.intersect(ball_local(angle, 0)).Volume(), 0.05)
        self.assertGreater(CUP_OUTER_R - CUP_INNER_R, 2.3)
        inlet_gate = gate_local(False)
        outlet_gate = gate_local(True)
        self.assertLess(inlet_gate.intersect(ball_local(0, -43.5)).Volume(), 0.05)
        self.assertGreater(outlet_gate.intersect(ball_local(0, 43.5)).Volume(), 100)
        self.assertLess(
            outlet_gate.intersect(ball_local(RELEASE_ANGLE, 43.5)).Volume(), 0.05
        )

    def test_duplo_grid_and_floor_height_transitions(self):
        in_guide = guide_floor_profile(False)
        out_guide = guide_floor_profile(True)
        self.assertEqual(in_guide[0], -32)
        self.assertAlmostEqual(out_guide[0], -16, places=7)
        self.assertAlmostEqual(in_guide[3], UPPER_RAIL_FLOOR)
        self.assertAlmostEqual(out_guide[4], LOWER_RAIL_FLOOR)
        self.assertAlmostEqual(
            in_guide[0] - out_guide[0], -16.0
        )
        self.assertGreater(self.parts["guide_inlet"].BoundingBox().zmax, 90)
        self.assertGreaterEqual(self.parts["guide_outlet"].BoundingBox().zmin, -0.01)
        self.assertLess(AXIS_SLOPE, 0)
        self.assertLess(AXIS_TILT_DEG, -5.0)

    def test_axle_and_parts_fit_a1_mini_nominal_build_space(self):
        for name, part in self.parts.items():
            b = part.BoundingBox()
            self.assertLess(b.xlen, 180.0, name)
            self.assertLess(b.ylen, 180.0, name)
            self.assertLess(b.zlen, 180.0, name)


if __name__ == "__main__":
    unittest.main()
