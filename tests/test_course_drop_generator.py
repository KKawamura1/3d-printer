"""CAD-free schema/constraint checks for shared steep-drop prototypes."""
import copy
import unittest
from pathlib import Path

from brickcad.course_drop_generator import load_spec, validate_spec

ROOT=Path(__file__).resolve().parents[1]


class SteepDropSchemaTests(unittest.TestCase):
    def test_east_south_share_one_generator(self):
        a=load_spec(ROOT/"experiments/course_drop_east/course.json")
        b=load_spec(ROOT/"experiments/course_drop_south/course.json")
        self.assertEqual(a["geometry"]["exit"],"east")
        self.assertEqual(b["geometry"]["exit"],"south")
        self.assertEqual(a["geometry"]["ramp_grade"],b["geometry"]["ramp_grade"])

    def test_bad_windows_slope_and_direction_rejected(self):
        spec=load_spec(ROOT/"experiments/course_drop_east/course.json")
        for key,new in (
            ("exit","north"),("ramp_grade",0.2),
            ("height_change",0),("kind","curve")):
            test=copy.deepcopy(spec)
            test["geometry"][key]=new
            with self.subTest(key=key),self.assertRaises(ValueError):
                validate_spec(test)
        test=copy.deepcopy(spec)
        test["enclosure"]["windows"]=[{"side":"south","x_mm":0,"width_mm":8}]
        with self.assertRaises(ValueError):
            validate_spec(test)


if __name__=="__main__":
    unittest.main()
