"""Discover CAD build configs, select changed models, generate validated STL artifacts.

New models opt in through parts/<name>/cad-build.json or
experiments/<run>/cad-build.json. Planning does not import CadQuery.
"""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BUILD_ROOT = Path('build/cad-artifacts')
DELIVERY = Path('build/cad-delivery')


def path_under(base, path):
    if not isinstance(path, str) or not path or '\\' in path:
        raise ValueError(f'Invalid path: {path!r}')
    parts = PurePosixPath(path).parts
    if path.startswith('/') or any(p in ('.', '..') for p in parts):
        raise ValueError(f'Unsafe path: {path}')
    return base.joinpath(*parts)


def discover(root=ROOT):
    specs = {}
    for kind in ('parts', 'experiments'):
        for file in sorted((root / kind).glob('*/cad-build.json')):
            name = file.parent.relative_to(root).as_posix()
            spec = json.loads(file.read_text(encoding='utf-8'))
            command, outputs = spec.get('command'), spec.get('stl')
            if not isinstance(command, list) or not command or not all(isinstance(s, str) and s for s in command):
                raise ValueError(f'{file}: command must be nonempty argv')
            if not isinstance(outputs, list) or not outputs or not all(isinstance(s, str) for s in outputs):
                raise ValueError(f'{file}: stl must be nonempty list')
            if not isinstance(spec.get('requires', []), list) or not all(isinstance(s, str) for s in spec.get('requires', [])):
                raise ValueError(f'{file}: requires must be list')
            if not isinstance(spec.get('auto', True), bool):
                raise ValueError(f'{file}: auto must be boolean')
            for output in outputs:
                path_under(root, output)
                if not output.endswith('.stl'):
                    raise ValueError(f'{file}: expected .stl: {output}')
            specs[name] = spec
    for name, spec in specs.items():
        for req in spec.get('requires', []):
            if req not in specs or req == name:
                raise ValueError(f'{name}: invalid dependency {req}')
    ordered, visiting = [], set()
    def visit(name):
        if name in visiting:
            raise ValueError(f'CAD dependency cycle at {name}')
        if name in ordered:
            return
        visiting.add(name)
        for req in specs[name].get('requires', []):
            visit(req)
        visiting.remove(name)
        ordered.append(name)
    for name in specs:
        visit(name)
    return specs, ordered


def imports_for(file, root=ROOT, visited=None):
    visited = set() if visited is None else visited
    if file in visited or not (root / file).is_file():
        return visited
    visited.add(file)
    tree = ast.parse((root / file).read_text(encoding='utf-8'))
    package = file[:-3].replace('/', '.').split('.')[:-1]
    for node in ast.walk(tree):
        names = []
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            prefix = (node.module or '').split('.') if node.module else []
            if node.level:
                prefix = package[:max(0, len(package)-node.level+1)] + prefix
            names = ['.'.join(prefix)] + ['.'.join(prefix + [a.name]) for a in node.names]
        for name in names:
            if name.split('.')[0] in ('brickcad', 'parts', 'experiments'):
                candidate = name.replace('.', '/') + '.py'
                if (root / candidate).is_file():
                    imports_for(candidate, root, visited)
    return visited


def choose(specs, order, changed=None, targets='changed', root=ROOT):
    if targets not in ('changed', 'all'):
        requested = [s.strip() for s in targets.split(',') if s.strip()]
        missing = set(requested) - specs.keys()
        if missing:
            raise ValueError('Unknown CAD target(s): ' + ', '.join(sorted(missing)))
        selected = set(requested)
    elif targets == 'all':
        selected = {n for n, s in specs.items() if s.get('auto', True)}
    else:
        if changed is None:
            raise ValueError('Changed mode needs a base SHA; use --targets all manually')
        changed = set(changed)
        # Workflow/logging changes should run fast tests, not regenerate all models.
        # Only shared model/toolchain inputs invalidate every opted-in design.
        force_all = any(p == 'requirements.txt' or p.startswith(('brickcad/', 'profiles/'))
                        for p in changed)
        selected = set()
        for name, spec in specs.items():
            if not spec.get('auto', True):
                continue
            direct = any(p.startswith(name + '/') and not p.endswith('.stl')
                         and '/records/' not in p and not p.endswith('.md') for p in changed)
            imported = changed.intersection(imports_for(name + '/design.py', root))
            if force_all or direct or imported:
                selected.add(name)
        while True:
            more = {n for n, s in specs.items() if s.get('auto', True) and
                    set(s.get('requires', [])).intersection(selected)}
            if more <= selected:
                break
            selected |= more
    def include(name):
        for req in specs[name].get('requires', []):
            if req not in selected:
                selected.add(req)
                include(req)
    for name in list(selected):
        include(name)
    return [n for n in order if n in selected]


