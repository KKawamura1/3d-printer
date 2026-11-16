"""Fast planning tests; expensive solid/mesh verification runs in Actions."""
import unittest

from brickcad.course_windows import CUTS, VERSIONS, WINDOW_HEIGHT, WINDOW_LENGTH, source_model, window_cutter
from scripts.course_followup_print import (
    EXPECTED_MISSING, PRINTED_PR56, missing_ids, split_plates,
)
from experiments.course_validation_plate.assemble import Rect, fits
from scripts.course_catalog import load_registry


class FollowupPhysicalValidationPlanTests(unittest.TestCase):
    def test_seven_remaining_models_are_exactly_the_catalogue_difference(self):
        models = {m["id"] for m in load_registry()["models"]}
        self.assertEqual(len(models), 20)
        self.assertEqual(models - PRINTED_PR56, EXPECTED_MISSING)
        self.assertEqual(set(missing_ids()), EXPECTED_MISSING)

    def test_only_large_closed_tunnels_get_new_windowed_version(self):
        self.assertEqual(len(VERSIONS), 6)
        self.assertEqual(set(CUTS), set(VERSIONS))
        self.assertEqual(len(set(VERSIONS.values())), 6)
        for original, new_id in VERSIONS.items():
            model = source_model(original)
            self.assertEqual(model["course"]["enclosure"], "tunnel")
            self.assertEqual(model["course"]["windows"], 0)
            self.assertNotEqual(original, new_id)
            box = window_cutter(original).BoundingBox()
            self.assertAlmostEqual(box.xlen, WINDOW_LENGTH, delta=.01)
            self.assertAlmostEqual(box.zlen, WINDOW_HEIGHT, delta=.01)
            # Every opening is above the lower floor / below the roof.
            self.assertGreater(box.zmin, 15)
            self.assertLess(box.zmax, 50)
        for invalid in ["C02-V8", "GC01-V5", "D01-V3", "S01-V8"]:
            with self.assertRaisesRegex(ValueError, "approved"):
                source_model(invalid)

    def test_all_large_windowed_meshes_fit_one_or_more_nonoverlapping_plates(self):
        # Representative actual nominal footprints; no resizing, 4 mm gaps.
        models = [Rect(name, 63.8, 63.8) for name in list(VERSIONS.values())[:4]]
        models += [Rect(name, 63.8, 31.8) for name in list(VERSIONS.values())[4:]]
        result = split_plates(models)
        ids = [m.id for plate in result for m in plate]
        self.assertEqual(set(ids), set(VERSIONS.values()))
        self.assertEqual(len(ids), len(VERSIONS))
        for plate in result:
            for i, pos in enumerate(plate):
                self.assertTrue(fits(pos, plate[:i] + plate[i+1:]))

    def test_seven_remaining_models_partioned_without_loss(self):
        # Five 4x4 + one 2x4 + one 2x2 (depending on placement):
        dimensions = [
            (63.8,63.8), (63.8,63.8), (63.8,63.8),
            (63.8,63.8), (63.8,63.8), (63.8,31.8),
            (31.8,31.8)
        ]
        items = [Rect(name,*dim) for name,dim in zip(sorted(EXPECTED_MISSING),dimensions)]
        plates = split_plates(items)
        self.assertEqual({m.id for plate in plates for m in plate}, EXPECTED_MISSING)
        self.assertGreaterEqual(len(plates), 2)


if __name__ == "__main__":
    unittest.main()
