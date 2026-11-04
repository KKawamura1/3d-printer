"""Geometry checks for SB03-V2. Static CAD is not physical rolling validation."""
import math
import unittest

import cadquery as cq

from brickcad.ports import Port
from brickcad.standards import BALL_TRACK, DUPLO
from brickcad.verify import intersection, VOLUME_TOL
from parts.one_way_drop_start.design import (
    PART_ID, OneWayDrop, ball_path_intersections, build_one_way_drop,
    inlet_ball_intersections, centerline, ports,
)


class OneWayDropTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c=OneWayDrop()
        cls.shape,cls.profile=build_one_way_drop(cls.c)

    def test_id_size_and_shallow_e31_receiver(self):
        c,p=self.c,self.profile
        self.assertEqual(PART_ID,'SB03-V2')
        self.assertEqual((p.nx,p.ny,p.height),(2,2,2*DUPLO.height))
        self.assertAlmostEqual(p.width,31.8)
        self.assertEqual((p.stud_radius,p.stud_inner_radius,p.tube_radius),(4.7,3.2,6.6))
        self.assertEqual(p.cavity_xy,(25.4,25.4))
        self.assertAlmostEqual(c.outlet_floor-c.receiver_depth,1.6)
        self.assertEqual(p.tubes(),[(0.,0.)])
        self.assertTrue(self.shape.isValid())
        self.assertEqual(len(self.shape.Solids()),1)

    def test_round_top_inlet_standard_size_and_open(self):
        c=self.c
        self.assertAlmostEqual(c.inlet_diameter, BALL_TRACK.opening)
        z=2*DUPLO.height-0.5
        self.assertFalse(self.shape.isInside(cq.Vector(0,0,z)))
        self.assertFalse(self.shape.isInside(cq.Vector(12.5,0,z)))
        self.assertTrue(self.shape.isInside(cq.Vector(13.7,0,z)))
        # A circular top hole leaves NO intact stud centers on a 2x2 brick.
        self.assertFalse(self.shape.isInside(cq.Vector(8,8,40.)))
        self.assertFalse(self.shape.isInside(cq.Vector(-8,-8,40.)))

    def test_single_east_outlet_mates_standard_floor(self):
        c=self.c
        (outlet,)=ports(c)
        self.assertEqual(outlet.floor_xyz_mm,(16.,0.,BALL_TRACK.floor))
        self.assertEqual(outlet.outward,(1.,0.,0.))
        self.assertAlmostEqual(outlet.section_radius_mm,BALL_TRACK.radius)
        # One-sided: east channel opens, west end is a solid end-wall.
        self.assertFalse(self.shape.isInside(cq.Vector(15.5,0,20.)))
        self.assertTrue(self.shape.isInside(cq.Vector(-15.,0,23.)))

    def test_vertical_R16_curve_tangents_not_8p5deg_slope(self):
        c=self.c
        self.assertAlmostEqual(c.bend_radius,DUPLO.pitch)
        start,end=centerline(c,0),centerline(c,1)
        self.assertAlmostEqual(start.x,0.)
        self.assertAlmostEqual(start.z,c.outlet_axis_z+16.)
        self.assertAlmostEqual(end.x,16.)
        self.assertAlmostEqual(end.z,c.outlet_axis_z)
        self.assertAlmostEqual(start.z-end.z,16.)
        d=1e-4
        near_start=centerline(c,d)
        near_end=centerline(c,1-d)
        self.assertLess(abs(near_start.x-start.x),1e-5)
        self.assertLess(abs(end.z-near_end.z),1e-5)
        self.assertLess(near_start.z,start.z)
        self.assertLess(near_end.x,end.x)
        # The curved scoop, unlike V1, stops a purely vertical drop.
        low=cq.Solid.makeSphere(BALL_TRACK.ball_diameter/2,
                               cq.Vector(0,0,26.),angleDegrees1=-90)
        self.assertGreater(intersection(self.shape,low),.1)

    def test_tube_slot_and_floor_not_pierced(self):
        # A real tube hole and ring should exist below the shallow chamber.
        self.assertFalse(self.shape.isInside(cq.Vector(0,0,1.)))
        self.assertTrue(self.shape.isInside(cq.Vector(5.5,2.,2.)))
        self.assertTrue(self.shape.isInside(cq.Vector(0,0,5.9)))
        self.assertFalse(self.shape.isInside(cq.Vector(0,0,12.)))

    def test_smooth_R16_ball_clearance_and_entry(self):
        self.assertLess(max(ball_path_intersections(self.c,self.shape,31)),VOLUME_TOL)
        self.assertLess(max(inlet_ball_intersections(self.c,self.shape)),VOLUME_TOL)
        radius=BALL_TRACK.ball_diameter/2
        for x in (-.4,.4):
            for z in (40.,42.):
                ball=cq.Solid.makeSphere(radius,cq.Vector(x,0,z),angleDegrees1=-90)
                self.assertLess(intersection(self.shape,ball),VOLUME_TOL)
        # Full circular mouth at the east exterior.
        for degrees in range(0,360,45):
            a=math.radians(degrees)
            y=.85*self.c.passage_radius*math.cos(a)
            z=self.c.outlet_axis_z+.85*self.c.passage_radius*math.sin(a)
            self.assertFalse(self.shape.isInside(cq.Vector(15.8,y,z)))

    def test_oversized_sphere_is_rejected_by_inlet(self):
        ball=cq.Solid.makeSphere(14.,cq.Vector(0,0,38.4),angleDegrees1=-90)
        self.assertGreater(intersection(self.shape,ball),VOLUME_TOL)

    def test_invalid_specs_rejected(self):
        for variant in (dict(cells=3),dict(courses=3),dict(inlet_diameter=26.0),
                        dict(outlet_floor=7.),dict(passage_radius=13.5),
                        dict(receiver_depth=5.),dict(bend_radius=20.),
                        dict(loft_steps=4),dict(inlet_extension=0.),
                        dict(outlet_extension=4.)):
            with self.subTest(variant=variant):
                with self.assertRaises(ValueError):OneWayDrop(**variant)
        with self.assertRaises(ValueError):centerline(self.c,1.5)

if __name__=='__main__':
    unittest.main()