def changed_paths(base, root=ROOT):
    if not base or set(base) == {'0'}:
        # First push of a new branch has no previous branch commit.
        base = subprocess.check_output(
            ['git', 'merge-base', 'HEAD', 'origin/main'], cwd=root, text=True).strip()
    out = subprocess.check_output(
        ['git', 'diff', '--name-only', '-z', '--no-renames', f'{base}...HEAD'], cwd=root)
    return [p.decode('utf-8') for p in out.split(b'\0') if p]


def validate_stl(file):
    with file.open('rb') as src:
        header = src.read(84)
    size = file.stat().st_size
    if len(header) != 84 or size <= 84 or (size-84) % 50:
        raise ValueError(f'Invalid binary STL size: {file}')
    faces = struct.unpack_from('<I', header, 80)[0]
    if faces <= 0 or 84 + 50*faces != size:
        raise ValueError(f'Invalid triangle count: {file}')
    digest = hashlib.sha256()
    with file.open('rb') as src:
        for block in iter(lambda: src.read(1024*1024), b''):
            digest.update(block)
    return {'bytes': size, 'triangles': faces, 'sha256': digest.hexdigest()}


def build(specs, selected, previews=False, root=ROOT, build_root=BUILD_ROOT, delivery=DELIVERY):
    manifest = {'source_sha': os.environ.get('GITHUB_SHA'),
                'generated_utc': datetime.now(timezone.utc).isoformat(),
                'targets': selected, 'files': {}, 'physical_fit_validated': False,
                'slicing_validated': False, 'visual_review_performed': False}
    (root / delivery).mkdir(parents=True, exist_ok=True)
    for name in selected:
        spec = specs[name]
        out = path_under(root, (build_root / name).as_posix())
        preview_root = path_under(root, (build_root / 'previews' / name).as_posix())
        cmd = [arg.replace('{out}', str(out)).replace('{preview}', str(preview_root))
               for arg in spec['command']]
        print('CAD START', name, cmd, flush=True)
        subprocess.run([sys.executable, 'scripts/run-stage.py', '--name', name.replace('/', '-'),
                        '--timeout', str(spec.get('timeout', 1200)), '--', *cmd], check=True, cwd=root)
        for rel in spec['stl']:
            source = path_under(out, rel)
            report_file = source.parent / 'report.json'
            report = json.loads(report_file.read_text(encoding='utf-8'))
            if report.get('passed') is not True or report.get('mesh', {}).get('passed') is not True:
                raise ValueError(f'CAD verification failed: {source}')
            metadata = validate_stl(source)
            target = path_under(root / delivery / name, rel)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            shutil.copyfile(report_file, target.parent / 'report.json')
            metadata['report'] = str(Path(name) / Path(rel).parent / 'report.json')
            manifest['files'][str(Path(name) / rel)] = metadata
            if previews and (source.parent / 'viewer.html').exists():
                capture_dir = path_under(preview_root, Path(rel).parent.as_posix())
                subprocess.run([sys.executable, 'scripts/run-stage.py',
                                '--name', 'preview-' + name.replace('/', '-'),
                                '--timeout', '300', '--', 'node', 'scripts/cad-capture.cjs',
                                str(source.parent), str(capture_dir)], check=True, cwd=root)
                shutil.copytree(capture_dir, target.parent / 'previews', dirs_exist_ok=True)
        print('CAD VERIFIED', name, flush=True)
    (root / delivery / 'manifest.json').write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print('CAD ARTIFACTS', list(manifest['files']), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('plan', 'build'), required=True)
    parser.add_argument('--base', default='')
    parser.add_argument('--targets', default='changed')
    parser.add_argument('--previews', action='store_true')
    args = parser.parse_args()
    specs, order = discover()
    selected = choose(specs, order, changed_paths(args.base) if args.targets == 'changed' else None, args.targets)
    print('CAD selected:', ', '.join(selected) or '(none)', flush=True)
    if args.mode == 'plan':
        if os.getenv('GITHUB_OUTPUT'):
            with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
                output.write(f'has_models={str(bool(selected)).lower()}\n')
                output.write('targets=' + ','.join(selected) + '\n')
        return
    if not selected:
        raise ValueError('No CAD models selected')
    build(specs, selected, previews=args.previews)


if __name__ == '__main__':
    main()
