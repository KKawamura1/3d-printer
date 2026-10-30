import unittest
from parts.play_set.design import plan
from brickcad.model import brick_from_fit


class PlaySetPlanTests(unittest.TestCase):
    def test_only_requested_parts_with_bed_clearance(self):
        records=plan()
        self.assertEqual(len({r['id'] for r in records}),8)
        for kind,size in (('sloped_curve',63.8),('elbow',63.8),('tunnel',31.8)):
            group=[r for r in records if r['kind']==kind]
            self.assertEqual(len(group),4 if kind=="tunnel" else 2)
            for r in group:
                self.assertEqual(r['rotation_deg'],0)
                for coord in r['centre_xy_mm']:
                    self.assertLessEqual(abs(coord)+size/2+2,90)
        boxes=[(r,31.8 if r['kind']=='tunnel' else 63.8) for r in records]
        for i,(a,sa) in enumerate(boxes):
            for b,sb in boxes[i+1:]:
                # 4 mm clearance permits two independent 2 mm brims.
                self.assertTrue(any(abs(x-y)>=(sa+sb)/2+4 for x,y in zip(a['centre_xy_mm'],b['centre_xy_mm'])))

    def test_versioned_fit_preserves_e27_dimensions_and_old_trials(self):
        p=brick_from_fit('duplo-e27-play-v1',nx=2,ny=2)
        self.assertEqual((p.width,p.depth,p.stud_radius*2,p.stud_inner_radius*2,p.tube_radius*2),(31.8,31.8,9.4,6.4,13.5))
        self.assertEqual(p.cavity_xy,(25.4,25.4))
        self.assertEqual(brick_from_fit('duplo-rail-trial-v1').tube_radius,6.65)
        self.assertEqual(brick_from_fit('duplo-rail-trial-v1').stud_radius,4.6)
