"""Fast, CAD-free validation of issue #39 recipes and safe failures."""
import copy
from pathlib import Path
import unittest
from brickcad.course_generator import SUPPORTED, validate_spec, load_spec


class CourseSchemaTests(unittest.TestCase):
    def test_all_reference_recipes(self):
        for kind, spec in SUPPORTED.items():
            with self.subTest(kind=kind):
                self.assertEqual(validate_spec(copy.deepcopy(spec)), spec)

    def test_reject_unsupported_shapes_and_options(self):
        original = copy.deepcopy(SUPPORTED["windowed_downhill_tunnel"])
        trials = []
        changed = copy.deepcopy(original); changed["geometry"]["size"] = [4, 4, 3]; trials.append(changed)
        changed = copy.deepcopy(original); changed["geometry"]["height_change"] = -2; trials.append(changed)
        changed = copy.deepcopy(original); changed["enclosure"]["windows"] = []; trials.append(changed)
        changed = copy.deepcopy(original); changed["connection"]["profile"] = "duplo-nominal-v1"; trials.append(changed)
        changed = copy.deepcopy(original); changed["legacy"]["module"] = "os"; trials.append(changed)
        for bad in trials:
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    validate_spec(bad)
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            validate_spec({"geometry": {"kind": "i_turn"}})

    def test_both_repo_recipes(self):
        root = Path(__file__).resolve().parents[1]
        for name in ("course_replay_t01", "course_replay_d01"):
            spec = load_spec(root / "experiments" / name / "course.json")
            self.assertEqual(spec, SUPPORTED[spec["geometry"]["kind"]])


if __name__ == "__main__":
    unittest.main()
