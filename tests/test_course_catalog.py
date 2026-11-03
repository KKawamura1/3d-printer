import copy
import json
from pathlib import Path
import tempfile
import unittest
from scripts.course_catalog import CATEGORIES, load_registry, select


class CourseCatalogTests(unittest.TestCase):
    def setUp(self):
        self.registry = load_registry()

    def test_full_coverage_and_three_reversible_models(self):
        models = select(self.registry, "all")
        self.assertEqual(len(models), 20)
        self.assertEqual(sorted(n for m in models for n in m["issue37_no"]),
                         CATEGORIES)
        self.assertEqual(sum(len(m["issue37_no"]) == 2 for m in models), 3)
        self.assertEqual(sum(m["source"]["kind"] == "legacy" for m in models), 1)

    def test_select_by_id_and_category(self):
        models = select(self.registry, "2,3")
        self.assertEqual([m["id"] for m in models], ["GC01-V5"])
        self.assertEqual([m["id"] for m in select(self.registry, "E01-V3,S01-V8")],
                         ["E01-V3", "S01-V8"])

    def test_reject_bad_category_coverage(self):
        broken = copy.deepcopy(self.registry)
        broken["models"][-1]["issue37_no"] = [21]
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bad.json"
            p.write_text(json.dumps(broken))
            with self.assertRaisesRegex(ValueError, "23 categories"):
                load_registry(p)

    def test_reject_unknown_model(self):
        with self.assertRaisesRegex(ValueError, "Unknown"):
            select(self.registry, "NOT-A-CAD")


if __name__ == "__main__":
    unittest.main()
