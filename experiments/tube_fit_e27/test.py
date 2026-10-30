import unittest
import cadquery as cq
from brickcad.model import build as build_brick
from brickcad.verify import exact_bounds
from experiments.tube_fit_e27.design import build, plan


class TubeFitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.samples = [build(r) for r in plan()]

    def test_fixed_top_and_receiver_geometry(self):
        top = cq.Workplane('XY', origin=(0,0,17.61)).box(40,40,7,centered=(True,True,False)).val()
        reference = self.samples[0][1].intersect(top)
        for p,s in self.samples:
            self.assertTrue(s.isValid())
            self.assertEqual(len(s.Solids()), 1)
            for actual, expected in zip(exact_bounds(s), (31.8,31.8,23.7)):
                self.assertAlmostEqual(actual, expected, places=6)
            self.assertEqual(p.cavity_xy, (25.4,25.4))
            self.assertEqual((2*p.stud_radius,2*p.stud_inner_radius,2*p.tube_inner_radius), (9.4,6.4,9.4))
            candidate = s.intersect(top)
            self.assertLess(reference.cut(candidate).Volume()+candidate.cut(reference).Volume(), 1e-6)
            for axis in range(2):
                for sign in (-1,1):
                    point = [0,0,1]; point[axis] = sign*12.69
                    self.assertFalse(s.isInside(cq.Vector(*point)))
                    point[axis] = sign*12.71
                    self.assertTrue(s.isInside(cq.Vector(*point)))

    def test_tube_steps_and_label_contact_clearance(self):
        band = cq.Workplane('XY').box(40,40,5,centered=(True,True,False)).val()
        for index,(p,s) in enumerate(self.samples):
            self.assertFalse(s.isInside(cq.Vector(p.tube_radius+.005,0,1)))
            self.assertTrue(s.isInside(cq.Vector(p.tube_radius-.005,0,1)))
            self.assertFalse(s.isInside(cq.Vector(0,0,1)))
            raw = build_brick(p,corner_radius=.8,stud_lip_radius=.5,entry=.3)
            removed = raw.cut(s)
            self.assertGreater(removed.Volume(), 1)
            self.assertLess(removed.intersect(band).Volume(),1e-7)
            if index:
                previous = self.samples[index-1][1].intersect(band)
                current = s.intersect(band)
                self.assertLess(previous.cut(current).Volume(), 1e-7)
                self.assertGreater(current.cut(previous).Volume(), 1)


if __name__ == '__main__':
    unittest.main()
