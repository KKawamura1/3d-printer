"""Regression tests: every production course receives the same E31/engrave API.

These are deliberately CAD-free and execute in the fast catalogue CI job.
The geometry-specific BRep parity and printability are tested separately.
"""
import ast
from pathlib import Path
import unittest

from brickcad.course_contract import (
    CATEGORY_AXES, RECEIVER_DEPTH_MM, TUBE_RADIUS_MM,
    SLOT_END_Z_MM, MARK_SIZE_MM, MARK_DEPTH_MM,
    course_axes, kernel_for, course_fit, add_course_receiver_features,
    engrave_course, engrave_course_west, CourseBuildAudit,
    audited_production_course,
)

ROOT = Path(__file__).resolve().parents[1]
BUILDERS = (
    "course_loft_family", "course_r48_tunnel", "course_r48_sloped_tunnel",
    "course_prod_sharp_curve", "course_prod_steep_drop", "course_prod_downhill",
    "course_straight_tunnel", "course_straight_rail",
)


class CourseContractTests(unittest.TestCase):
    def test_explicit_fixed_connector_and_engraving(self):
        self.assertEqual((RECEIVER_DEPTH_MM, TUBE_RADIUS_MM, SLOT_END_Z_MM), (4.75, 6.60, 3.50))
        self.assertEqual((MARK_SIZE_MM, MARK_DEPTH_MM), (3.0, .4))
        with self.assertRaisesRegex(ValueError, "shallow 4.75"):
            add_course_receiver_features(None, (), 6.60, receiver_depth=17.60)
        with self.assertRaisesRegex(ValueError, "13.20"):
            add_course_receiver_features(None, (), 6.65, receiver_depth=4.75)
        with self.assertRaisesRegex(TypeError, "receiver_depth"):
            add_course_receiver_features(None, (), 6.60)
        with self.assertRaisesRegex(ValueError, "cannot override"):
            course_fit(nx=2, ny=2, tube_radius=6.65)
        with self.assertRaisesRegex(ValueError, "cannot override"):
            course_fit(nx=2, ny=2, fit_profile_id="duplo-straight-rail-trial-v1")
        with self.assertRaisesRegex(ValueError, "3.0 mm"):
            engrave_course(None, "R01-V1", x=0, y=0, z=0, size=2.5)
        with self.assertRaisesRegex(ValueError, "3.0 mm"):
            engrave_course_west(None, "SC02-V12", x=0, y=0, z=0, depth=.3)

    def test_runtime_audit_rejects_missing_and_double_finishing(self):
        with self.assertRaisesRegex(ValueError, "fit bypassed"):
            with audited_production_course("R01-V1"):
                pass
        with self.assertRaisesRegex(ValueError, "E31 receiver bypassed"):
            with audited_production_course("R01-V1") as audit:
                audit.fit_calls += 1
        with self.assertRaisesRegex(ValueError, "exactly one final standard"):
            with audited_production_course("R01-V1") as audit:
                audit.fit_calls += 1
                audit.receiver_calls += 1
                audit.marked_labels.extend(["R01-V1", "R01-V1"])
        with self.assertRaisesRegex(ValueError, "exactly one final standard"):
            with audited_production_course("SC02L-V6") as audit:
                audit.fit_calls += 1
                audit.receiver_calls += 1
                audit.marked_labels.extend(["SC02-V12", "SC02L-V6"])
        with audited_production_course("R01-V1") as audit:
            audit.fit_calls += 1
            audit.receiver_calls += 1
            audit.marked_labels.append("R01-V1")
        self.assertEqual(audit.manifest()["final_marking_labels"], ["R01-V1"])
        self.assertEqual(audit.manifest()["e31_receiver_calls"], 1)
        with self.assertRaisesRegex(ValueError, "Nested"):
            with audited_production_course("R01-V1"):
                with audited_production_course("C01-V6"):
                    pass

    def test_sloped_r48_intermediate_cannot_engrave_a_fixed_model_id(self):
        path = ROOT / "brickcad/course_r48_sloped_tunnel.py"
        tree = ast.parse(path.read_text())
        intermediate = next(
            n for n in tree.body if isinstance(n, ast.FunctionDef) and
            n.name == "open_curve"
        )
        self.assertFalse(
            any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                and n.func.id in {"engrave_west", "engrave"} for n in ast.walk(intermediate)),
            "Intermediate geometry must not contain a temporary engraved ID",
        )
        self.assertIn("engrave_west", path.read_text().split("def build_course")[1])

    def test_pure_axis_routing_without_legacy_special_case(self):
        expected = {
            1: "straight_rail", 6: "straight_tunnel", 7: "horizontal_r48_tunnel",
            9: "sharp_r16", 11: "loft", 12: "loft",
            16: "downhill_windowed", 17: "sloped_r48_tunnel",
            19: "loft", 21: "drop", 24: "drop",
        }
        for number, kernel in expected.items():
            with self.subTest(number=number):
                self.assertEqual(kernel_for(course_axes(
                    [number], windows=3 if number == 16 else 0)), kernel)
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            kernel_for({"slope": "steep", "curve": "gentle_left",
                        "enclosure": "tunnel", "windows": 0})
        with self.assertRaisesRegex(ValueError, "Window"):
            course_axes([1], windows=3)
        with self.assertRaisesRegex(ValueError, "reverse-running"):
            course_axes([1, 6])

    def test_all_geometry_builders_are_forced_through_shared_fit_and_marking(self):
        for name in BUILDERS:
            path = ROOT / "brickcad" / (name + ".py")
            tree = ast.parse(path.read_text())
            from_contract = set()
            for node in ast.walk(tree):
                if not isinstance(node, ast.ImportFrom):
                    continue
                direct = {a.name for a in node.names}
                if node.module == "brickcad.course_contract":
                    from_contract |= direct
                if node.module == "brickcad.model":
                    self.assertNotIn("brick_from_fit", direct, name)
                if node.module == "brickcad.marking":
                    self.fail(f"{name} imports the raw engraving bypass")
                if node.module == "parts.tunnel.e31_fit":
                    self.assertNotIn("add_e31_05_receiver_features", direct, name)
            self.assertIn("course_fit", from_contract, name)
            self.assertIn("add_course_receiver_features", from_contract, name)
            self.assertTrue(
                {"engrave_course", "engrave_course_west"} & from_contract, name
            )
            calls = {n.func.id for n in ast.walk(tree)
                     if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
            self.assertIn("course_fit", calls, name)
            self.assertTrue(
                {"add_e31_05_receiver_features", "add_course_receiver_features"} & calls,
                name,
            )
            self.assertTrue({"engrave", "engrave_west", "engrave_course", "engrave_course_west"} & calls, name)
            # The only profile selector in a production geometry builder is course_fit.
            src = path.read_text()
            self.assertNotIn("duplo-straight-rail-trial-v1", src, name)
            self.assertNotIn('brick_from_fit("duplo-e27-play-v1"', src, name)


if __name__ == "__main__":
    unittest.main()
