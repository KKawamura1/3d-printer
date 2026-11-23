"""GW01 V4: angle, compatibility, port clearance and static motion envelope."""
import math
import unittest

from experiments.gravity_wheel_g01 import axial_v3 as shared
from experiments.gravity_wheel_g01 import axial_v4 as v4


class GW01V4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parts = v4.build_parts()
        cls.checks = v4.validate(cls.parts)

    def test_all_shared_static_constraints(self):
        self.assertEqual(len(self.parts), 6)
        self.assertTrue(all(self.checks.values()),
                        [k for k, passed in self.checks.items() if not passed])

    def test_120_degree_discharge_lands_on_duplo_grid(self):
        inlet_x = shared.guide_floor_profile(False)[0]
        outlet_x = shared.guide_floor_profile(True, v4.RELEASE_ANGLE)[0]
        self.assertAlmostEqual(inlet_x, -32.0, places=6)
        self.assertAlmostEqual(outlet_x, +16.0, places=6)
        self.assertAlmostEqual(outlet_x - inlet_x, 3 * shared.PITCH, places=6)
        self.assertGreater(v4.RELEASE_ANGLE, 90)
        self.assertLess(v4.RELEASE_ANGLE, 180)

    def test_discharge_gate_blocks_early_ball_and_opens_at_120(self):
        plate = shared.gate_local(True, v4.RELEASE_ANGLE)
        self.assertGreater(plate.intersect(shared.ball_local(0, 43.5)).Volume(), 100)
        self.assertLess(
            plate.intersect(shared.ball_local(v4.RELEASE_ANGLE, 43.5)).Volume(),
            0.05
        )

    def test_rotor_stays_identical_between_variants(self):
        # Crucial mechanical interface: only the gate and output rail move.
        old_rotor = shared.build_parts(60)["rotor"]
        self.assertAlmostEqual(
            old_rotor.Volume(), self.parts["rotor"].Volume(), places=4
        )
        self.assertAlmostEqual(
            old_rotor.BoundingBox().xlen, self.parts["rotor"].BoundingBox().xlen
        )

    def test_energy_limit_documented(self):
        # Ball net drop from start after 120 degrees is positive but would
        # disappear at 180 degrees. Friction and rotor dynamics remain unknown.
        d120 = shared.POCKET_X * math.sin(math.radians(v4.RELEASE_ANGLE))
        d180 = shared.POCKET_X * math.sin(math.pi)
        self.assertGreater(d120, 27.0)
        self.assertAlmostEqual(d180, 0.0, places=5)
        self.assertLess(d120, shared.POCKET_X)


if __name__ == "__main__":
    unittest.main()
