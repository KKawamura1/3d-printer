import unittest
from brickcad.calibration import specification, coupon
from brickcad.model import build
from brickcad.verify import geometry_report

class CalibrationTest(unittest.TestCase):
    def test_male_female_independent(self):
        p=specification(-0.04,0.12,family="lego")
        self.assertAlmostEqual(p.stud_radius*2,4.88)
        self.assertAlmostEqual(p.wall,1.38)
        self.assertAlmostEqual(p.tube_radius*2,6.26)
        self.assertTrue(geometry_report(p,build(p))['passed'])
    def test_labels_preserve_connection_surfaces(self):
        p,s=coupon(5,0.12,0.12,family="lego")
        raw=build(p)
        self.assertAlmostEqual(raw.Volume()-s.Volume(),1.4)
        # Groove is outside: the receiver's entire interior remains unchanged.
        import cadquery as cq
        region=cq.Workplane('XY').box(12,12,9.6,centered=(True,True,False)).val()
        self.assertAlmostEqual(s.intersect(region).Volume(),raw.intersect(region).Volume())

    def test_default_duplo_independent_compensation_and_holes(self):
        p=specification(-0.04,0.12)
        self.assertEqual(p.family,'duplo')
        self.assertEqual(p.pitch,16)
        self.assertEqual(p.height,19.2)
        self.assertEqual(p.stud_height,4.5)
        self.assertEqual(p.stud_inner_radius,3.25)
        self.assertAlmostEqual(p.stud_radius*2,9.48)
        self.assertAlmostEqual(p.wall,3.08)
        self.assertAlmostEqual(p.tube_radius*2,12.86)
        self.assertTrue(geometry_report(p,build(p))['passed'])

    def test_duplo_reference_and_labelled_receiver(self):
        from brickcad.verify import fit_report
        import cadquery as cq
        p,s=coupon(5,0.12,0.12)
        self.assertAlmostEqual(p.height,6.4)
        self.assertGreaterEqual(p.height-p.roof,p.stud_height)
        raw=build(p)
        self.assertAlmostEqual(raw.Volume()-s.Volume(),1.4)
        cavity_region=cq.Workplane('XY').box(26,26,19.2,centered=(True,True,False)).val()
        self.assertAlmostEqual(s.intersect(cavity_region).Volume(),raw.intersect(cavity_region).Volume())
        r=fit_report(p,s)
        self.assertEqual(r['reference_parameters']['family'],'duplo')
        self.assertEqual(r['reference_parameters']['pitch'],16)
        self.assertEqual(r['reference_parameters']['stud_inner_radius'],3.25)
        self.assertTrue(r['negative_controls_passed'])

    def test_duplo_full_height_option_keeps_connection_geometry(self):
        p,s=coupon(3,0.04,0.04,body_height=19.2)
        short,_=coupon(3,0.04,0.04)
        self.assertEqual(p.height,19.2)
        for name in ('pitch','wall','roof','stud_radius','stud_inner_radius','stud_height','tube_radius','tube_inner_radius'):
            self.assertEqual(getattr(p,name),getattr(short,name))
