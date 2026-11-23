"""GW02-V15: external stop correction and separate entry/exit guides."""
import unittest

from experiments.gravity_wheel_g02 import open_cup_v4 as v4
from experiments.gravity_wheel_g02 import open_cup_v14 as old
from experiments.gravity_wheel_g02 import open_cup_v15 as gw


class V15Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parts = gw.build_parts()
        cls.old = old.build_parts()

    def test_static_and_swept_shape_contracts(self):
        checks = gw.static_checks(self.parts)
        self.assertTrue(all(checks.values()), [k for k,v in checks.items() if not v])

    def test_8_existing_components_remain_compatible(self):
        for name in ("rotor_front", "stand_front", "stand_back_stop",
                     "axle", "rotor_joiner"):
            with self.subTest(name=name):
                self.assertLess(self.old[name].cut(self.parts[name]).Volume(), .01)
                self.assertLess(self.parts[name].cut(self.old[name]).Volume(), .01)

    def test_external_boss_and_short_pin_clearance(self):
        pin = self.parts["stop_pin"]
        self.assertGreater(gw.PIN_START_Y, v4.CUP_OUT_R)
        boss = gw.external_stop_boss_local()
        self.assertGreater(boss.BoundingBox().ymax, 21)
        self.assertLess(self.parts["rotor_back"].intersect(pin).Volume(), .01)
        self.assertGreater(
            v4.world(v4.rotate(boss, 172)).intersect(pin).Volume(), .2)

    def test_guide_receivers_and_floors(self):
        for name in ("entry_guide", "exit_guide"):
            with self.subTest(name=name):
                s = gw.printing_pose(name, self.parts[name])
                self.assertAlmostEqual(s.BoundingBox().zmin, 0, delta=.01)
                self.assertEqual(len(s.Solids()), 1)
        entry = gw.guide_head("entry")
        exit = gw.guide_head("exit")
        self.assertGreater(entry.Volume(), 2000)
        self.assertGreater(exit.Volume(), 2000)

    def test_mouths_on_appropriate_side_and_level(self):
        entry, exit = gw.entry_mouth_world(), gw.exit_mouth_world()
        self.assertGreater(entry[0], 0)
        self.assertGreater(entry[1], 80)
        self.assertLess(exit[0], 0)
        self.assertLess(exit[1], 50)


if __name__ == "__main__":
    unittest.main()
