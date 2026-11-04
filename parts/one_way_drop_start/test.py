"""Geometry checks for SB03-V1. Static CAD is not physical rolling validation."""
import math
import unittest

import cadquery as cq

from brickcad.ports import Port
from brickcad.standards import BALL_TRACK, DUPLO
from brickcad.verify import intersection, VOLUME_TOL
from parts.one_way_drop_start.design import (
    PART_ID, OneWayDrop, ball_path_intersections, build_one_way_drop,
    drop_intersections, ports,
)


class OneWayDropTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c=OneWayDrop()
        cls.shape,cls.profile=build_one_way_drop(cls.c)

    def test_id_size_and_shallow_e31_receiver(self):
        c,p=self.c,self.profile
        self.assertEqual(PART_ID,'SB03-V1')
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

    def test_no_flat_trap_or_reverse_slope(self):
        c=self.c
        self.assertGreater(c.floor(-14.),c.floor(0.))
        self.assertGreater(c.floor(0.),c.floor(10.))
        self.assertGreater(c.floor(10.),c.floor(16.))
        for x in (-11.,-6.,0.,6.,12.,15.):
            self.assertTrue(self.shape.isInside(cq.Vector(x,0,c.floor(x)-.15)))
            self.assertFalse(self.shape.isInside(cq.Vector(x,0,c.floor(x)+.15)))

    def test_tube_slot_and_floor_not_pierced(self):
        # A real tube hole and ring should exist below the shallow chamber.
        self.assertFalse(self.shape.isInside(cq.Vector(0,0,1.)))
        self.assertTrue(self.shape.isInside(cq.Vector(5.5,2.,2.)))
        self.assertTrue(self.shape.isInside(cq.Vector(0,0,5.9)))
        self.assertFalse(self.shape.isInside(cq.Vector(0,0,12.)))

    def test_static_ball_clearance_drop_and_to_exit(self):
        self.assertLess(max(ball_path_intersections(self.c,self.shape,21)),VOLUME_TOL)
        self.assertLess(max(drop_intersections(self.c,self.shape)),VOLUME_TOL)
        # Check falling spheres with minor left/right entrance offsets.
        radius=BALL_TRACK.ball_diameter/2
        for x in (-.45,.45):
            for z in (28.,34.):
                ball=cq.Solid.makeSphere(radius,cq.Vector(x,0,z),angleDegrees1=-90)
                self.assertLess(intersection(self.shape,ball),VOLUME_TOL,
                                f'sphere stuck at x={x},z={z}')

    def test_oversized_sphere_is_rejected_by_inlet(self):
        ball=cq.Solid.makeSphere(14.,cq.Vector(0,0,38.4),angleDegrees1=-90)
        self.assertGreater(intersection(self.shape,ball),VOLUME_TOL)

    def test_invalid_specs_rejected(self):
        for variant in (dict(cells=3),dict(courses=3),dict(inlet_diameter=26.0),
                        dict(outlet_floor=7.),dict(passage_radius=13.5),
                        dict(receiver_depth=5.),dict(slope=0),dict(blind_end_x=-15.8),
                        dict(inlet_bottom_z=10)):
            with self.subTest(variant=variant):
                with self.assertRaises(ValueError):OneWayDrop(**variant)


if __name__=='__main__':
    unittest.main()
