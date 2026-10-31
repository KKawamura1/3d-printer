import cadquery as cq
from brickcad.verify import intersection, VOLUME_TOL
from parts.steep_gentle_tunnel_left.design import xy, height, MIRROR, path
import unittest
from parts.steep_gentle_tunnel_left.design import build_part, verify, ports, DROP
class Geometry(unittest.TestCase):
    def test_continuous_clearance_and_structure(self):
        shape,p=build_part()
        checks,_=verify(shape,p)
        self.assertTrue(all(checks.values()),checks)
        # PR38/S02: prove the fall chamber has a supporting landing floor
        # and the nominal clearance does not erroneously fit a 28mm ball.
        x,y,_,_=xy(12.)
        self.assertTrue(shape.isInside(cq.Vector(
            x,-y if MIRROR else y,height(12.,'low')-1.)))
        pts=path()
        oversize=cq.Solid.makeSphere(
            14.,pts[len(pts)//2],angleDegrees1=-90)
        self.assertGreater(intersection(shape,oversize),VOLUME_TOL)
    def test_port_drop(self):
        self.assertAlmostEqual(ports()[0].floor_xyz_mm[2]-ports()[1].floor_xyz_mm[2],DROP)
