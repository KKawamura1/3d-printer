import unittest
import cadquery as cq
from parts.steep_gentle_tunnel_right.design import build_part, verify, ports, DROP, height, slope, FLOOR, RAMP_START, RAMP_END, RAMP_DROP
class Geometry(unittest.TestCase):
    def test_continuous_clearance_and_structure(self):
        shape,p=build_part()
        checks,_=verify(shape,p)
        if not checks["continuous_sphere_path_clear"]:
            from parts.steep_gentle_tunnel_right.design import path as centres
            pts=centres()
            sphere=sorted(enumerate(_["sphere_intersections_mm3"]),key=lambda row:row[1],reverse=True)[:8]
            segment=sorted(enumerate(_["segment_intersections_mm3"]),key=lambda row:row[1],reverse=True)[:8]
            print("SG02 collision spheres",[(i,round(v,3),pts[i].toTuple()) for i,v in sphere],flush=True)
            print("SG02 collision segments",[(i,round(v,3),pts[i].toTuple(),pts[i+1].toTuple()) for i,v in segment],flush=True)
            r=12.13
            for i,v in sphere[:4]:
                overlap=shape.intersect(cq.Solid.makeSphere(
                    r,pts[i],angleDegrees1=-90))
                box=overlap.BoundingBox()
                print("SG02 collision bbox",i,round(v,3),
                      (round(box.xmin,2),round(box.xmax,2)),
                      (round(box.ymin,2),round(box.ymax,2)),
                      (round(box.zmin,2),round(box.zmax,2)),flush=True)
        self.assertTrue(all(checks.values()),checks)
    def test_ramp_continuity_and_version(self):
        import json
        from pathlib import Path
        from parts.steep_gentle_tunnel_right.design import PART_ID
        spec=json.loads((Path(__file__).parent/'cad-build.json').read_text())
        self.assertEqual(spec['version'],PART_ID)
        self.assertAlmostEqual(height(RAMP_START),FLOOR+RAMP_DROP)
        self.assertAlmostEqual(height(RAMP_END),FLOOR)
        for s in (RAMP_START,16.,28.,RAMP_END):
            self.assertAlmostEqual(height(s-1e-6),height(s+1e-6),delta=1e-5)
            self.assertAlmostEqual(slope(s-1e-6),slope(s+1e-6),delta=1e-5)

    def test_partial_lower_tubes_remain(self):
        from parts.steep_gentle_tunnel_right.design import loft
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
        from parts.steep_gentle_tunnel_right.design import PART_ID, xy, MIRROR
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

    def test_ramp_is_continuous_and_keeps_drop(self):
        self.assertAlmostEqual(height(RAMP_START), FLOOR+RAMP_DROP)
        self.assertAlmostEqual(height(RAMP_END), FLOOR)
        for s in (RAMP_START, 16., 28., RAMP_END):
            self.assertAlmostEqual(height(s-1e-6), height(s+1e-6), delta=1e-5)
            self.assertAlmostEqual(slope(s-1e-6), slope(s+1e-6), delta=1e-5)
        self.assertLess(slope(20.), -.6)
