import unittest
import cadquery as cq
from brickcad.receiver_trial import build, plan


class ReceiverTrialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shapes=[build(r)[1] for r in plan()]

    def test_only_intended_contact_features_change(self):
        a,b,c=self.shapes
        # Export-independent probes away from the 0.3 mm entry chamfer.
        self.assertFalse(a.isInside(cq.Vector(0,12.68,1)))
        self.assertTrue(b.isInside(cq.Vector(0,12.68,1)))
        self.assertFalse(c.isInside(cq.Vector(0,12.68,1)))
        self.assertFalse(a.isInside(cq.Vector(6.65,0,1)))
        self.assertFalse(b.isInside(cq.Vector(6.65,0,1)))
        self.assertTrue(c.isInside(cq.Vector(6.65,0,1)))
        # Compare full solids in the top band, including holes, rims and roof.
        top=cq.Workplane('XY',origin=(0,0,17.61)).box(40,40,7,centered=(True,True,False)).val()
        at=a.intersect(top)
        for s in (b,c):
            st=s.intersect(top)
            self.assertLess(at.cut(st).Volume()+st.cut(at).Volume(),1e-6)
        # At +/-X all cavities must still begin at 12.70 mm.
        for s in self.shapes:
            for sign in (-1,1):
                self.assertFalse(s.isInside(cq.Vector(sign*12.69,0,1)))
                self.assertTrue(s.isInside(cq.Vector(sign*12.71,0,1)))
            self.assertFalse(s.isInside(cq.Vector(0,0,1)))
            self.assertTrue(s.isValid())
            self.assertEqual(len(s.Solids()),1)


if __name__=='__main__':unittest.main()
