"""Fast design-contract tests for the single-SD04 aesthetic window pilot."""
import unittest

from experiments.course_window_rhythm.design import (
    PART_ID, SOURCE_ID, CENTRES_X_MM, WIDTH_MM, STRAIGHT_SECTION,
    WINDOW_COUNT, MIN_RIB_MM, MIN_EDGE_MARGIN_MM,
    design_windows, cut_pentagon, recipe,
)


class SingleFacadeWindowRhythmTests(unittest.TestCase):
    def test_only_one_new_version_not_silent_edit(self):
        self.assertEqual(PART_ID,"SD04-V17")
        self.assertEqual(SOURCE_ID,"SD04-V10")
        self.assertEqual(WINDOW_COUNT,3)

    def test_exactly_three_evenly_spaced_pointed_windows(self):
        windows=design_windows()
        self.assertEqual(len(windows),3)
        x=[w.centre_x for w in windows]
        self.assertEqual(tuple(x),CENTRES_X_MM)
        self.assertAlmostEqual(x[1]-x[0],x[2]-x[1])
        self.assertAlmostEqual(x[1]-x[0],8.)
        left=x[0]-WIDTH_MM/2-STRAIGHT_SECTION[0]
        right=STRAIGHT_SECTION[1]-(x[-1]+WIDTH_MM/2)
        self.assertAlmostEqual(left,right)
        self.assertGreaterEqual(left,MIN_EDGE_MARGIN_MM)
        self.assertGreaterEqual(x[1]-x[0]-WIDTH_MM,MIN_RIB_MM)

    def test_five_sided_gothic_arched_windows_follow_slope_in_unison(self):
        windows=design_windows()
        for w in windows:
            self.assertEqual(len(w.outline_xz),5)
            l,r=w.outline_xz[:2]
            shoulder=w.outline_xz[2]
            tip=w.outline_xz[3]
            self.assertAlmostEqual(r[0]-l[0],WIDTH_MM)
            self.assertAlmostEqual(tip[0],w.centre_x)
            self.assertGreater(tip[1],shoulder[1])
            self.assertGreater(tip[1]-w.floor_z,20.)
            self.assertLess(tip[1]-w.floor_z,23.)
            self.assertGreater(cut_pentagon(w).Volume(),30.)
        f=[w.floor_z for w in windows]
        self.assertGreater(f[0],f[1])
        self.assertGreater(f[1],f[2])

    def test_mirror_geometry_and_inlet_only_facade(self):
        cfg=recipe()
        self.assertTrue(cfg.mirror)
        self.assertEqual(cfg.route,"sharp")
        self.assertTrue(cfg.tunnel)
        windows=design_windows(cfg)
        for w in windows:
            self.assertGreater(min(pt[0] for pt in w.outline_xz),STRAIGHT_SECTION[0])
            self.assertLess(max(pt[0] for pt in w.outline_xz),STRAIGHT_SECTION[1])


if __name__=="__main__":
    unittest.main()
