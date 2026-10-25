import json
import unittest
import cadquery as cq
from brickcad.xy_trial import build,DEFAULT_PROFILE
from brickcad.rail import rounded_brick


class XYTrialTests(unittest.TestCase):
    def test_outer_faces_change_but_receiver_and_studs_do_not(self):
        profile=json.loads(DEFAULT_PROFILE.read_text());p,s=build(profile)
        baseline=rounded_brick(p)
        # Remove all exterior faces: compare the whole receiver/cavity and
        # central tube, not just one nominal point in the contact zone.
        cavity_band=cq.Workplane('XY').box(26,26,17.59,centered=(True,True,False)).val()
        a=baseline.intersect(cavity_band);b=s.intersect(cavity_band)
        self.assertLess(a.cut(b).Volume()+b.cut(a).Volume(),1e-6)
        top=cq.Workplane('XY',origin=(0,0,19.21)).box(40,40,5,centered=(True,True,False)).val()
        a=baseline.intersect(top);b=s.intersect(top)
        self.assertLess(a.cut(b).Volume()+b.cut(a).Volume(),1e-6)
        self.assertEqual(p.studs(),[(-8,-8),(-8,8),(8,-8),(8,8)])
        self.assertFalse(s.isInside(cq.Vector(0,0,1)))
        self.assertTrue(s.isInside(cq.Vector(6,0,1)))

    def test_bounds_invalid_and_stud_selection(self):
        profile=json.loads(DEFAULT_PROFILE.read_text())
        from brickcad.verify import exact_bounds
        for d in (9.36,9.40,9.44):
            p,s=build(dict(profile,stud_diameter_mm=d))
            for a,b in zip(exact_bounds(s),[32,31.87,23.7]):self.assertAlmostEqual(a,b,places=6)
        for key,value in [('body_x_mm',float('nan')),('body_y_mm',33),('stud_diameter_mm',9.55),('stud_hole_mm',6.0)]:
            with self.assertRaises(ValueError):build(dict(profile,**{key:value}))


if __name__=='__main__':unittest.main()
