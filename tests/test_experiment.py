import unittest
from collections import Counter
import cadquery as cq
from brickcad.experiment import plan, coupon
from brickcad.rail import rounded_brick

class ExperimentTests(unittest.TestCase):
    def test_design_and_layout(self):
        rows=plan()
        self.assertEqual(len({r['id'] for r in rows}),16)
        self.assertEqual(Counter(r['rotation_deg'] for r in rows if r['variant']=='C'),{0:4,90:4})
        for r in rows:
            self.assertEqual(r['variant']=='C',(r['row_from_back']+r['column_from_left'])%2==0)
            self.assertTrue(all(20.9 <= x <= 159.1 for x in r['bed_center_xy_mm']))
        base=next(r for r in rows if r['variant']=='C')
        keys=('stud_diameter_mm','tube_diameter_mm','wall_mm')
        for r in rows:
            self.assertEqual(sum(r[k]!=base[k] for k in keys),0 if r['variant']=='C' else 1)

    def test_marks_leave_fit_surfaces_unchanged(self):
        for r in (plan()[0],plan()[-1],plan()[1],plan()[3],plan()[4]):
            with self.subTest(id=r['id']):
                p,s=coupon(r);raw=rounded_brick(p)
                self.assertGreater(raw.Volume()-s.Volume(),1)
                self.assertTrue(s.isValid())
                self.assertEqual(len(s.Solids()),1)
                for z in (0,18.2):
                    slab=cq.Workplane('XY').box(40,40,6,centered=(True,True,False)).translate((0,0,z)).val()
                    self.assertLess(raw.cut(s).intersect(slab).Volume(),1e-6)
                # Direction arrows are on the two specified exterior faces.
                self.assertFalse(s.isInside(cq.Vector(0,-15.8,16)))
                self.assertFalse(s.isInside(cq.Vector(15.8,0,16)))

if __name__=='__main__':unittest.main()
