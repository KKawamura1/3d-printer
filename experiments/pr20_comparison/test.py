import unittest
import cadquery as cq
from parts.tunnel.design import build_tunnel, ball_sweep, Tunnel
from brickcad.verify import VOLUME_TOL
from experiments.pr20_comparison.design import VARIANTS


class RoofComparisonTests(unittest.TestCase):
    def test_variant_ids(self):
        self.assertEqual(set(VARIANTS),{'T02-V1','T03-V1','T04-V1'})

    def test_circular_and_transition_roofs_leave_ball_clearance(self):
        t=Tunnel()
        for roof in ('circle','transition'):
            with self.subTest(roof=roof):
                s,p=build_tunnel(roof=roof,label='T99-V1')
                self.assertTrue(s.isValid())
                self.assertEqual(len(s.Solids()),1)
                self.assertLess(ball_sweep(s,p,t,24.26),VOLUME_TOL)
                self.assertGreater(ball_sweep(s,p,t,28.),VOLUME_TOL)
                # Same opening but different central roofs; this also rejects
                # accidentally generating four copies of the original roof.
                z=t.floor+2*t.radius+.1
                self.assertTrue(s.isInside(cq.Vector(-15.,0,z)))
                self.assertEqual(s.isInside(cq.Vector(0,0,z)),roof=='circle')

    def test_unknown_roof_rejected(self):
        with self.assertRaises(ValueError):build_tunnel(roof='unknown')


class DSupportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from experiments.pr20_comparison.design import build_wall_curve, d_supports
        cls.shape,cls.p=build_wall_curve()
        cls.supports=d_supports(cls.p)

    def test_closed_caps_instead_of_c_shapes(self):
        import math
        self.assertEqual(len(self.supports),5)
        self.assertEqual(sum(r['hollow'] for _,r in self.supports),4)
        for support,r in self.supports:
            self.assertTrue(support.isValid())
            self.assertEqual(len(support.Solids()),1)
            x,y=r['centre_xy_mm'];d=math.hypot(x+32,y-32)
            # The cap is real material at the radial cut, not an open C.
            at=r['cap_offset_mm']+(.6 if r['inner_boundary'] else -.6)
            self.assertTrue(support.isInside(cq.Vector(x+at*(x+32)/d,y+at*(y-32)/d,2)))
            # Both faces of the former slit now connect along a closed perimeter.
            if r['hollow']:
                face=min(support.Faces(),key=lambda f:abs(f.Center().z-4.75))
                self.assertEqual(len(face.innerWires()),1)

    def test_no_added_floors_or_blocking_stud_collision(self):
        from parts.sloped_curve.design import receiver_audit, curved_footprint
        for x,y in [(-16,16),(-24,24),(24,-24)]:
            self.assertFalse(self.shape.isInside(cq.Vector(x,y,1)))
            self.assertFalse(self.shape.isInside(cq.Vector(x,y,6.1)))
        for support,_ in self.supports:
            self.assertLess(support.cut(curved_footprint()).Volume(),VOLUME_TOL)
            # Cap material is contained within the original tube OD.
            # Only the pre-existing trial's small OD interference can remain.
            for x,y in self.p.studs():
                centre=cq.Vector(x,y,2)
                self.assertFalse(support.isInside(centre))
        self.assertTrue(receiver_audit(self.shape,self.p)['no_blocking_collision'])
