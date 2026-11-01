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
    def test_port_drop(self):
        self.assertAlmostEqual(ports()[0].floor_xyz_mm[2]-ports()[1].floor_xyz_mm[2],DROP)

    def test_ramp_is_continuous_and_keeps_drop(self):
        self.assertAlmostEqual(height(RAMP_START), FLOOR+RAMP_DROP)
        self.assertAlmostEqual(height(RAMP_END), FLOOR)
        for s in (RAMP_START, 16., 28., RAMP_END):
            self.assertAlmostEqual(height(s-1e-6), height(s+1e-6), delta=1e-5)
            self.assertAlmostEqual(slope(s-1e-6), slope(s+1e-6), delta=1e-5)
        self.assertLess(slope(20.), -.6)
