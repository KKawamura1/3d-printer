import json
from pathlib import Path
import struct
import tempfile
import unittest
from dataclasses import replace
import cadquery as cq
from brickcad.model import Brick, build
from brickcad.verify import geometry_report, intersection, place, mesh_check, VOLUME_TOL, exact_bounds


class HarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p=Brick()
        cls.nominal=build(cls.p)

    def test_reference_dimensions_and_features(self):
        # Explicit target values: independent of model's derived properties.
        s=self.nominal
        for a,b in zip(exact_bounds(s),(31.8,15.8,11.4)):
            self.assertAlmostEqual(a,b,places=6)
        self.assertTrue(geometry_report(self.p,s)['passed'])
        self.assertTrue(s.isInside(cq.Vector(-12,-4,10.5)))
        self.assertFalse(s.isInside(cq.Vector(-12,-4,0.5)))
        self.assertTrue(s.isInside(cq.Vector(3,0,1)))
        self.assertFalse(s.isInside(cq.Vector(0,0,1)))

    def test_other_rectangles_and_changed_dimensions(self):
        for p in (Brick(nx=2,ny=2),Brick(nx=3,ny=2),Brick(nx=3,ny=3),
                  Brick(clearance=.12),Brick(height=10,roof=1.4,stud_height=1.7)):
            with self.subTest(p=p):self.assertTrue(geometry_report(p,build(p))['passed'])

    def test_aligned_and_rotated_mating(self):
        s=self.nominal
        for xyz,angle in [((0,0,9.6),0),((8,0,9.6),0),((0,0,9.6),90),((0,0,10.2),0)]:
            self.assertLess(intersection(s,place(s,xyz,angle)),VOLUME_TOL)

    def test_negative_controls_and_tolerance_direction(self):
        s=self.nominal
        self.assertGreater(intersection(s,place(s,(4,0,9.6))),1)
        self.assertGreater(intersection(s,place(s,(0,0,9.3))),1)
        tight=build(Brick(clearance=-.04))
        loose=build(Brick(clearance=.08))
        self.assertGreater(intersection(s,place(tight)),VOLUME_TOL)
        self.assertGreater(intersection(tight,place(s)),VOLUME_TOL)
        self.assertLess(intersection(s,place(loose)),VOLUME_TOL)
        self.assertLess(intersection(loose,place(s)),VOLUME_TOL)

    def test_geometry_gate_rejects_capped_bottom(self):
        cap=cq.Workplane('XY').box(31.8,15.8,.4,centered=(True,True,False)).val()
        broken=self.nominal.fuse(cap)
        self.assertFalse(geometry_report(self.p,broken)['passed'])

    def test_actual_export_and_corrupt_mesh_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            stl=Path(tmp)/'brick.stl'
            cq.exporters.export(self.nominal,str(stl),tolerance=.01,angularTolerance=.1)
            m=mesh_check(stl)
            self.assertTrue(m['passed'],m)
            self.assertTrue(geometry_report(self.p,self.nominal)['passed'])
            self.assertAlmostEqual(m['signed_volume_mm3'],self.nominal.Volume(),delta=.5)
            data=bytearray(stl.read_bytes())
            # Remove a triangle while preserving syntactically valid STL.
            count=struct.unpack_from('<I',data,80)[0]
            struct.pack_into('<I',data,80,count-1)
            stl.write_bytes(data[:-50])
            self.assertFalse(mesh_check(stl)['passed'])

    def test_invalid_parameters(self):
        for kw in ({'nx':1},{'nx':2.5},{'clearance':.5},{'roof':9},
                   {'wall':.2},{'tube_inner_radius':3.2},{'pitch':float('nan')},
                   {'body_gap':-1},{'stud_height':-1}):
            with self.subTest(kw=kw),self.assertRaises(ValueError):Brick(**kw)


if __name__=='__main__':unittest.main()
