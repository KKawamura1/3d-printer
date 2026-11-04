"""Compare the protected R16 running geometry to immutable PR #36 CAD.

The reference files are read from a pinned Git SHA, not from a moving branch.
A temporary git worktree isolates the original parts code. The tests fail
if the history is not present; reference comparison is never silently skipped.
"""
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import unittest

from brickcad.course_curve_generator import load_spec
from brickcad.course_sharp_curve import build_course,checks

ROOT=Path(__file__).resolve().parents[1]
PIN="fc70fdd3bf34a6b675595d54c721cec4544e1e76"


class R16ParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import cadquery as cq
        cls.cq=cq
        cls.tmp=tempfile.TemporaryDirectory(prefix="curve-pr36-ref-")
        cls.ref=Path(cls.tmp.name)/"reference"
        try:
            subprocess.run(["git","cat-file","-e",PIN+"^{commit}"],
                           cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
            subprocess.run(["git","worktree","add","--detach","--quiet",
                            str(cls.ref),PIN],cwd=ROOT,check=True)
        except Exception:
            cls.tmp.cleanup()
            raise RuntimeError(
                "Pinned PR #36 CAD sources unavailable: full history is required")

    @classmethod
    def tearDownClass(cls):
        subprocess.run(["git","worktree","remove","--force",str(cls.ref)],
                       cwd=ROOT,check=False,stdout=subprocess.DEVNULL)
        cls.tmp.cleanup()

    def _old_shape(self,kind):
        step=Path(self.tmp.name)/(kind+".step")
        script=(
            "import cadquery as cq\n"
            "from parts.sharp_curve.design import build_curve\n"
            "from parts.sharp_curve_tunnel.design import build_tunnel\n"
            "import sys\n"
            "shape = (build_curve()[0] if sys.argv[1]=='open' "
            "else build_tunnel()[0])\n"
            "cq.exporters.export(shape,sys.argv[2])\n"
        )
        env=os.environ.copy()
        env["PYTHONPATH"]=str(self.ref)
        subprocess.run([sys.executable,"-c",script,kind,str(step)],
                       cwd=self.ref,env=env,check=True,
                       stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=180)
        return self.cq.importers.importStep(str(step)).val()

    def test_original_pr36_running_geometry_without_old_slots_or_marking(self):
        for kind,label in (("open","C01-V5"),("tunnel","C02-V5")):
            with self.subTest(kind=kind):
                config=load_spec(ROOT/"experiments"/("course_curve_"+kind)/"course.json")
                shape,p,path=build_course(config,reference_label=label,mark=False)
                checks_dict,nominal,oversize,bounds=checks(shape,p,path,kind)
                self.assertTrue(all(checks_dict.values()),checks_dict)
                reference=self._old_shape(kind)
                self.assertTrue(reference.isValid() and shape.isValid())
                self.assertEqual(len(reference.Solids()),1)
                # PR #60 intentionally changes E31 slots beneath Z5.05 and
                # north-wall engraving near Y+15.9. Protect the actual
                # running channel and roof, not the old rejected details.
                protected=self.cq.Workplane("XY").box(
                    40.,31.,90.,centered=(True,True,False)
                ).translate((0.,-.5,5.4)).val()
                previous=reference.intersect(protected)
                current=shape.intersect(protected)
                a=previous.cut(current).Volume()
                b=current.cut(previous).Volume()
                self.assertLess(a,.05,("lost protected material",kind,a))
                self.assertLess(b,.05,("added protected material",kind,b))


if __name__=="__main__":
    unittest.main()
