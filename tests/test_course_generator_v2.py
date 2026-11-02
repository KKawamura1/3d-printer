"""Fast tests of recipe constraints, no CadQuery or large meshes required."""
import copy
import json
from pathlib import Path
import unittest
from brickcad.course_generator_v2 import validate_spec, load_spec

PATH = Path(__file__).resolve().parents[1]/"experiments/course_windows_w01/course.json"


class ConfigurableDownhillSchemaTests(unittest.TestCase):
    def test_valid_recipe(self):
        spec = load_spec(PATH)
        self.assertEqual(spec["id"]+"-"+spec["version"], "W01-V1")
        self.assertEqual(len(spec["enclosure"]["windows"]), 2)

    def test_window_variations_supported(self):
        for windows in ([], [{"side":"south","x_mm":0,"width_mm":8}],
                        [{"side":"south","x_mm":-16,"width_mm":8},
                         {"side":"south","x_mm":0,"width_mm":8},
                         {"side":"south","x_mm":16,"width_mm":8}]):
            spec = load_spec(PATH)
            spec["enclosure"]["windows"] = windows
            self.assertEqual(validate_spec(spec), spec)

    def test_invalid_constraints_rejected(self):
        changes = [
            ("geometry",{"kind":"drop"}),
            ("connection",{"profile":"nominal"}),
            ("enclosure",{"kind":"open","windows":[]}),
            ("enclosure",{"kind":"tunnel","windows":[{"side":"north","x_mm":0,"width_mm":8}]}),
            ("enclosure",{"kind":"tunnel","windows":[{"side":"south","x_mm":0,"width_mm":24.26}]}),
            ("enclosure",{"kind":"tunnel","windows":[{"side":"south","x_mm":0,"width_mm":8},
                                                    {"side":"south","x_mm":5,"width_mm":8}]}),
        ]
        for field, value in changes:
            with self.subTest(field=field, value=value):
                spec = load_spec(PATH)
                spec[field] = value
                with self.assertRaises(ValueError):
                    validate_spec(spec)


if __name__ == "__main__":
    unittest.main()
