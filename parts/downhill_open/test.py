import cadquery as cq
from brickcad.verify import intersection, VOLUME_TOL
from parts.downhill_open.design import path, xy, height, LENGTH, MIRROR
import unittest
from parts.downhill_open.design import build_part, verify, ports, DROP
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
        from parts.downhill_open.design import PART_ID, loft
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
        # PR58 B: the shortened E31 slots must not break through the floor.
        from parts.tunnel.e31_fit import SLOT_END_Z, SLOT_END_RADIUS
        from parts.downhill_open.design import DEPTH
        self.assertAlmostEqual(SLOT_END_Z,3.50)
        self.assertLess(SLOT_END_Z+SLOT_END_RADIUS,DEPTH)
        self.assertGreater(len(p.tubes()),0)
        for x,y in p.tubes():
            for dx,dy in ((6.5,0),(-6.5,0),(0,6.5),(0,-6.5)):
                self.assertFalse(shape.isInside(cq.Vector(x+dx,y+dy,3.5)),
                                 (x,y,dx,dy,'slot closed'))
                self.assertTrue(shape.isInside(cq.Vector(x+dx,y+dy,4.4)),
                                (x,y,dx,dy,'slot pierced roof'))

    def test_standard_visible_engraving(self):
        import inspect
        import json
        from pathlib import Path
        from brickcad.marking import engrave
        from parts.downhill_open.design import PART_ID, LABEL_X, LABEL_Z
        shape,p=build_part()
        bare,_=build_part(label=None)
        params=inspect.signature(engrave).parameters
        self.assertEqual(params['size'].default,3.)
        self.assertEqual(params['depth'].default,.4)
        spec=json.loads((Path(__file__).parent/'cad-build.json').read_text())
        self.assertEqual(PART_ID,spec['version'])
        self.assertGreater(LABEL_Z-3./2,6.35)
        # The outer -Y wall is exposed even when adjacent rails are connected.
        # Reconstruct the standard cutter, and assert material is really removed.
        tool=(cq.Workplane('XZ',origin=(LABEL_X,-p.depth/2+.4,LABEL_Z))
              .text(PART_ID,3.,.45,font='DejaVu Sans',
                    kind='bold',combine=False).val())
        bb=tool.BoundingBox()
        self.assertGreater(bb.xmin,-p.width/2+2)
        self.assertLess(bb.xmax,-2)
        self.assertGreater(tool.Volume(),1.)
        self.assertGreater(intersection(bare,tool),.5)
        self.assertLess(intersection(shape,tool),.10)
        self.assertGreater(bare.Volume()-shape.Volume(),.5)

    def test_port_drop(self):
        self.assertAlmostEqual(ports()[0].floor_xyz_mm[2]-ports()[1].floor_xyz_mm[2],DROP)
