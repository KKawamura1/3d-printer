"""Check window placement against actual centreline and vertical ball trajectory.

Fast design tests are complemented by a slow, physical-geometry workflow that
verifies line-of-sight through the manufactured BRep and watertight STLs.
"""
import math
import unittest

from brickcad.course_visibility_windows import (
    VISIBLE_DUAL_IDS, VISIBLE_SINGLE_IDS, BOTTOM_ABOVE_FLOOR,
    CURVED_SAMPLES, E01_FRONT, E01_EXIT, SHARP_SAMPLES,
    track_at, view_plan, _cutter, canonical_model,
)
from brickcad.standards import BALL_TRACK
from scripts.course_followup_print import EXPECTED_MISSING


class SightlineWindowPlanningTests(unittest.TestCase):
    def test_all_four_unprinted_closed_cad_kinds_have_new_unique_versions(self):
        closed = {"E01-V3", "SC02-V12", "SD04-V10", "S01-V8"}
        self.assertEqual(set(VISIBLE_DUAL_IDS)&EXPECTED_MISSING,closed)
        self.assertEqual(set(VISIBLE_SINGLE_IDS),{"SD04-V10"})
        self.assertEqual(len(VISIBLE_DUAL_IDS),7)
        self.assertEqual(len(set(VISIBLE_DUAL_IDS.values())),7)
        self.assertTrue(set(VISIBLE_DUAL_IDS.values()).isdisjoint(
            set(VISIBLE_SINGLE_IDS.values())))

    def test_horiz_r48_windows_see_start_middle_and_end_not_one_corner(self):
        for sid in ("E01-V3","E01L-V1"):
            model=canonical_model(sid)
            views=view_plan(sid,model["source"]["recipe"])
            self.assertEqual([len(side) for side in views],[3,3])
            tvalues=sorted({v.t for face in views for v in face})
            self.assertLess(tvalues[0],.2)
            self.assertGreater(tvalues[-1],.8)
            self.assertTrue(any(v.face=="east" for v in views[1]))
            self.assertEqual([v.t for v in views[0]],list(E01_FRONT))
            self.assertEqual([v.t for v in views[1]],list(E01_EXIT))
            self.assertTrue(all(abs(v.floor_mm-BALL_TRACK.floor)<1e-8
                                for face in views for v in face))

    def test_sloped_r48_windows_follow_real_curve_with_inclined_heights(self):
        for sid in ("SC02-V12","SC02L-V6"):
            model=canonical_model(sid)
            recipe=model["source"]["recipe"]
            views=view_plan(sid,recipe)
            self.assertEqual([len(x) for x in views],[3,3])
            self.assertEqual([v.t for v in views[0]],list(CURVED_SAMPLES))
            for i in range(3):
                self.assertEqual(views[0][i].t,views[1][i].t)
                self.assertEqual(views[0][i].floor_mm,views[1][i].floor_mm)
                outer=views[0][i]
                x,y,z=outer.track_xyz
                # Radial cutter origin is outside the curved exterior wall
                # (the closest wall to this part of the ball's track).
                cx,cy=-32.,32. if recipe["direction"]=="right" else -32.
                self.assertAlmostEqual(math.hypot(
                    outer.origin_xyz[0]-cx,outer.origin_xyz[1]-cy),65.5,delta=.001)
                n=outer.inward_xy
                dx=x-outer.origin_xyz[0]
                dy=y-outer.origin_xyz[1]
                self.assertGreater(dx*n[0]+dy*n[1],10)
            self.assertGreater(views[0][0].window_bottom,
                               views[0][-1].window_bottom+16.)
            self.assertTrue(all(abs(v.window_bottom-v.floor_mm-
                                    BOTTOM_ABOVE_FLOOR)<1e-8
                                for face in views for v in face))

    def test_sharp_corners_have_viewpoints_along_full_track(self):
        for sid in ("SD03-V11","SD04-V10"):
            model=canonical_model(sid)
            views=view_plan(sid,model["source"]["recipe"])
            self.assertEqual([len(side) for side in views],[3,2])
            self.assertEqual([v.t for v in views[0]],list(SHARP_SAMPLES))
            self.assertEqual(views[0][-1].face,"sharp_outer")
            self.assertGreater(views[0][0].window_bottom,
                               views[0][-1].window_bottom+10)
            # First two samples are along the straight inlet,
            # last moves around the curved outlet.
            self.assertLess(views[0][0].track_xyz[0],
                            views[0][1].track_xyz[0])
            self.assertGreater(views[0][-1].track_xyz[0],0)

    def test_every_cut_is_local_tall_pentagon_viewing_toward_its_ball(self):
        for sid in VISIBLE_DUAL_IDS:
            model=canonical_model(sid)
            for face in view_plan(sid,model["source"]["recipe"]):
                for v in face:
                    with self.subTest(part=sid,t=v.t,face=v.face):
                        nx,ny=v.inward_xy
                        self.assertAlmostEqual(nx*nx+ny*ny,1.,delta=1e-6)
                        dx=v.track_xyz[0]-v.origin_xyz[0]
                        dy=v.track_xyz[1]-v.origin_xyz[1]
                        self.assertGreater(dx*nx+dy*ny,3)
                        self.assertGreater(v.window_peak-v.window_bottom,
                                           v.width_mm*2)
                        self.assertLess(v.window_bottom,v.track_xyz[2])
                        self.assertGreater(v.window_shoulder,v.track_xyz[2])
                        self.assertGreater(_cutter(v).Volume(),30.)

    def test_small_steep_drop_uses_one_tall_sightline_per_side(self):
        model=canonical_model("S01-V8")
        plan=view_plan("S01-V8",model["source"]["recipe"])
        self.assertEqual([len(v) for v in plan],[1,1])
        self.assertEqual({face[0].face for face in plan},{"south","north"})
        self.assertLess(plan[0][0].window_bottom,16)
        self.assertGreater(plan[0][0].window_peak,40)


if __name__=="__main__":
    unittest.main()
