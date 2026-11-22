"""Fast geometry-layout checks; expensive full BRep/STL runs are opt-in."""
import math
import unittest
from types import SimpleNamespace

import cadquery as cq
from brickcad.course_marking_v2 import (
    POLICY_ID, SIZE_MM, DEPTH_MM, MarkSite, mark_tool, engrave_large,
)

from brickcad.course_architectural_windows import (
    MIN_POST, VERSIONS, model, plan, window_centres,
)
from experiments.course_expanded_windows.design import (
    COMPACT_WINDOW_WIDTH, EXPANDED_CONVEX_COUNT, EXPANDED_FLAT_COUNT,
    TRIALS, expanded_facade, layout, minimum_solid_post,
    large_mark_site,
)


class ExpandedCourseWindowLayoutTests(unittest.TestCase):
    def test_new_ids_and_exclusion_of_sc02_and_fragile_small_parts(self):
        self.assertEqual(len(TRIALS), 6)
        self.assertEqual(len(set(TRIALS.values())), 6)
        for source, version in TRIALS.items():
            self.assertIn(source, VERSIONS)
            self.assertNotEqual(version, VERSIONS[source])
        self.assertNotIn("SC02-V12", TRIALS)  # Already in PR #85
        self.assertNotIn("C02-V8", TRIALS)
        self.assertFalse(any(k.startswith("S0") for k in TRIALS))
        self.assertNotIn("D01-V3", TRIALS)

    def test_all_trial_facades_increase_windows_with_solid_posts(self):
        expected = {
            "E01-V3": (6, 8), "E01L-V1": (6, 8),
            "SC02L-V6": (3, 5),
            "SD03-V11": (6, 8), "SD04-V10": (6, 8),
            "T01-V6": (3, 4),
        }
        for source in TRIALS:
            with self.subTest(source=source):
                faces, before, after = layout(source)
                self.assertEqual((before, after), expected[source])
                for face, centres, post in faces:
                    self.assertGreaterEqual(post, MIN_POST)
                    self.assertEqual(post, minimum_solid_post(face, centres))
                    self.assertEqual(len(set(centres)), len(centres))
                    self.assertTrue(all(0 < c < face.length for c in centres))
                    self.assertNotIn("concave", face.name)
                    self.assertNotEqual(face.kind, "concave")

    def test_short_facades_use_smaller_windows_not_weaker_pillars(self):
        for sid in ("E01-V3", "E01L-V1", "T01-V6"):
            for face in plan(model(sid)):
                updated, centres = expanded_facade(sid, face)
                self.assertEqual(len(centres), EXPANDED_FLAT_COUNT)
                self.assertAlmostEqual(updated.width, COMPACT_WINDOW_WIDTH)
                self.assertGreaterEqual(minimum_solid_post(updated, centres), MIN_POST)
                self.assertGreaterEqual(centres[0] - updated.width / 2, 3 - 1e-7)

    def test_curved_exterior_more_holes_without_changing_flat_or_concave(self):
        for sid in ("SC02L-V6", "SD03-V11", "SD04-V10"):
            faces = plan(model(sid))
            for face in faces:
                updated, centres = expanded_facade(sid, face)
                if face.kind == "convex":
                    self.assertEqual(len(centres), EXPANDED_CONVEX_COUNT)
                    self.assertGreater(updated.width, face.width)
                    self.assertGreaterEqual(minimum_solid_post(updated, centres), MIN_POST)
                    self.assertEqual(
                        tuple(round(c/face.length, 6) for c in centres),
                        tuple(round((i+1)/6, 6) for i in range(5)))
                else:
                    self.assertEqual(centres, window_centres(face))
                    self.assertEqual(updated, face)


    def test_shared_5mm_mark_policy_sites_for_all_six(self):
        self.assertEqual(SIZE_MM, 5.)
        self.assertEqual(DEPTH_MM, .4)
        self.assertEqual(POLICY_ID, "course-id-5mm-bold-recessed-v2")
        versions = {
            "E01-V3": "E01-V10", "E01L-V1": "E01L-V8",
            "SC02L-V6": "SC02L-V13", "SD03-V11": "SD03-V18",
            "SD04-V10": "SD04-V23", "T01-V6": "T01-V9",
        }
        self.assertEqual(TRIALS, versions)
        for sid in TRIALS:
            source = model(sid)
            fit = SimpleNamespace(width=63.8, depth=(31.8 if sid.startswith(("T01", "SD")) else 63.8))
            site = large_mark_site(sid, source, fit)
            self.assertIsInstance(site, MarkSite)
            self.assertIn(site.face, ("south", "west"))
            self.assertLess(site.z_mm, 13.)
            self.assertGreater(mark_tool(TRIALS[sid], site).Volume(), 0)

    def test_large_marker_rejects_actual_window_overlap(self):
        # Synthetic 3D plaque: an intact label works; same-sized hole behind
        # its glyph must fail instead of silently truncating the engraving.
        block = cq.Workplane("XY").box(50, 2, 30).val().translate((0, -1, 15))
        site = MarkSite("south", 0, -2, 10)
        label = "T01-V9"
        audit = SimpleNamespace(model_id=label, marked_labels=[])
        marked, details = engrave_large(block, block, label, site, audit=audit)
        self.assertTrue(marked.isValid())
        self.assertEqual(audit.marked_labels, [label])
        self.assertGreater(details["actual_material_coverage"], 0.7)
        self.assertLessEqual(details["window_mark_overlap_mm3"], .01)
        removed_wall = cq.Workplane("XY").box(35, 2, 9).val().translate((0, -1, 10))
        holed = block.cut(removed_wall).clean()
        with self.assertRaisesRegex(ValueError, "overlaps a window"):
            engrave_large(holed, block, label, site,
                          audit=SimpleNamespace(model_id=label, marked_labels=[]))
        with self.assertRaisesRegex(ValueError, "one correct"):
            engrave_large(block, block, label, site, audit=audit)


if __name__ == "__main__":
    unittest.main()
