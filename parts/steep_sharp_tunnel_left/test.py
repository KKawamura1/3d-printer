import unittest
from parts.steep_sharp_tunnel_left.design import *
class Geometry(unittest.TestCase):
    def test_left_turn(self):
        shape,p=build_tunnel()
        self.assertTrue(shape.isValid())
        self.assertEqual(len(shape.Solids()),1)
        self.assertLess(max(swept_ball_path_collisions(shape)),VOLUME_TOL)
        self.assertEqual(ports()[1].outward,(0.,1.,0.))
        self.assertTrue(shape.isInside(cq.Vector(0,-15.2,18.)))
