import cadquery as cq
from brickcad.verify import intersection, VOLUME_TOL
from parts.sharp_downhill_tunnel_left.design import path, xy, height, LENGTH, MIRROR
import unittest
from parts.sharp_downhill_tunnel_left.design import build_part, verify, ports, DROP
class Geometry(unittest.TestCase):
    def test_continuous_clearance_and_structure(self):
        shape,p=build_part()
        checks,_=verify(shape,p)
        self.assertTrue(all(checks.values()),checks)
        # C01/C02 lesson: nominal sphere clearance is not sufficient;
        # reject an oversized sphere and require support under the rail.
        centres=path()
        oversize=cq.Solid.makeSphere(
            14., centres[len(centres)//2], angleDegrees1=-90)
        self.assertGreater(intersection(shape,oversize),VOLUME_TOL)
        for fraction in (.15,.35,.65,.85):
            s=LENGTH*fraction
            x,y,_,_=xy(s)
            self.assertTrue(shape.isInside(
                cq.Vector(x,-y if MIRROR else y,height(s)-.15)),
                "missing rolling floor at s="+str(s))

    def test_versioned_footprint_clipped_receiver_supports(self):
        from parts.sharp_downhill_tunnel_left.design import PART_ID, loft
        from brickcad.model import receiver
        from brickcad.verify import intersection
        import json
        from pathlib import Path
        spec = json.loads((Path(__file__).parent / 'cad-build.json').read_text())
        self.assertEqual(spec['version'], PART_ID)
        shape, p = build_part()
        mask = loft('mask').intersect(
            cq.Workplane('XY').box(p.width, p.depth, 100,
                                   centered=(True, True, False)).val())
        # These are pre-E31 supports: clipped receiver rings must not disappear.
        for x, y in p.tubes():
            ring = (cq.Workplane('XY', origin=(x, y, .8))
                    .circle(p.tube_radius).circle(p.tube_inner_radius)
                    .extrude(.5).val())
            clipped = ring.intersect(mask)
            if clipped.Volume() > 1. and clipped.Volume() < ring.Volume() - 1.:
                self.assertGreater(intersection(shape, clipped),
                                   .85 * clipped.Volume(), (x, y))

    def test_port_drop(self):
        self.assertAlmostEqual(ports()[0].floor_xyz_mm[2]-ports()[1].floor_xyz_mm[2],DROP)
