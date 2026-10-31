import unittest
import cadquery as cq
from brickcad.ports import mate, straight_ports
from brickcad.standards import BALL_TRACK
from brickcad.verify import intersection, VOLUME_TOL
from parts.downhill_tunnel.design import (
    PART_ID, Downhill, build_downhill, ball_positions,
    floor_z, ports, sampled_ball_intersections,
)


class DownhillTunnelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = Downhill()
        cls.shape, cls.p = build_downhill(cls.d)

    def test_grid_height_and_ports(self):
        self.assertEqual(PART_ID, "D01-V1")
        self.assertEqual((self.p.nx,self.p.ny),(4,2))
        self.assertAlmostEqual(self.p.height,57.6)
        high, low = ports(self.d)
        self.assertAlmostEqual(high.floor_xyz_mm[0],-32.0)
        self.assertAlmostEqual(high.floor_xyz_mm[2],25.55)
        self.assertEqual(low.floor_xyz_mm,(32.0,0.0,6.35))
        self.assertAlmostEqual(high.floor_xyz_mm[2]-low.floor_xyz_mm[2],19.2)
        self.assertAlmostEqual(high.section_radius_mm,BALL_TRACK.radius)
        self.assertAlmostEqual(floor_z(-31.9),25.55)
        self.assertAlmostEqual(floor_z(31.9),6.35)
        self.assertTrue(self.shape.isValid())
        self.assertEqual(len(self.shape.Solids()),1)

    def test_e31_receiver_and_windows(self):
        self.assertEqual((self.p.tube_radius,self.p.stud_radius,
                          self.p.stud_inner_radius),(6.60,4.70,3.20))
        self.assertEqual(self.p.cavity_xy,(57.4,25.4))
        self.assertLess(self.d.window_width,BALL_TRACK.ball_diameter)
        self.assertGreaterEqual(self.d.window_bottom_offset,6.)
        for x in (-16.,0.,16.):
            self.assertFalse(self.shape.isInside(cq.Vector(
                x,-15.2,floor_z(x)+12.)))
            self.assertTrue(self.shape.isInside(cq.Vector(
                x,-15.2,floor_z(x)+4.)))
            self.assertTrue(self.shape.isInside(cq.Vector(
                x+5.,-15.2,floor_z(x)+12.)))

    def test_ball_samples_clear_with_oversize_negative(self):
        self.assertLess(max(sampled_ball_intersections(self.shape,self.d,33)),VOLUME_TOL)
        # A ball wider than the entrance cannot pass; test the geometry rejects it.
        p=next(ball_positions(self.d,count=33,diameter=28.))
        oversized=cq.Solid.makeSphere(14.,p,angleDegrees1=-90)
        self.assertGreater(intersection(self.shape,oversized),VOLUME_TOL)

    def test_roof_floor_and_fitting_level(self):
        self.assertGreaterEqual(3*19.2-(self.d.low_floor+self.d.drop+
                                         self.d.inner_roof_above_floor),1.6)
        self.assertGreaterEqual(self.d.low_floor-self.d.receiver_depth,1.6-1e-5)
        high,low=ports(self.d)
        left,right=straight_ports(4, BALL_TRACK.floor, BALL_TRACK.radius)
        self.assertTrue(mate(right.placed((-64,0,19.2)),high)["compatible"])
        self.assertTrue(mate(low,left.placed((64,0,0)))["compatible"])


if __name__=="__main__":
    unittest.main()
