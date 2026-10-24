import math
import unittest
from dataclasses import replace
from brickcad.ports import Port, straight_ports, mate
from brickcad.pitagora import assembly, verify, swept_ball


class PortTests(unittest.TestCase):
    def test_grid_join_rotation_and_height(self):
        left, right = straight_ports(2,6.35,12.87)
        self.assertTrue(mate(right,left.placed((32,0,0)))['compatible'])
        self.assertAlmostEqual(mate(right,left.placed((32,0,0)))['mouth_gap_mm'],.2)
        self.assertFalse(mate(right,left.placed((32,0,19.2)))['compatible'])
        self.assertFalse(mate(right,right)['compatible'])
        # Turn a complete connection through 90 degrees; Z datum unchanged.
        self.assertTrue(mate(right.placed(yaw_deg=90),
                             left.placed((32,0,0)).placed(yaw_deg=90))['compatible'])
        self.assertTrue(mate(right,right.placed((32,0,0),180))['compatible'])

    def test_reject_wrong_section_and_invalid_input(self):
        a,b=straight_ports(2,6.35,12.87)
        self.assertFalse(mate(b,replace(a.placed((32,0,0)),section_radius_mm=13.))['compatible'])
        for kwargs in [dict(section_radius_mm=math.nan),dict(outward=(2,0,0)),
                       dict(face_inset_mm=-1),dict(floor_xyz_mm=(0,0,math.inf))]:
            with self.assertRaises(ValueError):
                replace(a,**kwargs)
        for size in [0,-1,math.inf,math.nan]:
            with self.assertRaises(ValueError):swept_ball(size)


class M1AssemblyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.modules,_=assembly()

    def test_full_continuous_path_and_geometry_controls(self):
        report=verify(self.modules)
        self.assertTrue(report['passed'],report)
        self.assertEqual(len(report['joints']),3)
        self.assertTrue(all(j['mouth_gap_mm']==.2 for j in report['joints']))

    def test_metadata_height_error_is_not_accepted(self):
        modules=[dict(m) for m in self.modules]
        modules[1]['ports']=tuple(p.placed((0,0,1)) for p in modules[1]['ports'])
        self.assertFalse(verify(modules)['checks']['ports_match'])

    def test_geometry_error_even_with_unchanged_port_metadata(self):
        modules=[dict(m) for m in self.modules]
        modules[1]['shape']=modules[1]['shape'].translate((0,0,1))
        self.assertFalse(verify(modules)['checks']['continuous_path_clear'])


if __name__=='__main__':unittest.main()
