"""Run only test files affected by a PR, once, including transitive CAD imports."""
import argparse
import ast
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


def dependencies(path, seen=None):
    seen = set() if seen is None else seen
    if path in seen or not (ROOT / path).is_file():
        return seen
    seen.add(path)
    module = path[:-3].replace('/', '.')
    package = module.rsplit('.', 1)[0]
    for node in ast.walk(ast.parse((ROOT / path).read_text())):
        names = []
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            prefix = node.module or ''
            if node.level:
                prefix = '.'.join(package.split('.')[:len(package.split('.'))-node.level+1]
                                  + ([prefix] if prefix else []))
            names = [prefix] + [prefix + '.' + alias.name for alias in node.names]
        for name in names:
            if name.split('.')[0] in ('brickcad', 'parts', 'experiments'):
                candidate = name.replace('.', '/') + '.py'
                if (ROOT / candidate).is_file():
                    dependencies(candidate, seen)
    return seen


def select(changed):
    tests = sorted(p.relative_to(ROOT).as_posix()
                   for folder in ('tests', 'parts', 'experiments')
                   for p in (ROOT / folder).rglob('test*.py'))
    if changed is None:
        return tests
    graph = {test: dependencies(test) for test in tests}
    known = set().union(*graph.values())
    # Config changes affect the owning design and its transitive dependents.
    changed = set(changed)
    for path in list(changed):
        if path.startswith(('parts/', 'experiments/')) and path.endswith('.json') and len(path.split('/')) == 3:
            owner = '/'.join(path.split('/')[:2]) + '/design.py'
            changed.add(owner)
    # A model owns its adjacent tests even if those tests import a new design
    # module (e.g. design_e31.py) rather than the changed legacy design.py.
    # This also covers cad-build.json changes mapped to design.py above.
    owners = {'/'.join(path.split('/')[:2]) for path in changed
              if path.startswith(('parts/', 'experiments/'))
              and path.endswith('.py') and len(path.split('/')) >= 3
              and not path.split('/')[-1].startswith('test')}
    adjacent_tests = {test for test in tests
                      if any(test.startswith(owner + '/test') for owner in owners)}
    # CI plumbing changes validate the selector itself, not every historical CAD
    # model. The workflow separately runs lightweight version/report tests.
    if {'scripts/ci-tests.py', '.github/workflows/cad.yml'} & changed:
        changed.add('tests/test_ci_selection.py')
    # Unknown/new CAD code and shared geometry inputs still fail open.
    if any(p.startswith('profiles/') or p in ('requirements.txt', 'brickcad/__init__.py') or
           (p.startswith(('brickcad/', 'parts/', 'experiments/')) and p.endswith('.py') and p not in known and not p.endswith('/__init__.py')) or
           (p.startswith('tests/') and p not in tests) for p in changed):
        return tests
    return [test for test in tests if test in adjacent_tests or graph[test].intersection(changed)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', help='PR base SHA; omit to run all tests')
    parser.add_argument('--plan', action='store_true', help='Select without importing CAD or running tests')
    args = parser.parse_args()
    os.chdir(ROOT)
    changed = None if not args.base else set(subprocess.check_output(
        ['git', 'diff', '--name-only', '-z', '--no-renames', args.base + '...HEAD'],
        text=True).split('\0')) - {''}
    selected = select(changed)
    print('Selected: ' + (', '.join(selected) or '(none)'), flush=True)
    if args.plan:
        if os.environ.get('GITHUB_OUTPUT'):
            with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
                output.write(f'has_tests={str(bool(selected)).lower()}\n')
        return
    sys.path.insert(0, str(ROOT))
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(
        p[:-3].replace('/', '.')) for p in selected)
    if not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful():
        raise SystemExit(1)


if __name__ == '__main__':
    main()
