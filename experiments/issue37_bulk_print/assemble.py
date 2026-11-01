"""Assemble 13 SHA-pinned, CAD-verified STL files into two A1 mini plates.
Only XY translations and 90-degree rotations; geometry/labels are unchanged.
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
SLOTS = {
    # Plate 01 prioritizes high-risk tunnel designs.  Two 4x4, two 2x4,
    # four 2x2 tunnel parts, plus one complex open sloped curve as control.
    'big-00': (A, A, 0), 'big-10': (B, A, 0),
    'big-01': (A, B, 0),
    'medium-right-0': (C, A, 90), 'medium-right-1': (B, B, 90),
    'small-bottom-0': (A, C, 0),
    'small-bottom-1': (A + 31.8 + GAP, C, 0),
    'small-bottom-2': (A + 2 * (31.8 + GAP), C, 0),
    'small-bottom-3': (A + 3 * (31.8 + GAP), C, 0),
    # Plate 02 contains the simpler, mostly dominated open-track variants.
    'p2-big': (8, 8, 0),
    'p2-medium-0': (78, 8, 0),
    'p2-medium-1': (78, 45, 0),
    'p2-medium-2': (8, 78, 0)
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

def assemble(manifest_path, source_root, out):
    manifest = json.loads(Path(manifest_path).read_text())
    if (manifest.get('schema'), manifest.get('bed_mm'), manifest.get('minimum_gap_mm')) != (1, BED, GAP):
        raise ValueError('Unknown plate specification')
    items = manifest['items']
    if len(items) != 13 or {x['plate'] for x in items} != {1, 2}:
        raise ValueError('Expected 13 specimens in two explicit plates')
    if len({x['id'] for x in items}) != 13 or len({x['slot'] for x in items}) != 13:
        raise ValueError('Duplicate ID or plate slot')
    validated = []
    for item in items:
        source = Path(source_root) / f'pr{item["pr"]}' / item['path']
        report_path = source.with_name('report.json')
        if not source.is_file() or not report_path.is_file():
            raise FileNotFoundError(f'No source STL or CAD report: {source}')
        report = json.loads(report_path.read_text())
        if report.get('passed') is not True or report.get('mesh', {}).get('passed') is not True:
            raise ValueError(f'CAD validation failed: {item["id"]}')
        sha = hashlib.sha256(source.read_bytes()).hexdigest()
        if sha != item['sha256']:
            raise ValueError(f'Incorrect source STL for {item["id"]}: {sha}')
        mesh = read_stl(source)
        x, y, turn = SLOTS[item['slot']]
        moved, lo, hi = place(mesh, x, y, turn)
        metadata = {'id': item['id'], 'pr': item['pr'], 'rotation_deg': turn,
                    'source_sha256': sha, 'bounds_min_mm': lo, 'bounds_max_mm': hi,
                    'triangles': len(mesh)}
        validated.append((item, source, moved, metadata))
    for plate in (1, 2):
        check_rects([meta for item, _, _, meta in validated if item['plate'] == plate])

    out = Path(out)
    (out / 'individual').mkdir(parents=True, exist_ok=True)
    for item, source, _, _ in validated:
        shutil.copyfile(source, out / 'individual' / f'{item["id"]}.stl')
    release = {'bed_mm': BED, 'minimum_gap_mm': GAP, 'slicing_validated': False,
               'physical_fit_validated': False, 'source_manifest': items, 'plates': {}}
    for plate in (1, 2):
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
    args = p.parse_args()
    assemble(args.manifest, args.sources, args.out)

if __name__ == '__main__':
    main()
