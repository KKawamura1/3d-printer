import itertools
import unittest

import cadquery as cq

from brickcad.course_loft_family import LoftSettings, height, xy
from brickcad.standards import DUPLO
from experiments.compact_curve.design import SPECIMENS
from experiments.compact_curve.export import actual_mouths_match


class CompactCurveTests(unittest.TestCase):
    def test_four_downhill_recipes_and_common_port_path(self):
        expected = set(itertools.product((False, True), (False, True)))
        self.assertEqual({(s.tunnel, s.left) for s in SPECIMENS}, expected)
        self.assertEqual([s.id for s in SPECIMENS],
                         ["X4A-05", "X4A-06", "X4A-07", "X4A-08"])
        self.assertTrue(all(s.drop_mm == DUPLO.height for s in SPECIMENS))
        for specimen in SPECIMENS:
            config = LoftSettings.from_dict(vars(specimen.settings))
            self.assertEqual(xy(0, config), (-32, 0, 1, 0))
            for actual, expected in zip(xy(config.length, config), (16, -16, 0, -1)):
                self.assertAlmostEqual(actual, expected)
            self.assertAlmostEqual(height(0, config), 6.35 + specimen.drop_mm)
            self.assertAlmostEqual(height(config.length, config), 6.35)

    def test_trial_mark_is_fully_contained_on_the_short_west_skirt(self):
        from brickcad.course_finish import west_skirt_label_tool

        for specimen in SPECIMENS:
            with self.subTest(id=specimen.id):
                cutter = west_skirt_label_tool(
                    specimen.id, x=-31.9, y=0., face_width_mm=31.8)
                bounds = cutter.BoundingBox()
                self.assertGreaterEqual(bounds.ymin, -14.9)
                self.assertLessEqual(bounds.ymax, 14.9)
                self.assertGreaterEqual(bounds.zmin, .4)
                self.assertLessEqual(bounds.zmax, 4.35)

        with self.assertRaisesRegex(ValueError, "exceeds the west receiver skirt"):
            west_skirt_label_tool(
                "X4A-WAY-TOO-LONG-FOR-SKIRT", x=-31.9, y=0.)

    def test_horizontal_sharp_tunnel_is_not_supported(self):
        with self.assertRaises(ValueError):
            LoftSettings.from_dict({
                "route": "sharp", "drop_mm": 0., "tunnel": True,
                "mirror": False, "mark_face": "south", "label_z_mm": 12.
            })

    def test_port_probe_detects_wrong_diameter_and_wrong_handedness(self):
        stock = cq.Workplane("XY").box(63.8, 31.8, 57.6,
                                      centered=(True, True, False)).val()

        def bores(radius):
            inlet = cq.Solid.makeCylinder(radius, 12, (-34, 0, 38.42), (1, 0, 0))
            outlet = cq.Solid.makeCylinder(radius, 12, (16, -18, 19.22), (0, 1, 0))
            return stock.cut(inlet, outlet)

        self.assertTrue(actual_mouths_match(bores(12.87), SPECIMENS[2]))
        self.assertFalse(actual_mouths_match(bores(13.20), SPECIMENS[2]))
        self.assertFalse(actual_mouths_match(bores(12.87), SPECIMENS[3]))


if __name__ == "__main__":
    unittest.main()
