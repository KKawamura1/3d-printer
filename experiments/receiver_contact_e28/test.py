"""Targeted CAD tests for E28; do not infer actual holding force."""
import unittest
import cadquery as cq

from brickcad.verify import exact_bounds
from experiments.receiver_contact_e28.design import plan, coupon, parameters


class ReceiverContactE28Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records=plan()
        cls.samples={r["id"]:coupon(r) for r in cls.records}

    def test_unique_ids_and_controls(self):
        self.assertEqual([r["id"] for r in self.records],
                         ["E28-01","E28-02","E28-03","E28-04"])
        self.assertEqual(len({tuple(r["bed_center_xy_mm"]) for r in self.records}),4)
        self.assertEqual(parameters(self.records[0]),parameters(self.records[1]))

    def test_exactly_one_receiver_feature_changes(self):
        base=self.samples["E28-01"][0]
        twin=self.samples["E28-02"][0]
        wall=self.samples["E28-03"][0]
        tube=self.samples["E28-04"][0]
        self.assertEqual(base,twin)
        for p in (base,twin,wall,tube):
            self.assertEqual((p.nx,p.ny,p.height,p.pitch),(2,2,19.2,16.0))
            self.assertEqual((p.stud_radius,p.stud_inner_radius,p.tube_inner_radius),
                             (4.7,3.2,4.7))
        self.assertEqual(base.cavity_xy,(25.4,25.4))
        self.assertEqual(wall.cavity_xy,(25.6,25.6))
        self.assertAlmostEqual(wall.tube_radius,base.tube_radius)
        self.assertEqual(tube.cavity_xy,base.cavity_xy)
        self.assertAlmostEqual(base.tube_radius*2,13.5)
        self.assertAlmostEqual(tube.tube_radius*2,13.3)

    def test_all_studs_geometrically_identical(self):
        top=(cq.Workplane("XY",origin=(0,0,19.2))
             .box(40,40,5,centered=(True,True,False)).val())
        base_top=self.samples["E28-01"][1].intersect(top)
        for _,shape in self.samples.values():
            self.assertEqual(len(shape.Solids()),1)
            self.assertTrue(shape.isValid())
            for actual,expected in zip(exact_bounds(shape),(31.8,31.8,23.7)):
                self.assertAlmostEqual(actual,expected,places=6)
            candidate=shape.intersect(top)
            self.assertLess(base_top.cut(candidate).Volume()
                            +candidate.cut(base_top).Volume(),1e-6)

    def test_cad_probes_separate_wall_and_tube(self):
        # At z=2 the entrance chamfer and exterior text cannot affect probes.
        v=lambda x:cq.Vector(x,0,2)
        baseline=self.samples["E28-01"][1]
        twin=self.samples["E28-02"][1]
        wall=self.samples["E28-03"][1]
        tube=self.samples["E28-04"][1]
        self.assertTrue(baseline.isInside(v(12.75)))
        self.assertFalse(wall.isInside(v(12.75)))
        self.assertTrue(tube.isInside(v(12.75)))
        self.assertTrue(baseline.isInside(v(6.70)))
        self.assertTrue(wall.isInside(v(6.70)))
        self.assertFalse(tube.isInside(v(6.70)))
        band=cq.Workplane("XY").box(40,40,4,centered=(True,True,False)).val()
        a,b=baseline.intersect(band),twin.intersect(band)
        self.assertLess(a.cut(b).Volume()+b.cut(a).Volume(),1e-6)


if __name__=="__main__":
    unittest.main()
