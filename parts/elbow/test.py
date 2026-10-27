import math
import tempfile
import unittest
from pathlib import Path
import cadquery as cq
from parts.elbow.design import build_elbow, verify, ball_sweep, ports, export
from brickcad.ports import mate, straight_ports
from brickcad.verify import intersection, VOLUME_TOL
from parts.tunnel.design import Tunnel


class ElbowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shape, cls.p = build_elbow()

    def test_full_curved_course_and_negative_controls(self):
        report = verify(self.shape)
        self.assertTrue(all(report['checks'].values()), report)
        self.assertEqual(len(report['joints']), 2)
        self.assertTrue(all(abs(j['mouth_gap_mm']-.2)<1e-9 for j in report['joints']))

    def test_sweep_covers_between_samples_and_both_caps(self):
        # Tiny obstacle off any round-number sampling angle must still be caught.
        a = math.radians(-37.123)
        z = Tunnel().floor+24.26/2+.05
        obstacle = cq.Workplane('XY', origin=(-32+48*math.cos(a),32+48*math.sin(a),z)).sphere(.2).val()
        self.assertGreater(intersection(ball_sweep(), obstacle), VOLUME_TOL)
        for x,y in [(-32,-16),(16,32)]:
            cap = cq.Workplane('XY',origin=(x,y,z)).sphere(1).val()
            self.assertGreater(intersection(ball_sweep(),cap), VOLUME_TOL)

    def test_grid_mating_and_hollow_upper_connection(self):
        self.assertEqual((self.p.nx,self.p.ny), (4,4))
        self.assertEqual(len(self.p.studs()),16)
        self.assertEqual(len(self.p.tubes()),9)
        west,north = ports()
        left,right = straight_ports(4,Tunnel().floor,Tunnel().radius)
        self.assertTrue(mate(north,left.placed((16,64,0),90))['compatible'])
        self.assertFalse(mate(west,right.placed((-64,-16,1)))['compatible'])
        from brickcad.model import nominal_brick, build
        upper = build(nominal_brick('duplo',4,4)).translate((0,0,38.4))
        # Existing trial profile deliberately has 0.036 mm radial tube interference;
        # upper nominal receiver on smaller trial studs remains geometrically clear.
        self.assertLess(intersection(self.shape,upper), VOLUME_TOL)
        self.assertTrue(all(not self.shape.isInside(cq.Vector(x,y,41)) for x,y in self.p.studs()))

    def test_invalid_ball(self):
        for diameter in [0,-1,math.inf,math.nan,96]:
            with self.assertRaises(ValueError): ball_sweep(diameter)

    def test_exported_files_are_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = export(Path(tmp))
            self.assertTrue(report['passed'])
            self.assertFalse(report['physical_fit_validated'])
            self.assertFalse(report['physical_rolling_validated'])
            self.assertTrue(report['mesh']['passed'])
            self.assertTrue(report['checks']['step_roundtrip'])
