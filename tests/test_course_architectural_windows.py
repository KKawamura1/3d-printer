"""Fast, BRep-free validations for the full architectural windows policy.

The full geometry / sightline checks are explicitly opt-in and run separately:
they take minutes and should not delay other feature PRs.
"""
import math
import unittest

from brickcad.course_architectural_windows import (
    VERSIONS, FLAT_RATIO, CONVEX_RATIO, CONVEX_DIVIDERS,
    flat_centres, convex_centres, model, plan, window_centres,
    _window_geometry, SHARP_OUTER_RADIUS, R48_OUTER_RADIUS,
)
from scripts.course_catalog import load_registry


class ArchitecturalFacades(unittest.TestCase):
    def test_all_windowless_roofed_pr56_shapes_are_covered(self):
        roofed=[m for m in load_registry()["models"]
                if m["course"]["enclosure"]=="tunnel"]
        old={m["id"] for m in roofed if m["course"]["windows"]==0}
        self.assertEqual(set(VERSIONS),old)
        self.assertEqual(len(VERSIONS),11)
        self.assertEqual(len(set(VERSIONS.values())),len(VERSIONS))
        self.assertNotIn("D01-V3",VERSIONS)
        self.assertEqual(
            next(m for m in roofed if m["id"]=="D01-V3")["source"]["recipe"]["windows"],
            [-16,0,16])

    def test_flat_group_reproduces_d01_negative_space(self):
        centres=flat_centres(63.8,8)
        self.assertEqual(tuple(round(x,2) for x in centres),(15.94,31.9,47.86))
        margins=[centres[0]-4,
                 centres[1]-centres[0]-8,
                 centres[2]-centres[1]-8,
                 63.8-(centres[-1]+4)]
        ratios=tuple(round(x/margins[1],6) for x in margins)
        self.assertEqual(ratios,FLAT_RATIO)

    def test_convex_group_exact_half_section_v20_ratio(self):
        length=32+SHARP_OUTER_RADIUS*math.pi/2
        centres,width=convex_centres(length)
        expected=[length*2/12,length*6/12,length*10/12]
        for a,b in zip(centres,expected):
            self.assertAlmostEqual(a,b,places=7)
        margins=[centres[0]-width/2,
                 centres[1]-centres[0]-width,
                 centres[2]-centres[1]-width,
                 length-(centres[-1]+width/2)]
        self.assertEqual(tuple(round(x/margins[0],6) for x in margins),CONVEX_RATIO)
        self.assertEqual(CONVEX_DIVIDERS,((1.5,2.5),(5.5,6.5),(9.5,10.5)))

    def test_concave_never_becomes_a_facade(self):
        for source_id in VERSIONS:
            for f in plan(model(source_id)):
                with self.subTest(source=source_id,face=f.name):
                    self.assertIn(f.kind,{"flat","convex","single"})
                    self.assertNotIn("inner-concave",f.name)
                    centres=window_centres(f)
                    self.assertEqual(len(centres),1 if f.kind=="single" else 3)
                    self.assertTrue(all(0<c<f.length for c in centres))
                    self.assertEqual(len(set(centres)),len(centres))
                    self.assertGreater(f.width,0)
                    # The optical cutter's view must point towards its
                    # intended ball sample and stay above the nominal floor.
                    for s in centres:
                        cutter,geo=_window_geometry(f,s)
                        self.assertGreater(cutter.Volume(),10)
                        self.assertGreater(min(z for _,z in geo[4]),11.5)

    def test_sharp_curves_include_entire_outer_façade(self):
        for sid in ("SD03-V11","SD04-V10"):
            faces=plan(model(sid))
            self.assertEqual([f.name for f in faces],
                             ["straight-to-convex-outer","opposite-flat-only"])
            self.assertEqual([f.kind for f in faces],["convex","flat"])
            self.assertAlmostEqual(faces[0].length,
                                   32+31.9*math.pi/2)
            self.assertEqual(len(window_centres(faces[0])),3)
            self.assertEqual(len(window_centres(faces[1])),3)
            start=faces[0].sample(0)
            join=faces[0].sample(32)
            after=faces[0].sample(32.00001)
            self.assertAlmostEqual(start[0][0],-32)
            self.assertAlmostEqual(join[0][0],after[0][0],places=3)
            self.assertAlmostEqual(join[0][1],after[0][1],places=3)

    def test_r48_convex_but_no_inner_wall_perforation(self):
        for sid in ("SC02-V12","SC02L-V6"):
            faces=plan(model(sid))
            self.assertEqual(len(faces),1)
            self.assertEqual(faces[0].kind,"convex")
            self.assertAlmostEqual(faces[0].length,math.pi/2*R48_OUTER_RADIUS)
            for s in window_centres(faces[0]):
                wall,normal,ball,floor=faces[0].sample(s)
                dx=ball[0]-wall[0]
                dy=ball[1]-wall[1]
                self.assertAlmostEqual(math.hypot(*normal),1.,places=6)
                self.assertGreater(dx*normal[0]+dy*normal[1],15.)
                self.assertAlmostEqual(ball[2]-floor,12.13,delta=.01)


if __name__=="__main__":
    unittest.main()
