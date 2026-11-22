"""Fast layout and design contract tests; actual CAD/STL is opt-in."""
import math
import unittest

from brickcad.course_architectural_windows import model
from brickcad.course_marking_v2 import SIZE_MM
from brickcad.course_r48_sloped_tunnel import curved_footprint
from experiments.course_compact_r48.design import (
    ARC_LENGTH, INNER_RADIUS, OUTER_RADIUS, TRIALS, WINDOWS,
    WINDOW_WIDTH_MM, min_post_mm, outer_facade, window_stations,
)


class CompactE01LayoutTests(unittest.TestCase):
    def test_versions_source_only_horizontal_e01(self):
        self.assertEqual(TRIALS, {
            "E01-V3": "E01-V11", "E01L-V1": "E01L-V9"})
        for source_id in TRIALS:
            m = model(source_id)
            self.assertEqual(m["course"]["slope"], "horizontal")
            self.assertEqual(m["source"]["recipe"]["radius_mm"], 48)
        self.assertEqual(SIZE_MM, 5.)

    def test_sightlines_track_r48_for_right_and_left(self):
        for left in (False, True):
            f = outer_facade(left)
            for t in (0, .125, .5, .875, 1):
                wall, normal, target, floor = f.sample(ARC_LENGTH*t)
                self.assertAlmostEqual(
                    math.hypot(wall[0]+32, wall[1]-( -32 if left else 32)),
                    OUTER_RADIUS, delta=.001)
                self.assertAlmostEqual(
                    math.hypot(target[0]+32,
                               target[1]-(-32 if left else 32)),
                    48, delta=.001)
                self.assertAlmostEqual(
                    normal[0]*(target[0]-wall[0])+
                    normal[1]*(target[1]-wall[1]),
                    OUTER_RADIUS-48, delta=.01)
                self.assertAlmostEqual(floor, target[2]-13.0,delta=1.)

    def test_nine_window_posts_preserve_strength_margin(self):
        s = window_stations()
        self.assertEqual(len(s), WINDOWS)
        self.assertEqual(WINDOWS, 9)
        self.assertEqual(WINDOW_WIDTH_MM, 6.5)
        self.assertGreater(min_post_mm(s), 3.)
        self.assertLess(min_post_mm(s), 4.)
        self.assertGreater(OUTER_RADIUS, INNER_RADIUS)
        self.assertAlmostEqual(ARC_LENGTH, OUTER_RADIUS*math.pi/2)

    def test_uses_sc02_actual_footprint(self):
        footprint = curved_footprint()
        self.assertTrue(footprint.isValid())
        self.assertGreater(footprint.Volume(), 0)


if __name__=="__main__":
    unittest.main()
