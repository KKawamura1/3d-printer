"""Fast contracts for two mirrored PR91 R48 left-hand courses."""
import unittest

from brickcad.course_finish import west_skirt_label_tool
from brickcad.course_r48_unified import R48FamilyConfig
from brickcad.standards import BALL_TRACK, DUPLO
from experiments.r48_left_rollout.export import SPECIMENS, RELIEF_MM, LOCATIONS


class R48LeftRolloutTests(unittest.TestCase):
    def test_only_two_missing_left_tunnels(self):
        self.assertEqual(SPECIMENS, {
            "X89-E01L-R10": 0.,
            "X89-SC02L-R10": DUPLO.height,
        })
        self.assertEqual(RELIEF_MM, 1.)
        self.assertEqual(list(LOCATIONS), list(SPECIMENS))
        self.assertEqual(LOCATIONS["X89-E01L-R10"], (-36., 0.))
        self.assertEqual(LOCATIONS["X89-SC02L-R10"], (36., 0.))

    def test_left_recipes_are_pr91_common_r48_r10(self):
        for model_id, drop_mm in SPECIMENS.items():
            with self.subTest(model=model_id):
                cfg = R48FamilyConfig(model_id, drop_mm, "roofed",
                                      direction="left", relief_mm=RELIEF_MM)
                self.assertEqual(cfg.enclosure, "roofed")
                self.assertEqual(cfg.direction, "left")
                self.assertEqual(cfg.relief_mm, 1.)
                self.assertEqual(cfg.roof_z,
                                 2 * DUPLO.height + drop_mm)
                self.assertAlmostEqual(BALL_TRACK.opening, 25.74)

    def test_engraving_fits_actual_reflected_skirt_with_1mm_margin(self):
        # PR91 physical right model uses west skirt Y=-31.9..0.
        # Reflection moves it to Y=0..31.9; the literal label must not be
        # mirrored or exceed this physical skirt (PR91's past failure).
        for model_id in SPECIMENS:
            label = model_id.removeprefix("X89-")
            tool = west_skirt_label_tool(
                label, x=-31.9, y=16., face_width_mm=31.9)
            b = tool.BoundingBox()
            with self.subTest(label=label):
                self.assertGreaterEqual(b.ymin, 1.)
                self.assertLessEqual(b.ymax, 30.9)
                self.assertGreaterEqual(b.zmin, .4)
                self.assertLessEqual(b.zmax, 4.35)

    def test_reject_oversized_label(self):
        with self.assertRaisesRegex(ValueError, "exceeds the west receiver skirt"):
            west_skirt_label_tool(
                "X89-SC02L-R10-OVERLONG", x=-31.9, y=16.,
                face_width_mm=31.9)


if __name__ == "__main__":
    unittest.main()
