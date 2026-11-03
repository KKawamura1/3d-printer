"""Production Issue #37 catalogue: one recipe schema and one finish contract."""
import ast
import copy
import json
from pathlib import Path
import tempfile
import unittest

from scripts.course_catalog import CATEGORIES, load_registry, select, validate_geometry_recipe
from brickcad.course_contract import (
    CATEGORY_AXES, PRODUCTION_CONTRACT, course_axes, kernel_for, validate_course_axes,
)

ROOT = Path(__file__).resolve().parents[1]


class CourseCatalogTests(unittest.TestCase):
    def setUp(self):
        self.registry = load_registry()

    def reject(self, modified, pattern):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "registry.json"
            file.write_text(json.dumps(modified))
            with self.assertRaisesRegex(ValueError, pattern):
                load_registry(file)

    def test_full_coverage_and_all_use_the_same_contract(self):
        models = select(self.registry, "all")
        self.assertEqual(len(models), 20)
        self.assertEqual(sorted(n for m in models for n in m["issue37_no"]), CATEGORIES)
        self.assertEqual(set(CATEGORY_AXES), set(CATEGORIES))
        self.assertEqual(sum(len(m["issue37_no"]) == 2 for m in models), 3)
        self.assertTrue(all(m["source"]["kind"] == "configured" for m in models))
        self.assertTrue(all("family" not in m["source"] for m in models))
        self.assertNotIn("RAIL-LEGACY", {m["id"] for m in models})
        self.assertEqual(select(self.registry, "1")[0]["id"], "R01-V1")
        self.assertEqual(select(self.registry, "1")[0]["source"]["reference"]["pr"], 67)
        self.assertEqual({kernel_for(m["course"]) for m in models}, {
            "straight_rail", "straight_tunnel", "loft", "sharp_r16", "drop",
            "horizontal_r48_tunnel", "sloped_r48_tunnel", "downhill_windowed",
        })
        self.assertTrue(PRODUCTION_CONTRACT.startswith("issue37-e31-05"))

    def test_every_geometry_recipe_matches_the_four_axes(self):
        for model in self.registry["models"]:
            with self.subTest(model=model["id"]):
                self.assertEqual(validate_course_axes(
                    model["course"], model["issue37_no"]),
                    kernel_for(model["course"]))
                validate_geometry_recipe(
                    kernel_for(model["course"]), model["course"],
                    model["source"]["recipe"])

    def test_select_by_id_and_category(self):
        self.assertEqual([m["id"] for m in select(self.registry, "2,3")], ["GC01-V5"])
        self.assertEqual([m["id"] for m in select(self.registry, "E01-V3,S01-V8")],
                         ["E01-V3", "S01-V8"])
        with self.assertRaisesRegex(ValueError, "Unknown"):
            select(self.registry, "RAIL-LEGACY")

    def test_reject_missing_or_mismatched_axes(self):
        broken = copy.deepcopy(self.registry)
        broken["models"][0]["course"]["slope"] = "gentle"
        self.reject(broken, "axes disagree")
        broken = copy.deepcopy(self.registry)
        del broken["models"][0]["course"]["windows"]
        self.reject(broken, "axes disagree|requires slope")
        broken = copy.deepcopy(self.registry)
        broken["models"][-1]["issue37_no"] = [21]
        self.reject(broken, "axes disagree|23 categories")

    def test_reject_legacy_fit_or_generator_disguised_as_configured(self):
        for mutation in (
            {"family": "legacy_rail"},
            {"fit_profile": "duplo-straight-rail-trial-v1"},
            {"kind": "legacy"},
        ):
            with self.subTest(mutation=mutation):
                broken = copy.deepcopy(self.registry)
                broken["models"][-3]["source"].update(mutation)
                self.reject(broken, "only use axes-configured CAD")
        broken = copy.deepcopy(self.registry)
        rail = next(m for m in broken["models"] if m["id"] == "R01-V1")
        rail["source"]["recipe"]["fit_profile"] = "duplo-straight-rail-trial-v1"
        self.reject(broken, "standard channel")

    def test_direction_recipe_cannot_disagree_with_axes(self):
        broken = copy.deepcopy(self.registry)
        model = next(m for m in broken["models"] if m["id"] == "E01L-V1")
        model["source"]["recipe"]["direction"] = "right"
        self.reject(broken, "direction")
        broken = copy.deepcopy(self.registry)
        model = next(m for m in broken["models"] if m["id"] == "SD04-V10")
        model["source"]["recipe"]["mirror"] = False
        self.reject(broken, "Loft recipe")
        broken = copy.deepcopy(self.registry)
        model = next(m for m in broken["models"] if m["id"] == "D01-V3")
        model["course"]["windows"] = 0
        self.reject(broken, "axes disagree")

    def test_no_original_part_builders_in_production(self):
        names = (
            "course_loft_family", "course_configured_special",
            "course_r48_tunnel", "course_r48_sloped_tunnel",
            "course_downhill", "course_downhill_primitives",
            "course_straight_tunnel", "course_straight_rail",
        )
        for name in names:
            tree = ast.parse((ROOT / "brickcad" / (name + ".py")).read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    self.assertFalse(
                        node.module.startswith("parts.") and
                        node.module.endswith(".design"), name)
                if isinstance(node, ast.Import):
                    self.assertFalse(
                        any(x.name.startswith("parts.") and
                            x.name.endswith(".design") for x in node.names), name)
        source = (ROOT / "scripts/course_catalog.py").read_text()
        self.assertNotIn("course_legacy_rail", source)
        self.assertNotIn("parts.straight_rail.design", source)


if __name__ == "__main__":
    unittest.main()
