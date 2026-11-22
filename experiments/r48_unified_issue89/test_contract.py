"""CAD-light regression tests for the Issue #89 common R48 generator."""
import math

import cadquery as cq
import unittest

from brickcad.course_contract import course_fit
from brickcad.course_r48_unified import (
    INTERIOR_RADIAL_RELIEF, HALF, MIN_RADIAL_SIDEWALL_MM, R48PairConfig, _progress,
    _proven_foundation,
    _window_cutters, centreline, complete_studs, complete_tubes,
    floor_z, grade, port_contract,
)
from brickcad.standards import BALL_TRACK, DUPLO


class SharedR48ContractTests(unittest.TestCase):
    def test_actual_sc02_foundation_is_the_shared_underbody(self):
        """Use a proven curved receiver instead of adding invented bed ribs."""
        from brickcad.course_r48_sloped_tunnel import FULL_TUBES
        base, fit = _proven_foundation()
        self.assertTrue(base.isValid())
        self.assertEqual(len(base.Solids()), 1)
        self.assertEqual(set(FULL_TUBES), set(complete_tubes(fit)))
        self.assertEqual(fit.tube_radius, 6.6)
        self.assertEqual(len(complete_studs(fit)), 7)
        # The original receiver is open under the track at Z=2 and still
        # forms structural supports on the perimeter. A broad solid slab
        # across the stud locations would fail this test.
        for x, y in fit.studs():
            self.assertFalse(base.isInside(cq.Vector(x, y, 2.), .001))

    def test_two_configurations_share_layout(self):
        fit = course_fit(nx=4, ny=4, height_units=2)
        self.assertEqual(len(complete_studs(fit)), 7)
        self.assertEqual(set(complete_tubes(fit)),
                         {(-16., -16.), (0., 0.), (16., 16.)})
        for drop in (0., DUPLO.height):
            self.assertEqual(len(list(_window_cutters(
                R48PairConfig("X89-contract", drop)))), 5)

    def test_drop_is_the_only_difference_in_track(self):
        for t in (0, .02, .25, .5, .75, .98, 1):
            flat = centreline(t, 0)
            slope = centreline(t, DUPLO.height)
            self.assertAlmostEqual(flat.x, slope.x, places=9)
            self.assertAlmostEqual(flat.y, slope.y, places=9)
            self.assertAlmostEqual(flat.z, BALL_TRACK.floor, places=9)
            self.assertAlmostEqual(slope.z - flat.z,
                                   DUPLO.height * (1 - 3*t*t + 2*t*t*t),
                                   places=9)
        self.assertAlmostEqual(floor_z(0, DUPLO.height),
                               BALL_TRACK.floor + DUPLO.height)
        self.assertAlmostEqual(floor_z(1, DUPLO.height), BALL_TRACK.floor)
        self.assertAlmostEqual(grade(0, DUPLO.height), 0)
        self.assertAlmostEqual(grade(1, DUPLO.height), 0)

    def test_ports_are_unchanged_even_with_interior_relief(self):
        flat = port_contract(0)
        sloped = port_contract(DUPLO.height)
        self.assertEqual(flat["opening_diameter_mm"], BALL_TRACK.opening)
        self.assertEqual(flat["west"][0][:2], (-32., -16.))
        self.assertEqual(flat["north"][0][:2], (16., 32.))
        self.assertEqual(flat["west"][1], (-1., 0., 0.))
        self.assertEqual(flat["north"][1], (0., 1., 0.))
        self.assertEqual(flat["north"], sloped["north"])
        self.assertAlmostEqual(sloped["west"][0][2] - flat["west"][0][2],
                               DUPLO.height, places=9)
        self.assertEqual(_progress(0), 0)
        self.assertEqual(_progress(1), 0)
        self.assertAlmostEqual(INTERIOR_RADIAL_RELIEF, 1.0)
        self.assertGreater(_progress(.5), .9)
        self.assertGreaterEqual(HALF - BALL_TRACK.radius - INTERIOR_RADIAL_RELIEF,
                                MIN_RADIAL_SIDEWALL_MM)

    def test_full_part_relief_ab_has_fixed_ports_and_safe_sidewalls(self):
        for drop in (0., DUPLO.height):
            for relief in (.4, 1.0):
                cfg = R48PairConfig("X89-test-relief", drop,
                                   relief_mm=relief)
                self.assertEqual(cfg.relief_mm, relief)
                self.assertGreaterEqual(
                    HALF - BALL_TRACK.radius - cfg.relief_mm,
                    MIN_RADIAL_SIDEWALL_MM)
                self.assertEqual(port_contract(cfg.drop_mm)
                                 ["opening_diameter_mm"],
                                 BALL_TRACK.opening)
        for invalid in (-.1, float("nan"), float("inf"), 2.0):
            with self.assertRaises(ValueError):
                R48PairConfig("bad-relief", 0., relief_mm=invalid)

    def test_roofs_allow_full_duplo_placement(self):
        self.assertAlmostEqual(R48PairConfig("X89-E01-U1", 0).roof_z, 38.4)
        self.assertAlmostEqual(
            R48PairConfig("X89-SC02-U1", DUPLO.height).roof_z, 57.6
        )

    def test_unsupported_geometry_rejected(self):
        for invalid in (1., 9.6, -19.2):
            with self.assertRaises(ValueError):
                R48PairConfig("bad", invalid)
        with self.assertRaises(ValueError):
            R48PairConfig("bad", 0., direction="diagonal")


if __name__ == "__main__":
    unittest.main()
