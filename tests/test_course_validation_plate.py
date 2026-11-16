"""Fast, CAD-free regression checks for the PR56 A1 mini packing job."""
import unittest

import numpy as np

from brickcad.course_contract import PRODUCTION_CONTRACT
from experiments.course_validation_plate import assemble as plate
from scripts.course_catalog import load_registry


class TestPR56OnePlate(unittest.TestCase):
    def test_targets_include_all_untested_and_only_one_printed_control(self):
        selected = plate.targets(load_registry())
        self.assertEqual(len(selected), 17)
        self.assertEqual(len(set(selected)), 17)
        self.assertEqual(set(selected) & plate.PR55_STAGE1, {plate.CONTROL_ID})
        self.assertIn("R01-V1", selected)
        self.assertNotIn("RAIL-LEGACY", selected)
        self.assertIn("T01-V6", selected)

    def test_small_rectangles_all_fit_and_keep_reference(self):
        shapes = [plate.Rect(plate.CONTROL_ID, 31.8, 31.8)]
        shapes += [plate.Rect(f"X{i}", 31.8, 31.8, 3) for i in range(9)]
        packed = plate.pack(shapes, attempts=24)
        self.assertEqual(len(packed), 10)
        self.assertEqual(packed[0].id, plate.CONTROL_ID)
        for i, rectangle in enumerate(packed):
            self.assertTrue(plate.fits(rectangle, packed[:i] + packed[i + 1:]))

    def test_oversize_candidate_is_excluded_not_cropped(self):
        packed = plate.pack([
            plate.Rect(plate.CONTROL_ID, 31.8, 31.8),
            plate.Rect("HUGE", 190, 20),
            plate.Rect("GOOD", 50, 50),
        ], attempts=16)
        self.assertEqual({p.id for p in packed}, {plate.CONTROL_ID, "GOOD"})

    def test_missing_reference_fails(self):
        with self.assertRaisesRegex(ValueError, "mandatory"):
            plate.pack([plate.Rect("OTHER", 31.8, 31.8)])

    def test_bad_production_evidence_is_rejected(self):
        data = {
            "production_contract": PRODUCTION_CONTRACT,
            "models": [{
                "id": "R01-V1",
                "source": {"kind": "configured"},
                "geometry_verified": True,
                "legacy_unverified_e31": False,
                "production_contract": PRODUCTION_CONTRACT,
                "contract_evidence": {
                    "model_id": "R01-V1",
                    "production_contract": PRODUCTION_CONTRACT,
                    "fit_calls": 1,
                    "e31_receiver_calls": 1,
                    "final_marking_labels": ["WRONG-V1"],
                },
            }],
        }
        with self.assertRaisesRegex(ValueError, "engraving evidence"):
            plate.audit_source(data, ["R01-V1"])
        data["models"][0]["contract_evidence"]["final_marking_labels"] = ["R01-V1"]
        self.assertIn("R01-V1", plate.audit_source(data, ["R01-V1"]))

    def test_mesh_rotation_preserves_z_and_normal_length(self):
        mesh = np.zeros(1, dtype=plate.DTYPE)
        mesh["vertices"][0] = [[3, 4, 2], [5, 4, 2], [3, 6, 2]]
        mesh["normal"][0] = [0, 0, 1]
        rotated, lo, hi = plate.transform(
            mesh, plate.Placement("TEST", 7, 9, 2, 2, 90))
        self.assertAlmostEqual(lo[0], 7)
        self.assertAlmostEqual(lo[1], 9)
        self.assertAlmostEqual(lo[2], 0)
        self.assertAlmostEqual(hi[0], 9)
        self.assertAlmostEqual(hi[1], 11)
        self.assertEqual(rotated["normal"][0, 2], 1)
        self.assertTrue(np.all(mesh["vertices"][0, :, 2] == 2))


if __name__ == "__main__":
    unittest.main()
