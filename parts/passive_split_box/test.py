"""SB02 geometry checks: static CAD only; physical rolling is not asserted."""
import math
import unittest
import cadquery as cq
from brickcad.standards import BALL_TRACK, DUPLO
from brickcad.verify import VOLUME_TOL, intersection
from parts.passive_split_box.design import PART_ID, SplitStart, build_split_start, center_samples, ball_clearance, ports

class PassiveSplitBoxTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = SplitStart()
        cls.shape, cls.p = build_split_start(cls.config)

    def test_size_fit_and_single_print_part(self):
        self.assertEqual(PART_ID,'SB02-V2')
        self.assertEqual((self.p.nx,self.p.ny),(4,2))
        self.assertAlmostEqual(self.p.height,2*DUPLO.height)
        self.assertTrue(self.shape.isValid())
        self.assertEqual(len(self.shape.Solids()),1)
        self.assertEqual((self.p.stud_radius,self.p.stud_inner_radius,self.p.tube_radius),(4.7,3.2,6.60))
        self.assertEqual(self.p.cavity_xy,(57.4,25.4))
        self.assertAlmostEqual(self.config.exit_floor-self.config.receiver_depth,1.60)

    def test_top_hole_matches_exact_existing_standard(self):
        self.assertAlmostEqual(self.config.entry_diameter,BALL_TRACK.opening)
        r=self.config.entry_diameter/2
        for i in range(32):
            angle=2*math.pi*i/32
            x=math.cos(angle);y=math.sin(angle)
            self.assertFalse(self.shape.isInside(cq.Vector((r-.35)*x,(r-.35)*y,38.1)))
            self.assertTrue(self.shape.isInside(cq.Vector((r+.35)*x,(r+.35)*y,38.1)))

    def test_center_ridge_and_symmetric_slopes(self):
        c=self.config
        self.assertGreater(c.center_ridge_floor,c.exit_floor+5)
        self.assertAlmostEqual(c.floor(0),c.center_ridge_floor)
        for x in (2,8,16,24,31.9):
            self.assertAlmostEqual(c.floor(x),c.floor(-x))
            self.assertGreater(c.floor(x-0.1),c.floor(x+0.1))
        for x in (0,8,24,31.5):
            self.assertTrue(self.shape.isInside(cq.Vector(x,0,c.floor(x)-.2)))
            self.assertFalse(self.shape.isInside(cq.Vector(x,0,c.floor(x)+.2)))

    def test_four_studs_flanking_central_hole(self):
        self.assertEqual(len([s for s in self.p.studs() if abs(s[0])>16]),4)
        for x in (-24,24):
            for y in (-8,8):
                self.assertTrue(self.shape.isInside(cq.Vector(x+4,y,40.)))
        for x in (-8,8):
            for y in (-8,8):
                self.assertFalse(self.shape.isInside(cq.Vector(x,y,39.0)))

    def test_outlet_port_matches_existing_round_rail(self):
        west,east=ports(self.config)
        self.assertEqual(west.floor_xyz_mm,(-32.,0.,BALL_TRACK.floor))
        self.assertEqual(east.floor_xyz_mm,(32.,0.,BALL_TRACK.floor))
        self.assertEqual(west.outward,(-1.,0.,0.))
        self.assertEqual(east.outward,(1.,0.,0.))
        self.assertAlmostEqual(west.section_radius_mm,BALL_TRACK.radius)
        self.assertAlmostEqual(east.section_radius_mm,BALL_TRACK.radius)
        for x in (-31.5,31.5):
            self.assertFalse(self.shape.isInside(cq.Vector(x,0,18)))
            self.assertTrue(self.shape.isInside(cq.Vector(x,0,5.9)))

    def test_ball_drops_virtually_through_center_hole(self):
        r=BALL_TRACK.ball_diameter/2
        for x in (0.,-.4,.4):
            for z in (43.,39.,35.,31.,27.):
                sphere=cq.Solid.makeSphere(r,cq.Vector(x,0,z),angleDegrees1=-90)
                self.assertLess(intersection(self.shape,sphere),VOLUME_TOL,(x,z))

    def test_ball_samples_clear_both_downhill_routes(self):
        rows=ball_clearance(self.config,self.shape,count=41)
        self.assertLess(max(v['intersection_mm3'] for v in rows),VOLUME_TOL)
        self.assertEqual(len(rows),41)
        # Oversized ball must fail the same 25.74-mm-diameter exit aperture.
        inflated=cq.Solid.makeSphere(14.,cq.Vector(31.6,0,6.35+14.),angleDegrees1=-90)
        self.assertGreater(intersection(self.shape,inflated),VOLUME_TOL)

    def test_flattened_roof_and_round_exit_clearance(self):
        c=self.config
        self.assertAlmostEqual(c.roof_height,36.5)
        self.assertAlmostEqual(2*DUPLO.height-c.roof_height,1.9)
        for x in (-20.,-16.,16.,20.):
            self.assertFalse(self.shape.isInside(cq.Vector(x,0,c.roof_height-.3)))
            self.assertTrue(self.shape.isInside(cq.Vector(x,0,c.roof_height+.3)))
        # Interior sphere collision checks span both branches.
        samples=ball_clearance(c,self.shape,count=41)
        self.assertLess(max(v['intersection_mm3'] for v in samples),VOLUME_TOL)

    def test_reject_incompatible_dimensions(self):
        for changes in (dict(cells_x=5),dict(entry_diameter=30),dict(receiver_depth=5.),
                        dict(center_ridge_floor=20),dict(hole_bottom=18),
                        dict(roof_height=35.5),dict(roof_height=38.0)):
            with self.subTest(changes=changes),self.assertRaises(ValueError):SplitStart(**changes)

if __name__=='__main__':unittest.main()
