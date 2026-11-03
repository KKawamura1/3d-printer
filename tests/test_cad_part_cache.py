"""Regression tests for the test-only CAD BRep cache."""
import unittest

from brickcad.test_cache import cached_build_part


class FakeSolid:
    def __init__(self, value):
        self.value = value

    def copy(self, mesh=False):
        return FakeSolid(self.value)


class PartCacheTests(unittest.TestCase):
    def test_identical_builds_run_once_and_return_independent_copies(self):
        builds = []

        def build_part(label="A", *, mirror=False):
            builds.append((label, mirror))
            return FakeSolid(label), {"mirror": mirror}

        a, p1 = cached_build_part(build_part, label="A", mirror=True)
        b, p2 = cached_build_part(build_part, mirror=True, label="A")
        self.assertEqual(builds, [("A", True)])
        self.assertIsNot(a, b)
        self.assertEqual(p1, p2)
        a.value = "changed by test"
        self.assertEqual(b.value, "A")

    def test_different_parameters_have_distinct_builds(self):
        builds = []

        def build_part(*, mirror=False):
            builds.append(mirror)
            return FakeSolid(mirror), None

        a, _ = cached_build_part(build_part, mirror=False)
        b, _ = cached_build_part(build_part, mirror=True)
        self.assertEqual(builds, [False, True])
        self.assertFalse(a.value)
        self.assertTrue(b.value)


if __name__ == "__main__":
    unittest.main()
