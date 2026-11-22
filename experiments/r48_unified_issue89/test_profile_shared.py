"""Regression oracles for the refactored four-variant R48 profile/API.

Historical wire recipes are copied ONLY into tests to detect accidental
changes to print-tested passage shapes. They are not production generators.
"""
import math
import unittest
from unittest.mock import patch, sentinel

import cadquery as cq

from brickcad.course_section_profiles import passage_section_wire
from brickcad.course_r48_building_blocks import place_r48_wire
from brickcad.course_r48_unified import (
    R48FamilyConfig, R48PairConfig, build_r48_family,
    _passage_wire as new_roofed_wire, _progress, floor_z,
)
from brickcad.course_r48_sloped_tunnel import (
    _passage_wire as proven_roofed_wire,
    _zshift, _blend, CHANNEL_RADIUS, FLOOR, RADIUS,
)
from brickcad.course_loft_family import LoftSettings, wire as old_open_wire
from brickcad.standards import BALL_TRACK, DUPLO


def original_open(w, floor, radius):
    centre = floor + radius
    return (w.moveTo(-radius, centre)
            .threePointArc((0, floor), (radius, centre))
            .lineTo(radius, 95).lineTo(-radius, 95).close().val())


def original_roofed(w, floor, radius, roof, blend, center_x=0.):
    """Independent historical SC02/loft/new-PR91 teardrop equations."""
    centre = floor + radius
    a = radius / math.sqrt(2)
    bridge = centre + math.sqrt(2) * radius - roof

    def mix(circle, pointed):
        return circle * (1 - blend) + pointed * blend

    end = (mix(radius * math.cos(math.radians(75)), bridge),
           mix(centre + radius * math.sin(math.radians(75)), roof))
    mid = (mix(radius * .5, (a + bridge) / 2),
           mix(centre + radius * math.sqrt(3) / 2,
               (centre + a + roof) / 2))
    apex = (0, mix(centre + radius, roof))
    return (w.moveTo(center_x-a, centre+a)
            .threePointArc((center_x, floor), (center_x+a, centre+a))
            .threePointArc((center_x+mid[0], mid[1]),
                           (center_x+end[0], end[1]))
            .threePointArc((center_x+apex[0], apex[1]),
                           (center_x-end[0], end[1]))
            .threePointArc((center_x-mid[0], mid[1]),
                           (center_x-a, centre+a)).close().val())


def check_same_wire(test, actual, expected):
    """Compare actual OCC wires, including shape of curved edges and faces."""
    test.assertTrue(actual.isValid())
    test.assertEqual(len(actual.Edges()), len(expected.Edges()))
    test.assertAlmostEqual(actual.Length(), expected.Length(), places=8)
    test.assertAlmostEqual(cq.Face.makeFromWires(actual).Area(),
                           cq.Face.makeFromWires(expected).Area(), places=8)
    for a, b in zip(actual.Edges(), expected.Edges()):
        test.assertEqual(a.geomType(), b.geomType())
        test.assertAlmostEqual(a.Length(), b.Length(), places=8)
    for a, b in zip(actual.Vertices(), expected.Vertices()):
        v, u = a.Center(), b.Center()
        for k in ("x", "y", "z"):
            test.assertAlmostEqual(getattr(v, k), getattr(u, k), places=8)


