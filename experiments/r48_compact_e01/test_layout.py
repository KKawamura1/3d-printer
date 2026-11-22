"""Fast checks for the issue #89 E01/SC02 shape-language experiment.

Does not export STL or regenerate the old 20-shape catalog.
"""
import unittest

from brickcad.course_contract import course_fit
from brickcad.course_r48_sloped_tunnel import curved_footprint
from brickcad.course_r48_tunnel import RoofSettings
from brickcad.standards import BALL_TRACK

from experiments.r48_compact_e01.design import (
    PART_ID, RECIPE, SOURCE_ID, full_tube_centres, validate_mouth_clearance,
)


class CompactR48LayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mask = curved_footprint()
        cls.fit = course_fit(nx=4, ny=4, height_units=2)

    def test_model_is_opt_in_new_version(self):
        self.assertEqual(PART_ID, "E01-V11")
        self.assertEqual(SOURCE_ID, "E01-V3")
        self.assertEqual(RoofSettings.parse(RECIPE).radius_mm, 48)

    def test_shared_sloped_footprint_is_a_solid(self):
        self.assertTrue(self.mask.isValid())
        self.assertEqual(len(self.mask.Solids()), 1)

    def test_ports_keep_original_ball_track_mouth(self):
        self.assertGreater(BALL_TRACK.opening, BALL_TRACK.ball_diameter)
        self.assertIsNone(validate_mouth_clearance(self.mask))

    def test_complete_tube_centres_are_e31_safe(self):
        self.assertEqual(
            set(full_tube_centres(self.fit, self.mask)),
            {(-16.0, -16.0), (0.0, 0.0), (16.0, 16.0)},
        )
        # The original 4x4 support grid has 9 tubes. Six are either cut or
        # absent from the new silhouette and must not receive E31 full slots.
        self.assertEqual(len(self.fit.tubes()), 9)

    def test_sloped_outline_reduces_outer_footprint(self):
        # This corner of the old 4x4 box is intentionally eliminated.
        import cadquery as cq
        self.assertFalse(self.mask.isInside(cq.Vector(-24., 24., 10.)))
        self.assertTrue(self.mask.isInside(cq.Vector(0., 0., 10.)))


if __name__ == "__main__":
    unittest.main()
