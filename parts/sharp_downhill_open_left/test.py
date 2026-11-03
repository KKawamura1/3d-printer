import cadquery as cq
from brickcad.verify import intersection, VOLUME_TOL
from parts.sharp_downhill_open_left.design import path, xy, height, LENGTH, MIRROR
import unittest
from parts.sharp_downhill_open_left.design import build_part, verify, ports, DROP, PART_ID, LABEL_X, LABEL_Z
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
        from parts.sharp_downhill_open_left.design import PART_ID, loft
        from brickcad.verify import intersection
        import math
        shape,p=build_part()
        footprint=loft('mask').intersect(
            cq.Workplane('XY').box(p.width,p.depth,100,
                      centered=(True,True,False)).val())
        # The footprint must be mirrored as well as the finished solid.
        footprint=footprint.mirror('XZ')
        for x,y in p.tubes():
            ring=(cq.Workplane('XY',origin=(x,y,.8))
                  .circle(p.tube_radius).circle(p.tube_inner_radius)
                  .extrude(.5).val())
            trimmed=ring.intersect(footprint)
            if 1.<trimmed.Volume()<ring.Volume()-1.:
                self.assertGreater(intersection(shape,trimmed),
                                   .85*trimmed.Volume(),(x,y))
        # The shared engraving helper defines the only accepted size/depth.
        # Rebuild its tool to ensure the full 3mm label is actually cut on
        # the exterior straight side, not refilled by later geometry unions.
        import inspect
        from pathlib import Path
        import json
        from brickcad.marking import engrave
        params=inspect.signature(engrave).parameters
        self.assertEqual(params['size'].default,3.)
        self.assertEqual(params['depth'].default,.4)
        spec=json.loads((Path(__file__).parent/'cad-build.json').read_text())
        self.assertEqual(PART_ID,spec['version'])
        size=params['size'].default
        depth=params['depth'].default
        self.assertGreater(LABEL_Z-size/2,6.35)
        tool=(cq.Workplane('XZ',origin=(LABEL_X,-p.depth/2+depth,LABEL_Z))
              .text(PART_ID,size,depth+.05,font='DejaVu Sans',
                    kind='bold',combine=False).val())
        bb=tool.BoundingBox()
        self.assertGreater(bb.xmin,-p.width/2+2)
        self.assertLess(bb.xmax,-2)
        self.assertGreater(tool.Volume(),1.)
        self.assertLess(intersection(shape,tool),.10)

    def test_source_version_and_unmarked_mirror(self):
        from parts.sharp_downhill_open_right.design import build_part as right_build, PART_ID as right_id
        from parts.sharp_downhill_open_left.design import SOURCE_VERSION
        self.assertEqual(SOURCE_VERSION,right_id)
        right,_=right_build(label=None)
        left,_=build_part(label=None)
        expected=right.mirror('XZ')
        self.assertTrue(left.isValid())
        self.assertAlmostEqual(left.Volume(),expected.Volume(),delta=.01)
        self.assertLess(left.cut(expected).Volume()+expected.cut(left).Volume(),.05)

    def test_reflection_route_and_ports(self):
        from parts.sharp_downhill_open_right.design import path as right_path,ports as right_ports
        for a,b in zip(right_path(),path()):
            self.assertAlmostEqual(a.x,b.x)
            self.assertAlmostEqual(a.y,-b.y)
            self.assertAlmostEqual(a.z,b.z)
        for a,b in zip(right_ports(),ports()):
            self.assertAlmostEqual(a.floor_xyz_mm[0],b.floor_xyz_mm[0])
            self.assertAlmostEqual(a.floor_xyz_mm[1],-b.floor_xyz_mm[1])
            self.assertAlmostEqual(a.floor_xyz_mm[2],b.floor_xyz_mm[2])

    def test_port_drop(self):
        self.assertAlmostEqual(ports()[0].floor_xyz_mm[2]-ports()[1].floor_xyz_mm[2],DROP)
