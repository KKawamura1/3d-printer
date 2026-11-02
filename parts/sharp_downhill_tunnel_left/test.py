import cadquery as cq
from brickcad.verify import intersection, VOLUME_TOL
from parts.sharp_downhill_tunnel_left.design import path, xy, height, LENGTH, MIRROR
import unittest
from parts.sharp_downhill_tunnel_left.design import build_part, verify, ports, DROP
class Geometry(unittest.TestCase):
    def test_circular_inlet_and_outlet(self):
        # T01/D01 mouths on main use a true circle at both exterior faces.
        from brickcad.standards import BALL_TRACK
        from parts.sharp_downhill_tunnel_left.design import wire
        import math
        expected=math.pi*BALL_TRACK.radius**2
        for s in (-.3,0.,.5,LENGTH-.5,LENGTH,LENGTH+.3):
            with self.subTest(station=s):
                section=cq.Face.makeFromWires(wire(s,'passage'))
                self.assertTrue(section.isValid())
                self.assertAlmostEqual(section.Area(),expected,delta=.10)

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
        if MIRROR:
            mask=mask.mirror('XZ')
        # These are pre-E31 supports: clipped receiver rings must not disappear.
        for x, y in p.tubes():
            ring = (cq.Workplane('XY', origin=(x, y, .8))
                    .circle(p.tube_radius).circle(p.tube_inner_radius)
                    .extrude(.5).val())
            clipped = ring.intersect(mask)
            if clipped.Volume() > 1. and clipped.Volume() < ring.Volume() - 1.:
                self.assertGreater(intersection(shape, clipped),
                                   .85 * clipped.Volume(), (x, y))

    def test_side_engraving_uses_project_standard(self):
        # Match the central marking helper, not locally invented font sizes.
        import inspect
        from brickcad.marking import engrave
        from parts.sharp_downhill_tunnel_left.design import PART_ID, LABEL_X, LABEL_Z
        from pathlib import Path
        import json

        params=inspect.signature(engrave).parameters
        self.assertEqual(params['size'].default,3.)
        self.assertEqual(params['depth'].default,.4)
        size=params['size'].default
        depth=params['depth'].default
        spec=json.loads((Path(__file__).parent/'cad-build.json').read_text())
        self.assertEqual(PART_ID,spec['version'])
        self.assertGreater(LABEL_Z-size/2,6.35)
        shape,p=build_part()
        # Reconstruct the standard cutter to confirm readable exterior
        # placement and a genuine recess, not just successful CAD validity.
        tool=(cq.Workplane('XZ',origin=(LABEL_X,-p.depth/2+depth,LABEL_Z))
              .text(PART_ID,size,depth+.05,
                    font='DejaVu Sans',kind='bold',combine=False).val())
        bb=tool.BoundingBox()
        self.assertGreater(bb.xmin,-p.width/2+2)
        self.assertLess(bb.xmax,-2)
        self.assertLessEqual(bb.ymin,-p.depth/2)
        self.assertGreater(bb.ymax,-p.depth/2)
        self.assertGreater(tool.Volume(),1.)
        self.assertLess(intersection(shape,tool),.10)


    def test_left_geometry_is_mirrored_right_before_engraving(self):
        from parts.sharp_downhill_tunnel_right.design import build_part as shared_build
        from parts.sharp_downhill_tunnel_left.design import SOURCE_VERSION
        from parts.sharp_downhill_tunnel_right.design import PART_ID as RIGHT_VERSION
        self.assertEqual(SOURCE_VERSION,RIGHT_VERSION)
        right,_=shared_build(label=None)
        left,_=build_part(label=None)
        expected=right.mirror('XZ')
        self.assertTrue(left.isValid())
        self.assertAlmostEqual(left.Volume(),expected.Volume(),delta=.01)
        self.assertLess(left.cut(expected).Volume()+expected.cut(left).Volume(),.05)

    def test_port_drop(self):
        self.assertAlmostEqual(ports()[0].floor_xyz_mm[2]-ports()[1].floor_xyz_mm[2],DROP)
