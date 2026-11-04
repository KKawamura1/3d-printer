"""Geometric plan checks for the 12-way divided outer wall."""
import math
import unittest

from experiments.course_window_rhythm.curve_facade import (
    PART_ID, TOTAL_WALL_MM, BEND_OUTER_RADIUS_MM, DIVISIONS, SEGMENTS,
    WINDOW_CENTRES_U, WINDOW_WIDTH_MM, STRAIGHT_WALL_MM,
    design, rail_s, wall_frame, path_target, window_cutter, recipe,
)


class TwelveEqualSections(unittest.TestCase):
    def test_exact_requested_division_intervals(self):
        self.assertEqual(PART_ID, "SD04-V19")
        self.assertEqual(DIVISIONS, 12)
        self.assertEqual(SEGMENTS, ((2,3),(6,7),(10,11)))
        self.assertEqual(WINDOW_CENTRES_U,(2.5/12,6.5/12,10.5/12))
        self.assertAlmostEqual(WINDOW_WIDTH_MM,TOTAL_WALL_MM/12,places=7)

    def test_lengths_and_spacing_apply_to_the_entire_bent_outer_wall(self):
        self.assertAlmostEqual(TOTAL_WALL_MM,
                               32+BEND_OUTER_RADIUS_MM*math.pi/2)
        windows=design()
        self.assertEqual(len(windows),3)
        self.assertEqual([w.outer_face for w in windows],
                         ["straight","curve","curve"])
        pitch=TOTAL_WALL_MM/12
        self.assertTrue(all(
            abs(w.centre_wall_s-((a+b)/2)*pitch)<1e-7
            for w,(a,b) in zip(windows,SEGMENTS)))
        self.assertAlmostEqual(windows[1].centre_wall_s-windows[0].centre_wall_s,
                               4*pitch)
        self.assertAlmostEqual(windows[2].centre_wall_s-windows[1].centre_wall_s,
                               4*pitch)

    def test_wall_is_tangent_continuous_at_straight_curve_join(self):
        cfg=recipe()
        before,n0,kind0=wall_frame(STRAIGHT_WALL_MM,cfg)
        after,n1,kind1=wall_frame(STRAIGHT_WALL_MM+0.00001,cfg)
        self.assertEqual((kind0,kind1),("straight","curve"))
        self.assertAlmostEqual(before[0],after[0],places=3)
        self.assertAlmostEqual(before[1],after[1],places=3)
        self.assertAlmostEqual(n0[0],n1[0],places=3)
        self.assertAlmostEqual(n0[1],n1[1],places=3)

    def test_every_opening_follows_floor_height_and_faces_actual_course(self):
        cfg=recipe()
        windows=design(cfg)
        for w in windows:
            self.assertEqual(len(w.outline_local_xz),5)
            floor=w.floor_at_centre
            lower=[p[1] for p in w.outline_local_xz[:2]]
            self.assertLess(max(lower), floor+8)
            self.assertGreater(min(lower), floor+6)
            self.assertLess(w.outline_local_xz[0][0],
                            w.outline_local_xz[1][0])
            self.assertGreater(w.outline_local_xz[3][1],max(
                w.outline_local_xz[2][1],
                w.outline_local_xz[4][1]))
            nx,ny=w.inward_xy
            self.assertAlmostEqual(nx*nx+ny*ny,1,places=5)
            dx=w.path_target_xyz[0]-w.wall_origin_xy[0]
            dy=w.path_target_xyz[1]-w.wall_origin_xy[1]
            self.assertGreater(dx*nx+dy*ny,15)
            self.assertGreater(window_cutter(w).Volume(),40)

        self.assertGreater(windows[0].floor_at_centre,windows[1].floor_at_centre)
        self.assertGreater(windows[1].floor_at_centre,windows[2].floor_at_centre)
        self.assertAlmostEqual(rail_s(TOTAL_WALL_MM),cfg.length)

    def test_full_facade_is_distinct_from_previous_v18(self):
        windows=design()
        self.assertLess(windows[0].centre_wall_s,STRAIGHT_WALL_MM)
        self.assertGreater(windows[1].centre_wall_s,STRAIGHT_WALL_MM)
        self.assertGreater(windows[2].centre_wall_s,STRAIGHT_WALL_MM)

if __name__=="__main__":
    unittest.main()
