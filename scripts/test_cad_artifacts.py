"""Legacy command remains an alias of the version-pinned CAD runner."""
import importlib.util
from pathlib import Path
import unittest
import cad_versions


class LegacyCommandTests(unittest.TestCase):
    def test_old_entrypoint_uses_the_same_versioned_engine(self):
        old = Path(__file__).with_name('cad-artifacts.py')
        spec = importlib.util.spec_from_file_location('cad_legacy', old)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertIs(module.select, cad_versions.select)
        self.assertIs(module.build, cad_versions.build)


if __name__ == '__main__':
    unittest.main()
