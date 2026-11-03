"""Issue #37 horizontal R48 tunnel coverage and Issue #60 regression tests."""
import math
import tempfile
import unittest
from pathlib import Path

import cadquery as cq

from brickcad.verify import intersection, VOLUME_TOL
from parts.gentle_curve_tunnel.design import (
    PART_ID, LEFT_PART_ID, build_unmarked, mark_part,
    _mouth_round, export,
)
from parts.tunnel.design import Tunnel
from parts.tunnel.e31_fit import slot_end_z_for_receiver_depth


class GentleTunnelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base, cls.profile = build_unmarked()
        cls.right = mark_part(cls.base, cls.profile, "right")
        cls.left = mark_part(cls.base, cls.profile, "left")

    def test_e31_05_slots_and_full_supports(self):
        self.assertEqual(self.profile.tube_radius, 6.60)
        self.assertEqual(len(self.profile.tubes()), 9)
        self.assertEqual(len(self.profile.studs()), 16)
        self.assertEqual(slot_end_z_for_receiver_depth(Tunnel().cavity_height), 3.50)
        for shape in (self.right, self.left):
            self.assertTrue(shape.isValid())
            self.assertEqual(len(shape.Solids()), 1)
            # Below the running surface, between shallow cavity and track.
            self.assertTrue(shape.isInside(cq.Vector(0, 0, 5.0)))

    def test_both_circular_mouths_are_not_teardrops(self):
        self.assertTrue(_mouth_round(self.right, "right", Tunnel()))
        self.assertTrue(_mouth_round(self.left, "left", Tunnel()))

    def test_reflection_precedes_independent_engraving(self):
        self.assertGreater(self.base.Volume() - self.right.Volume(), .2)
        self.assertGreater(self.base.Volume() - self.left.Volume(), .2)
        # Neither version changes the 4x4 underside or the studs.
        for x, y in self.profile.tubes():
            self.assertFalse(self.right.isInside(cq.Vector(x, y, 1)))
            self.assertFalse(self.left.isInside(cq.Vector(x, y, 1)))
        for x, y in self.profile.studs():
            self.assertFalse(self.right.isInside(cq.Vector(x, y, 41)))
            self.assertFalse(self.left.isInside(cq.Vector(x, y, 41)))

    def test_paths_are_open_in_both_directions(self):
        from parts.elbow.design import ball_sweep
        self.assertLess(intersection(self.right, ball_sweep()), VOLUME_TOL)
        self.assertLess(intersection(self.left.mirror("XZ"), ball_sweep()), VOLUME_TOL)

    def test_direction_and_version_are_explicit(self):
        self.assertEqual((PART_ID, LEFT_PART_ID), ("E01-V3", "E01L-V1"))
        with self.assertRaises(ValueError):
            mark_part(self.base, self.profile, "other")

    def test_export_report_and_mesh(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = export(Path(tmp), direction="right")
            self.assertTrue(report["passed"], report["checks"])
            self.assertTrue(report["mesh"]["passed"])
            self.assertTrue(report["checks"]["circular_mouths"])
            self.assertTrue(report["checks"]["step_roundtrip"])
            self.assertFalse(report["physical_fit_validated"])
            self.assertFalse(report["physical_rolling_validated"])
