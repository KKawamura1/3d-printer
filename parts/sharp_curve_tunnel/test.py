"""C02-V7: retain the physically promising C02-V2 turn guidance."""
import unittest
import math
from unittest.mock import patch
import cadquery as cq
from brickcad.ports import mate, straight_ports
from brickcad.standards import BALL_TRACK, DUPLO
from brickcad.verify import VOLUME_TOL
from parts.sharp_curve_tunnel.design import PART_ID, build_tunnel, _engrave_north, SOURCE_CURVE_ID
from parts.sharp_curve.design import SharpCurve, ball_intersections, ports


class SharpCurveTunnelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c=SharpCurve()
        cls.shape,cls.p=build_tunnel(cls.c)

    def test_height_and_top_studs(self):
        self.assertEqual(PART_ID,"C02-V7")
        self.assertEqual(SOURCE_CURVE_ID,"C01-V6")
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
        mid=-16+self.c.turn_radius/(2**.5)
        self.assertFalse(self.shape.isInside(cq.Vector(mid,mid,34.)))
        self.assertTrue(self.shape.isInside(cq.Vector(mid,mid,36.)))
        self.assertTrue(self.shape.isInside(cq.Vector(-15.8,0,33.)))
        self.assertTrue(self.shape.isInside(cq.Vector(0,-15.8,33.)))
        self.assertGreater(self.p.height-35.,DUPLO.roof)

    def test_original_inner_wall_not_replaced_by_wide_chamber(self):
        # Solid in V2; V4 removed these surfaces and produced a ball trap.
        self.assertTrue(self.shape.isInside(cq.Vector(0., 12.5, 20.)))
        self.assertTrue(self.shape.isInside(cq.Vector(12.5, 0., 20.)))

    def test_e31_short_slot_clear_of_receiver_ceiling(self):
        from parts.tunnel.e31_fit import SLOT_END_Z, SLOT_END_RADIUS
        self.assertAlmostEqual(SLOT_END_Z,3.50)
        self.assertAlmostEqual(SLOT_END_Z+SLOT_END_RADIUS,4.15)
        self.assertGreaterEqual(self.c.receiver_depth-(SLOT_END_Z+SLOT_END_RADIUS),.60-1e-6)
        for x,y in ((6.5,0.),(0.,6.5),(-6.5,0.),(0.,-6.5)):
            self.assertFalse(self.shape.isInside(cq.Vector(x,y,2.25)))
            self.assertTrue(self.shape.isInside(cq.Vector(x,y,4.3)))

    def test_visible_ports_have_round_openings(self):
        # Verify visible entrances on 12 rays rather than only roof height.
        radius=self.c.section_radius
        center_z=self.c.floor+radius
        for angle in range(0,360,30):
            a=math.radians(angle)
            for r,is_solid in ((radius-.45,False),(radius+.45,True)):
                lateral=r*math.cos(a)
                z=center_z+r*math.sin(a)
                for xyz in ((-15.8,lateral,z),(lateral,-15.8,z)):
                    self.assertEqual(self.shape.isInside(cq.Vector(*xyz)),is_solid,
                                     msg=f"port={xyz}, r={r}, angle={angle}")

    def test_standard_engraving_on_finished_north_wall(self):
        from brickcad.marking import engrave
        blank=cq.Workplane("XY").box(31.8,31.8,38.4,
                        centered=(True,True,False)).val()
        with patch("parts.sharp_curve_tunnel.design.engrave",wraps=engrave) as marker:
            marked=_engrave_north(blank,PART_ID,31.8)
        self.assertEqual(marker.call_count,1)
        self.assertEqual(marker.call_args.kwargs,dict(x=0,y=-15.9,z=18.0))
        self.assertTrue(marked.isValid())
        self.assertGreater(blank.Volume()-marked.Volume(),.2)


if __name__=="__main__":
    unittest.main()
