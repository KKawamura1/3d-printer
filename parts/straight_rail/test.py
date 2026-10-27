import math
from pathlib import Path
import tempfile
import unittest
import cadquery as cq
from parts.straight_rail.design import Rail, build_rail, export, rounded_brick, fit_profile
from brickcad.verify import intersection, VOLUME_TOL

class RailTests(unittest.TestCase):
    def test_profile_and_invalid_depth(self):
        r=Rail()
        self.assertAlmostEqual(math.sqrt(r.radius**2-(r.height-r.floor-r.radius)**2)*2,r.opening)
        for kw in [dict(floor=5),dict(opening=32),dict(height=float('nan'))]:
            with self.assertRaises(ValueError):Rail(**kw)

    def test_ball_and_oversize_negative_control(self):
        shape,p=build_rail();r=Rail()
        for radius,clear in [(12.13,True),(14,False)]:
            ball=cq.Solid.makeSphere(radius,cq.Vector(0,0,r.floor+12.13+.05),angleDegrees1=-90)
            self.assertEqual(intersection(shape,ball)<VOLUME_TOL,clear)
        self.assertFalse(shape.isInside(cq.Vector(0,0,1)))
        self.assertTrue(shape.isInside(cq.Vector(0,0,6.2)))

    def test_exports_and_disclosed_interference(self):
        with tempfile.TemporaryDirectory() as t:
            for kind in ['rail','brick']:
                r=export(kind,Path(t)/kind)
                self.assertTrue(r['passed'])
                self.assertTrue(r['mesh']['passed'])
                self.assertFalse(r['physical_fit_validated'])
                self.assertFalse(r['fit_geometrically_clear'])
                self.assertTrue(next(x for x in r['fit']['insertion'] if x['pair']=='reference/printed' and x['lift_mm']==0)['collision'])
                self.assertAlmostEqual(r['nominal_tube_gap_mm'],-.036291501)
