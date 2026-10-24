import tempfile
import unittest
from pathlib import Path
import cadquery as cq
from brickcad.sloped_curve import export, ball_centre, BALL
from brickcad.verify import intersection, VOLUME_TOL


class SlopedCurveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name)
        cls.report = export(cls.out)
        cls.shape = cq.importers.importStep(str(cls.out/'brick.step')).val()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_printable_export_and_limits(self):
        self.assertTrue(self.report['passed'],self.report['checks'])
        self.assertFalse(self.report['physical_fit_validated'])
        self.assertFalse(self.report['physical_rolling_validated'])
        for size in self.report['geometry']['bounds_mm'][:2]:
            self.assertAlmostEqual(size,63.8,places=4)
        self.assertEqual(self.report['drop_mm'],19.2)
        self.assertGreater(self.report['max_slope_degrees'],20)
        self.assertTrue(self.report['mesh']['passed'])

    def test_real_endpoint_floors_and_horizontal_leadins(self):
        # Probe the exported STEP, rather than just checking port metadata.
        for x,y,z in [(-31.89,-16,25.55),(-31.5,-16,25.55),
                      (16,31.89,6.35),(16,31.5,6.35)]:
            self.assertTrue(self.shape.isInside(cq.Vector(x,y,z-.03)))
            self.assertFalse(self.shape.isInside(cq.Vector(x,y,z+.03)))

    def test_ball_between_verification_samples_and_blockage(self):
        c = ball_centre(.37123)
        sphere = cq.Solid.makeSphere(BALL/2,c,angleDegrees1=-90)
        self.assertLess(intersection(self.shape,sphere),VOLUME_TOL)
        self.assertGreater(intersection(self.shape,sphere.translate((0,0,-2))),VOLUME_TOL)

    def test_real_receiver_grid_and_roof(self):
        for x in (-16,0,16):
            for y in (-16,0,16):
                self.assertFalse(self.shape.isInside(cq.Vector(x,y,1)))
                self.assertTrue(self.shape.isInside(cq.Vector(x+5.5,y,1)))
        self.assertTrue(self.shape.isInside(cq.Vector(0,0,6.1)))
        self.assertTrue(all(j['compatible'] for j in self.report['joints']))
        self.assertGreater(self.report['low_ball_negative_control_mm3'],VOLUME_TOL)
