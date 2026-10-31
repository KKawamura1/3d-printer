"""Targeted CAD checks for E29; not a toy safety or fatigue test."""
import unittest

import cadquery as cq

from brickcad.verify import exact_bounds
from experiments.dual_fit_e29.design import (
    VERSION, SPECIMENS, GROOVE_PROFILE, coupon, parameters,
    SLOT_WIDTH, SLOT_END_RADIUS, BEAD_MINOR_RADIUS,
)


class E29Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parts = {r["id"]: coupon(r) for r in SPECIMENS}

    def test_variants_are_unique_and_fit_on_bed(self):
        self.assertEqual(VERSION, "E29-V3")
        self.assertEqual(len(self.parts), 5)
        self.assertEqual(len({tuple(r["xy"]) for r in SPECIMENS}), 5)
        self.assertLess(max(r["xy"][0] for r in SPECIMENS) + 15.9, 180)
        self.assertLess(max(r["xy"][1] for r in SPECIMENS) + 15.9, 180)

    def test_single_solid_and_nominal_finish_dimensions(self):
        for name, (p, shape) in self.parts.items():
            with self.subTest(name=name):
                self.assertTrue(shape.isValid())
                self.assertEqual(len(shape.Solids()), 1)
                for actual, expected in zip(exact_bounds(shape),
                                            (31.8, 31.8, 23.7)):
                    self.assertAlmostEqual(actual, expected, places=4)
                self.assertEqual(p.cavity_xy, (25.4, 25.4))
                self.assertEqual(p.stud_height, 4.5)
                self.assertEqual(p.stud_radius, 4.7)

    def test_integral_features_are_not_thin_hooks(self):
        # Design intent guardrails, not an actual minimum-thickness/FEM proof.
        self.assertGreaterEqual(4.51-3.20, 1.30)  # grooved stud wall
        self.assertGreaterEqual(6.60-4.70, 1.80)  # receiver tube wall
        self.assertGreaterEqual(SLOT_WIDTH, 1.)
        self.assertGreaterEqual(SLOT_END_RADIUS, .6)
        self.assertEqual(BEAD_MINOR_RADIUS, .16)
        self.assertGreaterEqual(min(z for _, z in GROOVE_PROFILE), 1.)

    def test_profile_changes_are_local(self):
        p = [parameters(r) for r in SPECIMENS]
        self.assertEqual(p[0], p[1])  # Stud waist only: same receiver
        self.assertEqual(p[2].tube_radius, 6.65)
        self.assertEqual(p[3], p[4])  # Waist only: same slotted bead receiver

    def test_stud_and_receiver_factor_isolation(self):
        # Compare receiver region only; exterior E29-XX engravings differ.
        below = cq.Workplane("XY").box(27, 27, 19.2,
                        centered=(True, True, False)).val()
        for left, right in (("E29-01", "E29-02"),
                            ("E29-04", "E29-05")):
            a = self.parts[left][1].intersect(below)
            b = self.parts[right][1].intersect(below)
            self.assertLess(a.cut(b).Volume()+b.cut(a).Volume(), 1e-5)
        self.assertGreater(self.parts["E29-01"][1].Volume()
                           - self.parts["E29-02"][1].Volume(), 5.)

    def test_slotted_and_bead_receiver_do_not_change_top(self):
        upper = (cq.Workplane("XY", origin=(0,0,19.2))
                 .box(36,36,4.5,centered=(True,True,False)).val())
        a = self.parts["E29-01"][1].intersect(upper)
        for part_id in ("E29-03", "E29-04"):
            b = self.parts[part_id][1].intersect(upper)
            self.assertLess(a.cut(b).Volume()+b.cut(a).Volume(), 1e-5)


if __name__ == "__main__":
    unittest.main()
