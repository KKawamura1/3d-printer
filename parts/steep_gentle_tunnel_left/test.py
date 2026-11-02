"""SG01 geometry regressions: ball path, landing support and roof.

CAD geometry does not establish spontaneous rolling or print tolerance.
"""
import cadquery as cq
from brickcad.verify import intersection, VOLUME_TOL
from parts.steep_gentle_tunnel_left.design import xy, height, MIRROR, path
import unittest
from parts.steep_gentle_tunnel_left.design import build_part, verify, ports, DROP, slope, FLOOR, RAMP_START, RAMP_END, RAMP_DROP
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
    def test_ramp_continuity_and_version(self):
        import json
        from pathlib import Path
        from parts.steep_gentle_tunnel_left.design import PART_ID
        spec=json.loads((Path(__file__).parent/'cad-build.json').read_text())
        self.assertEqual(spec['version'],PART_ID)
        self.assertAlmostEqual(height(RAMP_START),FLOOR+RAMP_DROP)
        self.assertAlmostEqual(height(RAMP_END),FLOOR)
        for s in (RAMP_START,16.,28.,RAMP_END):
            self.assertAlmostEqual(height(s-1e-6),height(s+1e-6),delta=1e-5)
            self.assertAlmostEqual(slope(s-1e-6),slope(s+1e-6),delta=1e-5)

    def test_partial_lower_tubes_remain(self):
        from parts.steep_gentle_tunnel_left.design import loft
        shape,p=build_part()
        clip=cq.Workplane('XY').box(p.width,p.depth,100,
                        centered=(True,True,False)).val()
        mask=loft('mask').intersect(clip)
        count=0
        for x,y in p.tubes():
            ring=(cq.Workplane('XY',origin=(x,y,.8))
                  .circle(p.tube_radius).circle(p.tube_inner_radius)
                  .extrude(.5).val())
            partial=ring.intersect(mask)
            if 1.<partial.Volume()<ring.Volume()-1.:
                count+=1
                self.assertGreater(intersection(shape,partial),
                                   .85*partial.Volume(),(x,y))
        self.assertGreater(count,0)

    def test_recessed_version_id_survives_all_unions(self):
        from parts.steep_gentle_tunnel_left.design import PART_ID, xy, MIRROR
        from brickcad.verify import intersection
        shape,p=build_part()
        _,y,_,_=xy(0)
        if MIRROR:
            y=-y
        plane=cq.Plane(origin=(-p.width/2+0.45,y,12),
                       xDir=(0,-1,0),normal=(-1,0,0))
        cutter=(cq.Workplane(plane).text(
            PART_ID,2,0.5,font='DejaVu Sans',
            kind='bold',combine=False).val())
        self.assertLess(intersection(shape,cutter),.10)

    def test_port_drop(self):
        self.assertAlmostEqual(ports()[0].floor_xyz_mm[2]-ports()[1].floor_xyz_mm[2],DROP)
