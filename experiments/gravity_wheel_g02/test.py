"""Focused static checks for GW02-V1 (not a dynamic or safety certification)."""
import unittest
import cadquery as cq
from experiments.gravity_wheel_g02 import design as g


class GW02Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parts = g.parts()
        cls.checks = g.static_checks(cls.parts)

    def test_valid_geometry_and_static_clearance(self):
        self.assertTrue(all(self.checks.values()),
                        [k for k,v in self.checks.items() if not v])

    def test_gravity_drop_and_nonzero_start_torque(self):
        self.assertGreater(g.POCKET_X, 0)
        self.assertAlmostEqual(2*g.POCKET_Z, 70.0)
        self.assertGreater(2*g.POCKET_Z, g.BALL_D)
        self.assertAlmostEqual(g.mouth_at(0).x, -g.mouth_at(180).x, places=6)

    def test_ball_fits_bore(self):
        s=cq.Solid.makeSphere(g.BALL_R,g.vec(g.POCKET_X,0,g.POCKET_Z),
                              angleDegrees1=-90)
        self.assertLess(g.rotor_local().intersect(s).Volume(), .05)

    def test_shroud_blocks_transit_exit_but_opens_at_endpoints(self):
        dx,dz=g.tube_vectors()
        cover=g.shroud_local()
        ball=cq.Solid.makeSphere(g.BALL_R,
             g.vec(g.POCKET_X+25*dx,0,g.POCKET_Z+25*dz),angleDegrees1=-90)
        self.assertLess(cover.intersect(ball).Volume(), .05)
        self.assertGreater(cover.intersect(g.rotate(ball,90)).Volume(),100)
        self.assertLess(cover.intersect(g.rotate(ball,180)).Volume(),.05)


if __name__=='__main__':
    unittest.main()
