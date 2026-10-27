import tempfile
import unittest
from pathlib import Path
import cadquery as cq
from brickcad.sloped_curve import export, ball_centre, BALL, build_curve, cut_receiver_edges
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
        # Compare actual exported contact wall, not only the source parameter.
        # 4x4 west face is -31.9; cavity starts at -28.7 (3.20 mm wall).
        self.assertTrue(self.shape.isInside(cq.Vector(-28.72,-16,1)))
        self.assertFalse(self.shape.isInside(cq.Vector(-28.68,-16,1)))
        calibration = self.report['receiver_audit']['calibration']
        self.assertAlmostEqual(calibration['equivalent_2x2_cavity_mm'],25.40)
        self.assertEqual(calibration['source_coupon'],'PR14 ID03 C-tube')
        self.assertFalse(calibration['transfer_validated'])
        for size in self.report['geometry']['bounds_mm'][:2]:
            self.assertAlmostEqual(size,63.8,delta=.02)  # .01 mm STL tessellation tolerance
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

        self.assertTrue(self.shape.isInside(cq.Vector(0,0,6.1)))
        self.assertTrue(all(j['compatible'] for j in self.report['joints']))
        self.assertGreater(self.report['low_ball_negative_control_mm3'],VOLUME_TOL)

    def test_bottom_only_rounding_keeps_receiver_contact_and_track(self):
        old,_ = build_curve(softened=False)
        tips = cut_receiver_edges(old)
        self.assertEqual(len(tips),20)
        # The 20 vertical cut corners deliberately remain unfilleted in F:
        # their R0.70 treatment caused Bambu Studio's floating cantilever warning.
        finish = self.report['receiver_finish']
        self.assertAlmostEqual(finish['cut_edge_radius_mm'],0.0)
        self.assertAlmostEqual(finish['bottom_edge_radius_mm'],.5)
        self.assertEqual(finish['clipped_vertical_corners'],20)
        self.assertGreater(finish['removed_volume_mm3'],1)
        self.assertLess(finish['removed_contact_above_entry_mm3'],VOLUME_TOL)
        self.assertLess(finish['added_contact_above_entry_mm3'],VOLUME_TOL)
        self.assertLess(finish['changed_track_mm3'],VOLUME_TOL)
        self.assertFalse(finish['physical_touch_validated'])
        # The three complete tubes still have the adopted 13.50 mm OD above the entry.
        for x,y in [(-16,-16),(0,0),(16,16)]:
            self.assertTrue(self.shape.isInside(cq.Vector(x+6.74,y,1)))
            self.assertFalse(self.shape.isInside(cq.Vector(x+6.76,y,1)))

    def test_bottom_lips_are_rounded_on_the_exported_solid(self):
        # Probe a full tube away from the clipped ends. At z=0 a R0.5
        # quarter-circle retreats .5 mm; by z=.5 the original radius returns.
        self.assertFalse(self.shape.isInside(cq.Vector(6.5,0,.01)))
        self.assertTrue(self.shape.isInside(cq.Vector(6.5,0,.2)))
        self.assertFalse(self.shape.isInside(cq.Vector(4.9,0,.01)))
        self.assertTrue(self.shape.isInside(cq.Vector(4.9,0,.2)))

    def test_removed_corner_floors_and_retained_connection(self):
        for x,y in [(-16,16),(-24,24),(24,-24)]:
            self.assertFalse(self.shape.isInside(cq.Vector(x,y,6.1)))
            self.assertFalse(self.shape.isInside(cq.Vector(x,y,1)))
        # Tube centred at (0,0) is fully below the rail and remains connected.
        self.assertTrue(self.shape.isInside(cq.Vector(5.5,0,1)))
        audit = self.report['receiver_audit']
        self.assertEqual(len(audit['studs']),16)
        self.assertTrue(audit['no_blocking_collision'])
        self.assertTrue(all(v['non_tube_intersection_mm3']<VOLUME_TOL for v in audit['studs']))
        self.assertTrue(all(v['non_tube_intersection_mm3']<VOLUME_TOL for v in audit['insertion']))
        self.assertAlmostEqual(audit['seating_roof_clearance_mm'],.25)
        # Known trial interference must be disclosed rather than called clear.
        self.assertFalse(audit['rigid_fit_clear'])
        self.assertGreater(audit['insertion'][-1]['total_intersection_mm3'],VOLUME_TOL)
        self.assertGreater(audit['measured_9p32_stud_intersection_mm3'],VOLUME_TOL)




