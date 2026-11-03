"""Issue #60 CAD regressions for all configured course families.

CAD checks are not physical slicing or rolling tests.
"""
import math
from pathlib import Path
import unittest
from unittest.mock import patch
import cadquery as cq

from brickcad.course_downhill import build_course as build_downhill
from brickcad.course_steep_drop import build_course as build_drop, geometry_checks
from brickcad.course_sharp_curve import build_course as build_curve
from brickcad.course_generator_v2 import load_spec as downhill_recipe
from brickcad.course_drop_generator import load_spec as drop_recipe
from brickcad.course_curve_generator import load_spec as curve_recipe
from parts.tunnel.e31_fit import SLOT_END_Z, SLOT_END_RADIUS, slot_end_z_for_receiver_depth

ROOT = Path(__file__).resolve().parents[1] / "experiments"


class Issue60CourseRegressionTests(unittest.TestCase):
    def test_shallow_receiver_contract(self):
        self.assertAlmostEqual(SLOT_END_Z, 3.50)
        self.assertAlmostEqual(SLOT_END_RADIUS, .65)
        self.assertAlmostEqual(slot_end_z_for_receiver_depth(4.75), 3.50)
        self.assertAlmostEqual(slot_end_z_for_receiver_depth(17.60), 4.40)
        self.assertGreaterEqual(4.75-(SLOT_END_Z+SLOT_END_RADIUS),.60-1e-6)

    def test_each_new_family_has_cad_geometry(self):
        for kind,spec_file,load,build in [
            ("windows","course_windows_w01/course.json",downhill_recipe,build_downhill),
            ("east","course_drop_east/course.json",drop_recipe,build_drop),
            ("south","course_drop_south/course.json",drop_recipe,build_drop),
            ("curve-open","course_curve_open/course.json",curve_recipe,build_curve),
            ("curve-tunnel","course_curve_tunnel/course.json",curve_recipe,build_curve),
        ]:
            with self.subTest(kind=kind):
                shape,p,*_=build(load(ROOT/spec_file))
                self.assertTrue(shape.isValid())
                self.assertEqual(len(shape.Solids()),1)

    def test_final_standard_engravings_remove_real_wall(self):
        for kind,spec_file,load,build,face in [
            ("windows","course_windows_w01/course.json",downhill_recipe,build_downhill,"south"),
            ("east","course_drop_east/course.json",drop_recipe,build_drop,"south"),
            ("south","course_drop_south/course.json",drop_recipe,build_drop,"north"),
            ("curve-open","course_curve_open/course.json",curve_recipe,build_curve,"north"),
            ("curve-tunnel","course_curve_tunnel/course.json",curve_recipe,build_curve,"north"),
        ]:
            with self.subTest(kind=kind):
                spec=load(ROOT/spec_file)
                marked,p,*_=build(spec)
                if kind=="windows":
                    with patch("brickcad.course_downhill.engrave",
                               side_effect=lambda shape,label,**kwargs:shape):
                        blank,p,*_=build(spec)
                else:
                    blank,p,*_=build(spec,mark=False)
                removed=blank.cut(marked).clean()
                self.assertGreater(removed.Volume(),.2)
                bounds=removed.BoundingBox()
                edge=-p.depth/2 if face=="south" else p.depth/2
                actual=bounds.ymin if face=="south" else bounds.ymax
                self.assertAlmostEqual(actual,edge,delta=.06)
                self.assertLessEqual(bounds.ylen,.42)

    def test_steep_drop_mouths_and_gentle_slope(self):
        for side in ("east","south"):
            spec=drop_recipe(ROOT/("course_drop_"+side+"/course.json"))
            with self.subTest(side=side):
                shape,p,d=build_drop(spec)
                checks,*_=geometry_checks(shape,p,d,side)
                self.assertTrue(checks["visible_mouths_are_circular"])
                self.assertTrue(checks["short_receiver_slot_roof"])
                self.assertAlmostEqual(math.degrees(math.atan(d.ramp_grade)),14.03624347,places=4)


if __name__=="__main__":
    unittest.main()
