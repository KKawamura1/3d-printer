"""S03-V5: mirror unmarked S02-V11 geometry, then engrave readable left ID.

CAD geometry, roof, E31-05 receiver, floor, ramp and circular openings are
fully shared with the right variant. The only transform is reflection in XZ.
"""
from dataclasses import asdict
from pathlib import Path
import hashlib
import json
import math

import cadquery as cq

from brickcad.ports import Port
from brickcad.standards import BALL_TRACK, DUPLO
from brickcad.verify import VOLUME_TOL, exact_bounds, intersection, mesh_check
from parts.steep_drop_hole.design import SteepDrop
from parts.steep_sharp_curve_tunnel import design as right

PART_ID = "S03-V5"
SOURCE_RIGHT_ID = right.PART_ID
SOURCE_DROP_ID = right.SOURCE_DROP_ID
SHAFT_X = right.SHAFT_X


def ports(d=SteepDrop(shaft_x=SHAFT_X)):
    high, _ = right.ports(d)
    return (
        high,
        Port("low_north", (0., 16., d.low_floor),
             (0., 1., 0.), d.section_radius),
    )


def _south_engraving_tool(label, width):
    # South-facing normal is -Y. The X direction must be +X when viewed
    # from outside: otherwise the part ID would read backwards.
    plane = cq.Plane(origin=(0., -width / 2 + .4, 18.),
                     xDir=(1, 0, 0), normal=(0, -1, 0))
    return cq.Workplane(plane).text(
        label, 3.0, .45, font="DejaVu Sans",
        kind="bold", combine=False).val()


def build_tunnel(d=SteepDrop(shaft_x=SHAFT_X), *, label=PART_ID):
    bare_right, p = right.build_tunnel(d, label=None)
    bare_left = bare_right.mirror("XZ")
    if not bare_left.isValid() or len(bare_left.Solids()) != 1:
        raise ValueError("Mirrored left geometry must be one valid solid")
    cutter = _south_engraving_tool(label, p.depth)
    left = bare_left.cut(cutter).clean()
    if not left.isValid() or len(left.Solids()) != 1:
        raise ValueError("Left engraving invalidated the mirrored body")
    removed = bare_left.Volume() - left.Volume()
    if removed < .2:
        raise ValueError("Left engraving is not recessed in the south face")
    return left, p


def _path_centres(d):
    return tuple(cq.Vector(p.x, -p.y, p.z)
                 for p in right._path_centres(d))


def ball_path_collisions(shape, d=SteepDrop(shaft_x=SHAFT_X)):
    radius = BALL_TRACK.ball_diameter / 2.
    centres = []
    path = _path_centres(d)
    for a, b in zip(path, path[1:]):
        for i in range(6):
            centres.append(a.add(b.sub(a).multiply(i / 5.)))
    return [intersection(shape, cq.Solid.makeSphere(
        radius, p, angleDegrees1=-90)) for p in centres]


def swept_ball_path_collisions(shape, d=SteepDrop(shaft_x=SHAFT_X)):
    radius = BALL_TRACK.ball_diameter / 2.
    path = _path_centres(d)
    volumes = []
    for a, b in zip(path, path[1:]):
        v = b.sub(a)
        volumes.append(intersection(shape, cq.Solid.makeCylinder(
            radius, v.Length, a, v.normalized())))
        volumes.append(intersection(shape, cq.Solid.makeSphere(
            radius, a, angleDegrees1=-90)))
    volumes.append(intersection(shape, cq.Solid.makeSphere(
        radius, path[-1], angleDegrees1=-90)))
    return volumes


def circular_mouth_checks(shape, d):
    # Reuse the right version's 16-direction verification after reflecting
    # left back to right. No duplicate opening geometry to maintain.
    return right.circular_mouth_checks(shape.mirror("XZ"), d)


def export(out=Path("build/steep-sharp-tunnel-left")):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    d = SteepDrop(shaft_x=SHAFT_X)
    shape, p = build_tunnel(d)
    stl = out / "brick.stl"
    cq.exporters.export(shape, str(stl), tolerance=.01, angularTolerance=.1)
    removed_facets = right._remove_collapsed_triangles(stl)
    mesh = mesh_check(stl)
    samples = ball_path_collisions(shape, d)
    sweeps = swept_ball_path_collisions(shape, d)
    bounds = exact_bounds(shape)
    blank_right, _ = right.build_tunnel(d, label=None)
    blank_left = blank_right.mirror("XZ")
    engraving_removed = blank_left.Volume() - shape.Volume()
    checks = dict(
        single_valid_solid=shape.isValid() and len(shape.Solids()) == 1,
        bounds_2x2x3=all(abs(a - b) < .01
                           for a, b in zip(bounds, (31.8, 31.8, 62.1))),
        watertight_mesh=mesh["passed"],
        ball_samples_clear=max(samples) < VOLUME_TOL,
        ball_sweep_clear=max(sweeps) < VOLUME_TOL,
        left_exit_north=ports(d)[1].outward == (0., 1., 0.),
        low_west_wall_closed=shape.isInside(
            cq.Vector(-15.7, 0., d.low_centre_z)),
        roof_present=shape.isInside(cq.Vector(0., 0., p.height - .1)),
        receiver_bore_open=not shape.isInside(cq.Vector(0., 0., 1.)),
        receiver_wall_present=shape.isInside(cq.Vector(3.89, 3.89, 1.)),
        four_upper_studs=all(shape.isInside(
            cq.Vector(x + 3.9, y, p.height + 1.))
            for x, y in p.studs()),
        gentle_ramp=abs(d.ramp_grade - .25) < 1e-8,
        left_south_engraving=engraving_removed > .2,
        mirrored_blank_has_same_volume=abs(
            blank_right.Volume() - blank_left.Volume()) < 1e-3,
    )
    checks.update(circular_mouth_checks(shape, d))
    report = dict(
        part_id=PART_ID, sources=[SOURCE_RIGHT_ID, SOURCE_DROP_ID],
        passed=all(checks.values()), checks=checks,
        description="2x2x3 roofed left-turn, S02 unmarked mirror then S03 engraving",
        parameters=asdict(d), bounds_mm=bounds,
        ports=[asdict(port) for port in ports(d)],
        mirror=dict(source=SOURCE_RIGHT_ID, plane="XZ",
                    order="mirror-unmarked-geometry-then-engrave",
                    label=PART_ID, text_size_mm=3.0),
        mesh=mesh, collapsed_facets_removed=removed_facets,
        engraved_volume_removed_mm3=engraving_removed,
        ball_samples_mm3=samples, ball_sweep_mm3=sweeps,
        sha256_stl=hashlib.sha256(stl.read_bytes()).hexdigest(),
        physical_rolling_validated=False,
        support_free_slicing_validated=False,
        physical_fit_validated=False,
        limitations=[
            "Mirrored CAD volume and sphere clearance do not guarantee natural rolling.",
            "South text is engraved after mirroring to avoid mirrored glyphs.",
            "Real print must confirm text legibility, mouth finish and connections.",
        ])
    (out / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    cq.exporters.export(shape, str(out / "brick.step"))
    print(PART_ID, "PASS" if report["passed"] else "FAIL", checks, flush=True)
    if not report["passed"]:
        raise RuntimeError("S03 mirrored CAD verification failed")
    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path,
                        default=Path("build/steep-sharp-tunnel-left"))
    export(parser.parse_args().out)
