"""Small, affected-only tests for the four SC02 trial geometries.

Do not regenerate historical course geometry for an unrelated experiment.
The actual four STLs are validated once by the incremental artifact workflow.
"""
import unittest

from brickcad.course_architectural_windows import model, plan
from brickcad.course_r48_sloped_tunnel import _clearance_factor
from experiments.sc02_robustness.design import (
    SOURCE_ID, TRIALS, LARGE_WINDOW_COUNT, LARGE_WINDOW_WIDTH_MM,
    centres_for, check_plan,
)


class SC02RobustnessTests(unittest.TestCase):
    def test_trial_matrix_is_independent(self):
        self.assertEqual(
            [(t.part_id,t.radial_extra_mm,t.expanded_windows) for t in TRIALS],
            [('SC02-V18',.2,False), ('SC02-V19',.4,False),
             ('SC02-V20',0.,True), ('SC02-V21',.4,True)])

    def test_end_mouths_and_clearance_ramp(self):
        check_plan()  # compare actual wire vertices at both mouths
        self.assertEqual(_clearance_factor(0.),0.)
        self.assertEqual(_clearance_factor(1.),0.)
        self.assertAlmostEqual(_clearance_factor(.5),1.)
        self.assertTrue(0 < _clearance_factor(.1) < 1)

    def test_five_windows_have_separating_posts(self):
        faces=plan(model(SOURCE_ID))
        self.assertEqual(len(faces),1)
        face=faces[0]
        self.assertEqual(face.kind,'convex')
        centres=centres_for(face,True)
        self.assertEqual(len(centres),LARGE_WINDOW_COUNT)
        self.assertEqual(len(centres_for(face,False)),3)
        self.assertGreaterEqual(
            min(b-a for a,b in zip(centres,centres[1:]))-LARGE_WINDOW_WIDTH_MM,
            2.5,
        )
        self.assertGreaterEqual(centres[0]-LARGE_WINDOW_WIDTH_MM/2,2.5)
        self.assertGreaterEqual(face.length-centres[-1]-LARGE_WINDOW_WIDTH_MM/2,2.5)


if __name__=='__main__':
    unittest.main()
