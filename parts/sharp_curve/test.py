"""Targeted CAD tests for the 2x2x1 R16 right curve."""
import unittest
import cadquery as cq

from brickcad.ports import mate, straight_ports
from brickcad.standards import BALL_TRACK, DUPLO
from brickcad.verify import VOLUME_TOL
from parts.sharp_curve.design import (
    PART_ID, SharpCurve, build_curve, ball_intersections, ports
)


class SharpCurveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = SharpCurve()
        cls.shape, cls.p = build_curve(cls.c)

    def test_footprint_and_revision(self):
        self.assertEqual(PART_ID, "C01-V4")
        self.assertEqual((self.p.nx, self.p.ny), (2,2))
        self.assertAlmostEqual(self.p.height, DUPLO.height)
        self.assertAlmostEqual(self.c.turn_radius, 16.)
        self.assertTrue(self.shape.isValid())
        self.assertEqual(len(self.shape.Solids()), 1)

    def test_right_turn_and_rail_sections(self):
        west, south = ports(self.c)
        self.assertEqual(west.floor_xyz_mm, (-16.,0.,BALL_TRACK.floor))
        self.assertEqual(south.floor_xyz_mm, (0.,-16.,BALL_TRACK.floor))
        incoming = straight_ports(2,BALL_TRACK.floor,BALL_TRACK.radius)[1].placed((-32.,0.,0.))
        outgoing = straight_ports(2,BALL_TRACK.floor,BALL_TRACK.radius)[0].placed(
            (0.,-32.,0.), -90)
        self.assertTrue(mate(incoming,west)["compatible"])
        self.assertTrue(mate(south,outgoing)["compatible"])

    def test_ball_path_clear_and_oversize_blocked(self):
        self.assertLess(max(ball_intersections(self.shape,self.c,samples=19)),VOLUME_TOL)
        self.assertGreater(max(ball_intersections(self.shape,self.c,diameter=28.,samples=5)),VOLUME_TOL)

    def test_e31_receiver_and_studless_open_top(self):
        self.assertAlmostEqual(self.p.tube_radius,6.60)
        self.assertEqual(self.p.cavity_xy,(25.4,25.4))
        self.assertFalse(self.shape.isInside(cq.Vector(0,0,1)))
        self.assertTrue(self.shape.isInside(cq.Vector(4.,4.,1)))
        self.assertAlmostEqual(self.shape.BoundingBox().zmax, DUPLO.height, places=5)
        for x,y in self.p.studs():
            self.assertFalse(self.shape.isInside(cq.Vector(x,y,22)))


if __name__ == "__main__":
    unittest.main()
