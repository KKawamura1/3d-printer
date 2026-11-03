"""Cross-PR exact (unengraved) CAD parity against current pinned sources.

References are explicit Git SHAs of the latest reviewed independent PR heads
on 2026-11-03. Both shapes have NO marking before comparison. Equality is
checked in both directions, rather than comparing STL bounds or visual plots.

Run after updating reference PR SHAs if their heads move.
"""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import cadquery as cq

from brickcad.course_drop_generator import load_spec as load_drop
from brickcad.course_curve_generator import load_spec as load_curve
from brickcad.course_generator_v2 import load_spec as load_downhill
from brickcad.course_steep_drop import build_course as build_drop
from brickcad.course_sharp_curve import build_course as build_curve
from brickcad.course_downhill import build_course as build_downhill
from parts.downhill_tunnel.design import Downhill, build_downhill as legacy_downhill

ROOT = Path(__file__).resolve().parents[1]
PINNED_REFERENCES = {
    "S01": "105405cf037bba555724f77c5bb1c714dbf7b547",  # PR38 S01-V8
    "S02": "3b65a1c6dcf04169bac4f1bc23d24720f49405fd",  # PR41 S02-V15
    "C01": "262b41fe6ff4adc47f71ee4d36dc7d1f6337d302",  # PR36 C01-V6, C02-V8
    "C02": "262b41fe6ff4adc47f71ee4d36dc7d1f6337d302",
}
# An OCC/STEP-based symmetric difference below 0.001 cubic mm is effectively
# geometric identity at the sub-voxel scale, not just coincident dimensions.
MAX_DELTA_MM3 = .001

REFERENCE_SCRIPT = r'''
import cadquery as cq
import sys
kind, path = sys.argv[1:]
if kind == "S01":
    from parts.steep_drop_hole.design import build_steep_drop
    model = build_steep_drop(label=None)[0]
elif kind == "S02":
    from parts.steep_sharp_curve_tunnel.design import build_tunnel
    model = build_tunnel(label=None)[0]
elif kind == "C01":
    from parts.sharp_curve import design as d
    d._engrave_north = lambda shape, *args: shape
    model = d.build_curve()[0]
elif kind == "C02":
    from parts.sharp_curve_tunnel import design as d
    d._engrave_north = lambda shape, *args: shape
    model = d.build_tunnel()[0]
else:
    raise ValueError(kind)
assert model.isValid() and len(model.Solids()) == 1, kind
cq.exporters.export(model, path)
'''


class CrossPrUnmarkedParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="current-course-parity-")
        cls.root = Path(cls.temp.name)
        cls.references = {}
        try:
            for index, (kind, sha) in enumerate(PINNED_REFERENCES.items()):
                if sha in cls.references:
                    continue
                directory = cls.root / ("ref-" + str(index))
                subprocess.run(
                    ["git", "cat-file", "-e", sha + "^{commit}"],
                    cwd=ROOT, check=True, stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                )
                subprocess.run(
                    ["git", "worktree", "add", "--detach", "--quiet",
                     str(directory), sha],
                    cwd=ROOT, check=True, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                cls.references[sha] = directory
        except Exception:
            cls._cleanup()
            raise

    @classmethod
    def _cleanup(cls):
        for path in getattr(cls, "references", {}).values():
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(path)],
                cwd=ROOT, check=False, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        cls.temp.cleanup()

    @classmethod
    def tearDownClass(cls):
        cls._cleanup()

    def compare(self, label, original, generated, *, tolerance=MAX_DELTA_MM3):
        self.assertTrue(original.isValid(), (label, "reference invalid"))
        self.assertTrue(generated.isValid(), (label, "generated invalid"))
        self.assertEqual(len(original.Solids()), 1, label)
        self.assertEqual(len(generated.Solids()), 1, label)
        only_reference = original.cut(generated).Volume()
        only_generated = generated.cut(original).Volume()
        print(
            f"UNMARKED BREP PARITY {label}: "
            f"ref={original.Volume():.9f} generated={generated.Volume():.9f} "
            f"missing={only_reference:.9f} extra={only_generated:.9f} mm3",
            flush=True,
        )
        self.assertLessEqual(only_reference, tolerance, (label, "missing", only_reference))
        self.assertLessEqual(only_generated, tolerance, (label, "extra", only_generated))

    def original(self, kind):
        sha = PINNED_REFERENCES[kind]
        root = self.references[sha]
        target = self.root / (kind + ".step")
        env = os.environ.copy()
        env["PYTHONPATH"] = str(root)
        proc = subprocess.run(
            [sys.executable, "-c", REFERENCE_SCRIPT, kind, str(target)],
            cwd=root, env=env, capture_output=True, text=True, timeout=180,
        )
        self.assertEqual(proc.returncode, 0, (kind, proc.stdout, proc.stderr))
        shape = cq.importers.importStep(str(target)).val()
        self.assertTrue(shape.isValid(), kind)
        return shape

    def test_x01_vs_pr38_s01(self):
        spec = load_drop(ROOT/"experiments/course_drop_east/course.json")
        shape, _, _ = build_drop(spec, mark=False)
        self.compare("X01 vs PR38 S01-V8", self.original("S01"), shape)

    def test_x02_vs_pr41_s02(self):
        spec = load_drop(ROOT/"experiments/course_drop_south/course.json")
        shape, _, _ = build_drop(spec, mark=False)
        self.compare("X02 vs PR41 S02-V15", self.original("S02"), shape)

    def test_y01_vs_pr36_c01(self):
        spec = load_curve(ROOT/"experiments/course_curve_open/course.json")
        shape, _, _ = build_curve(spec, mark=False)
        self.compare("Y01 vs PR36 C01-V6", self.original("C01"), shape)

    def test_y02_vs_pr36_c02(self):
        spec = load_curve(ROOT/"experiments/course_curve_tunnel/course.json")
        shape, _, _ = build_curve(spec, mark=False)
        self.compare("Y02 vs PR36 C02-V8", self.original("C02"), shape)

    def test_w01_with_d01_windows_vs_main_d01(self):
        spec = copy.deepcopy(load_downhill(
            ROOT/"experiments/course_windows_w01/course.json"))
        spec["enclosure"]["windows"] = [
            {"side": "south", "x_mm": x, "width_mm": 8} for x in (-16, 0, 16)
        ]
        # Test geometry before either text cutter; the window count differs
        # intentionally for the real W01 recipe, and is equalized only here.
        with patch("brickcad.course_downhill.engrave",
                   side_effect=lambda shape, label, **kwargs: shape):
            candidate, _, _ = build_downhill(spec)
        with patch("parts.downhill_tunnel.design.engrave",
                   side_effect=lambda shape, label, **kwargs: shape):
            baseline, _ = legacy_downhill(Downhill())
        self.compare("W01 generator with D01 windows vs main D01-V3",
                     baseline, candidate)

    def test_replay_uses_exact_latest_source(self):
        from brickcad.course_generator import SUPPORTED
        from parts.tunnel import design_e31
        from parts.downhill_tunnel import design
        self.assertEqual(SUPPORTED["straight_tunnel"]["legacy"]["part_id"],
                         design_e31.PART_ID)
        self.assertEqual(SUPPORTED["windowed_downhill_tunnel"]["legacy"]["part_id"],
                         design.PART_ID)


if __name__ == "__main__":
    unittest.main()
