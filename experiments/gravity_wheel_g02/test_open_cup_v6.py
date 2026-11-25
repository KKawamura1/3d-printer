"""GW02-V6 tests: split-print geometry and assembly compatibility."""
import unittest

from experiments.gravity_wheel_g02 import open_cup_v6 as gw


class GW02V6Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parts = gw.build_parts()
        cls.checks = gw.static_checks(cls.parts)

    def test_all_static_and_printability_checks(self):
        self.assertTrue(all(self.checks.values()),
                        [k for k, passed in self.checks.items() if not passed])
        self.assertEqual(set(self.parts), {
            "rotor_front", "rotor_back", "rotor_joiner",
            "stand_front", "stand_back_stop", "axle", "stop_pin"
        })

    def test_rotor_halves_rest_on_broad_flat_faces(self):
        for name in ("rotor_front", "rotor_back"):
            with self.subTest(name=name):
                printed = gw.orient_for_print(name, self.parts[name])
                pose = gw.v4.print_pose_report(printed)
                self.assertAlmostEqual(pose["min_z_mm"], 0, delta=.01)
                self.assertGreater(pose["bed_contact_faces_mm2"], 150)
                self.assertLess(pose["max_z_mm"], 35)

    def test_front_reinforcement_is_one_printable_solid(self):
        front, back = gw.rotor_halves_local()
        self.assertEqual(len(front.Solids()), 1)
        self.assertEqual(len(back.Solids()), 1)
        self.assertLess(gw.reinforced_rotor_local().intersect(
            gw.v4.ball_local()).Volume(), .1)

    def test_joiner_count_and_physical_clearance(self):
        self.assertEqual(len(gw.JOIN_POINTS), 4)
        self.assertLess(gw.PIN_R, gw.HOLE_R)
        self.assertLess(gw.PIN_LENGTH, 2 * gw.HOLE_DEPTH)
        printed = gw.orient_for_print("rotor_joiner", self.parts["rotor_joiner"])
        pose = gw.v4.print_pose_report(printed)
        self.assertAlmostEqual(pose["min_z_mm"], 0, delta=.01)
        self.assertAlmostEqual(pose["max_z_mm"], gw.PIN_LENGTH, delta=.1)

    def test_assembled_rotor_preserves_v4_ball_path(self):
        front, back = gw.rotor_halves_local()
        combined = front.fuse(back)
        full = gw.reinforced_rotor_local()
        self.assertLess(combined.cut(full).Volume(), .05)
        self.assertLess(combined.intersect(gw.v4.ball_local()).Volume(), .1)
        for angle in (0, 60, 120, 160, 180):
            rotor = gw.v4.world(gw.v4.rotate(combined, angle))
            for stand in ("stand_front", "stand_back_stop"):
                with self.subTest(angle=angle, stand=stand):
                    self.assertLess(rotor.intersect(self.parts[stand]).Volume(), .1)


if __name__ == "__main__":
    unittest.main()