class SharedProfileParityTests(unittest.TestCase):
    def test_open_reference_and_legacy_open_curves(self):
        for drop in (0., DUPLO.height):
            config = LoftSettings("gentle", drop, False, False, "west", 12.)
            for fraction in (0., .1, .35, .5, .75, 1.):
                s = config.length * fraction
                floor = BALL_TRACK.floor + drop * (
                    1 - 3*fraction*fraction + 2*fraction*fraction*fraction)
                distance = min(max(0,s), max(0,config.length-s))
                blend = min(1., distance/5.)
                radius = BALL_TRACK.radius + (14.-BALL_TRACK.radius)*blend
                expected = original_open(cq.Workplane(
                    cq.Plane(origin=(-32+48*math.cos(-math.pi/2+s/48),
                                     32+48*math.sin(-math.pi/2+s/48),0),
                             xDir=(-math.cos(-math.pi/2+s/48),
                                   -math.sin(-math.pi/2+s/48),0),
                             normal=(-math.sin(-math.pi/2+s/48),
                                     math.cos(-math.pi/2+s/48),0))),
                    floor, radius)
                check_same_wire(self, old_open_wire(s, "passage", config), expected)

    def test_proven_sc02_roofed_wire_parity(self):
        recipe = {"lip_mm": 1., "transition_mm": 4.}
        for t in (0., .02, .25, .5, .8, 1.):
            floor = FLOOR + _zshift(t)
            expected = place_r48_wire(original_roofed(
                cq.Workplane("XZ"), floor, CHANNEL_RADIUS,
                floor+30.30, _blend(t, recipe), RADIUS), t)
            check_same_wire(self, proven_roofed_wire(t, recipe), expected)

    def test_new_e01_sc02_relief_profiles_match_original(self):
        for drop in (0., DUPLO.height):
            for relief in (.4, 1.):
                config = R48PairConfig("X92-parity", drop, relief_mm=relief)
                for t in (0., .02, .25, .5, .8, 1.):
                    floor = floor_z(t, drop)
                    progress = _progress(t)
                    radius = BALL_TRACK.radius + relief * progress
                    expected = original_roofed(
                        cq.Workplane("XZ"), floor, radius, floor+30.3,
                        progress, RADIUS)
                    expected = expected.rotate(
                        (0, 0, 0), (0, 0, 1), -90+90*t
                    ).translate((-32., 32., 0))
                    check_same_wire(self, new_roofed_wire(t, config), expected)


class FamilyDispatchTests(unittest.TestCase):
    def test_all_four_variants_use_one_api(self):
        for drop in (0., DUPLO.height):
            open_cfg = R48FamilyConfig("X92-open", drop, "open")
            with patch("brickcad.course_loft_family.build_course",
                       return_value=(sentinel.open_part, sentinel.fit)) as build:
                result, meta = build_r48_family(open_cfg, marked=False)
            self.assertIs(result, sentinel.open_part)
            recipe = build.call_args.args[0]
            self.assertEqual(recipe.route, "gentle")
            self.assertEqual(recipe.drop_mm, drop)
            self.assertFalse(recipe.tunnel)
            self.assertIsNone(build.call_args.kwargs["label"])
            self.assertEqual(meta["port_contract"]["opening_diameter_mm"],
                             BALL_TRACK.opening)

            roof_cfg = R48FamilyConfig("X92-roof", drop, "roofed",
                                       relief_mm=.4)
            with patch("brickcad.course_r48_unified.build_r48",
                       return_value=(sentinel.roof_part, {})) as build:
                result, _ = build_r48_family(roof_cfg, marked=False)
            self.assertIs(result, sentinel.roof_part)
            inner = build.call_args.args[0]
            self.assertIsInstance(inner, R48PairConfig)
            self.assertEqual(inner.drop_mm, drop)
            self.assertEqual(inner.relief_mm, .4)
            self.assertFalse(build.call_args.kwargs["marked"])

    def test_reject_unverified_family_variants(self):
        for enclosure in ("unknown", ""):
            with self.assertRaises(ValueError):
                R48FamilyConfig("X92-bad", 0., enclosure)
        with self.assertRaises(ValueError):
            R48FamilyConfig("X92-bad", 0., "open", relief_mm=.4)
        with self.assertRaises(ValueError):
            R48FamilyConfig("X92-bad", 1., "roofed")
        with self.assertRaises(ValueError):
            R48FamilyConfig("X92-bad", 0., "roofed", relief_mm=3.)
        with self.assertRaises(ValueError):
            R48FamilyConfig("X92-bad", 0., "roofed", direction="up")


if __name__ == "__main__":
    unittest.main()
