import unittest
import cadquery as cq
from parts.tunnel.design_e31 import Tunnel, build_tunnel, ball_sweep
from parts.straight_rail.design import Rail, build_rail
from brickcad.verify import intersection, VOLUME_TOL


class TunnelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t=Tunnel()
        cls.shape,cls.p=build_tunnel(cls.t)

    def test_swept_ball_and_oversize_control(self):
        self.assertLess(ball_sweep(self.shape,self.p,self.t,24.26),VOLUME_TOL)
        self.assertGreater(ball_sweep(self.shape,self.p,self.t,28),VOLUME_TOL)

    def test_join_with_existing_rail(self):
        rail,_=build_rail()
        # DUPLO grid: centres 48 mm apart leaves the usual 0.2 mm body gap.
        assembly=self.shape.fuse(rail.translate((-48,0,0)))
        self.assertEqual(self.t.floor,Rail().floor)
        self.assertEqual(self.t.radius,Rail().radius)
        for x in (-17.,-16.1,-16.,-15.9,-15.):
            ball=cq.Solid.makeSphere(12.13,cq.Vector(x,0,18.53),angleDegrees1=-90)
            self.assertLess(intersection(assembly,ball),VOLUME_TOL)

    def test_adopted_e27_connection_geometry(self):
        self.assertEqual((self.p.stud_radius,self.p.stud_inner_radius,self.p.tube_radius),(4.7,3.2,6.60))
        self.assertEqual(self.p.cavity_xy,(25.4,25.4))
        self.assertFalse(self.shape.isInside(cq.Vector(6.5,0,2.25)))  # E31-05 open radial slot
        self.assertTrue(self.shape.isInside(cq.Vector(4.78,4.78,2.25)))  # R0.20 bead, 45-degree quadrant
        self.assertFalse(self.shape.isInside(cq.Vector(4.85,4.85,2.25)))
        for x,y in self.p.studs():
            self.assertTrue(self.shape.isInside(cq.Vector(x+4.69,y,39.5)))
            self.assertFalse(self.shape.isInside(cq.Vector(x+4.71,y,39.5)))
            self.assertFalse(self.shape.isInside(cq.Vector(x,y,39.5)))

    def test_round_entry_high_ceiling_style(self):
        from parts.tunnel.design_e31 import PART_ID
        self.assertEqual(PART_ID, 'T01-V4')
        # Internal roof is higher than the circular entrance at this position.
        z_circle=self.t.floor+2*self.t.radius
        self.assertFalse(self.shape.isInside(cq.Vector(0,0,z_circle+0.2)))
        self.assertTrue(self.shape.isInside(cq.Vector(0,0,self.t.ceiling+0.5)))

    def test_receiver_separated_from_passage(self):
        # Full 1.6 mm floor above receiver at the lowest channel location.
        for z in (4.8,5.5,6.3):
            self.assertTrue(self.shape.isInside(cq.Vector(0,0,z)))
        self.assertFalse(self.shape.isInside(cq.Vector(0,0,6.4)))
        self.assertTrue(self.shape.isInside(cq.Vector(0,0,34.9)))

    def test_reject_insufficient_floor_and_roof(self):
        for kwargs in (dict(cavity_height=5.),dict(ceiling=37.),dict(floor=float('nan'))):
            with self.assertRaises(ValueError):Tunnel(**kwargs)


if __name__=='__main__':unittest.main()
