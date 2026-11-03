"""Regression for issue #39 replay source isolation after PR #59."""
import unittest

from cad_versions import ROOT, model_sources


class CourseReplaySourceIsolationTests(unittest.TestCase):
    def test_t01_and_d01_fingerprint_only_their_reference_exporter(self):
        tunnel = model_sources(ROOT, "experiments/course_replay_t01")
        downhill = model_sources(ROOT, "experiments/course_replay_d01")
        self.assertIn("parts/tunnel/design_e31.py", tunnel)
        self.assertNotIn("parts/downhill_tunnel/design.py", tunnel)
        self.assertIn("parts/downhill_tunnel/design.py", downhill)
        self.assertNotIn("parts/tunnel/design_e31.py", downhill)


if __name__ == "__main__":
    unittest.main()
