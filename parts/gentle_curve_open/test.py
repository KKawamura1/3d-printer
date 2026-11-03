import cadquery as cq
from brickcad.verify import intersection, VOLUME_TOL
from parts.gentle_curve_open.design import path, xy, height, LENGTH, MIRROR
import unittest
from parts.gentle_curve_open.design import build_part, verify, ports, DROP, PART_ID, LABEL_Z
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
        from parts.gentle_curve_open.design import PART_ID, loft
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
        # Issue #60: use the global 3mm bold / 0.4mm deep standard and
        # ensure the entire marking is carved on the exposed west inlet face.
        import inspect
        import json
        from pathlib import Path
        from brickcad.marking import engrave_west
        params=inspect.signature(engrave_west).parameters
        self.assertEqual(params['size'].default,3.)
        self.assertEqual(params['depth'].default,.4)
        build_spec=json.loads((Path(__file__).parent/'cad-build.json').read_text())
        self.assertEqual(PART_ID,build_spec['version'])
        size=params['size'].default
        depth=params['depth'].default
        _,y,_,_=xy(0)
        if MIRROR: y=-y
        plane=cq.Plane(origin=(-p.width/2+depth,y,LABEL_Z),
                       xDir=(0,-1,0),normal=(-1,0,0))
        cutter=(cq.Workplane(plane).text(
            PART_ID,size,depth+.05,font='DejaVu Sans',
            kind='bold',combine=False).val())
        bounds=cutter.BoundingBox()
        self.assertLess(bounds.zmax,height(0))  # No cut into the running channel.
        self.assertGreater(bounds.ymin,-p.depth/2)
        self.assertLess(bounds.ymax,p.depth/2)
        unmarked,_=build_part(label=None)
        expected=intersection(unmarked,cutter)
        self.assertGreater(expected,.80*cutter.Volume(),
                           'Standard-size text does not fit the outer inlet wall')
        self.assertLess(intersection(shape,cutter),.10,
                        'Final geometry refilled or omitted the recessed label')
        self.assertGreater(unmarked.Volume()-shape.Volume(),expected-.10)

    def test_port_drop(self):
        self.assertAlmostEqual(ports()[0].floor_xyz_mm[2]-ports()[1].floor_xyz_mm[2],DROP)
