"""C02 targeted CAD checks: dimensions, curved channel, roof, and receiver."""
import unittest
import cadquery as cq
from brickcad.ports import mate, straight_ports
from brickcad.standards import BALL_TRACK, DUPLO
from brickcad.verify import VOLUME_TOL
from parts.sharp_curve_tunnel.design import PART_ID, build_tunnel
from parts.sharp_curve.design import SharpCurve, ball_intersections, ports


class SharpCurveTunnelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c=SharpCurve()
        cls.shape,cls.p=build_tunnel(cls.c)

    def test_height_and_top_studs(self):
        self.assertEqual(PART_ID,"C02-V1")
        self.assertEqual((self.p.nx,self.p.ny),(2,2))
        self.assertAlmostEqual(self.p.height,2*DUPLO.height)
        self.assertTrue(self.shape.isValid())
        self.assertEqual(len(self.shape.Solids()),1)
        for x,y in self.p.studs():
            self.assertTrue(self.shape.isInside(cq.Vector(x,y,38.3)))
            self.assertFalse(self.shape.isInside(cq.Vector(x,y,41.)))
            self.assertTrue(self.shape.isInside(cq.Vector(x+4.,y,41.)))

    def test_same_right_turn_as_c01(self):
        west,south=ports(self.c)
        self.assertEqual(west.floor_xyz_mm,(-16.,0.,BALL_TRACK.floor))
        self.assertEqual(south.floor_xyz_mm,(0.,-16.,BALL_TRACK.floor))
        incoming=straight_ports(2,BALL_TRACK.floor,BALL_TRACK.radius)[1].placed((-32.,0.,0.))
        outgoing=straight_ports(2,BALL_TRACK.floor,BALL_TRACK.radius)[0].placed((0.,-32.,0.),-90)
        self.assertTrue(mate(incoming,west)["compatible"])
        self.assertTrue(mate(south,outgoing)["compatible"])

    def test_ball_path_and_negative_control(self):
        self.assertLess(max(ball_intersections(self.shape,self.c,samples=19)),VOLUME_TOL)
        self.assertGreater(max(ball_intersections(self.shape,self.c,diameter=28.,samples=5)),VOLUME_TOL)

    def test_underside_and_ceiling(self):
        self.assertAlmostEqual(self.p.tube_radius,6.60)
        self.assertEqual(self.p.cavity_xy,(25.4,25.4))
        self.assertFalse(self.shape.isInside(cq.Vector(0,0,1)))
        self.assertTrue(self.shape.isInside(cq.Vector(4,4,1)))
        self.assertTrue(self.shape.isInside(cq.Vector(-4.686,-4.686,37.4)))
        self.assertGreater(self.p.height-(self.c.floor+2*self.c.section_radius),DUPLO.roof)


if __name__=="__main__":
    unittest.main()
