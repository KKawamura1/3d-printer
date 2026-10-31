"""Fast, CAD-independent checks for the remote STL artifact packager."""
import json
from pathlib import Path
import struct
from tempfile import TemporaryDirectory
import unittest

from scripts.package_print_stl import (
    EXPECTED_SPECIMENS, SOURCE_STLS, load_passed_report, package, verify_binary_stl,
)


class PackagePrintStlTest(unittest.TestCase):
    @staticmethod
    def make_stl(path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b" " * 80 + struct.pack("<I", 1) + b"\x00" * 50)
        (path.parent / "report.json").write_text(
            json.dumps({"passed": True, "mesh": {"passed": True}}), encoding="utf-8"
        )

    def test_packages_both_plate_and_uniques(self):
        with TemporaryDirectory() as temp:
            base = Path(temp)
            parts = base / "parts"
            comparison = base / "comparisons"
            out = base / "release"
            for name, (folder, relative) in SOURCE_STLS.items():
                root = comparison if folder in {"S02-V2", "T02-V1", "T03-V1", "T04-V1"} else parts
                self.make_stl(root / relative)
            batch = parts / "batch"
            self.make_stl(batch / "play-set-8.stl")
            (batch / "report.json").write_text(
                json.dumps({"passed": True, "mesh": {"passed": True},
                            "specimens": [{"id": label} for label in EXPECTED_SPECIMENS]}),
                encoding="utf-8"
            )
            package(parts, comparison, out)
            self.assertEqual(len(list(out.glob("*.stl"))), 8)
            manifest = json.loads((out / "manifest.json").read_text())
            self.assertEqual(manifest["specimens"], EXPECTED_SPECIMENS)
            self.assertEqual(len(manifest["files"]), 8)
            self.assertEqual(len((out / "SHA256SUMS.txt").read_text().splitlines()), 8)
            with self.assertRaises(ValueError):
                package(parts, comparison, out)

    def test_rejects_corrupted_or_unverified_source(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / "brick.stl"
            path.write_bytes(b" " * 80 + struct.pack("<I", 42))
            with self.assertRaises(ValueError):
                verify_binary_stl(path)
            report = path.with_name("report.json")
            report.write_text(json.dumps({"passed": False, "mesh": {"passed": True}}))
            with self.assertRaises(ValueError):
                load_passed_report(report)


if __name__ == "__main__":
    unittest.main()
