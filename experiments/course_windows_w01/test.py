"""Validate configurable W01, and compare PR59 D01-V3 to its new CAD composition."""
import copy
import unittest

from brickcad.course_generator_v2 import load_spec, validate_spec
from brickcad.course_downhill import build_course, geometry_checks
from brickcad.verify import VOLUME_TOL
from parts.downhill_tunnel.design import build_downhill, Downhill
from pathlib import Path

SPEC = Path(__file__).with_name("course.json")


class ConfiguredDownhillTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = load_spec(SPEC)
        cls.shape, cls.p, cls.d = build_course(cls.spec)

    def test_two_window_course(self):
        checks, collisions, bounds = geometry_checks(
            self.shape, self.p, self.d, self.spec["enclosure"]["windows"])
        self.assertTrue(all(checks.values()), checks)
        self.assertLess(max(collisions), VOLUME_TOL)
        self.assertEqual(len(self.spec["enclosure"]["windows"]), 2)
        self.assertEqual((self.p.nx,self.p.ny), (4,2))

    def test_legacy_d01_brep_symmetrical_difference(self):
        # Exact legacy D01 spec through the newly composed BRep, not legacy exporter.
        reference_spec = copy.deepcopy(self.spec)
        reference_spec["id"], reference_spec["version"] = "D01", "V3"
        reference_spec["enclosure"]["windows"] = [
            {"side":"south","x_mm":x,"width_mm":8} for x in (-16,0,16)]
        validate_spec(reference_spec)
        rebuilt, _, _ = build_course(reference_spec)
        legacy, _ = build_downhill(Downhill())
        self.assertTrue(rebuilt.isValid() and legacy.isValid())
        self.assertLess(legacy.cut(rebuilt).Volume(), .05)
        self.assertLess(rebuilt.cut(legacy).Volume(), .05)


if __name__ == "__main__":
    unittest.main()
