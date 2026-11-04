"""Incremental CAD validation for a configured R16 prototype."""
import unittest
from pathlib import Path

from brickcad.course_curve_generator import load_spec
from brickcad.course_sharp_curve import build_course, checks
from brickcad.verify import VOLUME_TOL

SPEC=Path(__file__).with_name("course.json")


class R16ConfigCadTests(unittest.TestCase):
    def test_configured_assembled_curve(self):
        spec=load_spec(SPEC)
        shape,p,path=build_course(spec)
        result,balls,too_big,bounds=checks(shape,p,path,spec["enclosure"]["kind"])
        self.assertTrue(all(result.values()),result)
        self.assertLess(max(balls),VOLUME_TOL)
        self.assertGreater(max(too_big),VOLUME_TOL)
        self.assertTrue(shape.isValid())


if __name__=="__main__":
    unittest.main()
