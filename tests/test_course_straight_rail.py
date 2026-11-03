"""Full CAD test for production horizontal x straight x open R01-V1."""
import unittest

from brickcad.course_contract import (
    RECEIVER_DEPTH_MM, SLOT_END_Z_MM, TUBE_RADIUS_MM, PRODUCTION_CONTRACT,
)
from brickcad.course_straight_rail import build_course, StraightChannel
from brickcad.verify import exact_bounds


class StraightRailCourseTests(unittest.TestCase):
    def test_rail_geometry_and_marking_are_current(self):
        spec = {"channel": "standard", "length_mm": 63.8}
        bare, profile = build_course("R01-V1", spec, marked=False)
        marked, _ = build_course("R01-V1", spec, marked=True)
        self.assertTrue(bare.isValid() and marked.isValid())
        self.assertEqual(len(bare.Solids()), 1)
        self.assertEqual(len(marked.Solids()), 1)
        self.assertEqual(profile.fit_profile_id, "duplo-e27-play-v1")
        self.assertAlmostEqual(profile.tube_radius, TUBE_RADIUS_MM)
        self.assertEqual(len(profile.tubes()), 3)
        self.assertEqual((RECEIVER_DEPTH_MM, SLOT_END_Z_MM), (4.75, 3.50))
        self.assertTrue(all(abs(x-y)<.01 for x,y in
                            zip(exact_bounds(marked), (63.8, 31.65, 19.13))))
        removed = bare.cut(marked).Volume()
        self.assertGreater(removed, 0.2)
        self.assertLess(removed, 200)
        self.assertTrue(PRODUCTION_CONTRACT.startswith("issue37-e31-05"))

    def test_old_historical_fit_recipe_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            build_course("R01-V1", {
                "width_mm": 31.65, "length_mm": 63.8,
                "fit_profile": "duplo-straight-rail-trial-v1",
            }, marked=False)


if __name__ == "__main__":
    unittest.main()
