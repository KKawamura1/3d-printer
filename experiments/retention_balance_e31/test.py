"""Targeted E31-V2 geometry tests; no physical-fit or safety claims."""
import unittest

import cadquery as cq

from brickcad.verify import exact_bounds
from experiments.unified_fit_e30.design import coupon as e30_coupon
from experiments.retention_balance_e31.design import (
    VERSION, SOURCE_VERSIONS, SPECIMENS, plan, parameters, coupon,
    BEAD_RADII, TUBE_RADII, SHORT_SLOT_END_Z,
)


class E31Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parts = {r["id"]: coupon(r) for r in SPECIMENS}

    def test_version_ids_bed_and_plate_layout(self):
        self.assertEqual(VERSION, "E31-V2")
        self.assertEqual(SOURCE_VERSIONS, {"E29":"E29-V3","E30":"E30-V1"})
        self.assertEqual(len(plan()), 5)
        self.assertEqual(len(self.parts), 5)
        self.assertEqual(len({r["id"] for r in SPECIMENS}), 5)
        self.assertEqual(len({tuple(r["xy"]) for r in SPECIMENS}), 5)
        self.assertEqual(
            set(self.parts), {"E31-01","E31-05","E31-07","E31-08","E31-09"})
        for r in SPECIMENS:
            self.assertIn(r["xy"][0], (45,90,135))
            self.assertIn(r["xy"][1], (68,112))
        self.assertEqual(
            (max(r["xy"][0] for r in SPECIMENS)-min(r["xy"][0] for r in SPECIMENS)+31.8,
             max(r["xy"][1] for r in SPECIMENS)-min(r["xy"][1] for r in SPECIMENS)+31.8),
            (121.8,75.8))

    def test_single_valid_solid_and_unmodified_studs(self):
        for name,(p,shape) in self.parts.items():
            with self.subTest(name=name):
                self.assertTrue(shape.isValid())
                self.assertEqual(len(shape.Solids()), 1)
                for actual,expected in zip(exact_bounds(shape),
                                           (31.8,31.8,23.7)):
                    self.assertAlmostEqual(actual,expected,places=4)
                self.assertEqual(p.cavity_xy, (25.4,25.4))
                self.assertEqual(p.stud_radius, 4.7)
                self.assertEqual(p.stud_inner_radius, 3.2)
                self.assertEqual(p.stud_height, 4.5)

    def test_reference_coupons_match_e30_07_mating_geometry(self):
        _,original=e30_coupon(dict(id="E30-07",kind="slotted_bead"))
        mating_region=cq.Workplane("XY").box(
            27,27,23.7,centered=(True,True,False)).val()
        original=original.intersect(mating_region)
        for label in ("E31-01",):
            new=self.parts[label][1].intersect(mating_region)
            delta=original.cut(new).Volume()+new.cut(original).Volume()
            self.assertLess(delta,1e-5)

    def test_one_factor_conditions_and_upper_geometry(self):
        base=self.parts["E31-01"][0]
        self.assertEqual(base.tube_radius,6.60)
        for row in SPECIMENS:
            p=parameters(row)
            if row["kind"] in TUBE_RADII:
                self.assertEqual(p.tube_radius,TUBE_RADII[row["kind"]])
            else:
                self.assertEqual(p,base)
        self.assertEqual(BEAD_RADII, {"bead_020":.20})
        self.assertEqual(TUBE_RADII, {"tube_1328":6.64})
        # Equal maximum bead OD 13.60 mm, different mechanism.
        self.assertAlmostEqual(
            2 * (base.tube_radius + BEAD_RADII["bead_020"]), 13.60)
        self.assertAlmostEqual(
            2 * (TUBE_RADII["tube_1328"] + .16), 13.60)
        self.assertEqual(SHORT_SLOT_END_Z,3.60)
        upper=cq.Workplane("XY",origin=(0,0,19.2)).box(
            36,36,4.5,centered=(True,True,False)).val()
        baseline=self.parts["E31-01"][1].intersect(upper)
        for name,(p,shape) in self.parts.items():
            with self.subTest(name=name):
                new=shape.intersect(upper)
                delta=baseline.cut(new).Volume()+new.cut(baseline).Volume()
                self.assertLess(delta,1e-5)

    def test_every_variant_changes_receiver_geometry(self):
        # Clip away exterior ID engraving, only compare inside receiver.
        zone=cq.Workplane("XY").box(
            27,27,18,centered=(True,True,False)).val()
        baseline=self.parts["E31-01"][1].intersect(zone)
        for name in ("E31-05","E31-07","E31-08","E31-09"):
            with self.subTest(name=name):
                altered=self.parts[name][1].intersect(zone)
                delta=baseline.cut(altered).Volume()+altered.cut(baseline).Volume()
                self.assertGreater(delta,1e-4)


if __name__ == "__main__":
    unittest.main()
