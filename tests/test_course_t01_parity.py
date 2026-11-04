"""Guard independent T01 construction against the current T01-V6 BRep.

Compare both pre-fit and post-fit geometry to pinpoint structural regressions.
The existing original module is used only as a test oracle, never in production.
"""
import unittest
from unittest.mock import patch

from brickcad.course_straight_tunnel import build_course
from parts.tunnel import design_e31 as reference
import brickcad.course_straight_tunnel as independent
from parts.tunnel.e31_fit import add_e31_05_receiver_features as original_fit

TOLERANCE_MM3 = .001


def symmetric_difference(a, b):
    return (a.cut(b).Volume(), b.cut(a).Volume(),
            abs(a.Volume() - b.Volume()))


class IndependentStraightTunnelParityTests(unittest.TestCase):
    def test_unmarked_stages_match_current_t01(self):
        stages = {}

        def capture(prefix):
            def hook(shape, *args, **kwargs):
                stages[prefix + "_before_fit"] = shape
                result = original_fit(shape, *args, **kwargs)
                stages[prefix + "_after_fit"] = result
                return result
            return hook

        def no_mark(shape, *args, **kwargs):
            return shape

        with patch.object(reference, "add_e31_05_receiver_features",
                          capture("reference")), patch.object(reference, "engrave",
                          no_mark):
            baseline = reference.build_tunnel()[0]
        recipe = {"roof": "transition", "transition_mm": 4, "ceiling_mm": 34.8}
        with patch.object(independent, "add_e31_05_receiver_features",
                          capture("configured")):
            candidate = build_course("T01-V6", recipe, marked=False)[0]

        self.assertTrue(baseline.isValid())
        self.assertTrue(candidate.isValid())
        for phase in ("before_fit", "after_fit"):
            old = stages["reference_" + phase]
            new = stages["configured_" + phase]
            delta = symmetric_difference(old, new)
            print("T01 STAGE", phase, "reference volume", old.Volume(),
                  "configured volume", new.Volume(),
                  "missing/extra/delta", delta, flush=True)
            for d in delta:
                self.assertLessEqual(d, TOLERANCE_MM3,
                                     (phase, delta))
        for d in symmetric_difference(baseline, candidate):
            self.assertLessEqual(d, TOLERANCE_MM3)


if __name__ == "__main__":
    unittest.main()
