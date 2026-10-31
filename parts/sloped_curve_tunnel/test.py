"""Targeted geometry tests for SC02-V5 (Issue #37 M31-05)."""
import tempfile
import unittest
from pathlib import Path

import cadquery as cq

from brickcad.verify import intersection, VOLUME_TOL
from parts.sloped_curve_tunnel.design import (
    PART_ID, BALL, DROP, RADIUS, RETAINED_TUBES,
    CLIPPED_RECEIVER_TUBES, TOP_Z, MARK_Y, MARK_Z, MARK_DEPTH,
    _roof_probe, _stud_shell_present, ball_centre, export, ports,
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

    def test_engraved_id_still_visible_after_cover_union(self):
        self.assertEqual(self.report['marking']['text'], 'SC02-V5')
        self.assertEqual(self.report['marking']['depth_mm'], MARK_DEPTH)
        self.assertTrue(self.report['checks']['engraved_id_recess_remains_open'])

        # The same text cutter must intersect a plain wall (negative control)
        # but have zero volume overlap with the exported, engraved STEP solid.
        width = self.report['geometry']['parameters']['width']
        plane = cq.Plane(origin=(-width/2+MARK_DEPTH, MARK_Y, MARK_Z),
                         xDir=(0,-1,0), normal=(-1,0,0))
        glyphs = (cq.Workplane(plane).text(
            PART_ID, 3., MARK_DEPTH+.05, font='DejaVu Sans',
            kind='bold', combine=False).val())
        unmarked_wall = cq.Solid.makeBox(
            0.5, 20., 7., cq.Vector(-width/2, MARK_Y-10, MARK_Z-3.5))
        self.assertGreater(intersection(unmarked_wall, glyphs), .2)
        self.assertLess(intersection(self.shape, glyphs), VOLUME_TOL)

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

    def test_flat_top_and_clipped_top_studs(self):
        self.assertEqual(self.report['top']['plane_z_mm'], TOP_Z)
        self.assertAlmostEqual(self.report['geometry']['bounds_mm'][2], TOP_Z+4.5, delta=.03)
        self.assertTrue(self.report['checks']['flat_top'])
        self.assertTrue(self.report['checks']['ten_top_stud_shells'])
        self.assertFalse(self.report['top']['physical_fit_validated'])
        self.assertEqual(sum(_stud_shell_present(self.shape,x,y)
                             for x in (-24,-8,8,24) for y in (-24,-8,8,24)), 10)
        self.assertFalse(self.shape.isInside(cq.Vector(-24,-24,TOP_Z+1)),
                         'DUPLO stud centre must remain hollow')
        # The two unsupported corners stay empty, not full square plates.
        for x,y in [(-24,24),(24,-24)]:
            self.assertFalse(self.shape.isInside(cq.Vector(x,y,TOP_Z-1)))

    def test_corner_removal_and_receiver(self):
        for x,y in [(-24.,24.),(24.,-24.),(-16.,16.)]:
            self.assertFalse(self.shape.isInside(cq.Vector(x,y,1)))
        self.assertEqual(len(RETAINED_TUBES), 3)
        self.assertEqual(len(CLIPPED_RECEIVER_TUBES), 4)
        self.assertEqual(len(self.report['receiver_supports']['clipped_tubes']), 4)
        self.assertFalse(self.report['receiver_supports']['vertical_cut_edge_fillets'])
        self.assertFalse(self.report['receiver_supports']['physical_support_and_fit_validated'])
        for x,y in CLIPPED_RECEIVER_TUBES:
            self.assertTrue(self.shape.isInside(cq.Vector(x+5.7,y,1.)),(x,y))
        self.assertEqual(self.report['e31_05']['split_slots'], 4)
        self.assertFalse(self.report['e31_05']['physical_transfer_validated'])
        self.assertAlmostEqual(self.report['e31_05']['tube_od_mm'], 13.2)
        # Probe E31-05 bead at 45 degrees, away from four split slots.
        x = 6.7/(2**.5)
        self.assertTrue(self.shape.isInside(cq.Vector(x,x,2.25)))
        self.assertFalse(self.shape.isInside(cq.Vector(x+.3,x+.3,2.25)))


if __name__ == '__main__':
    unittest.main()
