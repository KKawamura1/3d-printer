"""Regression guards for PR56's shared, BRep-neutral course helpers."""
import struct
import tempfile
import unittest
from pathlib import Path

import cadquery as cq

from brickcad.course_artifacts import export_geometry, normalize_binary_stl
from brickcad.course_geometry import (
    smoothstep_fall, smoothstep_rise_expanded, smoothstep_rise_factored,
)


class SharedCoursePrimitivesTests(unittest.TestCase):
    def test_interpolation_keeps_original_arithmetic(self):
        for t in (-.02, 0., .001, .125, .25, .5, .875, .995, 1., 1.02):
            with self.subTest(t=t):
                self.assertEqual(smoothstep_fall(t), 1-3*t*t+2*t*t*t)
                self.assertEqual(smoothstep_rise_expanded(t), 3*t*t-2*t*t*t)
                self.assertEqual(smoothstep_rise_factored(t), t*t*(3-2*t))

    def test_stl_filters_float32_collapsed_facets_without_reordering(self):
        def facet(a,b,c):
            return struct.pack("<12fH", 0.,0.,1., *a, *b, *c, 0)
        good1=facet((0.,0.,0.),(1.,0.,0.),(0.,1.,0.))
        collapsed=facet((0.,0.,0.),(1.,0.,0.),(1.,0.,0.))
        good2=facet((0.,0.,0.),(0.,0.,1.),(1.,1.,1.))
        header=b"c"*80
        with tempfile.TemporaryDirectory() as tmp:
            stl=Path(tmp)/"sample.stl"
            stl.write_bytes(header+struct.pack("<I",3)+good1+collapsed+good2)
            self.assertEqual(normalize_binary_stl(stl),2)
            self.assertEqual(stl.read_bytes(),header+struct.pack("<I",2)+good1+good2)
            # Repeated normalization must be byte-for-byte stable.
            self.assertEqual(normalize_binary_stl(stl),2)
            self.assertEqual(stl.read_bytes(),header+struct.pack("<I",2)+good1+good2)

    def test_invalid_stl_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            stl=Path(tmp)/"invalid.stl"
            for payload in (b"", b"x"*80+struct.pack("<I",0)):
                with self.subTest(payload_length=len(payload)):
                    stl.write_bytes(payload)
                    with self.assertRaises(ValueError):
                        normalize_binary_stl(stl)

    def test_common_export_writes_stl_step_and_checks_mesh(self):
        shape=cq.Workplane("XY").box(10,10,10).val()
        with tempfile.TemporaryDirectory() as tmp:
            stl,mesh=export_geometry(shape,tmp,tolerance=.02,angular_tolerance=.15)
            self.assertTrue(stl.is_file())
            self.assertTrue((Path(tmp)/"brick.step").is_file())
            self.assertGreater(stl.stat().st_size,84)
            self.assertTrue(mesh["passed"],mesh)
            self.assertTrue(shape.isValid())


if __name__=="__main__":
    unittest.main()
