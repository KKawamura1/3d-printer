"""CAD-free strict validation of PR36-inspired shared R16 recipe."""
import copy
import unittest
from pathlib import Path
from brickcad.course_curve_generator import load_spec,validate_spec

ROOT=Path(__file__).resolve().parents[1]


class CurveConfigTests(unittest.TestCase):
    def test_variants_use_same_route(self):
        specs=[load_spec(ROOT/"experiments"/("course_curve_"+k)/"course.json")
               for k in ("open","tunnel")]
        self.assertEqual([s["enclosure"]["kind"] for s in specs],["open","tunnel"])
        self.assertEqual([s["geometry"]["radius_mm"] for s in specs],[16,16])
        self.assertEqual([s["connection"]["studs"] for s in specs],["none","roof_four"])

    def test_unimplemented_options_rejected(self):
        src=load_spec(ROOT/"experiments/course_curve_tunnel/course.json")
        for group,key,value in [
            ("geometry","radius_mm",48),("geometry","exit","north"),
            ("geometry","height_change",-1),("geometry","size",[4,4,2]),
            ("enclosure","windows",[{"side":"north","x_mm":0}]),
            ("connection","studs","none")]:
            with self.subTest(group=group,key=key):
                a=copy.deepcopy(src)
                a[group][key]=value
                with self.assertRaises(ValueError):
                    validate_spec(a)
        a=copy.deepcopy(src)
        a["id"]="C02"
        with self.assertRaises(ValueError):
            validate_spec(a)


if __name__=="__main__":
    unittest.main()
