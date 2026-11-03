"""Issue #60 regressions: mirrored geometry and unmirrored, visible left ID."""
import tempfile
import unittest
from pathlib import Path

import cadquery as cq

from brickcad.verify import intersection
from parts.sloped_curve_tunnel import design as right
from parts.sloped_curve_tunnel_left.design import PART_ID, SOURCE_RIGHT_ID, export


class SC02LeftTunnelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name)
        cls.report = export(cls.out)
        cls.shape = cq.importers.importStep(str(cls.out / "brick.step")).val()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_left_stl_and_right_source(self):
        self.assertEqual(PART_ID, "SC02L-V4")
        self.assertEqual(SOURCE_RIGHT_ID, "SC02-V10")
        self.assertEqual(self.report["part_id"], PART_ID)
        self.assertTrue(self.report["passed"], self.report["checks"])
        self.assertTrue(self.report["mesh"]["passed"])
        self.assertEqual(len(self.shape.Solids()), 1)
        self.assertEqual(self.report["direction"], "left")
        self.assertEqual(self.report["mirror"]["plane"], "XZ")
        self.assertFalse(self.report["physical_fit_validated"])
        self.assertFalse(self.report["physical_rolling_validated"])
        self.assertFalse(self.report["slicer_support_free_validated"])

    def test_port_mirroring(self):
        high, low = self.report["ports"]
        self.assertEqual(tuple(high["floor_xyz_mm"][:2]), (-32., 16.))
        self.assertEqual(tuple(low["floor_xyz_mm"][:2]), (16., -32.))
        self.assertEqual(tuple(low["outward"]), (0., -1., 0.))
        self.assertAlmostEqual(high["floor_xyz_mm"][2] - low["floor_xyz_mm"][2], 19.2)
        for key in ("high_west_circular_clear", "high_west_circular_rim",
                    "low_north_circular_clear", "low_north_circular_rim"):
            self.assertTrue(self.report["checks"][key], key)

    def test_post_mirror_standard_engraving(self):
        mark = self.report["marking"]
        self.assertEqual(mark["text"], PART_ID)
        self.assertEqual(mark["size_mm"], 3.)
        self.assertEqual(mark["depth_mm"], .4)
        self.assertEqual(mark["font"], "DejaVu Sans Bold")
        self.assertEqual(mark["y_mm"], -right.MARK_Y)
        self.assertTrue(mark["applied_after_cover_studs_and_mirroring"])
        self.assertTrue(self.report["checks"]["engraved_id_has_wall_negative_control"])
        self.assertTrue(self.report["checks"]["engraved_id_recess_remains_open"])
        # A readable left glyph cut is made on the original west plane,
        # NOT obtained by mirroring the already-marked right-hand body.
        cutter = cq.Workplane(cq.Plane(
            origin=(-31.9 + right.MARK_DEPTH, -right.MARK_Y, right.MARK_Z),
            xDir=(0, -1, 0), normal=(-1, 0, 0))).text(
            PART_ID, right.MARK_SIZE, right.MARK_DEPTH + .05,
            font="DejaVu Sans", kind="bold", combine=False).val()
        plain_wall = cq.Solid.makeBox(.5,20.,7.,
            cq.Vector(-31.9,-right.MARK_Y-10,right.MARK_Z-3.5))
        control = intersection(plain_wall, cutter)
        self.assertGreater(control,.2)
        self.assertLess(intersection(self.shape, cutter), .02*control)

    def test_clipped_supports_and_shortened_slots(self):
        self.assertEqual(len(self.report["receiver_supports"]["clipped_tubes"]), 4)
        self.assertEqual(self.report["e31_05"]["tube_count"], 3)
        self.assertFalse(self.report["e31_05"]["partial_tube_beads"])
        self.assertTrue(self.report["checks"]["e31_slot_ceiling_margin"])


    def test_step_roundtrip_precision_and_bounds(self):
        # Closed mesh plus single valid STEP solid, precise volume and bounds.
        result = self.report["step_roundtrip"]
        self.assertTrue(self.report["checks"]["step_roundtrip"])
        self.assertTrue(result["valid_solid"])
        self.assertEqual(result["relative_volume_tolerance"], 1e-6)
        self.assertEqual(result["volume_integration"], "brickcad.verify.precise_volume")
        self.assertLess(result["relative_volume_error"], 1e-6)
        self.assertLess(max(result["bounds_delta_mm"]), .02)

if __name__ == "__main__":
    unittest.main()
