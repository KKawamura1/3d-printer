import unittest
from parts.steep_gentle_tunnel_right.design import build_part, verify, ports, DROP, height, slope, FLOOR, RAMP_START, RAMP_END, RAMP_DROP
class Geometry(unittest.TestCase):
    def test_continuous_clearance_and_structure(self):
        shape,p=build_part()
        checks,_=verify(shape,p)
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
