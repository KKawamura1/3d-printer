"""Assemble PR-pinned Issue #37 geometry into separately selectable A1 mini plates.
Only XY translations and 90-degree rotations; geometry/labels are unchanged.
The 23 course categories map to 20 physical specimens (3 reversible candidates).
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import numpy as np

DTYPE = np.dtype([('normal', '<f4', (3,)), ('vertices', '<f4', (3, 3)), ('attr', '<u2')])
BED, GAP = 180.0, 4.0
START = (BED - (2 * 63.8 + 31.8 + 2 * GAP)) / 2
A, B = START, START + 63.8 + GAP
C = B + 63.8 + GAP
# Fixed, explicit locations; each plate is independently printable on A1 mini.
# Four large 4x4 shapes fit plate 3, with two rotated 2x4 along the right edge.
SLOTS = {
    'p1-big': (4, 4, 0),
    'p1-medium': (72, 4, 0),
    'p1-small-a': (4, 72, 0),
    'p1-small-b': (40, 72, 0),

    'p2-big-a': (4, 4, 0),
    'p2-big-b': (72, 4, 0),
    'p2-medium-a': (4, 72, 0),
    'p2-medium-b': (72, 72, 0),
    'p2-medium-c': (4, 108, 0),
    'p2-medium-d': (72, 108, 0),
    'p2-small-a': (140, 4, 0),
    'p2-small-b': (140, 40, 0),

    'p3-big-a': (4, 4, 0),
    'p3-big-b': (72, 4, 0),
    'p3-big-c': (4, 72, 0),
    'p3-big-d': (72, 72, 0),
    'p3-side-medium-a': (140, 4, 90),
    'p3-side-medium-b': (140, 72, 90),
    'p3-small-a': (4, 140, 0),
    'p3-small-b': (40, 140, 0),
}

def read_stl(path):
    raw = path.read_bytes()
    if len(raw) < 134 or (len(raw) - 84) % DTYPE.itemsize:
        raise ValueError(f'Invalid binary STL size: {path}')
    count = struct.unpack_from('<I', raw, 80)[0]
    if count < 1 or len(raw) != 84 + count * DTYPE.itemsize:
        raise ValueError(f'Invalid STL triangle count: {path}')
    mesh = np.frombuffer(raw, dtype=DTYPE, offset=84).copy()
    if not np.isfinite(mesh['vertices']).all() or not np.isfinite(mesh['normal']).all():
        raise ValueError(f'Nonfinite mesh: {path}')
    return mesh

def place(mesh, x, y, turn):
    mesh = mesh.copy()
    vertices = mesh['vertices']
    if turn == 90:
        old_x = vertices[..., 0].copy()
        vertices[..., 0] = -vertices[..., 1]
        vertices[..., 1] = old_x
        normals = mesh['normal']
        old_x = normals[..., 0].copy()
        normals[..., 0] = -normals[..., 1]
        normals[..., 1] = old_x
    elif turn != 0:
        raise ValueError('Only right-angle rotations are allowed')
    low = vertices.reshape(-1, 3).min(axis=0)
    vertices[..., 0] += x - float(low[0])
    vertices[..., 1] += y - float(low[1])
    vertices[..., 2] -= float(low[2])
    flat = vertices.reshape(-1, 3)
    return mesh, flat.min(axis=0).astype(float).tolist(), flat.max(axis=0).astype(float).tolist()

def check_rects(items):
    for it in items:
        lo, hi = it['bounds_min_mm'], it['bounds_max_mm']
        if min(lo[:2]) < 0.001 or max(hi[:2]) > BED - 0.001:
            raise ValueError(f'Outside A1 mini bed: {it["id"]}')
    for i, first in enumerate(items):
        for second in items[i + 1:]:
            la, ha = first['bounds_min_mm'], first['bounds_max_mm']
            lb, hb = second['bounds_min_mm'], second['bounds_max_mm']
            clear = (ha[0] + GAP - 0.001 <= lb[0] or hb[0] + GAP - 0.001 <= la[0]
                     or ha[1] + GAP - 0.001 <= lb[1] or hb[1] + GAP - 0.001 <= la[1])
            if not clear:
                raise ValueError(f'Model spacing violated: {first["id"]}, {second["id"]}')

def parse_plates(spec):
    if spec == 'all':
        return (1, 2, 3)
    if spec not in ('1', '2', '3'):
        raise ValueError('Select --plates 1, 2, 3, or all')
    return (int(spec),)


def assemble(manifest_path, source_root, out, plates=(1,)):
    manifest = json.loads(Path(manifest_path).read_text())
    if (manifest.get('schema'), manifest.get('bed_mm'), manifest.get('minimum_gap_mm')) != (2, BED, GAP):
        raise ValueError('Unknown plate specification')
    planned = manifest['items']
    expected_counts = {1: 4, 2: 8, 3: 8}
    if len(planned) != 20 or any(sum(i['plate'] == p for i in planned) != n for p, n in expected_counts.items()):
        raise ValueError('Expected 4+8+8 specimens over three plates')
    if len({x['id'] for x in planned}) != len(planned) or len({(x['plate'], x['slot']) for x in planned}) != len(planned):
        raise ValueError('Duplicate ID or plate slot')
    expected_categories = list(range(1, 22)) + [24, 25]
    categories = sorted(no for item in planned for no in item['issue37_no'])
    if categories != expected_categories or manifest.get('issue37_supported_numbers') != expected_categories:
        raise ValueError(f'Issue #37 category coverage not 23/23: {categories}')
    if any(x['slot'] not in SLOTS for x in planned):
        raise ValueError('Unknown plate slot')
    if set(plates) - {1, 2, 3} or not plates:
        raise ValueError('Unknown plate selection')
    items = [item for item in planned if item['plate'] in plates]

    validated = []
    for item in items:
        source = Path(source_root) / f'pr{item["pr"]}' / item['path']
        if not source.is_file():
            raise FileNotFoundError(f'No source STL: {source}')
        if not item.get('repository_stl'):
            report_path = source.with_name('report.json')
            if not report_path.is_file():
                raise FileNotFoundError(f'No CAD report: {report_path}')
            report = json.loads(report_path.read_text())
            if report.get('passed') is not True or report.get('mesh', {}).get('passed') is not True:
                raise ValueError(f'CAD validation failed: {item["id"]}')
        elif not item.get('legacy_unverified_e31'):
            raise ValueError(f'Repository STL requires explicit legacy flag: {item["id"]}')
        sha = hashlib.sha256(source.read_bytes()).hexdigest()
        if not item.get('head_sha') or len(item['head_sha']) != 40:
            raise ValueError(f'Unpinned source revision: {item["id"]}')
        if item.get('sha256') and sha != item['sha256']:
            raise ValueError(f'Incorrect pinned source STL for {item["id"]}: {sha}')
        if not (item.get('rebuild_from_source') or item.get('repository_stl')) and not (item.get('run') and item.get('artifact')):
            raise ValueError(f'Artifact reference missing: {item["id"]}')
        mesh = read_stl(source)
        x, y, turn = SLOTS[item['slot']]
        moved, lo, hi = place(mesh, x, y, turn)
        metadata = {'id': item['id'], 'pr': item['pr'], 'rotation_deg': turn,
                    'source_sha256': sha, 'bounds_min_mm': lo, 'bounds_max_mm': hi,
                    'triangles': len(mesh)}
        validated.append((item, source, moved, metadata))
    for plate in plates:
        check_rects([meta for item, _, _, meta in validated if item['plate'] == plate])

    out = Path(out)
    (out / 'individual').mkdir(parents=True, exist_ok=True)
    for item, source, _, _ in validated:
        shutil.copyfile(source, out / 'individual' / f'{item["id"]}.stl')
    resolved_sources = [{**item, 'sha256': meta['source_sha256']}
                        for item, _, _, meta in validated]
    release = {'bed_mm': BED, 'minimum_gap_mm': GAP,
               'planned_categories': manifest['issue37_supported_numbers'],
               'planned_specimens': len(planned), 'selected_plates': list(plates),
               'printed_categories': sorted(no for item in items for no in item['issue37_no']),
               'reverse_direction_unverified': manifest['reverse_direction_unverified'],
               'legacy_unverified_e31_ids': [x['id'] for x in items if x.get('legacy_unverified_e31')],
               'slicing_validated': False, 'physical_fit_validated': False,
               'source_manifest': resolved_sources, 'plates': {}}
    for plate in plates:
        chosen = [(item, moved, meta) for item, _, moved, meta in validated if item['plate'] == plate]
        filename = f'issue37-plate-{plate:02d}-{len(chosen)}parts.stl'
        count = sum(len(mesh) for _, mesh, _ in chosen)
        header = f'Issue37 plate {plate}, {len(chosen)} independent solids'.encode().ljust(80, b'\0')
        destination = out / filename
        with destination.open('wb') as f:
            f.write(header)
            f.write(struct.pack('<I', count))
            for _, mesh, _ in chosen:
                f.write(mesh.tobytes())
        if len(read_stl(destination)) != count:
            raise ValueError('Combined STL integrity failed')
        digest = hashlib.sha256(destination.read_bytes()).hexdigest()
        release['plates'][str(plate)] = {'file': filename, 'sha256': digest,
                                        'triangles': count, 'items': [meta for _, _, meta in chosen]}
        print(f'{filename}: {len(chosen)} items, {count} triangles, SHA256 {digest}', flush=True)
    (out / 'manifest.json').write_text(json.dumps(release, indent=2, ensure_ascii=False) + '\n')
    return release

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--manifest', type=Path, default=Path(__file__).with_name('sources.json'))
    p.add_argument('--sources', type=Path, default=Path('build/issue37-sources'))
    p.add_argument('--out', type=Path, default=Path('build/issue37-print-plates'))
    p.add_argument('--plates', choices=['1', '2', '3', 'all'], default='1')
    args = p.parse_args()
    assemble(args.manifest, args.sources, args.out, plates=parse_plates(args.plates))

if __name__ == '__main__':
    main()
