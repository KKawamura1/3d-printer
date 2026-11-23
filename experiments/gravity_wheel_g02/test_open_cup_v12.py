"""Regression tests for GW02-V12's flat-backed, support-free rotor halves."""
import unittest

import cadquery as cq

from experiments.gravity_wheel_g02 import open_cup_v12 as gw
from experiments.gravity_wheel_g02 import open_cup_v4 as v4


class GW02V12Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parts = gw.build_parts()

    def test_rotor_mechanics_and_plate_geometry(self):
        checks = gw.static_checks(self.parts)
        self.assertTrue(all(checks.values()),
                        [k for k, passed in checks.items() if not passed])

    def test_flat_outer_panels_on_bed_without_temporary_posts(self):
        for name in ("rotor_front", "rotor_back"):
            with self.subTest(name=name):
                printable = gw.orient_for_print(name, self.parts[name])
                bounds = printable.BoundingBox()
                self.assertAlmostEqual(bounds.zmin, 0, delta=.01)
                self.assertLessEqual(bounds.zmax, 16.02)
                self.assertEqual(len(printable.Solids()), 1)
                self.assertGreater(
                    v4.print_pose_report(printable)["bed_contact_faces_mm2"],
                    2000)

    def test_ball_does_not_intersect_closed_outer_panels(self):
        rotor = gw.rotor_half_local(-1).fuse(gw.rotor_half_local(1))
        for angle in (0, 180):
            ball = v4.rotate(v4.ball_local(), angle)
            self.assertLess(rotor.intersect(ball).Volume(), .1)

    def test_dowels_remain_separate_small_printables(self):
        joiner = self.parts["rotor_joiner"]
        printed = gw.orient_for_print("rotor_joiner", joiner)
        self.assertAlmostEqual(joiner.Volume(), printed.Volume(), delta=.001)
        self.assertLess(printed.BoundingBox().xlen, 4)
        self.assertEqual(len(printed.Solids()), 1)

    def test_ten_parts_fit_single_plate_without_overlap(self):
        poses = {name: gw.orient_for_print(name, shape)
                 for name, shape in self.parts.items()}
        plate = gw.plate_parts(poses)
        self.assertEqual(len(plate), 10)
        checks = gw.v11.plate_checks(plate)
        self.assertTrue(all(checks.values()),
                        [k for k, passed in checks.items() if not passed])

    def test_no_legacy_sacrificial_support(self):
        self.assertFalse(hasattr(gw, "sacrificial_roof_support_local"))
        self.assertFalse(hasattr(gw, "sacrificial_stop_support_local"))


if __name__ == "__main__":
    unittest.main()
