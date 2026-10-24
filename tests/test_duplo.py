import tempfile
import unittest
from pathlib import Path
from dataclasses import replace
import cadquery as cq
from brickcad.model import nominal_brick, from_profile, build
from brickcad.verify import exact_bounds, geometry_report, fit_report, mesh_check, intersection, place, VOLUME_TOL


class DuploTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p=nominal_brick('duplo')
        cls.shape=build(cls.p)

    def test_dimensions_and_hollow_studs(self):
        p,s=self.p,self.shape
        for a,b in zip(exact_bounds(s),(63.8,31.8,23.7)):
            self.assertAlmostEqual(a,b,places=6)
        self.assertEqual(len(p.studs()),8)
        self.assertEqual(len(p.tubes()),3)
        self.assertTrue(geometry_report(p,s)['passed'])
        # Independently anchored first stud at (-24,-8), outer r=4.7, inner r=3.25.
        self.assertFalse(s.isInside(cq.Vector(-24,-8,21)))
        self.assertTrue(s.isInside(cq.Vector(-20,-8,21)))
        self.assertTrue(s.isInside(cq.Vector(-24,-8,18.5)))
        self.assertFalse(s.isInside(cq.Vector(0,0,1)))
        self.assertTrue(s.isInside(cq.Vector(6,0,1)))

    def test_family_reference_and_full_insertion_path(self):
        r=fit_report(self.p,self.shape)
        self.assertEqual(r['reference_parameters']['pitch'],16)
        self.assertEqual(r['reference_parameters']['stud_inner_radius'],3.25)
        self.assertEqual(r['reference_parameters']['height'],19.2)
        self.assertGreater(max(x['lift_mm'] for x in r['insertion']),4.5)
        self.assertFalse(any(x['collision'] for x in r['insertion']))
        self.assertTrue(r['negative_controls_passed'])
        self.assertFalse(any(x['collision'] for x in r['poses'] if 'negative_control' not in x['name']))

    def test_tight_candidate_detected_both_directions(self):
        tight=build(replace(self.p,clearance=-.04))
        self.assertGreater(intersection(self.shape,place(tight,(0,0,19.2))),VOLUME_TOL)
        self.assertGreater(intersection(tight,place(self.shape,(0,0,19.2))),VOLUME_TOL)

    def test_small_brick_and_file_export(self):
        p=from_profile({'family':'duplo','nx':2,'ny':2})
        s=build(p)
        self.assertAlmostEqual(exact_bounds(s)[0],31.8,places=6)
        self.assertTrue(geometry_report(p,s)['passed'])
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'duplo.stl'
            cq.exporters.export(s,str(path),tolerance=.01,angularTolerance=.1)
            self.assertTrue(mesh_check(path)['passed'])

    def test_hollow_stud_capping_is_rejected(self):
        p=self.p
        cap=(cq.Workplane('XY',origin=(-24,-8,p.height+2)).circle(3.25).extrude(.5)).val()
        self.assertFalse(geometry_report(p,self.shape.fuse(cap))['passed'])

    def test_lego_preserved_and_invalid_family(self):
        self.assertEqual(from_profile({}).pitch,8)
        self.assertEqual(from_profile({'family':'duplo'}).pitch,16)
        with self.assertRaises(ValueError):from_profile({'family':'unknown'})
        with self.assertRaises(ValueError):replace(self.p,stud_inner_radius=4.5)
