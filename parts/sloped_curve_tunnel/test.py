"""Targeted geometry tests for SC02-V2 (Issue #37 M31-05)."""
import tempfile
import unittest
from pathlib import Path

import cadquery as cq

from brickcad.verify import intersection, VOLUME_TOL
from parts.sloped_curve_tunnel.design import (
    PART_ID, BALL, DROP, RADIUS, RETAINED_TUBES,
    _roof_probe, ball_centre, export, ports,
)


class SlopedCurveTunnelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name)
        cls.report = export(cls.out)
        cls.shape = cq.importers.importStep(str(cls.out/'brick.step')).val()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_export_geometry_and_id(self):
        self.assertTrue(self.report['passed'], self.report['checks'])
        self.assertEqual(self.report['part_id'], PART_ID)
        self.assertTrue(self.report['mesh']['passed'])
        self.assertFalse(self.report['physical_fit_validated'])
        self.assertFalse(self.report['physical_rolling_validated'])
        self.assertFalse(self.report['slicer_support_free_validated'])
        self.assertEqual(len(self.shape.Solids()), 1)
        self.assertAlmostEqual(self.report['curve']['radius_mm'], RADIUS)
        self.assertAlmostEqual(self.report['curve']['drop_mm'], DROP)
        self.assertEqual(self.report['curve']['mouth'], 'circular')
        self.assertEqual(self.report['curve']['interior_roof'], 'teardrop')

    def test_grid_ports_and_enclosed_roof(self):
        west,north = ports()
        self.assertEqual(west.floor_xyz_mm[:2], (-32.,-16.))
        self.assertEqual(north.floor_xyz_mm[:2], (16.,32.))
        self.assertAlmostEqual(west.floor_xyz_mm[2]-north.floor_xyz_mm[2], 19.2)
        self.assertTrue(self.shape.isInside(_roof_probe(.5)))
        for t in (0., .25, .5, .75, 1.):
            self.assertFalse(self.shape.isInside(ball_centre(t)))
        self.assertLess(intersection(self.shape, cq.Solid.makeSphere(
            BALL/2,ball_centre(.37123),angleDegrees1=-90)), VOLUME_TOL)
        self.assertGreater(intersection(self.shape, cq.Solid.makeSphere(
            BALL/2,ball_centre(.5)-cq.Vector(0,0,2),angleDegrees1=-90)), VOLUME_TOL)

    def test_corner_removal_and_receiver(self):
        for x,y in [(-24.,24.),(24.,-24.),(-16.,16.)]:
            self.assertFalse(self.shape.isInside(cq.Vector(x,y,1)))
        self.assertEqual(len(RETAINED_TUBES), 3)
        self.assertEqual(self.report['e31_05']['split_slots'], 4)
        self.assertFalse(self.report['e31_05']['physical_transfer_validated'])
        self.assertAlmostEqual(self.report['e31_05']['tube_od_mm'], 13.2)
        # Probe E31-05 bead at 45 degrees, away from four split slots.
        x = 6.7/(2**.5)
        self.assertTrue(self.shape.isInside(cq.Vector(x,x,2.25)))
        self.assertFalse(self.shape.isInside(cq.Vector(x+.3,x+.3,2.25)))


if __name__ == '__main__':
    unittest.main()
