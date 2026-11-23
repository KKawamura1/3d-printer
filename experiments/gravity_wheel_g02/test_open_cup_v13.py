"""Regression checks: Issue #99 GW02-V13 stand-roof cutouts."""
import unittest

from experiments.gravity_wheel_g02 import open_cup_v12 as v12
from experiments.gravity_wheel_g02 import open_cup_v13 as gw
from experiments.gravity_wheel_g02 import open_cup_v4 as v4


class GW02V13Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old = v12.build_parts()
        cls.parts = gw.build_parts()

    def test_support_free_geometry_and_ten_piece_plate(self):
        checks = gw.static_checks(self.parts)
        self.assertTrue(all(checks.values()),
                        [k for k, passed in checks.items() if not passed])

    def test_only_stand_roofs_are_changed(self):
        for name in ("rotor_front", "rotor_back", "rotor_joiner",
                     "axle", "stop_pin"):
            with self.subTest(part=name):
                old, new = self.old[name], self.parts[name]
                self.assertAlmostEqual(old.Volume(), new.Volume(), delta=.01)
                self.assertLess(old.cut(new).Volume(), .01)
                self.assertLess(new.cut(old).Volume(), .01)

    def test_E31_receiver_and_tube_intact_below_roof(self):
        guard = v4.box(100, 200, 6, 0, 0, 1.7)  # Z -1.3..4.7
        for name in ("stand_front", "stand_back_stop"):
            with self.subTest(part=name):
                removed = self.old[name].cut(self.parts[name])
                self.assertGreater(removed.Volume(), 200)
                self.assertLess(removed.intersect(guard).Volume(), .01)
                self.assertLess(
                    self.parts[name].cut(self.old[name]).Volume(), .01)

    def test_four_windows_respect_post_and_central_tube(self):
        for side in (-1, 1):
            with self.subTest(side=side):
                cutter = gw.roof_window_cutters(side * v4.STAND_Y)
                self.assertEqual(len(cutter.Solids()), 4)
                post = v4.box(
                    2 * gw.PILLAR_KEEP_HALF_X,
                    2 * gw.PILLAR_KEEP_HALF_Y,
                    8, 0, side * v4.STAND_Y, 6)
                tube = v4.cyl(
                    gw.TUBE_KEEP_OUT_R - .01, 8,
                    (0, side * v4.STAND_Y, 3), (0, 0, 1))
                self.assertLess(cutter.intersect(post).Volume(), .01)
                self.assertLess(cutter.intersect(tube).Volume(), .01)

    def test_unchanged_stand_top_and_bearing(self):
        guard = v4.box(100, 200, 90, 0, 0, 51.52)  # Z >= 6.52
        for name in ("stand_front", "stand_back_stop"):
            with self.subTest(part=name):
                changed = self.old[name].cut(self.parts[name])
                self.assertLess(changed.intersect(guard).Volume(), .01)

    def test_plate_unchanged_footprints(self):
        poses = {name: v12.orient_for_print(name, part)
                 for name, part in self.parts.items()}
        placed = v12.plate_parts(poses)
        self.assertEqual(len(placed), 10)
        checks = v12.v11.plate_checks(placed)
        self.assertTrue(all(checks.values()),
                        [key for key, passed in checks.items() if not passed])


if __name__ == "__main__":
    unittest.main()
