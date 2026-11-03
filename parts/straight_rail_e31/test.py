"""R01-V1: measured top-channel continuity and E31-05 regression checks."""
import tempfile
import unittest
from pathlib import Path
import cadquery as cq
from brickcad.verify import VOLUME_TOL
from parts.straight_rail.design import Rail, build_rail as build_legacy
from parts.straight_rail_e31.design import (
    PART_ID, RECEIVER_DEPTH_MM, build_rail, export, swept_ball_intersection,
)
from parts.tunnel.e31_fit import slot_end_z_for_receiver_depth


class E31StraightRailTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shape,cls.p=build_rail()

    def test_measured_channel_matches_legacy(self):
        previous,_=build_legacy()
        r=Rail()
        self.assertEqual(PART_ID,"R01-V1")
        self.assertAlmostEqual(r.floor,6.35)
        self.assertEqual(len(self.p.tubes()),3)
        self.assertAlmostEqual(self.p.width,63.8)
        self.assertAlmostEqual(self.p.depth,31.65)
        self.assertAlmostEqual(self.p.height,19.13)
        for x in (-26.,0.,26.):
            for y in (-10.,0.,10.):
                for z in (6.2,6.6,10.,13.,17.):
                    self.assertEqual(self.shape.isInside(cq.Vector(x,y,z)),
                                     previous.isInside(cq.Vector(x,y,z)),(x,y,z))
        self.assertEqual(len(self.shape.Solids()),1)

    def test_shallow_receiver_three_full_tubes(self):
        self.assertEqual(self.p.cavity_xy,(57.4,25.4))
        self.assertAlmostEqual(self.p.tube_radius,6.60)
        self.assertEqual(slot_end_z_for_receiver_depth(RECEIVER_DEPTH_MM),3.50)
        self.assertEqual(slot_end_z_for_receiver_depth(17.60),4.40)
        self.assertAlmostEqual(RECEIVER_DEPTH_MM-(3.50+.65),.60)
        for x,y in self.p.tubes():
            self.assertFalse(self.shape.isInside(cq.Vector(x,y,1.)))
            self.assertFalse(self.shape.isInside(cq.Vector(x+6.5,y,3.5)))
            self.assertTrue(self.shape.isInside(cq.Vector(x+6.5,y,4.4)))
            self.assertTrue(self.shape.isInside(cq.Vector(x,y,5.5)))

    def test_swept_ball_negative_control_and_no_studs(self):
        r=Rail()
        self.assertLess(swept_ball_intersection(self.shape,24.26),VOLUME_TOL)
        self.assertGreater(swept_ball_intersection(self.shape,28.),VOLUME_TOL)
        self.assertFalse(self.shape.isInside(cq.Vector(8,0,r.height+1.)))
        self.assertTrue(self.shape.isInside(cq.Vector(0,0,r.floor-.1)))
        self.assertFalse(self.shape.isInside(cq.Vector(0,0,r.floor+.1)))

    def test_standard_marking_and_stl_report(self):
        r=Rail()
        self.assertTrue(self.shape.isInside(cq.Vector(26,-r.width/2+.6,10.)))
        with tempfile.TemporaryDirectory() as t:
            report=export(Path(t))
            self.assertTrue(report["passed"],report["geometry"]["checks"])
            self.assertTrue(report["mesh"]["passed"])
            self.assertEqual(report["marking"]["label"],PART_ID)
            self.assertEqual(report["marking"]["size_mm"],3.)
            self.assertEqual(report["marking"]["depth_mm"],.4)
            self.assertFalse(report["physical_fit_validated"])
            self.assertFalse(report["slicing_validated"])


if __name__=="__main__":
    unittest.main()
