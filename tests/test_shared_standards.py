"""Contracts for new parts: independent dimensions and reproducible profiles."""
from dataclasses import FrozenInstanceError, asdict, replace
import json
import unittest
import cadquery as cq
from brickcad.model import brick_from_fit, from_profile, nominal_brick, build
from brickcad.provenance import design_manifest
from brickcad.standards import FIT_PROFILES, fit_profile, BALL_TRACK
from brickcad.verify import geometry_report, VOLUME_TOL


class SharedStandardsTests(unittest.TestCase):
    def test_body_compensation_preserves_receiver_and_grid(self):
        p = brick_from_fit('duplo-nominal-v1', nx=2, ny=2)
        wider = replace(p, body_offset_xy=(.2, .07))
        self.assertEqual(wider.cavity_xy, (25.4, 25.4))
        self.assertEqual(wider.studs(), p.studs())
        self.assertEqual(wider.tubes(), p.tubes())
        self.assertAlmostEqual(wider.width, 32.)
        self.assertAlmostEqual(wider.depth, 31.87)
        shape = build(wider)
        self.assertTrue(geometry_report(wider, shape)['passed'])
        # Independently anchored inner face x=12.7, including the enlarged body.
        self.assertFalse(shape.isInside(cq.Vector(12.69, 0, 1)))
        self.assertTrue(shape.isInside(cq.Vector(12.71, 0, 1)))

    def test_receiver_and_stud_adjustments_are_independent(self):
        p = brick_from_fit('duplo-nominal-v1', nx=2, ny=2)
        altered = replace(p, receiver_inset_xy=(3.2, 3.4), tube_radius=6.7)
        self.assertEqual(altered.stud_radius, p.stud_radius)
        self.assertEqual(altered.width, p.width)
        self.assertEqual(altered.cavity_xy, (25.6, 25.2))
        shape = build(altered)
        self.assertTrue(geometry_report(altered, shape)['passed'])
        self.assertFalse(shape.isInside(cq.Vector(0, 12.59, 1)))
        self.assertTrue(shape.isInside(cq.Vector(0, 12.61, 1)))
        stud_changed = replace(p, stud_radius=4.66)
        self.assertEqual(stud_changed.cavity_xy, p.cavity_xy)
        self.assertEqual(stud_changed.tube_radius, p.tube_radius)

    def test_named_nominal_is_same_solid_as_legacy_reference(self):
        a = build(nominal_brick('duplo', 2, 2))
        b = build(brick_from_fit('duplo-nominal-v1', nx=2, ny=2))
        self.assertLess(a.cut(b).Volume()+b.cut(a).Volume(), VOLUME_TOL)

    def test_straight_rail_preserves_historical_asymmetric_receiver(self):
        p = brick_from_fit('duplo-straight-rail-trial-v1', nx=4, ny=2,
                           body_offset_xy=(0., -.15))
        self.assertAlmostEqual(p.cavity_xy[0], 57.63)
        self.assertAlmostEqual(p.cavity_xy[1], 25.48)

    def test_json_roundtrip_and_height_units(self):
        p = from_profile(dict(fit_profile_id='duplo-rail-trial-v1', nx=2, ny=2, height_units=2))
        self.assertEqual(p.height, 38.4)
        self.assertAlmostEqual(p.cavity_xy[0], 25.48)
        self.assertEqual(from_profile(json.loads(json.dumps(asdict(p)))), p)
        self.assertIsInstance(p.body_offset_xy, tuple)
        self.assertIsInstance(p.receiver_inset_xy, tuple)

    def test_versions_are_frozen_and_invalid_inputs_rejected(self):
        with self.assertRaises(TypeError):
            FIT_PROFILES['new'] = fit_profile('duplo-nominal-v1')
        with self.assertRaises(FrozenInstanceError):
            fit_profile('duplo-nominal-v1').stud_radius = 5.
        for kw in (dict(height_units=0), dict(height_units=1.5), dict(family='lego'),
                   dict(body_offset_xy=None), dict(body_offset_xy=[1]),
                   dict(receiver_inset_xy=(float('nan'), 3)),
                   dict(receiver_inset_xy=(16., 3.3))):
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                brick_from_fit('duplo-nominal-v1', **kw)
        with self.assertRaises(ValueError):
            brick_from_fit('unknown-v1')

    def test_manifest_records_baseline_overrides_and_source(self):
        p = brick_from_fit('duplo-xy-trial-v1', nx=2, ny=2, tube_radius=6.65)
        manifest = design_manifest(p, channel=BALL_TRACK)
        self.assertEqual(manifest['fit_baseline']['tube_radius'], 6.75)
        self.assertEqual(manifest['resolved_parameters']['tube_radius'], 6.65)
        self.assertEqual(manifest['receiver_opening_xy_mm'], [25.4, 25.4])
        self.assertIn('brickcad/connections.py', manifest['source_files'])
        self.assertIn('brickcad/standards.py', manifest['source_files'])
        self.assertFalse(manifest['physical_fit_validated'])
        self.assertIsNone(manifest['print_setup'])
        json.dumps(manifest)
