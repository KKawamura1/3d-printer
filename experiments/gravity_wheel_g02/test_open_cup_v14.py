"""Tests for V14's permanent, print-supported geometry (#99).

Tests intentionally verify clearance/geometry, NOT the number of supports
Bambu Studio will generate (which requires a new actual slicer G-code).
"""
import unittest

from experiments.gravity_wheel_g02 import open_cup_v4 as v4
from experiments.gravity_wheel_g02 import open_cup_v12 as v12
from experiments.gravity_wheel_g02 import open_cup_v13 as v13
from experiments.gravity_wheel_g02 import open_cup_v14 as gw


class GW02V14Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old = v13.build_parts()
        cls.parts = gw.build_parts()

    def test_shape_checks_and_plate(self):
        checks = gw.static_checks(self.parts)
        self.assertTrue(all(checks.values()),
                        [k for k, ok in checks.items() if not ok])

    def test_shared_receiver_unchanged_to_z4p70(self):
        base = v4.box(100, 200, 6, 0, 0, 1.7)
        for name in ("stand_front", "stand_back_stop"):
            with self.subTest(name=name):
                old, new = self.old[name], self.parts[name]
                self.assertLess(old.intersect(base).cut(new).Volume(), .01)
                self.assertLess(new.intersect(base).cut(old).Volume(), .01)

    def test_conical_cavity_above_tube(self):
        for side, name in ((-1, "stand_front"), (1, "stand_back_stop")):
            with self.subTest(name=name):
                cone = gw.cone_roof_clearance(side * v4.STAND_Y)
                removed = self.old[name].cut(self.parts[name])
                self.assertGreater(removed.intersect(cone).Volume(), 80)
                self.assertLess(self.parts[name].intersect(cone).Volume(), .5)

    def test_lips_have_outer_panel_braces(self):
        original = v12.rotor_halves_local()
        updated = gw.rotor_halves_local()
        self.assertEqual(len(updated), 2)
        for side, old, new in zip((-1, 1), original, updated):
            with self.subTest(side=side):
                web = gw.lip_plate_web_local(side)
                self.assertLess(web.cut(new).Volume(), .01)
                self.assertLess(old.cut(new).Volume(), .01)
                self.assertGreater(new.cut(old).Volume(), 10)

    def test_rear_brace_no_extra_printable(self):
        self.assertGreater(
            self.parts["stand_back_stop"].cut(
                self.old["stand_back_stop"]).Volume(), 100)
        printables = {name: v12.orient_for_print(name, shape)
                      for name, shape in self.parts.items()}
        plate = v12.plate_parts(printables)
        self.assertEqual(len(plate), 10)
        self.assertTrue(all(v12.v11.plate_checks(plate).values()))

    def test_axle_stop_joiner_bitwise_geometry(self):
        for name in ("axle", "stop_pin", "rotor_joiner"):
            self.assertLess(self.parts[name].cut(self.old[name]).Volume(), .01)
            self.assertLess(self.old[name].cut(self.parts[name]).Volume(), .01)


if __name__ == "__main__":
    unittest.main()
