"""Versioned CAD generator. Only version bumps of maintained parts build on push.
Experiments are always manual; dependencies refer to immutable historical versions.
"""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
VERSION = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]*$')


def git(root, *args):
    return subprocess.check_output(['git', *args], cwd=root, stderr=subprocess.DEVNULL)


def valid_path(text):
    if not isinstance(text, str) or not text or text.startswith('/') or '\\' in text:
        raise ValueError(f'Unsafe path: {text!r}')
    if any(p in ('..', '.') for p in PurePosixPath(text).parts):
        raise ValueError(f'Unsafe path: {text!r}')
    return text


def check(name, spec):
    if not isinstance(spec, dict) or not isinstance(spec.get('version'), str) or not VERSION.fullmatch(spec['version']):
        raise ValueError(f'{name}: version is required')
    if not isinstance(spec.get('command'), list) or not spec['command'] or not all(isinstance(x, str) for x in spec['command']):
        raise ValueError(f'{name}: command must be an argv list')
    if not isinstance(spec.get('stl'), list) or not spec['stl']:
        raise ValueError(f'{name}: missing STL outputs')
    for file in spec['stl']:
        if not valid_path(file).endswith('.stl'):
            raise ValueError(f'{name}: invalid STL path')
    if not isinstance(spec.get('requires', []), list):
        raise ValueError(f'{name}: requires must be a list')
    for dep in spec.get('requires', []):
        if not isinstance(dep, dict) or set(dep) != {'target', 'version'}:
            raise ValueError(f'{name}: dependency must pin target and version')
        target, revision = dep['target'], dep['version']
        if not isinstance(target, str) or not target.startswith(('parts/', 'experiments/')) or target == name:
            raise ValueError(f'{name}: invalid dependency target')
        if not isinstance(revision, str) or not VERSION.fullmatch(revision):
            raise ValueError(f'{name}: invalid dependency version')
    if not isinstance(spec.get('auto', name.startswith('parts/')), bool):
        raise ValueError(f'{name}: invalid auto flag')
    if name.startswith('experiments/') and spec.get('auto', False):
        raise ValueError(f'{name}: experiments must be manual')
    if not isinstance(spec.get('timeout', 1200), int) or spec.get('timeout', 1200) <= 0:
        raise ValueError(f'{name}: invalid timeout')
    return spec


def discover(root=ROOT):
    specs = {}
    for group in ('parts', 'experiments'):
        for file in sorted((root / group).glob('*/cad-build.json')):
            name = file.parent.relative_to(root).as_posix()
            specs[name] = check(name, json.loads(file.read_text()))
    return specs


def imports_for(file, root, seen=None):
    seen = set() if seen is None else seen
    if file in seen or not (root / file).exists():
        return seen
    seen.add(file)
    tree = ast.parse((root / file).read_text())
    package = file.removesuffix('.py').replace('/', '.').split('.')[:-1]
    for node in ast.walk(tree):
        names = []
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            prefix = node.module.split('.') if node.module else []
            if node.level:
                prefix = package[:max(0, len(package)-node.level+1)] + prefix
            names = ['.'.join(prefix)] + ['.'.join(prefix + [a.name]) for a in node.names]
        for item in names:
            if item.split('.')[0] in ('parts', 'experiments', 'brickcad'):
                candidate = item.replace('.', '/') + '.py'
                if (root / candidate).exists():
                    imports_for(candidate, root, seen)
    return seen


def prior_version(root, base, name):
    try:
        old = json.loads(git(root, 'show', f'{base}:{name}/cad-build.json'))
        return old.get('version')
    except subprocess.CalledProcessError:
        return None


