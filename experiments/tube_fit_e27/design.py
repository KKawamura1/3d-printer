"""E27: one-job 13.35–13.50 mm receiver-tube comparison, fixed top/cavity."""
from dataclasses import asdict
from pathlib import Path
import hashlib
import json
import cadquery as cq
from brickcad.model import brick_from_fit, build as build_brick
from brickcad.provenance import design_manifest
from brickcad.render import viewer
from brickcad.standards import ROUNDED_EDGES
from brickcad.verify import exact_bounds, fit_report
from experiments.full_height_fit.design import export_stl


def plan():
    return [dict(id=f'E27-{i+1:02}', condition=chr(65+i),
                 tube_diameter_mm=d, bed_center_xy_mm=[69+42*(i%2), 69+42*(i//2)],
                 rotation_deg=0)
            for i, d in enumerate((13.35, 13.40, 13.45, 13.50))]


def parameters(record):
    return brick_from_fit('duplo-xy-trial-v1', nx=2, ny=2,
                          tube_radius=record['tube_diameter_mm']/2)


def build(record):
    p = parameters(record)
    shape = build_brick(p, corner_radius=.8, stud_lip_radius=.5, entry=.3)
    # Run-qualified, font-independent seven-segment marks on the -Y wall.
    # z=9.1..13.9, above the complete insertion/contact zone.
    segments = dict(a=(0,2.1,1.9,.45), g=(0,0,1.9,.45), d=(0,-2.1,1.9,.45),
                    f=(-.75,1.05,.45,2.1), b=(.75,1.05,.45,2.1),
                    e=(-.75,-1.05,.45,2.1), c=(.75,-1.05,.45,2.1))
    glyphs = dict(zip('0123456789', ('abcdef','bc','abged','abgcd','fgbc',
                                   'afgcd','afgecd','abc','abcdefg','abfgcd')))
    glyphs.update(E='afged', **{'-':'g'})
    for index, char in enumerate(record['id']):
        for segment in glyphs[char]:
            x,z,w,h = segments[segment]
            tool = (cq.Workplane('XY').box(w,.5,h)
                    .translate((x+(index-2.5)*3.1, -p.depth/2, 11.5+z)).val())
            shape = shape.cut(tool)
    shape = shape.clean()
    assert shape.isValid() and len(shape.Solids()) == 1
    return p, shape


def generate(out):
    out = Path(out)
    if out.exists() and any(out.iterdir()):
        raise ValueError('Use an empty output directory')
    out.mkdir(parents=True, exist_ok=True)
    records = plan()
    placed = []
    for record in records:
        print('Generating', record['id'], flush=True)
        p, shape = build(record)
        folder = out/record['id']
        folder.mkdir()
        mesh = export_stl(shape, folder/'brick.stl')
        cq.exporters.export(shape, str(folder/'brick.step'))
        restored = cq.importers.importStep(str(folder/'brick.step')).val()
        assert restored.isValid() and len(restored.Solids()) == 1
        assert abs(restored.Volume()-shape.Volume()) < 1e-4
        manifest = design_manifest(p, finish=ROUNDED_EDGES)
        source = Path(__file__)
        manifest['source_files']['experiments/tube_fit_e27/design.py'] = hashlib.sha256(source.read_bytes()).hexdigest()
        report = dict(passed=True, physical_fit_validated=False, slicing_validated=False,
                      specimen=record, design=manifest,
                      geometry=dict(parameters=asdict(p), bounds_mm=exact_bounds(shape)),
                      fit=fit_report(p, shape), step_roundtrip_passed=True, **mesh)
        viewer(shape, p, report, folder)
        (folder/'report.json').write_text(json.dumps(report, indent=2)+'\n')
        x,y = record['bed_center_xy_mm']
        placed.append(shape.translate((x-90,y-90,0)))
    plate = cq.Compound.makeCompound(placed)
    assert plate.isValid() and len(plate.Solids()) == 4
    for i,a in enumerate(placed):
        for b in placed[i+1:]:
            assert a.intersect(b).Volume() < 1e-7
    mesh = export_stl(plate, out/'E27-plate.stl')
    report = dict(passed=True, physical_fit_validated=False, slicing_validated=False,
                  variants=records, bounds_mm=exact_bounds(plate), plate_mesh=mesh,
                  plate_translation_to_bed_xy_mm=[90,90], bed_size_mm=[180,180],
                  limitations=['One specimen per condition; bed-position effects are not isolated.',
                               'Rigid CAD intersections do not predict clutch force.',
                               'Inner wall must be checked in the actual slicer.'])
    (out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=Path('build/tube-fit-e27'))
    generate(parser.parse_args().out)
