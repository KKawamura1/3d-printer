import unittest
from brickcad.calibration import specification, coupon
from brickcad.model import build
from brickcad.verify import geometry_report

class CalibrationTest(unittest.TestCase):
    def test_male_female_independent(self):
        p=specification(-0.04,0.12)
        self.assertAlmostEqual(p.stud_radius*2,4.88)
        self.assertAlmostEqual(p.wall,1.38)
        self.assertAlmostEqual(p.tube_radius*2,6.26)
        self.assertTrue(geometry_report(p,build(p))['passed'])
    def test_labels_preserve_connection_surfaces(self):
        p,s=coupon(5,0.12,0.12)
        raw=build(p)
        self.assertAlmostEqual(raw.Volume()-s.Volume(),1.4)
        # Groove is outside: the receiver's entire interior remains unchanged.
        import cadquery as cq
        region=cq.Workplane('XY').box(12,12,9.6,centered=(True,True,False)).val()
        self.assertAlmostEqual(s.intersect(region).Volume(),raw.intersect(region).Volume())
