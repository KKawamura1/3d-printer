"""Issue #39 configured replay: validate recipe and the reference geometry."""
from pathlib import Path
import unittest
from brickcad.course_generator import load_spec, validate_spec, SUPPORTED

CONFIG = Path(__file__).with_name("course.json")


class ConfiguredCourseTest(unittest.TestCase):
    def test_recipe(self):
        spec = load_spec(CONFIG)
        self.assertEqual(spec, SUPPORTED[spec["geometry"]["kind"]])
        self.assertEqual(spec["id"] + "-" + spec["version"], spec["legacy"]["part_id"])

    def test_reject_unimplemented_options(self):
        spec = load_spec(CONFIG)
        spec["enclosure"] = dict(spec["enclosure"], windows=[{"side": "north"}])
        with self.assertRaisesRegex(ValueError, "explicit engine adapter"):
            validate_spec(spec)

    def test_reference_brep_and_ball_path(self):
        from parts.downhill_tunnel.design import (
            Downhill, build_downhill, sampled_ball_intersections, PART_ID
        )
        from brickcad.verify import VOLUME_TOL
        d = Downhill()
        shape, fit = build_downhill(d)
        self.assertEqual(PART_ID, "D01-V2")
        self.assertTrue(shape.isValid())
        self.assertEqual(len(shape.Solids()), 1)
        self.assertEqual((fit.nx, fit.ny), (4, 2))
        self.assertAlmostEqual(fit.tube_radius, 6.60)
        self.assertLess(max(sampled_ball_intersections(shape, d)), VOLUME_TOL)


if __name__ == "__main__":
    unittest.main()
