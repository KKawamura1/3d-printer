"""Fast checks for a reproducible nine-part overnight A1-mini witness."""
import unittest
import numpy as np

from scripts.course_followup_print import EXPECTED_MISSING
from scripts.course_overnight_plate import (
    OVERNIGHT_LAYOUT, WINDOWED_ON_PLATE, DUAL_ON_PLATE,
    OPEN_UNPRINTED, DTYPE, transform_for_plate,
    raster_projection, BED_MM,
)
import importlib.util


class OvernightPrintPlanTests(unittest.TestCase):
    def test_covers_seven_originals_plus_two_windowed_variants(self):
        names = [row[2] for row in OVERNIGHT_LAYOUT]
        self.assertEqual(len(names), 9)
        self.assertEqual(len(set(names)), 9)
        self.assertEqual(set(names), OPEN_UNPRINTED | set(WINDOWED_ON_PLATE))
        self.assertEqual(len(OPEN_UNPRINTED), 3)
        self.assertEqual(len(DUAL_ON_PLATE), 5)
        self.assertEqual(set(WINDOWED_ON_PLATE) - DUAL_ON_PLATE, {"SD04-V11"})
        self.assertEqual(EXPECTED_MISSING - OPEN_UNPRINTED,
                         {"E01-V3", "SC02-V12", "SD04-V10", "S01-V8"})
        self.assertTrue(
            (EXPECTED_MISSING - OPEN_UNPRINTED) <=
            {v for k,v in WINDOWED_ON_PLATE.items() if k in DUAL_ON_PLATE})
        self.assertEqual(BED_MM, 180.)

    def test_mesh_rotated_without_scaling_or_vertical_change(self):
        mesh = np.zeros(1, dtype=DTYPE)
        mesh["vertices"][0] = [[0.,0.,3.],[4.,0.,3.],[0.,2.,3.]]
        mesh["normal"][0] = [0., 0., 1.]
        for rot in range(4):
            with self.subTest(rot=rot):
                transformed = transform_for_plate(mesh, 20, 30, rot)
                self.assertEqual(len(transformed), 1)
                z = transformed["vertices"][0,:,2]
                self.assertTrue(np.allclose(z, [0., 0., 0.]))
                self.assertTrue(np.allclose(transformed["normal"][0], [0.,0.,1.]))
                a = transformed["vertices"][0,1,:2]-transformed["vertices"][0,0,:2]
                b = transformed["vertices"][0,2,:2]-transformed["vertices"][0,0,:2]
                self.assertAlmostEqual(float(np.linalg.norm(a)), 4.)
                self.assertAlmostEqual(float(np.linalg.norm(b)), 2.)
                if importlib.util.find_spec("cv2") is not None:
                    self.assertGreater(raster_projection(transformed).sum(), 0)

    def test_all_witness_points_have_bed_compatible_coordinates(self):
        for row,col,name,rot in OVERNIGHT_LAYOUT:
            self.assertGreaterEqual(row,0)
            self.assertGreaterEqual(col,0)
            self.assertLess(row,360)
            self.assertLess(col,360)
            self.assertIn(rot,(0,1,2,3))


if __name__ == "__main__":
    unittest.main()
