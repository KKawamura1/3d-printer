import cadquery as cq
from brickcad.verify import intersection, VOLUME_TOL
from parts.sloped_curve_open_right.design import path, xy, height, LENGTH, MIRROR
import unittest
from parts.sloped_curve_open_right.design import build_part, verify, ports, DROP
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

    def test_clipped_receivers_and_final_engraving(self):
        # Regression for SC02-V5: useful partial underside tubes must survive
        # footprint clipping, with E31 applied only to full tubes.
        from parts.sloped_curve_open_right.design import PART_ID, loft
        from brickcad.verify import intersection
        import math
        shape,p=build_part()
        footprint=loft('mask').intersect(
            cq.Workplane('XY').box(p.width,p.depth,100,
                      centered=(True,True,False)).val())
        for x,y in p.tubes():
            ring=(cq.Workplane('XY',origin=(x,y,.8))
                  .circle(p.tube_radius).circle(p.tube_inner_radius)
                  .extrude(.5).val())
            trimmed=ring.intersect(footprint)
            if 1.<trimmed.Volume()<ring.Volume()-1.:
                self.assertGreater(intersection(shape,trimmed),
                                   .85*trimmed.Volume(),(x,y))
        # Reconstruct the original label cutter; a later fuse must never
        # refill the recessed text (the SC02-V4 regression).
        _,y,_,_=xy(0)
        if MIRROR: y=-y
        plane=cq.Plane(origin=(-p.width/2+.3,y,5.55),
                       xDir=(0,-1,0),normal=(-1,0,0))
        label=(cq.Workplane(plane).text(
            PART_ID,1.1,.35,font='DejaVu Sans',
            kind='bold',combine=False).val())
        self.assertLess(intersection(shape,label),.10)

    def test_port_drop(self):
        self.assertAlmostEqual(ports()[0].floor_xyz_mm[2]-ports()[1].floor_xyz_mm[2],DROP)
