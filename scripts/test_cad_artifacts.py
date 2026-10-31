"""Fast planner and STL integrity tests; no CadQuery or Chromium imports."""
import importlib.util
import json
from pathlib import Path
import struct
from tempfile import TemporaryDirectory
import unittest

file = Path(__file__).with_name('cad-artifacts.py')
spec = importlib.util.spec_from_file_location('cad_artifacts', file)
cad = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cad)


class PlannerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name, source, requires, auto in [
            ('parts/alpha', 'from brickcad.geometry import part\n', [], True),
            ('parts/beta', 'from parts.alpha.design import part\n', [], True),
            ('experiments/manual', 'from parts.beta.design import part\n', ['parts/beta'], False),
        ]:
            folder = self.root / name
            folder.mkdir(parents=True)
            (folder / 'design.py').write_text(source)
            (folder / 'cad-build.json').write_text(json.dumps({
                'command': ['python', '-m', name.replace('/', '.') + '.design', '--out', '{out}'],
                'stl': ['brick.stl'], 'requires': requires, 'auto': auto
            }))
        (self.root / 'brickcad').mkdir()
        (self.root / 'brickcad/geometry.py').write_text('def part(): pass\n')
        self.specs, self.order = cad.discover(self.root)

    def test_changed_rebuilds_transitive_users(self):
        self.assertEqual(cad.choose(self.specs, self.order, changed={'parts/alpha/design.py'}, root=self.root),
                         ['parts/alpha', 'parts/beta'])
        self.assertEqual(cad.choose(self.specs, self.order, changed={'parts/beta/cad-build.json'}, root=self.root),
                         ['parts/beta'])
        self.assertEqual(cad.choose(self.specs, self.order, changed={'brickcad/geometry.py'}, root=self.root),
                         ['parts/alpha', 'parts/beta'])

    def test_docs_and_generated_stl_do_not_rebuild(self):
        for change in ('parts/alpha/README.md', 'parts/alpha/model.stl'):
            self.assertEqual(cad.choose(self.specs, self.order, changed={change}, root=self.root), [])

    def test_manual_requires_only_requested_dependencies(self):
        self.assertEqual(cad.choose(self.specs, self.order, targets='experiments/manual', root=self.root),
                         ['parts/beta', 'experiments/manual'])
        self.assertEqual(cad.choose(self.specs, self.order, targets='all', root=self.root),
                         ['parts/alpha', 'parts/beta'])
        with self.assertRaisesRegex(ValueError, 'Unknown CAD target'):
            cad.choose(self.specs, self.order, targets='parts/missing', root=self.root)

    def test_bad_paths_and_dependencies(self):
        with self.assertRaises(ValueError):
            cad.path_under(self.root, '../escape.stl')
        with self.assertRaises(ValueError):
            cad.path_under(self.root, '/etc/password')
        (self.root / 'parts/alpha/cad-build.json').write_text(json.dumps({
            'command': ['echo', 'hello'], 'stl': ['../../escape.stl']
        }))
        with self.assertRaises(ValueError):
            cad.discover(self.root)

    def test_binary_stl_integrity(self):
        file = self.root / 'model.stl'
        file.write_bytes(b' '*80 + struct.pack('<I', 1) + b'\0'*50)
        self.assertEqual(cad.validate_stl(file)['triangles'], 1)
        file.write_bytes(file.read_bytes()[:-1])
        with self.assertRaises(ValueError):
            cad.validate_stl(file)


if __name__ == '__main__':
    unittest.main()
