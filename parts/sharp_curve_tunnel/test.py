"""C02-V3 checks: circular ports, wider inner chamber, roof and receiver."""
import unittest
import cadquery as cq
from brickcad.ports import mate, straight_ports
from brickcad.standards import BALL_TRACK, DUPLO
from brickcad.verify import VOLUME_TOL
from parts.sharp_curve_tunnel.design import (PART_ID, CHAMBER_RADIUS, CHAMBER_CAP_Z, build_tunnel)
from parts.sharp_curve.design import SharpCurve, ball_intersections, ports


class SharpCurveTunnelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c=SharpCurve()
        cls.shape,cls.p=build_tunnel(cls.c)

    def test_height_and_top_studs(self):
        self.assertEqual(PART_ID,"C02-V3")
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

    def test_enlarged_turn_room_and_mouths(self):
        # C02-V2 passed nominal R16 collision checks but physically jammed.
        # These points were solid in V2: guard against shrinking the new room.
        self.assertAlmostEqual(CHAMBER_RADIUS, 13.25)
        self.assertAlmostEqual(CHAMBER_CAP_Z, 21.)
        self.assertFalse(self.shape.isInside(cq.Vector(0.,12.5,20.)))
        self.assertFalse(self.shape.isInside(cq.Vector(12.5,0.,20.)))
        # The enlarged room must not open new mouths on north or east.
        self.assertTrue(self.shape.isInside(cq.Vector(0.,14.2,20.)))
        self.assertTrue(self.shape.isInside(cq.Vector(14.2,0.,20.)))
        self.assertTrue(self.shape.isInside(cq.Vector(-15.8,0.,33.)))
        self.assertTrue(self.shape.isInside(cq.Vector(0.,-15.8,33.)))
        self.assertTrue(self.shape.isInside(cq.Vector(0.,0.,6.2)))
        self.assertFalse(self.shape.isInside(cq.Vector(0.,0.,6.5)))
        self.assertFalse(self.shape.isInside(cq.Vector(0.,0.,33.)))
        self.assertTrue(self.shape.isInside(cq.Vector(0.,0.,37.4)))

    def test_underside_and_ceiling(self):
        self.assertAlmostEqual(self.p.tube_radius,6.60)
        self.assertEqual(self.p.cavity_xy,(25.4,25.4))
        self.assertFalse(self.shape.isInside(cq.Vector(0,0,1)))
        self.assertTrue(self.shape.isInside(cq.Vector(4,4,1)))
        self.assertTrue(self.shape.isInside(cq.Vector(-4.686,-4.686,37.4)))
        mid=-16+self.c.turn_radius/(2**.5)
        self.assertFalse(self.shape.isInside(cq.Vector(mid,mid,34.)))
        self.assertTrue(self.shape.isInside(cq.Vector(mid,mid,36.)))
        self.assertTrue(self.shape.isInside(cq.Vector(-15.8,0,33.)))
        self.assertTrue(self.shape.isInside(cq.Vector(0,-15.8,33.)))
        self.assertGreater(self.p.height-35.,DUPLO.roof)


if __name__=="__main__":
    unittest.main()
