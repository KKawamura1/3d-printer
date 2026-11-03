"""Reference-oracle parity for the independent loft family.

The production generator NEVER calls old CAD builders. This test is the only
place that imports immutable historical CAD to measure BRep symmetric deltas.
Both completed engraved and unmarked solids must match independently.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import cadquery as cq
from brickcad.course_loft_family import build_course

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "experiments/course_catalog/registry.json"
TOLERANCE_MM3 = .001

REFERENCE_SCRIPT = r"""
import importlib
import sys
model, label, destination = sys.argv[1:]
module = importlib.import_module(model)
shape, params = module.build_part(label=None if label == '<unmarked>' else label)
assert shape.isValid() and len(shape.Solids()) == 1
shape.exportBrep(destination)
"""


class LoftFamilyReferenceParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="loft-parity-")
        cls.worktrees = {}
        cls.models = [m for m in json.loads(REGISTRY.read_text())["models"]
                      if m["source"]["kind"] == "configured"]
        cls.root = Path(cls.temp.name)
        try:
            for index,sha in enumerate(sorted({m["source"]["reference"]["sha"]
                                               for m in cls.models})):
                workspace = cls.root / ("source-" + str(index))
                subprocess.run(["git","fetch","origin",sha],cwd=ROOT,check=True,
                               stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
                subprocess.run(["git","worktree","add","--detach",str(workspace),sha],
                               cwd=ROOT,check=True,stdout=subprocess.DEVNULL,
                               stderr=subprocess.PIPE)
                cls.worktrees[sha]=workspace
        except Exception:
            cls.release()
            raise

    @classmethod
    def release(cls):
        for p in getattr(cls,"worktrees",{}).values():
            subprocess.run(["git","worktree","remove","--force",str(p)],
                           cwd=ROOT,check=False,stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
        cls.temp.cleanup()

    @classmethod
    def tearDownClass(cls):
        cls.release()

    def reference_shape(self, model, marked):
        source = model["source"]["reference"]
        workspace = self.worktrees[source["sha"]]
        module = source["target"].replace("/",".")+".design"
        output = self.root / (model["id"] + ("-marked" if marked else "-raw") + ".brep")
        env = dict(os.environ)
        env["PYTHONPATH"] = str(workspace)
        proc = subprocess.run(
            [sys.executable,"-c",REFERENCE_SCRIPT,module,
             model["id"] if marked else "<unmarked>",str(output)],
            cwd=workspace,env=env,text=True,capture_output=True,timeout=300)
        self.assertEqual(proc.returncode,0,(model["id"],proc.stdout,proc.stderr))
        return cq.Shape.importBrep(str(output))

    def compare(self, model, marked):
        actual,p = build_course(model["source"]["recipe"],
                                label=model["id"] if marked else None)
        baseline = self.reference_shape(model,marked)
        name = model["id"] + ("/marked" if marked else "/unmarked")
        self.assertTrue(actual.isValid(),name)
        self.assertEqual(len(actual.Solids()),1,name)
        delta = abs(baseline.Volume()-actual.Volume())
        removed = baseline.cut(actual).Volume()
        extra = actual.cut(baseline).Volume()
        print(f"LOFT BREP PARITY {name}: missing={removed:.9f} "
              f"extra={extra:.9f} volume_delta={delta:.9f} mm3",flush=True)
        self.assertLessEqual(delta,TOLERANCE_MM3,name)
        self.assertLessEqual(removed,TOLERANCE_MM3,name)
        self.assertLessEqual(extra,TOLERANCE_MM3,name)

    def test_independent_loft_family_exact_geometry(self):
        for model in self.models:
            for marked in (False, True):
                with self.subTest(model=model["id"],marked=marked):
                    self.compare(model,marked)


if __name__=="__main__":
    unittest.main()
