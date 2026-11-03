"""Compare independent Issue37 CAD against exact pinned original BReps."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import cadquery as cq
from scripts.course_catalog import load_registry
from brickcad.course_contract import kernel_for

ROOT=Path(__file__).resolve().parents[1]
REFERENCE=r"""
import importlib,sys
from unittest.mock import patch
ident,mark,module,path=sys.argv[1:]
m=importlib.import_module(module)
if ident=="T01-V6":
    assert module=="parts.tunnel.design_e31", (ident,module)
    assert m.PART_ID==ident, (ident,m.PART_ID)
marked=mark=="marked"
if ident.startswith("SC02"):
    shared=importlib.import_module("parts.sloped_curve_tunnel.design")
    shape=shared.build_part(side="left" if ident.startswith("SC02L") else "right",marked=marked)[0]
elif ident.startswith("E01"):
    side="left" if ident.startswith("E01L") else "right"
    shared=importlib.import_module("parts.gentle_curve_tunnel.design")
    shape=shared.build_part(side)[0] if marked else shared.build_unmarked()[0]
    if not marked and side=="left":shape=shape.mirror("XZ")
elif ident=="T01-V6":
    if marked:shape=m.build_tunnel()[0]
    else:
        with patch.object(m,"engrave",lambda shape,*a,**kw:shape):
            shape=m.build_tunnel()[0]
elif ident=="D01-V3":
    if marked:shape=m.build_downhill()[0]
    else:
        with patch.object(m,"engrave",lambda shape,*a,**kw:shape):
            shape=m.build_downhill()[0]
elif ident=="R01-V1":
    if marked: shape=m.build_rail()[0]
    else:
        with patch.object(m,"engrave",lambda shape,*a,**kw:shape):
            shape=m.build_rail()[0]
elif ident.startswith(("C01","C02")):
    f=m.build_curve if ident.startswith("C01") else m.build_tunnel
    if marked:shape=f()[0]
    else:
        with patch.object(m,"_engrave_north",lambda shape,*a,**kw:shape):
            shape=f()[0]
elif ident.startswith("S01"):
    shape=m.build_steep_drop(label=ident if marked else None)[0]
elif ident.startswith("S02"):
    shape=m.build_tunnel(label=ident if marked else None)[0]
elif ident.startswith("S03"):
    shape=(m.build_tunnel(label=ident)[0] if marked else
           m.right.build_tunnel(label=None)[0].mirror("XZ"))
else:
    shape=m.build_part(label=ident if marked else None)[0]
assert shape.isValid() and len(shape.Solids())==1
shape.exportBrep(path)
"""

def build(model,marked):
    s=model["source"]
    family=kernel_for(model["course"])
    recipe=s["recipe"]
    name=model["id"]
    if family=="loft":
        from brickcad.course_loft_family import build_course
        return build_course(recipe,label=name if marked else None)[0]
    if family in ("sharp_r16","drop"):
        from brickcad.course_configured_special import build_course
        return build_course(name,family,recipe,mark=marked)[0]
    if family=="horizontal_r48_tunnel":
        from brickcad.course_r48_tunnel import build_course
        return build_course(name,recipe,marked=marked)[0]
    if family=="sloped_r48_tunnel":
        from brickcad.course_r48_sloped_tunnel import build_course
        return build_course(name,recipe,marked=marked)[0]
    if family=="straight_tunnel":
        from brickcad.course_straight_tunnel import build_course
        return build_course(name,recipe,marked=marked)[0]
    if family=="straight_rail":
        from brickcad.course_straight_rail import build_course
        return build_course(name,recipe,marked=marked)[0]
    if family=="downhill_windowed":
        from brickcad.course_downhill import build_course
        ident,version=name.split("-")
        windows=[{"side":"south","x_mm":x,"width_mm":recipe["window_width_mm"]}
                 for x in recipe["windows"]]
        spec={"id":ident,"version":version,"enclosure":{"windows":windows}}
        if marked:return build_course(spec)[0]
        with patch("brickcad.course_downhill.engrave",
                   side_effect=lambda shape,*a,**kw:shape):
            return build_course(spec)[0]
    raise ValueError("Missing configured CAD family")

class PinnedCADParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix="course-parity-")
        cls.root=Path(cls.temp.name)
        registry=load_registry()["models"]
        selected=os.environ.get("COURSE_PARITY_MODELS","GC01-V5")
        ids={m["id"] for m in registry} if selected=="all" else set(selected.split(","))
        cls.models=[m for m in registry if m["id"] in ids]
        if len(cls.models)!=len(ids):raise ValueError("Unknown model(s) in parity selector")
        cls.worktrees={}
        try:
            for index,sha in enumerate(sorted({m["source"]["reference"]["sha"]
                                               for m in cls.models})):
                dest=cls.root/("ref-"+str(index))
                subprocess.run(["git","fetch","origin",sha],cwd=ROOT,check=True,
                               stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
                subprocess.run(["git","worktree","add","--detach",str(dest),sha],
                               cwd=ROOT,check=True,stdout=subprocess.DEVNULL,
                               stderr=subprocess.PIPE)
                cls.worktrees[sha]=dest
        except Exception:
            cls.close()
            raise
    @classmethod
    def close(cls):
        for d in getattr(cls,"worktrees",{}).values():
            subprocess.run(["git","worktree","remove","--force",str(d)],cwd=ROOT,
                           check=False,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        cls.temp.cleanup()
    @classmethod
    def tearDownClass(cls):
        cls.close()

    def reference(self,m,marked):
        src=m["source"]["reference"]
        wd=self.worktrees[src["sha"]]
        path=self.root/(m["id"]+("-marked" if marked else "-bare")+".brep")
        module=src.get("module") or src["target"].replace("/",".")+".design"
        args=[sys.executable,"-c",REFERENCE,m["id"],
              "marked" if marked else "unmarked",module,str(path)]
        proc=subprocess.run(args,cwd=wd,env={**os.environ,"PYTHONPATH":str(wd)},
                            capture_output=True,text=True,timeout=900)
        self.assertEqual(proc.returncode,0,(m["id"],proc.stdout,proc.stderr))
        return cq.Shape.importBrep(str(path))

    def test_unmarked_and_engraved_parity(self):
        for m in self.models:
            for marked in (False,True):
                with self.subTest(id=m["id"],marked=marked):
                    reference=self.reference(m,marked)
                    result=build(m,marked)
                    only_old=reference.cut(result).Volume()
                    only_new=result.cut(reference).Volume()
                    delta=abs(reference.Volume()-result.Volume())
                    print("CAD PARITY",m["id"],marked,only_old,only_new,delta,flush=True)
                    self.assertLessEqual(only_old,.001)
                    self.assertLessEqual(only_new,.001)
                    self.assertLessEqual(delta,.001)

if __name__=="__main__":
    unittest.main()
