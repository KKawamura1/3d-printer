import itertools
import math
import unittest

import cadquery as cq

from brickcad.course_finish import WINDOW_WIDTH_MM
from brickcad.course_geometry import smoothstep_rise_expanded
from brickcad.course_loft_family import (
    CHANNEL_HALF_WIDTH, SHARP_INTERIOR_RELIEF_MM,
    LoftSettings, height, section_plane, wire, xy,
)
from brickcad.course_section_profiles import (
    end_relief_blend, interior_radius_mm, passage_section_wire,
    validate_interior_relief,
)
from brickcad.standards import BALL_TRACK, DUPLO
from experiments.compact_curve.design import (
    OUTER_WALL_WINDOW_CENTRES_MM, SPECIMENS, window_stations,
)
from experiments.compact_curve.export import actual_mouths_match


class CompactCurveTests(unittest.TestCase):
    def test_four_downhill_recipes_and_common_port_path(self):
        expected = set(itertools.product((False, True), (False, True)))
        self.assertEqual({(s.tunnel, s.left) for s in SPECIMENS}, expected)
        self.assertEqual([s.id for s in SPECIMENS],
                         ["X4A-05", "X4A-06", "X4A-07", "X4A-08"])
        self.assertTrue(all(s.drop_mm == DUPLO.height for s in SPECIMENS))
        for specimen in SPECIMENS:
            config = LoftSettings.from_dict(vars(specimen.settings))
            self.assertEqual(xy(0, config), (-32, 0, 1, 0))
            for actual, expected in zip(xy(config.length, config), (16, -16, 0, -1)):
                self.assertAlmostEqual(actual, expected)
            self.assertAlmostEqual(height(0, config), 6.35 + specimen.drop_mm)
            self.assertAlmostEqual(height(config.length, config), 6.35)

    def test_five_windows_cover_the_full_outer_wall_at_equal_pitch(self):
        # Count five physical openings: 2 straight and 3 curved.
        # Equal centreline spacing is NOT equal outer-wall spacing on R16.
        # Crucially compare BOTH end margins, not only window-to-window gaps.
        for specimen in SPECIMENS[2:]:
            config = specimen.settings
            actual = window_stations(config)
            nominal = OUTER_WALL_WINDOW_CENTRES_MM
            outer_radius = config.radius + CHANNEL_HALF_WIDTH
            total_outer = 32. + math.pi * outer_radius / 2.
            self.assertEqual(len(actual), 5)
            self.assertEqual(sum(s < 32. for s in actual), 2)
            self.assertEqual(sum(s > 32. for s in actual), 3)
            self.assertGreaterEqual(nominal[0] - WINDOW_WIDTH_MM/2, 3.)
            self.assertGreaterEqual(
                total_outer-nominal[-1]-WINDOW_WIDTH_MM/2, 3.)
            for station, distance in zip(actual, nominal):
                projected = (station if station <= 32.
                             else 32. + (station-32.) *
                             outer_radius/config.radius)
                self.assertAlmostEqual(projected, distance, places=9)
            gaps = [b-a for a, b in zip(nominal, nominal[1:])]
            self.assertEqual(gaps, [16., 16., 16., 16.])
            self.assertTrue(all(
                gap-WINDOW_WIDTH_MM >= 3. for gap in gaps))
            # A uniform centre pitch is not enough: X4A-V5 incorrectly
            # left over 20mm of empty outer wall after the last window.
            self.assertAlmostEqual(nominal[0],
                                   total_outer - nominal[-1], delta=.5)
            self.assertAlmostEqual(
                nominal[0] - WINDOW_WIDTH_MM/2,
                total_outer - nominal[-1] - WINDOW_WIDTH_MM/2, delta=.5)
            # Protect the join: a window must not straddle a straight wall
            # and a curved wall, otherwise the cutter might not open both.
            self.assertGreaterEqual(
                32.-nominal[1]-WINDOW_WIDTH_MM/2, 1.)
            self.assertGreaterEqual(
                nominal[2]-32.-WINDOW_WIDTH_MM/2, 1.)
            # The final curved opening must remain off the exit port.
            self.assertGreaterEqual(
                total_outer - nominal[-1] - WINDOW_WIDTH_MM/2, 3.)

    def test_r16_relief_matches_independent_legacy_formulas_and_wires(self):
        # PR91 and PR94 now share one kernel, but prior printed SD01-SD04
        # passages MUST keep their exact pre-refactor radius/roof arithmetic.
        for specimen in SPECIMENS[::2]:
            settings = specimen.settings
            samples = (-.3, 0., .5, 1., 3., 5., 12., 27., 32.,
                       settings.length / 2, settings.length - 5.,
                       settings.length - 1., settings.length,
                       settings.length + .3)
            for station in samples:
                with self.subTest(id=specimen.id, station=station):
                    distance = min(max(0, station),
                                   max(0, settings.length-station))
                    if settings.tunnel:
                        u = max(0., min(1., (distance-1.)/4.))
                        legacy_blend = min(.995, smoothstep_rise_expanded(u))
                    else:
                        legacy_blend = min(1., distance/5.)
                    relief_mode = ("smoothstep-expanded" if settings.tunnel
                                   else "linear")
                    shared_blend = end_relief_blend(
                        distance, mode=relief_mode)
                    self.assertEqual(shared_blend, legacy_blend)
                    radius = interior_radius_mm(
                        shared_blend, extra_radius_mm=SHARP_INTERIOR_RELIEF_MM)
                    legacy_radius = (
                        BALL_TRACK.radius+(14.-BALL_TRACK.radius)*legacy_blend)
                    self.assertEqual(radius, legacy_radius)

                    # Compare the actual OCC passage wire (not only its
                    # scalar radius) with the historical independently
                    # constructed section of the same model.
                    floor = height(station, settings)
                    roof = (floor+2*BALL_TRACK.radius+
                            (30.3-2*BALL_TRACK.radius)*legacy_blend
                            if settings.tunnel else None)
                    original = passage_section_wire(
                        cq.Workplane(section_plane(station, settings)),
                        floor=floor, radius=legacy_radius,
                        roof=roof, blend=legacy_blend,
                        open_top=95.)
                    shared = wire(station, "passage", settings)
                    self.assertEqual(len(original.Edges()),
                                     len(shared.Edges()))
                    for old_edge, new_edge in zip(original.Edges(),
                                                  shared.Edges()):
                        self.assertAlmostEqual(
                            old_edge.Length(), new_edge.Length(), places=10)

    def test_pr91_pr94_shared_relief_guards_keep_fixed_port(self):
        self.assertEqual(
            interior_radius_mm(0., extra_radius_mm=SHARP_INTERIOR_RELIEF_MM),
            BALL_TRACK.radius)
        # The drawing's 25.74mm nominal opening is rounded to 0.01mm;
        # the CAD kernel uses its slightly more precise half-section radius.
        self.assertAlmostEqual(2 * BALL_TRACK.radius,
                               BALL_TRACK.opening, places=2)
        self.assertEqual(
            validate_interior_relief(
                CHANNEL_HALF_WIDTH,
                extra_radius_mm=SHARP_INTERIOR_RELIEF_MM),
            SHARP_INTERIOR_RELIEF_MM)
        self.assertAlmostEqual(
            CHANNEL_HALF_WIDTH - 14., 1.9, places=7)
        with self.assertRaises(ValueError):
            validate_interior_relief(
                CHANNEL_HALF_WIDTH, extra_radius_mm=2.0)
        with self.assertRaisesRegex(ValueError,
                                    "Unknown passage-relief transition"):
            end_relief_blend(3., mode="unexpected")

    def test_trial_mark_is_fully_contained_on_the_short_west_skirt(self):
        from brickcad.course_finish import west_skirt_label_tool

        for specimen in SPECIMENS:
            with self.subTest(id=specimen.id):
                cutter = west_skirt_label_tool(
                    specimen.id, x=-31.9, y=0., face_width_mm=31.8)
                bounds = cutter.BoundingBox()
                self.assertGreaterEqual(bounds.ymin, -14.9)
                self.assertLessEqual(bounds.ymax, 14.9)
                self.assertGreaterEqual(bounds.zmin, .4)
                self.assertLessEqual(bounds.zmax, 4.35)

        with self.assertRaisesRegex(ValueError, "exceeds the west receiver skirt"):
            west_skirt_label_tool(
                "X4A-WAY-TOO-LONG-FOR-SKIRT", x=-31.9, y=0.)

    def test_horizontal_sharp_tunnel_is_not_supported(self):
        with self.assertRaises(ValueError):
            LoftSettings.from_dict({
                "route": "sharp", "drop_mm": 0., "tunnel": True,
                "mirror": False, "mark_face": "south", "label_z_mm": 12.
            })

    def test_port_probe_detects_wrong_diameter_and_wrong_handedness(self):
        stock = cq.Workplane("XY").box(63.8, 31.8, 57.6,
                                      centered=(True, True, False)).val()

        def bores(radius):
            inlet = cq.Solid.makeCylinder(radius, 12, (-34, 0, 38.42), (1, 0, 0))
            outlet = cq.Solid.makeCylinder(radius, 12, (16, -18, 19.22), (0, 1, 0))
            return stock.cut(inlet, outlet)

        self.assertTrue(actual_mouths_match(bores(12.87), SPECIMENS[2]))
        self.assertFalse(actual_mouths_match(bores(13.20), SPECIMENS[2]))
        self.assertFalse(actual_mouths_match(bores(12.87), SPECIMENS[3]))


if __name__ == "__main__":
    unittest.main()