def select(specs, target, *, changed=(), prior=None, root=None):
    if target == 'all':
        return sorted(n for n,s in specs.items() if s.get('auto', n.startswith('parts/')))
    if target != 'changed':
        requested = [x.strip() for x in target.split(',') if x.strip()]
        invalid = set(requested) - specs.keys()
        if invalid:
            raise ValueError(f'Unknown targets: {sorted(invalid)}')
        return requested
    if prior is None:
        raise ValueError('Incremental planning requires prior version map')
    changed = set(changed)
    selected, errors = [], []
    for name, spec in sorted(specs.items()):
        old = prior.get(name)
        bumped = old != spec['version']
        # A geometry source edit must be accompanied by a new revision.
        local_code = any(p.startswith(name + '/') and p.endswith('.py') and
                         not p.endswith('/test.py') and not p.endswith('/__init__.py')
                         for p in changed)
        imported = changed.intersection(imports_for(name + '/design.py', root) - {name + '/design.py'}) if root else set()
        config_changed = name + '/cad-build.json' in changed
        if old is not None and not bumped and (local_code or imported or config_changed):
            errors.append(f'{name}@{old}: design changed without version bump')
        if bumped and spec.get('auto', name.startswith('parts/')):
            selected.append(name)
    if errors:
        raise ValueError('Version bump required: ' + '; '.join(errors))
    return selected


def historical(root, name, version):
    path = f'{name}/cad-build.json'
    for sha in git(root, 'log', '--format=%H', 'HEAD', '--', path).decode().splitlines():
        try:
            spec = json.loads(git(root, 'show', f'{sha}:{path}'))
            if spec.get('version') != version:
                continue
            check(name, spec)
        except (ValueError, subprocess.CalledProcessError):
            continue
        checkout = (root / 'build/cad-history' / sha).resolve()
        if not (checkout / '.git').exists():
            checkout.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(['git', 'worktree', 'add', '--detach', str(checkout), sha],
                           cwd=root, check=True, stdout=subprocess.DEVNULL)
        return spec, checkout, sha
    raise ValueError(f'Cannot reproduce {name}@{version}: no versioned Git revision')


def resolve(root, specs, requested):
    ordered, active, done, pins = [], set(), set(), {}
    def visit(name, version):
        key = (name, version)
        if key in active:
            raise ValueError(f'Dependency cycle: {key}')
        if key in done:
            return
        if name in pins and pins[name] != version:
            raise ValueError(f'Conflicting versions of {name}: {pins[name]} and {version}')
        pins[name] = version
        if name in specs and specs[name]['version'] == version:
            spec, checkout, sha = specs[name], root, None
        else:
            spec, checkout, sha = historical(root, name, version)
        active.add(key)
        for dep in spec.get('requires', []):
            visit(dep['target'], dep['version'])
        active.remove(key)
        done.add(key)
        ordered.append((name, version, spec, checkout, sha))
    for name in requested:
        visit(name, specs[name]['version'])
    return ordered


