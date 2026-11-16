"""Fast checks for the proved D01-V3-style pointed window series."""
import unittest

from brickcad.course_lancet_windows import (
    LANCET_DUAL_IDS, LANCET_SINGLE_IDS, SURFACES, LEVELS,
    _choices, _family, _pentagon, _model,
)
from brickcad.course_double_windows import DOUBLE_VERSIONS
from scripts.course_followup_print import EXPECTED_MISSING


class TallPointedWindowTests(unittest.TestCase):
    def test_all_unprinted_closed_courses_now_have_new_pointed_ids(self):
        missing_closed = {"E01-V3","SC02-V12","SD04-V10","S01-V8"}
        self.assertEqual(missing_closed, set(LANCET_DUAL_IDS) & EXPECTED_MISSING)
        self.assertEqual(len(LANCET_DUAL_IDS), 7)
        self.assertEqual(set(LANCET_SINGLE_IDS), {"SD04-V10"})
        self.assertFalse(
            set(LANCET_DUAL_IDS.values()) & set(DOUBLE_VERSIONS.values()))
        self.assertFalse(
            set(LANCET_SINGLE_IDS.values()) & set(LANCET_DUAL_IDS.values()))

    def test_pointed_apertures_tall_narrow_and_preserve_floor_roof(self):
        for ident in LANCET_DUAL_IDS:
            with self.subTest(ident=ident):
                model = _model(ident)
                self.assertEqual(model["course"]["enclosure"], "tunnel")
                family = _family(ident)
                z0,z1,z2 = LEVELS[family]
                self.assertLess(z0,z1)
                self.assertLess(z1,z2)
                self.assertGreater(z1-z0, 7.)
                self.assertGreater(z2-z0, 11.)
                for surface in SURFACES[ident]:
                    side,_,start,depth = surface
                    cutter = _pentagon(
                        side, _choices(family,3)[0][0],
                        start,depth,family)
                    bb=cutter.BoundingBox()
                    self.assertAlmostEqual(bb.zmin,z0,delta=.01)
                    self.assertAlmostEqual(bb.zmax,z2,delta=.01)
                    slender=bb.xlen if side.startswith("y") else bb.ylen
                    self.assertLessEqual(slender, 6.01)
                    self.assertGreater(z2-z0,slender)

    def test_three_first_then_two_then_one_on_large_courses(self):
        for family in ("E01","SD"):
            choices = _choices(family,3)
            self.assertEqual(tuple(map(len,choices)),(3,2,1))
            self.assertGreater(min(choices[0][i+1]-choices[0][i]
                                   for i in range(2)), 6.)
        # The shorter usable SC02 wall supports two narrow windows,
        # not three separated by adequate strengthening ribs.
        self.assertEqual(tuple(map(len,_choices("SC02",3))),(2,1))
        self.assertEqual(_choices("SC02",3)[0],(-20.,-13.))
        self.assertEqual(tuple(map(len,_choices("S01",3))),(1,))

    def test_bad_source_is_rejected(self):
        for ident in ("GC01-V5","R01-V1","BAD-V2"):
            with self.assertRaisesRegex(ValueError,"Unknown"):
                _model(ident)


if __name__=="__main__":
    unittest.main()
