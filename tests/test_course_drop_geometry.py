"""CAD tests: single reusable steep-drop BRep with two different exit ports."""
import unittest
from pathlib import Path

from brickcad.course_drop_generator import load_spec
from brickcad.course_steep_drop import (
    build_course,geometry_checks,ball_centres,ports,exit_parameters,
)
from brickcad.standards import BALL_TRACK, DUPLO


class ConfiguredDropTests(unittest.TestCase):
    def test_east_and_south_outputs(self):
        root=Path(__file__).resolve().parents[1]
        shapes=[]
        for side,reference_rise in (("east",9.75),("south",8.45)):
            with self.subTest(exit=side):
                spec=load_spec(root/("experiments/course_drop_"+side+"/course.json"))
                shape,p,d=build_course(spec)
                checks,samples,sweeps,bounds=geometry_checks(shape,p,d,side)
                self.assertTrue(all(checks.values()),checks)
                self.assertEqual((p.nx,p.ny), (2,2))
                self.assertAlmostEqual(
                    d.ramp_grade*(d.ramp_end-exit_parameters(side)),reference_rise)
                self.assertAlmostEqual(ports(side,d)[0].floor_xyz_mm[2]-
                                       ports(side,d)[1].floor_xyz_mm[2],DUPLO.height)
                self.assertAlmostEqual(ports(side,d)[1].floor_xyz_mm[2], BALL_TRACK.floor)
                self.assertTrue(shape.isValid())
                shapes.append(shape)
        self.assertNotAlmostEqual(shapes[0].Volume(),shapes[1].Volume(),delta=1e-4)


if __name__=="__main__":
    unittest.main()
