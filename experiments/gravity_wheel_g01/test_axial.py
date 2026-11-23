"""Static geometry tests for GW01-V2 axial-feed wheel."""
import unittest
import cadquery as cq
from experiments.gravity_wheel_g01.axial import (
    AXIS_SLOPE, AXIS_TILT_DEG, BALL_R, OUTLET_ANGLES,
    build_parts, gate_local, pocket_center, rotor_local, validate,
)

class AxialGravityWheelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parts = build_parts()
        cls.checks = validate(cls.parts)

    def test_all_six_solids_and_rotation_envelope(self):
        self.assertTrue(all(self.checks.values()), self.checks)

    def test_ball_does_not_clip_rotating_cup(self):
        self.assertLess(AXIS_SLOPE, -0.08)
        self.assertLess(AXIS_TILT_DEG, -5.0)
        for a in (0, 30, 50, 64, 75, 90):
            x, z = pocket_center(a)
            ball = cq.Solid.makeSphere(BALL_R, cq.Vector(x, 20, z), angleDegrees1=-90)
            rotor = rotor_local().rotate((0, 0, 0), (0, 1, 0), -a)
            self.assertLess(rotor.intersect(ball).Volume(), 0.05, a)

    def test_exit_remains_above_assembly_floor(self):
        self.assertLessEqual(OUTLET_ANGLES[0], 50)
        self.assertGreaterEqual(OUTLET_ANGLES[-1], 80)
        self.assertGreater(self.parts["guide_outlet"].BoundingBox().zmin, 0)
        self.assertTrue(gate_local(False).isValid())
        self.assertTrue(gate_local(True).isValid())

if __name__ == "__main__":
    unittest.main()
