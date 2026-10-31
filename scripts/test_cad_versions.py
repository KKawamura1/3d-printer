"""Fast version-policy checks; do not load CadQuery or any historical model."""
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest

import cad_versions as cad


def spec(version, *, requires=None, auto=True):
    return {'version': version, 'auto': auto,
            'command': ['python', '-m', 'parts.alpha.design', '--out', '{out}'],
            'stl': ['brick.stl'], 'requires': requires or []}


class VersionSelectionTests(unittest.TestCase):
    def setUp(self):
        self.specs = {'parts/alpha': spec('A02-V1'), 'parts/beta': spec('B01-V1'),
                      'experiments/trial': spec('X01-V1', auto=False)}
        self.prior = {'parts/alpha': 'A01-V1', 'parts/beta': 'B01-V1',
                      'experiments/trial': 'X00-V1'}

    def test_only_bumped_part_runs(self):
        self.assertEqual(cad.select(self.specs, 'changed', prior=self.prior,
                                    changed=['parts/alpha/cad-build.json']),
                         ['parts/alpha'])

    def test_experiment_never_autoruns_even_when_bumped(self):
        self.prior['parts/alpha'] = 'A02-V1'
        self.assertEqual(cad.select(self.specs, 'changed', prior=self.prior,
                                    changed=['experiments/trial/cad-build.json']), [])
        self.assertEqual(cad.select(self.specs, 'all'), ['parts/alpha', 'parts/beta'])
        self.assertEqual(cad.select(self.specs, 'experiments/trial'), ['experiments/trial'])

    def test_unbumped_geometry_edit_fails_instead_of_stale_output(self):
        with self.assertRaisesRegex(ValueError, 'parts/beta'):
            cad.select(self.specs, 'changed', prior=self.prior,
                       changed=['parts/beta/design.py'])

    def test_docs_and_test_edits_do_not_regenerate(self):
        self.prior['parts/alpha'] = 'A02-V1'
        self.prior['experiments/trial'] = 'X01-V1'
        self.assertEqual(cad.select(self.specs, 'changed', prior=self.prior,
                                    changed=['parts/alpha/README.md',
                                             'parts/beta/test.py',
                                             'scripts/cad_versions.py']), [])

    def test_pin_required_and_experiment_not_auto(self):
        with self.assertRaisesRegex(ValueError, 'pin'):
            cad.check('experiments/trial', spec('X01-V1', requires=['parts/alpha']))
        with self.assertRaisesRegex(ValueError, 'manual'):
            cad.check('experiments/trial', spec('X01-V1', auto=True))
        self.assertEqual(cad.check('experiments/trial',
                                   spec('X01-V1', auto=False))['requires'], [])
        with self.assertRaises(ValueError):
            cad.check('parts/alpha', spec('bad version'))

    def test_shared_geometry_change_needs_bump(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            part = root / 'parts/beta'
            shared = root / 'brickcad'
            part.mkdir(parents=True)
            shared.mkdir(parents=True)
            (part / 'design.py').write_text('from brickcad.geometry import shape' + chr(10))
            (shared / 'geometry.py').write_text('shape = 1' + chr(10))
            self.prior['parts/alpha'] = 'A02-V1'
            self.prior['experiments/trial'] = 'X01-V1'
            with self.assertRaisesRegex(ValueError, 'parts/beta'):
                cad.select(self.specs, 'changed', prior=self.prior,
                           changed=['brickcad/geometry.py'], root=root)

    def test_config_edit_without_version_change_needs_bump(self):
        self.prior['parts/alpha'] = 'A02-V1'
        with self.assertRaisesRegex(ValueError, 'parts/alpha'):
            cad.select(self.specs, 'changed', prior=self.prior,
                       changed=['parts/alpha/cad-build.json'])

    def test_source_fingerprint_changes_with_geometry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            part = root / 'parts/alpha'
            part.mkdir(parents=True)
            (part / 'cad-build.json').write_text(json.dumps(spec('A01-V1')))
            (part / 'design.py').write_text('MODEL = 1' + chr(10))
            before = cad.source_fingerprint(root, 'parts/alpha')
            (part / 'design.py').write_text('MODEL = 2' + chr(10))
            self.assertNotEqual(before, cad.source_fingerprint(root, 'parts/alpha'))

    def test_stl_binary_integrity(self):
        with tempfile.TemporaryDirectory() as tmp:
            model = Path(tmp) / 'brick.stl'
            model.write_bytes(b' ' * 80 + struct.pack('<I', 1) + b'\0' * 50)
            self.assertEqual(cad.verify_stl(model)['triangles'], 1)
            model.write_bytes(model.read_bytes()[:-1])
            with self.assertRaises(ValueError):
                cad.verify_stl(model)


class HistoricalDependencyTests(unittest.TestCase):
    def test_pin_resolves_previous_git_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
            subprocess.run(['git', 'config', 'user.name', 'CAD Test'], cwd=root, check=True)
            subprocess.run(['git', 'config', 'user.email', 'cad@example.invalid'],
                           cwd=root, check=True)
            part = root / 'parts/alpha'
            part.mkdir(parents=True)
            (part / 'cad-build.json').write_text(json.dumps(spec('A01-V1')))
            (part / 'design.py').write_text('SOURCE = "old"\n')
            subprocess.run(['git', 'add', '.'], cwd=root, check=True)
            subprocess.run(['git', 'commit', '-qm', 'v1'], cwd=root, check=True)
            old = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
            (part / 'cad-build.json').write_text(json.dumps(spec('A02-V1')))
            (part / 'design.py').write_text('SOURCE = "new"\n')
            experiment = root / 'experiments/trial'
            experiment.mkdir(parents=True)
            experiment_spec = spec('X01-V1', auto=False,
                                   requires=[{'target':'parts/alpha','version':'A01-V1'}])
            (experiment / 'cad-build.json').write_text(json.dumps(experiment_spec))
            subprocess.run(['git', 'add', '.'], cwd=root, check=True)
            subprocess.run(['git', 'commit', '-qm', 'v2 and trial'], cwd=root, check=True)
            nodes = cad.resolve(root, cad.discover(root), ['experiments/trial'])
            self.assertEqual([(n, v) for n,v,*_ in nodes],
                             [('parts/alpha', 'A01-V1'), ('experiments/trial', 'X01-V1')])
            self.assertEqual(nodes[0][4], old)
            self.assertIn('old', (nodes[0][3] / 'parts/alpha/design.py').read_text())
            self.assertEqual(nodes[1][4], None)


if __name__ == '__main__':
    unittest.main()