def verify_stl(path):
    size = path.stat().st_size
    with path.open('rb') as src:
        header = src.read(84)
    if len(header) != 84 or size <= 84 or (size-84) % 50:
        raise ValueError(f'Invalid STL size: {path}')
    triangles = struct.unpack_from('<I', header, 80)[0]
    if not triangles or size != 84 + triangles * 50:
        raise ValueError(f'Invalid STL count: {path}')
    return {'bytes': size, 'triangles': triangles,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def build(root, specs, requested, previews=False):
    root = root.resolve()
    nodes = resolve(root, specs, requested)
    output = root / 'build/cad-delivery'
    deps = root / 'build/cad-artifacts/resolved'
    if deps.exists():
        shutil.rmtree(deps)
    deps.mkdir(parents=True)
    manifest = {'generated_utc': datetime.now(timezone.utc).isoformat(),
                'requested': requested, 'versions': {}, 'files': {},
                'physical_fit_validated': False, 'slicing_validated': False,
                'visual_review_performed': False}
    for name, version, spec, checkout, source_sha in nodes:
        out = (root / 'build/cad-artifacts' / name / version).resolve()
        out.mkdir(parents=True, exist_ok=True)
        cmd = [s.replace('{out}', str(out)).replace('{deps}', str(deps))
               for s in spec['command']]
        label = name.replace('/', '-') + '-' + version
        stamp = out / '.cad-version.json'
        cached = False
        if stamp.exists():
            try:
                identity = json.loads(stamp.read_text())
                cached = identity.get('version') == version and all(
                    (out / rel).exists() and
                    json.loads((out / rel).parent.joinpath('report.json').read_text()).get('passed') is True and
                    json.loads((out / rel).parent.joinpath('report.json').read_text()).get('mesh', {}).get('passed') is True and
                    verify_stl(out / rel)['sha256'] == identity['sha256'][rel]
                    for rel in spec['stl'])
            except (OSError, KeyError, ValueError, json.JSONDecodeError):
                cached = False
        # Only the affected model's tests; never replay unrelated models.
        if not cached and (checkout / name / 'test.py').exists():
            subprocess.run([sys.executable, str(root / 'scripts/run-stage.py'),
                            '--name', 'test-' + label, '--cwd', str(checkout),
                            '--timeout', '600', '--', sys.executable, '-m', 'unittest',
                            name.replace('/', '.') + '.test'], cwd=root, check=True)
        if not cached:
            subprocess.run([sys.executable, str(root / 'scripts/run-stage.py'), '--name', label,
                            '--cwd', str(checkout), '--timeout', str(spec.get('timeout', 1200)),
                            '--', *cmd], cwd=root, check=True)
        else:
            print('CAD CACHE HIT', name, version, flush=True)
        link = deps / name
        link.parent.mkdir(parents=True, exist_ok=True)
        if link.exists() or link.is_symlink():
            link.unlink()
        link.symlink_to(out, target_is_directory=True)
        manifest['versions'][name] = {'version': version, 'source_commit': source_sha,
                                      'cached': cached}
        for rel in spec['stl']:
            source = out / valid_path(rel)
            report = json.loads((source.parent / 'report.json').read_text())
            if report.get('passed') is not True or report.get('mesh', {}).get('passed') is not True:
                raise ValueError(f'CAD verification failed: {name}/{rel}')
            dst = output / name / version / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dst)
            shutil.copyfile(source.parent / 'report.json', dst.parent / 'report.json')
            key = str(Path(name) / version / rel)
            manifest['files'][key] = verify_stl(dst)
            if previews and (source.parent / 'viewer.html').exists():
                captured = root / 'build/cad-artifacts/previews' / name / version / Path(rel).parent
                subprocess.run([sys.executable, str(root / 'scripts/run-stage.py'),
                                '--name', 'preview-' + label, '--timeout', '300', '--',
                                'node', str(root / 'scripts/cad-capture.cjs'),
                                str(source.parent), str(captured)], cwd=root, check=True)
                shutil.copytree(captured, dst.parent / 'previews', dirs_exist_ok=True)
        if not cached:
            stamp.write_text(json.dumps({'version': version, 'sha256': {
                rel: verify_stl(out / rel)['sha256'] for rel in spec['stl']
            }}, indent=2) + chr(10))
    output.mkdir(parents=True, exist_ok=True)
    (output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + chr(10))
    print('CAD VERIFIED', ', '.join(manifest['files']), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=('plan', 'build'), required=True)
    parser.add_argument('--base', default='')
    parser.add_argument('--targets', default='changed')
    parser.add_argument('--previews', action='store_true')
    args = parser.parse_args()
    root = ROOT
    specs = discover(root)
    if args.targets == 'changed':
        base = args.base
        if not base or set(base) == {'0'}:
            base = git(root, 'merge-base', 'HEAD', 'origin/main').decode().strip()
        paths = git(root, 'diff', '--name-only', '-z', '--no-renames', base, 'HEAD')
        changed = [x.decode() for x in paths.split(bytes([0])) if x]
        prior = {name: prior_version(root, base, name) for name in specs}
        selected = select(specs, args.targets, changed=changed, prior=prior, root=root)
    else:
        selected = select(specs, args.targets)
    print('CAD selected:', ', '.join(selected) or '(none)', flush=True)
    if args.mode == 'plan':
        if os.getenv('GITHUB_OUTPUT'):
            with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
                output.write('has_models=' + str(bool(selected)).lower() + chr(10))
                output.write('targets=' + ','.join(selected) + chr(10))
        return
    if not selected:
        raise ValueError('No models selected')
    build(root, specs, selected, args.previews)


if __name__ == '__main__':
    main()
