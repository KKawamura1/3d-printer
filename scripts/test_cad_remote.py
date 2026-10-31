"""Fast selector and STL framing tests: no CAD generation required."""
import json
from pathlib import Path
import struct
from tempfile import TemporaryDirectory
import unittest

from scripts.cad_remote import load_jobs, select_jobs, ensure_stl


def spec(job_id, watch=None, deps=None, cascade=False):
    return dict(id=job_id, watch=watch or [f"parts/{job_id}/*.json"],
                depends_on=deps or [],
                rebuild_on_dependency_change=cascade,
                command=["python", "-m", "anything"],
                outputs=[{"path":f"build/{job_id}/brick.stl",
                          "name":f"{job_id}.stl",
                          "report":f"build/{job_id}/report.json"}])


class TargetedCadTests(unittest.TestCase):
    def test_one_changed_configuration_does_not_build_unrelated_models(self):
        jobs = {"tunnel": spec("tunnel"), "elbow": spec("elbow"),
                "plate": spec("plate", deps=["tunnel", "elbow"])}
        self.assertEqual(select_jobs(jobs, {"parts/tunnel/profile.json"}), ["tunnel"])
        self.assertEqual(select_jobs(jobs, {"cad/jobs/elbow.json"}), ["elbow"])
        self.assertEqual(select_jobs(jobs, {"docs/readme.md"}), [])

    def test_dependent_assembly_can_opt_in_to_rebuilding(self):
        jobs = {"tunnel": spec("tunnel"), "plate": spec("plate", deps=["tunnel"], cascade=True)}
        self.assertEqual(select_jobs(jobs, {"parts/tunnel/profile.json"}), ["plate", "tunnel"])

    def test_shared_inputs_select_only_direct_consumers(self):
        jobs = {"a": spec("a", ["brickcad/model.py"]),
                "b": spec("b", ["brickcad/render.py"])}
        self.assertEqual(select_jobs(jobs, {"brickcad/model.py"}), ["a"])
        self.assertEqual(select_jobs(jobs, {"parts/a/README.md"}), [])

    def test_config_is_validated_and_cycles_rejected(self):
        with TemporaryDirectory() as temp:
            d = Path(temp)
            (d / "a.json").write_text(json.dumps(spec("a", deps=["b"])))
            (d / "b.json").write_text(json.dumps(spec("b", deps=["a"])))
            with self.assertRaisesRegex(ValueError, "cycle"):
                load_jobs(d)
            (d / "b.json").write_text(json.dumps(spec("b")))
            self.assertEqual(sorted(load_jobs(d)), ["a", "b"])

    def test_binary_stl_framing(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / "valid.stl"
            path.write_bytes(b" " * 80 + struct.pack("<I", 1) + b"\x00" * 50)
            self.assertEqual(ensure_stl(path)["triangles"], 1)
            path.write_bytes(b" " * 80 + struct.pack("<I", 2) + b"\x00" * 50)
            with self.assertRaises(ValueError):
                ensure_stl(path)


if __name__ == "__main__":
    unittest.main()
