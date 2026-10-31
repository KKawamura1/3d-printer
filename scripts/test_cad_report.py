"""Lightweight contract tests; fake mesh validation avoids CAD setup."""
import json
from pathlib import Path
import tempfile
import unittest

from cad_report import verified_report


class ReportContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.stl = Path(self.tmp.name) / "brick.stl"
        self.stl.write_bytes(b"fake mesh, supplied to checker")

    def write_report(self, report):
        (self.stl.parent / "report.json").write_text(json.dumps(report))

    def test_missing_mesh_is_computed_and_persisted(self):
        self.write_report({"part_id": "D01-V1", "passed": True, "checks": {"ports": True}})
        called = []
        def checker(path):
            called.append(path)
            return {"passed": True, "triangles": 8}
        actual = verified_report(self.stl, mesh_validator=checker)
        self.assertEqual(called, [self.stl])
        self.assertTrue(actual["mesh"]["passed"])
        self.assertTrue(json.loads((self.stl.parent / "report.json").read_text())["mesh"]["passed"])
        self.assertEqual(actual["checks"], {"ports": True})

    def test_existing_mesh_does_not_run_checker_or_rewrite(self):
        self.write_report({"passed": True, "mesh": {"passed": True}})
        before = (self.stl.parent / "report.json").read_bytes()
        verified_report(self.stl, mesh_validator=lambda _: self.fail("unexpected check"))
        self.assertEqual((self.stl.parent / "report.json").read_bytes(), before)

    def test_negative_geometry_never_gets_repaired(self):
        self.write_report({"passed": False})
        with self.assertRaisesRegex(ValueError, "geometry verification"):
            verified_report(self.stl, mesh_validator=lambda _: {"passed": True})

    def test_negative_mesh_never_gets_overridden(self):
        self.write_report({"passed": True, "mesh": {"passed": False}})
        with self.assertRaisesRegex(ValueError, "mesh verification"):
            verified_report(self.stl, mesh_validator=lambda _: {"passed": True})

    def test_invalid_or_failed_generated_mesh_rejected(self):
        self.write_report({"passed": True})
        with self.assertRaisesRegex(ValueError, "mesh verification"):
            verified_report(self.stl, mesh_validator=lambda _: {"passed": False})


if __name__ == "__main__":
    unittest.main()
