"""Geometry/assembly tests for SB01-V1 (not a physical rolling certification)."""
import math
import unittest
import cadquery as cq

from brickcad.ports import mate, straight_ports
from brickcad.standards import BALL_TRACK, DUPLO
from parts.switch_start_box.design import (
    PART_ID, StartBox, assembled, build_body, build_lever, build_lid, ports,
)


class StartBoxTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config=StartBox()
        cls.body,cls.profile=build_body(cls.config)
        cls.lid=build_lid(cls.config)
        cls.lever=build_lever(cls.config)

    def test_grid_receiver_and_two_level_side_ports(self):
        c,p=self.config,self.profile
        self.assertEqual(PART_ID,'SB01-V1')
        self.assertEqual((p.nx,p.ny),(4,4))
        self.assertAlmostEqual(p.height,57.6)
        self.assertEqual((p.stud_radius,p.stud_inner_radius,p.tube_radius),(4.7,3.2,6.6))
        self.assertEqual(p.cavity_xy,(57.4,57.4))
        self.assertAlmostEqual(c.floor(0)-c.exit_floor,DUPLO.height)
        self.assertAlmostEqual(c.exit_floor-c.receiver_depth,1.6)
        left,right=ports(c)
        self.assertEqual(left.floor_xyz_mm,(-32.,0.,BALL_TRACK.floor))
        self.assertEqual(right.floor_xyz_mm,(32.,0.,BALL_TRACK.floor))
        west,east=straight_ports(4,BALL_TRACK.floor,BALL_TRACK.radius)
        self.assertTrue(mate(left,east.placed((-64,0,0)))['compatible'])
        self.assertTrue(mate(right,west.placed((64,0,0)))['compatible'])

    def test_all_three_printed_parts_are_one_valid_solid(self):
        for solid in (self.body,self.lid,self.lever):
            self.assertTrue(solid.isValid())
            self.assertEqual(len(solid.Solids()),1)
        self.assertGreater(self.lid.Volume(),1000)
        self.assertGreater(self.lever.Volume(),1000)

    def test_exit_floor_continuity_and_open_ports(self):
        c=self.config
        for x in (-31.5,-27.,-20.,-12.,0.,12.,20.,27.,31.5):
            self.assertTrue(self.body.isInside(cq.Vector(x,0,c.floor(x)-.20)))
            self.assertFalse(self.body.isInside(cq.Vector(x,0,c.floor(x)+.20)))
        for x in (-31.5,31.5):
            self.assertFalse(self.body.isInside(cq.Vector(x,0,25.)))

    def test_rocker_has_two_clear_selected_positions_and_end_stops(self):
        c=self.config
        for side,sign in (('left',-1),('right',1)):
            body=self.body
            lid=self.lid.translate((0,0,self.profile.height))
            lever=self.lever.rotate((0,0,0),(0,1,0),sign*c.tilt_deg).translate((0,0,c.axle_z))
            for a,b in ((body,lid),(body,lever),(lid,lever)):
                self.assertLess(a.intersect(b).Volume(),1e-5)
            # The selected low end is the requested side.
            self.assertLess(-sign*math.sin(math.radians(sign*c.tilt_deg)),0)
            # Mechanical wall bumps stop rotation after about 20 degrees.
            over=self.lever.rotate((0,0,0),(0,1,0),sign*23).translate((0,0,c.axle_z))
            self.assertGreater(body.intersect(over).Volume(),.2)

    def test_marble_geometry_clear_along_both_selected_routes(self):
        c=self.config
        radius=BALL_TRACK.ball_diameter/2
        angle=math.radians(c.tilt_deg)
        for side,sign in (('left',-1),('right',1)):
            body=self.body
            lid=self.lid.translate((0,0,self.profile.height))
            lever=self.lever.rotate((0,0,0),(0,1,0),sign*c.tilt_deg).translate((0,0,c.axle_z))
            for t in (0.,12.):
                x=sign*t
                top=c.axle_z+3.2/math.cos(angle)-t*math.tan(angle)
                center=cq.Vector(x,0,top+radius/math.cos(angle)+.4)
                ball=cq.Solid.makeSphere(radius,center,angleDegrees1=-90)
                self.assertLess(body.intersect(ball).Volume(),1e-4)
                self.assertLess(lid.intersect(ball).Volume(),1e-4)
                self.assertLess(lever.intersect(ball).Volume(),1e-4)
            for t in (29.,):
                x=sign*t
                z=c.floor(x)+radius*math.sqrt(1+.6**2)+.4
                ball=cq.Solid.makeSphere(radius,cq.Vector(x,0,z),angleDegrees1=-90)
                self.assertLess(body.intersect(ball).Volume(),1e-4)

    def test_invalid_geometry_rejected(self):
        with self.assertRaises(ValueError):StartBox(cells=5)
        with self.assertRaises(ValueError):StartBox(receiver_depth=5.0)
        with self.assertRaises(ValueError):StartBox(tilt_deg=40)
        with self.assertRaises(ValueError):StartBox(passage_width=24.0)
        with self.assertRaises(ValueError):assembled(self.config,'middle')


if __name__=='__main__':unittest.main()
