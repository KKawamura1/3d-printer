import unittest
import cadquery as cq
from experiments.stud_inner_wall.design import plan
from experiments.full_height_fit.design import coupon


class StudTrialTests(unittest.TestCase):
    def test_plan_and_stage_gate(self):
        rows=plan()
        self.assertEqual([r['stud_hole_diameter_mm'] for r in rows],[6.50,6.45,6.40,6.35])
        self.assertEqual({r['stud_diameter_mm'] for r in rows},{9.40})
        with self.assertRaises(ValueError):plan('diameters')
        with self.assertRaises(ValueError):plan('holes',6.4)
        for hole in (float('nan'),6.3,6.6):
            with self.assertRaises(ValueError):plan('diameters',hole)
        rows=plan('diameters',6.40)
        for d in (9.36,9.40,9.44):
            self.assertEqual(sum(r['stud_diameter_mm']==d for r in rows),2)
        self.assertEqual({r['stud_hole_diameter_mm'] for r in rows},{6.40})

    def test_combined_replicates_and_bed_clearance(self):
        rows=plan('combined',6.40)
        self.assertEqual(len(rows),14)
        self.assertEqual(len({r['id'] for r in rows}),14)
        from collections import Counter,defaultdict
        counts=Counter((r['stud_diameter_mm'],r['stud_hole_diameter_mm']) for r in rows)
        self.assertEqual(counts[(9.40,6.40)],4)
        self.assertEqual(sorted(counts.values()),[2,2,2,2,2,4])
        positions=defaultdict(list)
        for r in rows:
            x,y=r['bed_center_xy_mm']
            self.assertTrue(20.9 < x < 159.1 and 20.9 < y < 159.1)
            positions[(r['stage'],r['stud_diameter_mm'],r['stud_hole_diameter_mm'])].append((x,y))
        for pair in positions.values():
            self.assertEqual(len(pair),2)
            self.assertEqual([sum(v) for v in zip(*pair)],[180,180])
        for i,a in enumerate(rows):
            for b in rows[i+1:]:
                self.assertGreaterEqual(max(abs(x-y) for x,y in zip(a['bed_center_xy_mm'],b['bed_center_xy_mm'])),42)

    def test_only_studs_change_and_holes_remain_open(self):
        rows=plan()+plan('diameters',6.40)
        _,baseline=coupon(rows[0])
        below=cq.Workplane('XY').box(40,40,19.2,centered=(True,True,False)).val()
        baseline=baseline.intersect(below)
        for r in rows:
            with self.subTest(id=r['id'],stage=r['stage']):
                p,s=coupon(r)
                # Engraved IDs differ above contact zone, so compare the complete
                # underside through z=5, including entry chamfer and tube.
                band=cq.Workplane('XY').box(40,40,5,centered=(True,True,False)).val()
                a=baseline.intersect(band);b=s.intersect(band)
                self.assertLess(a.cut(b).Volume()+b.cut(a).Volume(),1e-7)
                self.assertEqual((p.wall,2*p.tube_radius,2*p.tube_inner_radius,p.height),(3.2,13.1,9.4,19.2))
                # Actual mid-height BRep cross sections of all four studs must
                # contain precisely the intended inner and outer circles.
                for x,y in p.studs():
                    window=cq.Workplane('XY',origin=(x,y,21)).box(12,12,.01,centered=(True,True,False)).val()
                    ring=s.intersect(window)
                    expected=3.141592653589793*(p.stud_radius**2-p.stud_inner_radius**2)*.01
                    self.assertAlmostEqual(ring.Volume(),expected,places=6)
                    hole=cq.Solid.makeCylinder(p.stud_inner_radius-.001,4.5,cq.Vector(x,y,19.2))
                    self.assertLess(s.intersect(hole).Volume(),1e-7)


if __name__=='__main__':unittest.main()
