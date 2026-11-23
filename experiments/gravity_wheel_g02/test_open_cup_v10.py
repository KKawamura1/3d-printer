"""GW02-V10: one print plate and slice-aware rib continuity regression."""
import unittest
from experiments.gravity_wheel_g02 import open_cup_v10 as gw


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

    def test_ribs_exist_across_all_print_layers(self):
        """Both opposed ribs must grow FROM the spokes, not start midair.

        V9's Bambu Studio G-code had a ~19.7 mm unsupported jump at
        print Z=11.2 mm because full ribs started at Y=+/-11 mm,
        whereas their supporting spokes ended at Y=+/-8 mm.
        """
        import cadquery as cq
        shape = gw.reinforced_rotor_local()
        for x, z in ((6, 20), (-6, -20)):
            for side in (-1, 1):
                for height in (8.1, 9, 10, 10.8, 11, 11.2, 12, 14, 17):
                    with self.subTest(x=x, z=z, side=side, height=height):
                        self.assertTrue(
                            shape.isInside(cq.Vector(x, side * height, z)),
                            "The full rib must remain attached through the "
                            "spoke-to-rib transition")

    def test_joiner_pin_cannot_inherit_rotor_scaffold(self):
        """The 4 joiner copies must remain small, separate, bed-ready pins."""
        original = self.parts["rotor_joiner"]
        printable = gw.orient_for_print("rotor_joiner", original)
        self.assertAlmostEqual(printable.Volume(), original.Volume(), delta=.01)
        bounds = printable.BoundingBox()
        self.assertLess(bounds.xlen, 4)
        self.assertLess(bounds.ylen, 4)
        self.assertEqual(len(printable.Solids()), 1)

    def test_removable_roof_posts_bond_to_both_halves(self):
        """Print-only supports run from the bed into the former 11-mm roofs."""
        import cadquery as cq
        raw = gw.reinforced_rotor_local()
        self.assertEqual(len(gw.ROOF_SUPPORT_POINTS), 4)
        for side in (-1, 1):
            posts = gw.sacrificial_roof_support_local(side)
            self.assertEqual(len(posts.Solids()), 4)
            for x, z in gw.ROOF_SUPPORT_POINTS:
                for layer in (0.2, 5.0, 10.5):
                    with self.subTest(side=side, x=x, z=z, layer=layer):
                        self.assertTrue(posts.isInside(
                            cq.Vector(x, side * layer, z)))
            self.assertGreater(raw.intersect(posts).Volume(), 1.0)
            name = "rotor_front" if side < 0 else "rotor_back"
            printable = gw.orient_for_print(name, self.parts[name])
            self.assertEqual(len(printable.Solids()), 1)
            self.assertGreater(printable.Volume() - self.parts[name].Volume(), 300)

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
