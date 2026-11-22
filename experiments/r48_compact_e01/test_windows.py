"""Quick geometric design checks for the E01-V12 window layout."""
import math
import unittest

from experiments.r48_compact_e01.windowed import (
    MODEL_ID, OUTER_RADIUS, WINDOW_COUNT, WINDOW_WIDTH, WINDOW_DEPTH,
    WINDOW_Z, window_centres, window_cutters
)


class TestE01WindowLayout(unittest.TestCase):
    def test_window_count_and_spacing(self):
        centres = window_centres()
        self.assertEqual(MODEL_ID, "E01-V12")
        self.assertEqual(len(centres), WINDOW_COUNT)
        gap = centres[1] - centres[0] - WINDOW_WIDTH
        self.assertGreaterEqual(gap, 2.5)
        arc = OUTER_RADIUS * math.pi / 2
        self.assertGreaterEqual(centres[0] - WINDOW_WIDTH / 2, 2.5)
        self.assertGreaterEqual(arc - centres[-1] - WINDOW_WIDTH / 2, 2.5)

    def test_cutters_are_valid_solid_pentagonal_prisms(self):
        cutters = list(window_cutters())
        self.assertEqual(len(cutters), WINDOW_COUNT)
        for cutter in cutters:
            self.assertTrue(cutter.isValid())
            self.assertEqual(len(cutter.Solids()), 1)
            self.assertGreater(cutter.Volume(), 200)
        self.assertLess(WINDOW_Z[-1], 38.4 - 1.6)
        self.assertGreater(WINDOW_Z[0], 6.35 + 2)

if __name__ == "__main__":
    unittest.main()
