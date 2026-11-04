"""Half-section shift (V20) gives symmetric 1:2:2:1 negative space."""
import unittest

from experiments.course_window_rhythm.curve_facade import (
    DIVISIONS,TOTAL_WALL_MM,SEGMENTS as V19_INTERVALS,design as v19_design,
)
from experiments.course_window_rhythm.curve_facade_balanced import (
    SEGMENTS,PART_ID,SHIFT_MM,PITCH_MM,design,
)


class Symmetric12ths(unittest.TestCase):
    def test_exact_half_section_shift(self):
        self.assertEqual(PART_ID,"SD04-V20")
        self.assertEqual(SEGMENTS,((1.5,2.5),(5.5,6.5),(9.5,10.5)))
        self.assertEqual(V19_INTERVALS,((2,3),(6,7),(10,11)))
        for (a,b),(x,y) in zip(V19_INTERVALS,SEGMENTS):
            self.assertEqual(a-x,.5)
            self.assertEqual(b-y,.5)
        self.assertAlmostEqual(SHIFT_MM,TOTAL_WALL_MM/24)

    def test_visual_negative_space_ratio_is_one_two_two_one(self):
        # Gap lengths are measured on continuous surface arclength,
        # excluding the widths of the three window apertures.
        gaps=[SEGMENTS[0][0], SEGMENTS[1][0]-SEGMENTS[0][1],
              SEGMENTS[2][0]-SEGMENTS[1][1], DIVISIONS-SEGMENTS[2][1]]
        self.assertEqual(gaps,[1.5,3.,3.,1.5])
        self.assertEqual([v/gaps[0] for v in gaps],[1.,2.,2.,1.])
        self.assertAlmostEqual(sum(gaps)+sum(b-a for a,b in SEGMENTS),12)

    def test_all_three_windows_move_same_real_distance_along_curved_wall(self):
        before=v19_design()
        after=design()
        self.assertEqual(len(before),len(after))
        self.assertEqual([x.outer_face for x in after],["straight","curve","curve"])
        for a,b in zip(before,after):
            self.assertAlmostEqual(a.centre_wall_s-b.centre_wall_s,SHIFT_MM)
            self.assertAlmostEqual(b.centre_wall_s,
                                   (b.dividers[0]+b.dividers[1])/2*PITCH_MM)
            self.assertEqual(len(b.outline_local_xz),5)

    def test_still_slope_following_and_symmetric_in_physical_mm(self):
        objects=design()
        margins=[SEGMENTS[0][0]*PITCH_MM,(12-SEGMENTS[-1][1])*PITCH_MM]
        self.assertAlmostEqual(margins[0],margins[1])
        self.assertGreater(objects[0].floor_at_centre,objects[1].floor_at_centre)
        self.assertGreater(objects[1].floor_at_centre,objects[2].floor_at_centre)


if __name__=="__main__":
    unittest.main()
