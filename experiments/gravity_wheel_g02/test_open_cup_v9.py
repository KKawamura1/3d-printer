"""V8: printable single-plate mesh and removable stop-lug support."""
import unittest
from experiments.gravity_wheel_g02 import open_cup_v9 as gw


class GW02V9Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parts = gw.build_parts()
        cls.checks = gw.static_checks(cls.parts)

    def test_static_geometry_and_print_plate(self):
        self.assertTrue(all(self.checks.values()),
                        [key for key, passed in self.checks.items() if not passed])

    def test_one_plate_ten_separate_objects(self):
        items = gw.plate_parts({name: gw.orient_for_print(name, shape)
                                for name, shape in self.parts.items()})
        self.assertEqual(len(items), 10)
        self.assertTrue(all(gw.plate_checks(items).values()))
        self.assertEqual(len([k for k in items if k.startswith("rotor_joiner_")]), 4)

    def test_striker_has_breakaway_support_from_bed(self):
        raw = self.parts["rotor_back"]
        printable = gw.orient_for_print("rotor_back", raw)
        self.assertGreater(printable.Volume() - raw.Volume(), 100)
        self.assertAlmostEqual(printable.BoundingBox().zmin, 0, delta=.01)
        self.assertEqual(len(printable.Solids()), 1)

    def test_assembled_rotor_does_not_gain_sacrificial_support(self):
        original = gw.reinforced_rotor_local()
        # The removable support is added ONLY in orient_for_print.
        # The slender neck deliberately penetrates the striker by ~1 mm^3
        # so the temporary post is printable and can be snapped off.
        # The assembled running geometry contains ONLY that tiny overlap,
        # not the tall support column.
        overlap = original.intersect(gw.sacrificial_stop_support_local()).Volume()
        self.assertGreater(overlap, .25)
        self.assertLess(overlap, 2.0)
        self.assertEqual(len(original.Solids()), 1)


if __name__ == "__main__":
    unittest.main()
