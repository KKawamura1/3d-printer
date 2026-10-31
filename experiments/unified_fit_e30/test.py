"""Tests for E30 one-print consolidation; physical fit remains untested."""
import unittest

import cadquery as cq
from brickcad.verify import exact_bounds
from experiments.dual_fit_e29.design import parameters as e29_parameters
from experiments.receiver_contact_e28.design import parameters as e28_parameters
from experiments.unified_fit_e30.design import (
    VERSION, SOURCE_VERSIONS, SPECIMENS, plan, parameters, coupon,
)


class UnifiedFitE30Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.coupons = {r["id"]: coupon(r) for r in SPECIMENS}

    def test_version_and_nine_distinct_coupons(self):
        self.assertEqual(VERSION, "E30-V1")
        self.assertEqual(SOURCE_VERSIONS, {"E28":"E28-V1","E29":"E29-V3"})
        self.assertEqual(len(plan()), 9)
        self.assertEqual(len(self.coupons), 9)
        self.assertEqual(len({tuple(r["xy"]) for r in SPECIMENS}), 9)
        self.assertEqual(len({r["id"] for r in SPECIMENS}), 9)
        for row in SPECIMENS:
            x, y = row["xy"]
            self.assertTrue(15.9 <= x <= 164.1 and 15.9 <= y <= 164.1)

    def test_conditions_match_original_e28_and_e29(self):
        a,b,wall,tube,groove,slot,bead,ha,hb=[parameters(r) for r in SPECIMENS]
        self.assertEqual(a,b)
        self.assertEqual(a,e29_parameters(dict(kind="baseline")))
        self.assertEqual(wall,e28_parameters(dict(
            condition="wall_relief",cavity_xy_mm=[25.60,25.60],
            tube_od_mm=13.50)))
        self.assertEqual(tube,e28_parameters(dict(
            condition="tube_relief",cavity_xy_mm=[25.40,25.40],
            tube_od_mm=13.30)))
        self.assertEqual(groove,e29_parameters(dict(kind="groove")))
        self.assertEqual(slot,e29_parameters(dict(kind="slotted")))
        self.assertEqual(bead,e29_parameters(dict(kind="slotted_bead")))
        self.assertEqual(ha,hb)
        self.assertEqual(ha,e29_parameters(dict(kind="hybrid")))

    def test_every_coupon_is_one_valid_safe_touch_nominal_solid(self):
        for name,(p,shape) in self.coupons.items():
            with self.subTest(name=name):
                self.assertTrue(shape.isValid())
                self.assertEqual(len(shape.Solids()),1)
                for actual, expected in zip(exact_bounds(shape),
                                            (31.8,31.8,23.7)):
                    self.assertAlmostEqual(actual,expected,places=4)
                self.assertEqual((p.stud_radius,p.stud_inner_radius),
                                 (4.7,3.2))

    def test_dupes_are_identical_except_outside_id(self):
        # Only compare the central mating geometry, excluding engraved outer wall.
        inner = cq.Workplane("XY").box(
            27,27,23.7,centered=(True,True,False)).val()
        for left,right in (("E30-01","E30-02"),("E30-08","E30-09")):
            a=self.coupons[left][1].intersect(inner)
            b=self.coupons[right][1].intersect(inner)
            self.assertLess(a.cut(b).Volume()+b.cut(a).Volume(),1e-5)

    def test_separation_and_bed(self):
        centers=[tuple(r["xy"]) for r in SPECIMENS]
        for i,(x,y) in enumerate(centers):
            for u,v in centers[i+1:]:
                self.assertTrue(abs(x-u)>=45 or abs(y-v)>=45)
        self.assertEqual(min(x for x,y in centers),45)
        self.assertEqual(max(x for x,y in centers),135)
        self.assertEqual(min(y for x,y in centers),45)
        self.assertEqual(max(y for x,y in centers),135)


if __name__=="__main__":
    unittest.main()
