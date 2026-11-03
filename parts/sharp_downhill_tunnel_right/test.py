import cadquery as cq
from brickcad.verify import intersection, VOLUME_TOL
from parts.sharp_downhill_tunnel_right.design import path, xy, height, LENGTH, MIRROR
import unittest
import json
from pathlib import Path
from parts.sharp_downhill_tunnel_right.design import build_part, verify, ports, DROP
class Geometry(unittest.TestCase):
    def test_circular_inlet_and_outlet(self):
        # T01/D01 mouths on main use a true circle at both exterior faces.
        from brickcad.standards import BALL_TRACK
        from parts.sharp_downhill_tunnel_right.design import wire
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
        # Issue #60 / PR58 B: the four E31 slots must end below the
        # underside ceiling, not cut into the bridge supporting the floor.
        from parts.tunnel.e31_fit import SLOT_END_Z, SLOT_END_RADIUS
        from parts.sharp_downhill_tunnel_right.design import loft, DEPTH
        self.assertAlmostEqual(SLOT_END_Z, 3.50)
        self.assertGreaterEqual(DEPTH - (SLOT_END_Z + SLOT_END_RADIUS), .60 - 1e-6)
        mask = loft('mask').intersect(
            cq.Workplane('XY').box(p.width, p.depth, 100,
                                   centered=(True, True, False)).val())
        full_tubes = [
            (tx, ty) for tx, ty in p.tubes()
            if all(mask.isInside(cq.Vector(
                tx + 6.85 * __import__('math').cos(i * __import__('math').pi / 4),
                ty + 6.85 * __import__('math').sin(i * __import__('math').pi / 4), 2))
                for i in range(8))
        ]
        self.assertTrue(full_tubes, "no complete E31 tubes found on right part")
        for tx, ty in full_tubes:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                with self.subTest(tube=(tx, ty), direction=(dx, dy)):
                    # Radius 6.5 is within the nominal 6.6 mm tube wall.
                    point = lambda z: cq.Vector(tx + 6.5*dx, ty + 6.5*dy, z)
                    self.assertFalse(shape.isInside(point(3.5)),
                                     "E31 slit not open on complete tube")
                    self.assertTrue(shape.isInside(point(4.3)),
                                    "E31 slit cuts too far into floor ceiling")
        for fraction in (.15,.35,.65,.85):
            s=LENGTH*fraction
            x,y,_,_=xy(s)
            self.assertTrue(shape.isInside(
                cq.Vector(x,-y if MIRROR else y,height(s)-.15)),
                "missing rolling floor at s="+str(s))

    def test_version_matches_geometry_label(self):
        spec = json.loads((Path(__file__).parent / 'cad-build.json').read_text())
        from parts.sharp_downhill_tunnel_right.design import PART_ID
        self.assertEqual(spec['version'], PART_ID)

    def test_versioned_footprint_clipped_receiver_supports(self):
        from parts.sharp_downhill_tunnel_right.design import PART_ID, loft
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

    def test_side_engraving_uses_project_standard(self):
        # Match the central marking helper, not locally invented font sizes.
        import inspect
        from brickcad.marking import engrave
        from parts.sharp_downhill_tunnel_right.design import PART_ID, LABEL_X, LABEL_Z
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


    def test_reflection_of_route_and_connection_ports(self):
        from parts.sharp_downhill_tunnel_right.design import path, ports
        right, left = path(), path(mirror=True)
        self.assertEqual(len(right),len(left))
        for a,b in zip(right,left):
            self.assertAlmostEqual(a.x,b.x)
            self.assertAlmostEqual(a.y,-b.y)
            self.assertAlmostEqual(a.z,b.z)
        right_ports,left_ports=ports(),ports(mirror=True)
        for a,b in zip(right_ports,left_ports):
            self.assertAlmostEqual(a.floor_xyz_mm[0],b.floor_xyz_mm[0])
            self.assertAlmostEqual(a.floor_xyz_mm[1],-b.floor_xyz_mm[1])
            self.assertAlmostEqual(a.floor_xyz_mm[2],b.floor_xyz_mm[2])

    def test_port_drop(self):
        self.assertAlmostEqual(ports()[0].floor_xyz_mm[2]-ports()[1].floor_xyz_mm[2],DROP)
