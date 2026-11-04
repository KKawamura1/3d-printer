"""Checks for large and small side-window prototypes (without generating CAD)."""
import unittest

from brickcad.course_double_windows import (
    DOUBLE_VERSIONS, OTHER_CUTS, WALL_PROBES, dual_cutters, _pr56_model,
)
from brickcad.course_windows import VERSIONS
from scripts.course_followup_print import EXPECTED_MISSING


class DoubleWindowCourseTests(unittest.TestCase):
    def test_all_four_pr56_missing_tunnels_have_two_window_variants(self):
        missing_roofed = {
            "E01-V3", "SC02-V12", "SD04-V10", "S01-V8",
        }
        self.assertEqual(missing_roofed, set(DOUBLE_VERSIONS) & EXPECTED_MISSING)
        self.assertEqual(len(DOUBLE_VERSIONS), 7)
        self.assertEqual(len(set(DOUBLE_VERSIONS.values())), 7)
        self.assertFalse(set(DOUBLE_VERSIONS.values()) & set(VERSIONS.values()))

    def test_each_candidate_uses_two_properly_separated_side_wall_cuts(self):
        for original,new_id in DOUBLE_VERSIONS.items():
            with self.subTest(original=original):
                base = _pr56_model(original)
                self.assertEqual(base["course"]["windows"], 0)
                self.assertEqual(base["course"]["enclosure"], "tunnel")
                self.assertNotEqual(new_id, original)
                a,b = dual_cutters(original)
                box1,box2 = a.BoundingBox(),b.BoundingBox()
                self.assertLess(
                    (box1.ymin + box1.ymax)*(box2.ymin + box2.ymax), 0,
                    "Two cuts must be on opposite global Y faces")
                self.assertGreaterEqual(box1.zmin,19.)
                self.assertGreaterEqual(box2.zmin,19.)
                self.assertLessEqual(box1.zmax,48.)
                self.assertLessEqual(box2.zmax,48.)
                # The narrow 2x2 case must not reuse the 10-mm 4x4 cut.
                if original == "S01-V8":
                    self.assertLess(box1.xlen,8.)
                    self.assertLess(box2.xlen,8.)

    def test_two_side_wall_probes_exist(self):
        self.assertEqual(set(OTHER_CUTS),set(DOUBLE_VERSIONS))
        self.assertEqual(set(WALL_PROBES),set(DOUBLE_VERSIONS))
        for original,(outer,inner) in WALL_PROBES.items():
            self.assertEqual(len(outer),3)
            self.assertEqual(len(inner),3)
            self.assertTrue(outer[1]*inner[1]<0)

    def test_open_course_and_unknown_source_rejected(self):
        for invalid in ("GC01-V5", "SC03-V5","D01-V3","ABC-V1"):
            with self.assertRaisesRegex(ValueError,"two-sided"):
                dual_cutters(invalid)


if __name__=="__main__":
    unittest.main()
