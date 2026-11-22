"""Issue #92: open R48 and roofed R48 must use the same path contract.

Keep the proven open-rail float evaluation exactly unchanged (especially
GC01/SC03/SC05). This test is deliberately CAD-light and does not recreate
the entire historical course catalogue.
"""
import math
import unittest

from brickcad.course_loft_family import LoftSettings, height, xy
from brickcad.course_r48_unified import centreline, floor_z, grade, port_contract
from brickcad.r48_path import (
    ARC_LENGTH_MM, RADIUS_MM, floor_at_s, grade_at_t, xy_at_s,
    horizontal_port_contract, validate_profile,
)
from brickcad.standards import BALL_TRACK, DUPLO


class SharedOpenRoofedR48Tests(unittest.TestCase):
    def test_open_legacy_coordinates_exact(self):
        for drop in (0., DUPLO.height):
            c = LoftSettings("gentle", drop, False, False, "west", 12.)
            for t in (0., .015, .1, .25, .5, .75, .97, 1.):
                s = ARC_LENGTH_MM * t
                a = -math.pi / 2 + s / 48.
                original = (-32 + 48 * math.cos(a),
                            32 + 48 * math.sin(a),
                            -math.sin(a), math.cos(a))
                self.assertEqual(xy(s, c), original)
                self.assertEqual(xy_at_s(s), original)
                # Preserve the original open-course arithmetic exactly.
                old_u = max(0., min(1., s / c.length))
                old_height = BALL_TRACK.floor + drop * (
                    1 - 3 * old_u * old_u + 2 * old_u * old_u * old_u)
                self.assertAlmostEqual(height(s, c), old_height, places=10)
                self.assertAlmostEqual(floor_at_s(s, drop), old_height, places=10)

    def test_roofed_matches_open_slope_and_xy(self):
        for drop in (0., DUPLO.height):
            c = LoftSettings("gentle", drop, False, False, "west", 12.)
            for t in (0., .1, .3, .5, .8, 1.):
                s = ARC_LENGTH_MM * t
                a = centreline(t, drop)
                x, y, _, _ = xy(s, c)
                self.assertAlmostEqual(a.x, x, places=9)
                self.assertAlmostEqual(a.y, y, places=9)
                self.assertAlmostEqual(a.z, height(s, c), places=9)
                self.assertAlmostEqual(floor_z(t, drop), height(s, c), places=9)
                self.assertAlmostEqual(grade(t, drop), grade_at_t(t, drop), places=12)

    def test_ports_identical(self):
        for drop in (0., DUPLO.height):
            self.assertEqual(port_contract(drop), horizontal_port_contract(drop))
        self.assertEqual(RADIUS_MM, 48.)
        self.assertEqual(validate_profile(DUPLO.height), DUPLO.height)
        with self.assertRaises(ValueError):
            validate_profile(9.6)


if __name__ == "__main__":
    unittest.main()
