"""Keep layout changes from making ordinary changes run historical CAD tests."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('ci_selection', Path(__file__).resolve().parents[1] / 'scripts/ci-tests.py')
ci = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ci)


class SelectionTests(unittest.TestCase):
    def test_docs_and_stls_do_not_run_cad(self):
        self.assertEqual(ci.select({'parts/tunnel/model.stl', 'parts/tunnel/README.md'}), [])
        self.assertEqual(ci.select({'experiments/receiver_fit/records/setup.json'}), [])

    def test_tunnel_selects_transitive_assembly_only(self):
        self.assertEqual(set(ci.select({'parts/tunnel/design.py'})), {
            'parts/tunnel/test.py', 'parts/elbow/test.py',
            'experiments/pitagora_m1/test.py',
            'experiments/pr20_comparison/test.py'})

    def test_ci_only_changes_do_not_run_all_historical_cad(self):
        self.assertEqual(ci.select({'scripts/ci-tests.py'}),
                         ['tests/test_ci_selection.py'])
        self.assertEqual(ci.select({'.github/workflows/cad.yml'}),
                         ['tests/test_ci_selection.py'])
        self.assertEqual(ci.select({'.github/workflows/cad.yml',
                                    'scripts/ci-tests.py'}),
                         ['tests/test_ci_selection.py'])

    def test_experiment_does_not_select_unrelated_models(self):
        self.assertEqual(ci.select({'experiments/receiver_fit/design.py'}), ['experiments/receiver_fit/test.py'])

    def test_adjacent_test_is_selected_once(self):
        self.assertEqual(ci.select({'parts/tunnel/test.py'}), ['parts/tunnel/test.py'])

    def test_config_selects_owner_and_dependents(self):
        self.assertEqual(ci.select({'experiments/xy_fit/profile.json'}), ['experiments/xy_fit/test.py'])

    def test_parts_never_import_experiments(self):
        for p in (ci.ROOT/'parts').rglob('design.py'):
            self.assertFalse(any(x.startswith('experiments/') for x in ci.dependencies(p.relative_to(ci.ROOT).as_posix())))
