"""Fast geometry parity checks for R48 underbody and outer shell helpers.

These compare actual CadQuery solids/wires to the pre-refactor operations,
including the bottom cavity that previously printed as a failed bridge.
"""
import unittest
from types import SimpleNamespace
from unittest.mock import patch, sentinel

import cadquery as cq

from brickcad.connections import make_receiver
from brickcad.course_r48_building_blocks import (
    loft_sections, outer_section_wire, receiver_underbody, sweep_enclosure,
    place_r48_wire,
)


def assert_geometry_matches(case, actual, expected):
    """Use both directed BRep differences, not just identical dimensions."""
    a = actual.val() if isinstance(actual, cq.Workplane) else actual
    b = expected.val() if isinstance(expected, cq.Workplane) else expected
    case.assertTrue(a.isValid())
    case.assertTrue(b.isValid())
    case.assertAlmostEqual(a.Volume(), b.Volume(), places=6)
    case.assertLess(a.cut(b).Volume(), 1e-5)
    case.assertLess(b.cut(a).Volume(), 1e-5)


class SharedUnderbodyParityTests(unittest.TestCase):
    def setUp(self):
        self.fit = SimpleNamespace(
            cavity_xy=(25.4, 25.4),
            tube_radius=6.6,
            tube_inner_radius=4.7,
            clearance=0.,
            tubes=lambda: [(0., 0.)],
        )

    def test_open_receiver_matches_original_model_receiver(self):
        outer = cq.Workplane("XY").box(
            32., 32., 6.35, centered=(True, True, False))
        legacy = make_receiver(outer, self.fit.tubes(),
                               self.fit.cavity_xy, 4.75,
                               self.fit.tube_radius - self.fit.clearance,
                               self.fit.tube_inner_radius, 0.)
        new = receiver_underbody(outer, self.fit, 4.75)
        assert_geometry_matches(self, new, legacy)
        # A standard stud inserted into a cavity must not hit a solid slab.
        self.assertFalse(new.val().isInside(cq.Vector(8., 8., 2.), .001))

    def test_sc02_receiver_keeps_exactly_the_specified_tubes(self):
        outer = cq.Workplane("XY").box(
            63.8, 63.8, 6.35, centered=(True, True, False))
        centers = ((-16., -16.), (0., 0.), (16., 16.))
        old = make_receiver(outer, centers, self.fit.cavity_xy,
                            4.75, self.fit.tube_radius,
                            self.fit.tube_inner_radius, 0.)
        new = receiver_underbody(outer, self.fit, 4.75,
                                 tubes=centers,
                                 tube_radius=self.fit.tube_radius,
                                 entry=0.)
        assert_geometry_matches(self, new, old)

    def test_outer_wires_are_the_historical_exact_shapes(self):
        for bottom, top, fillet in ((0., 19.2, 0.),
                                     (5.6, 57.6, 0.),
                                     (6.2, 38.4, .5)):
            raw = cq.Workplane("XZ").polyline([
                (32.1, bottom), (63.9, bottom),
                (63.9, top), (32.1, top)]).close().val()
            if fillet:
                corners = [v for v in raw.Vertices()
                           if v.Center().z > top - .01]
                raw = raw.fillet2D(fillet, corners)
            shared = outer_section_wire(cq.Workplane("XZ"),
                                        inner=32.1, outer=63.9,
                                        bottom=bottom, top=top,
                                        top_corner_radius=fillet)
            self.assertEqual(len(raw.Edges()), len(shared.Edges()))
            self.assertAlmostEqual(cq.Face.makeFromWires(raw).Area(),
                                   cq.Face.makeFromWires(shared).Area(),
                                   places=7)
            for old_edge, new_edge in zip(raw.Edges(), shared.Edges()):
                self.assertEqual(old_edge.geomType(), new_edge.geomType())
                self.assertAlmostEqual(old_edge.Length(),
                                       new_edge.Length(), places=8)

    def test_ruled_and_smooth_lofts_keep_historical_geometry(self):
        for ruled in (False, True):
            sections = []
            for z, size in ((0, 20.), (10., 23.), (20., 21.)):
                sections.append(cq.Workplane("XY", origin=(0, 0, z))
                                .rect(size, size).val())
            legacy = cq.Solid.makeLoft(sections, ruled=ruled)
            new = loft_sections(sections, ruled=ruled)
            assert_geometry_matches(self, new, legacy)


    def test_shared_r48_placement_preserves_proven_curve_positions(self):
        wire = (cq.Workplane("XZ")
                .polyline([(35., 6.2), (60., 6.2),
                           (60., 38.4), (35., 38.4)]).close().val())
        for t in (-.02, 0., .25, .5, .75, 1., 1.02):
            original = (wire.rotate((0, 0, 0), (0, 0, 1), -90 + 90*t)
                        .translate((-32., 32., 0)))
            shared = place_r48_wire(wire, t)
            self.assertEqual(len(original.Edges()), len(shared.Edges()))
            for a, b in zip(original.Vertices(), shared.Vertices()):
                for coordinate in ("x", "y", "z"):
                    self.assertAlmostEqual(getattr(a.Center(), coordinate),
                                           getattr(b.Center(), coordinate), places=9)

    def test_shared_enclosure_sweep_preserves_both_original_lofts(self):
        sections = (0., .25, .5, .75, 1.)
        def outer(t):
            return (cq.Workplane("XY", origin=(0, 0, 10*t))
                    .rect(30., 30.).val())
        def inside(t):
            return (cq.Workplane("XY", origin=(0, 0, 10*t))
                    .circle(10.).val())
        legacy_shell = cq.Solid.makeLoft([outer(t) for t in sections],
                                          ruled=True)
        legacy_hole = cq.Solid.makeLoft([inside(t) for t in sections],
                                         ruled=True)
        shell, hole = sweep_enclosure(outer, inside, sections, ruled=True)
        assert_geometry_matches(self, shell, legacy_shell)
        assert_geometry_matches(self, hole, legacy_hole)

    def test_sc02_connection_finishing_has_no_repeated_implementation(self):
        from brickcad.course_r48_sloped_tunnel import add_curve_connections
        fit = SimpleNamespace(tube_radius=6.6)
        steps = []
        with (
            patch("brickcad.course_r48_sloped_tunnel.clipped_receivers",
                  side_effect=lambda shape, p: (
                      steps.append("partial") or sentinel.partial)),
            patch("brickcad.course_r48_sloped_tunnel.add_e31_05_receiver_features",
                  side_effect=lambda shape, tubes, r, **kw: (
                      steps.append("e31") or sentinel.e31)),
            patch("brickcad.course_r48_sloped_tunnel.roof_studs",
                  side_effect=lambda shape, p, **kw: (
                      steps.append("stud") or sentinel.roof)),
        ):
            result = add_curve_connections(sentinel.base, fit, top_z=38.4)
        self.assertIs(result, sentinel.roof)
        self.assertEqual(steps, ["partial", "e31", "stud"])

if __name__ == "__main__":
    unittest.main()
